#include <drogon/drogon.h>
#include <librdkafka/rdkafkacpp.h>
#include <libpq-fe.h>
#include <random>
#include <sstream>
#include <iomanip>
#include <atomic>
#include <csignal>
#include <memory>
#include <mutex>
#include <thread>

#include <spdlog/spdlog.h>

#include "telemetry.hpp"

using namespace drogon;

std::atomic<bool> g_shutdown{false};
PGconn* g_pg_conn = nullptr;
std::mutex g_pg_mu;
std::unique_ptr<RdKafka::Producer> g_producer;
std::atomic<bool> g_producer_running{false};
std::thread g_poller;

// Delivery reports arrive on the poller thread; the broker's ack (or failure) is logged here.
class DeliveryLog : public RdKafka::DeliveryReportCb {
public:
    void dr_cb(RdKafka::Message& message) override {
        if (message.err() != RdKafka::ERR_NO_ERROR) {
            LOG_ERROR << "Kafka send failed: " << message.errstr();
        } else {
            LOG_INFO << "Event published to partition " << message.partition()
                     << " offset " << message.offset();
        }
    }
};
DeliveryLog g_dr_cb;

void signal_handler(int) { g_shutdown = true; }

std::string generate_uuid() {
    std::random_device rd;
    std::mt19937_64 gen(rd());
    std::uniform_int_distribution<uint64_t> dis;

    std::ostringstream oss;
    oss << std::hex << std::setfill('0');

    uint64_t part1 = dis(gen);
    uint64_t part2 = dis(gen);

    oss << std::setw(8) << (part1 & 0xFFFFFFFF) << "-";
    oss << std::setw(4) << ((part1 >> 32) & 0xFFFF) << "-";
    oss << std::setw(4) << (0x4000 | ((part1 >> 48) & 0x0FFF)) << "-";
    oss << std::setw(4) << (0x8000 | ((part2 >> 48) & 0x3FFF)) << "-";
    oss << std::setw(12) << (part2 & 0xFFFFFFFFFFFF);

    return oss.str();
}

std::string json_escape(const std::string& s) {
    std::ostringstream oss;
    for (char c : s) {
        if (c == '"' || c == '\\') oss << '\\';
        oss << c;
    }
    return oss.str();
}

void init_pg() {
    const char* conninfo = std::getenv("PG_CONNINFO");
    if (!conninfo) conninfo = "postgresql://appuser:apppass@postgres:5432/appdb";

    g_pg_conn = PQconnectdb(conninfo);
    if (PQstatus(g_pg_conn) != CONNECTION_OK) {
        LOG_ERROR << "Postgres connection failed: " << PQerrorMessage(g_pg_conn);
        PQfinish(g_pg_conn);
        g_pg_conn = nullptr;
        throw std::runtime_error("Postgres connection failed");
    }
    LOG_INFO << "Connected to Postgres";
}

void init_kafka() {
    const char* bootstrap = std::getenv("KAFKA_BOOTSTRAP");
    if (!bootstrap) bootstrap = "kafka:9094";

    std::string errstr;
    std::unique_ptr<RdKafka::Conf> conf(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));
    if (conf->set("bootstrap.servers", bootstrap, errstr) != RdKafka::Conf::CONF_OK ||
        conf->set("client.id", "order-service", errstr) != RdKafka::Conf::CONF_OK ||
        conf->set("acks", "all", errstr) != RdKafka::Conf::CONF_OK ||
        conf->set("dr_cb", &g_dr_cb, errstr) != RdKafka::Conf::CONF_OK) {
        throw std::runtime_error("Kafka config: " + errstr);
    }

    g_producer.reset(RdKafka::Producer::create(conf.get(), errstr));
    if (!g_producer) throw std::runtime_error("Kafka producer: " + errstr);

    // produce() only enqueues; this thread serves delivery reports.
    g_producer_running = true;
    g_poller = std::thread([] {
        while (g_producer_running) g_producer->poll(100);
    });
    LOG_INFO << "Kafka producer initialized";
}

int main() {
    std::signal(SIGTERM, signal_handler);
    std::signal(SIGINT, signal_handler);

    {
        const char* svc = std::getenv("OTEL_SERVICE_NAME");
        cndp::telemetry::init(svc ? svc : "order-service");
    }

    try {
        init_pg();
        init_kafka();
    } catch (const std::exception& e) {
        LOG_ERROR << "Initialization failed: " << e.what();
        return 1;
    }

    app().setLogLevel(trantor::Logger::kInfo);
    app().addListener("0.0.0.0", 8080);
    app().setUploadPath("/tmp");

    // Health endpoint
    app().registerHandler("/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value health;
            health["status"] = "ok";
            auto resp = HttpResponse::newHttpJsonResponse(health);
            callback(resp);
        },
        {Get});

    // POST /orders
    app().registerHandler("/orders",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            try {
                auto tracer = cndp::telemetry::tracer("order-service");
                opentelemetry::trace::StartSpanOptions server_opts;
                server_opts.kind = opentelemetry::trace::SpanKind::kServer;
                cndp::telemetry::SpanPtr root = tracer->StartSpan(
                    "POST /orders", {{"http.request.method", "POST"}, {"url.path", "/orders"}},
                    server_opts);
                // Every return below ends the request span.
                struct SpanGuard {
                    cndp::telemetry::SpanPtr& s;
                    ~SpanGuard() { s->End(); }
                } root_guard{root};

                auto json = req->getJsonObject();
                if (!json || !json->isMember("sku") || !json->isMember("quantity")) {
                    auto resp = HttpResponse::newHttpResponse();
                    resp->setStatusCode(k400BadRequest);
                    resp->setBody("{\"error\":\"sku and quantity required\"}");
                    callback(resp);
                    return;
                }

                std::string sku = (*json)["sku"].asString();
                int quantity = (*json)["quantity"].asInt();
                std::string order_id = generate_uuid();
                std::string status = "pending";

                // Insert into DB
                std::string quantity_s = std::to_string(quantity);
                const char* params[4] = {order_id.c_str(), sku.c_str(),
                                         quantity_s.c_str(), status.c_str()};
                std::unique_lock<std::mutex> pg_lock(g_pg_mu);
                PGresult* res = PQexecParams(g_pg_conn,
                    "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4)",
                    4, nullptr, params, nullptr, nullptr, 0);

                if (PQresultStatus(res) != PGRES_COMMAND_OK) {
                    LOG_ERROR << "Insert failed: " << PQerrorMessage(g_pg_conn);
                    PQclear(res);
                    auto resp = HttpResponse::newHttpResponse();
                    resp->setStatusCode(k500InternalServerError);
                    callback(resp);
                    return;
                }
                PQclear(res);
                pg_lock.unlock();

                // Publish to Kafka: producer span, its context travels as a traceparent header.
                opentelemetry::trace::StartSpanOptions producer_opts;
                producer_opts.kind = opentelemetry::trace::SpanKind::kProducer;
                producer_opts.parent = root->GetContext();
                cndp::telemetry::SpanPtr pub = tracer->StartSpan(
                    "order.placed publish",
                    {{"messaging.system", "kafka"}, {"messaging.destination.name", "order.placed"}},
                    producer_opts);
                std::ostringstream event;
                event << "{\"id\":\"" << json_escape(order_id) << "\","
                      << "\"sku\":\"" << json_escape(sku) << "\","
                      << "\"quantity\":" << quantity << ","
                      << "\"status\":\"" << json_escape(status) << "\"}";

                std::string event_str = event.str();
                // Enqueue; the delivery report callback logs the outcome.
                RdKafka::Headers* headers = RdKafka::Headers::create();
                headers->add("traceparent", cndp::telemetry::traceparent_of(pub));
                RdKafka::ErrorCode perr = g_producer->produce(
                    "order.placed", RdKafka::Topic::PARTITION_UA, RdKafka::Producer::RK_MSG_COPY,
                    event_str.data(), event_str.size(), nullptr, 0, 0, headers, nullptr);
                if (perr != RdKafka::ERR_NO_ERROR) {
                    delete headers;  // librdkafka owns the headers only when produce() succeeds
                    pub->SetStatus(opentelemetry::trace::StatusCode::kError, "produce failed");
                    pub->End();
                    spdlog::error("Kafka send failed: {}", RdKafka::err2str(perr));
                    // The event was not even queued: do not report the order as placed.
                    Json::Value err;
                    err["error"] = "event not published";
                    auto resp = HttpResponse::newHttpJsonResponse(err);
                    resp->setStatusCode(k503ServiceUnavailable);
                    callback(resp);
                    return;
                }

                pub->End();
                root->SetAttribute("order.id", order_id);
                spdlog::info("order placed id={} sku={} trace_id={}", order_id, sku,
                             cndp::telemetry::trace_id_of(root));

                // Return response
                Json::Value resp_json;
                resp_json["id"] = order_id;
                resp_json["sku"] = sku;
                resp_json["quantity"] = quantity;
                resp_json["status"] = status;

                auto resp = HttpResponse::newHttpJsonResponse(resp_json);
                resp->setStatusCode(k201Created);
                callback(resp);

            } catch (const std::exception& e) {
                LOG_ERROR << "Exception in POST /orders: " << e.what();
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k500InternalServerError);
                callback(resp);
            }
        },
        {Post});

    // GET /orders
    app().registerHandler("/orders",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            std::lock_guard<std::mutex> pg_lock(g_pg_mu);
            PGresult* res = PQexec(g_pg_conn, "SELECT id, sku, quantity, status FROM orders");

            if (PQresultStatus(res) != PGRES_TUPLES_OK) {
                LOG_ERROR << "Query failed: " << PQerrorMessage(g_pg_conn);
                PQclear(res);
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k500InternalServerError);
                callback(resp);
                return;
            }

            Json::Value orders(Json::arrayValue);
            int rows = PQntuples(res);
            for (int i = 0; i < rows; ++i) {
                Json::Value order;
                order["id"] = PQgetvalue(res, i, 0);
                order["sku"] = PQgetvalue(res, i, 1);
                order["quantity"] = std::stoi(PQgetvalue(res, i, 2));
                order["status"] = PQgetvalue(res, i, 3);
                orders.append(order);
            }
            PQclear(res);

            auto resp = HttpResponse::newHttpJsonResponse(orders);
            callback(resp);
        },
        {Get});

    app().run();

    // Drain pending messages (delivery reports still fire), then stop the poller.
    if (g_producer) g_producer->flush(10000);
    g_producer_running = false;
    if (g_poller.joinable()) g_poller.join();
    g_producer.reset();
    if (g_pg_conn) PQfinish(g_pg_conn);
    cndp::telemetry::shutdown();
    return 0;
}
