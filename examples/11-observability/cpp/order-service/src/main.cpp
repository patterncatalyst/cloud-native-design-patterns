// order-service: REST -> gRPC (inventory) -> Postgres -> Kafka, with traces, metrics and
// correlated logs through OpenTelemetry C++ and spdlog.

#include <atomic>
#include <future>
#include <chrono>
#include <csignal>
#include <iomanip>
#include <memory>
#include <mutex>
#include <random>
#include <sstream>
#include <string>
#include <thread>

#include <drogon/drogon.h>
#include <grpcpp/grpcpp.h>
#include <inventory.grpc.pb.h>
#include <libpq-fe.h>
#include <librdkafka/rdkafkacpp.h>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/spdlog.h>

#include "opentelemetry/metrics/provider.h"

#include "telemetry.hpp"

using namespace drogon;

namespace {

PGconn* g_pg = nullptr;
std::mutex g_pg_mu;
std::unique_ptr<RdKafka::Producer> g_producer;
std::thread g_poller;
std::atomic<bool> g_polling{false};
std::shared_ptr<grpc::Channel> g_grpc_channel;
std::unique_ptr<inventory::InventoryService::Stub> g_inventory_stub;
opentelemetry::nostd::unique_ptr<opentelemetry::metrics::Counter<uint64_t>> g_orders_placed;

std::string generate_uuid() {
    std::random_device rd;
    std::mt19937_64 gen(rd());
    std::uniform_int_distribution<uint64_t> dis;
    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    uint64_t p1 = dis(gen), p2 = dis(gen);
    oss << std::setw(8) << (p1 & 0xFFFFFFFF) << "-"
        << std::setw(4) << ((p1 >> 32) & 0xFFFF) << "-"
        << std::setw(4) << (0x4000 | ((p1 >> 48) & 0x0FFF)) << "-"
        << std::setw(4) << (0x8000 | ((p2 >> 48) & 0x3FFF)) << "-"
        << std::setw(12) << (p2 & 0xFFFFFFFFFFFF);
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

// Per-message state carried as the message opaque: the delivery report completes the promise
// the request is waiting on (empty string = delivered, otherwise the error).
struct Pending {
    std::promise<std::string> result;
};

class DeliveryLog : public RdKafka::DeliveryReportCb {
public:
    void dr_cb(RdKafka::Message& m) override {
        std::unique_ptr<Pending> pending(static_cast<Pending*>(m.msg_opaque()));
        if (m.err() != RdKafka::ERR_NO_ERROR)
            spdlog::error("order.placed delivery failed: {}", m.errstr());
        if (pending) pending->result.set_value(m.err() == RdKafka::ERR_NO_ERROR ? std::string() : m.errstr());
    }
};
DeliveryLog g_dr;

bool init_kafka(const std::string& bootstrap) {
    std::string err;
    std::unique_ptr<RdKafka::Conf> conf(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));
    if (conf->set("bootstrap.servers", bootstrap, err) != RdKafka::Conf::CONF_OK ||
        conf->set("client.id", "order-service", err) != RdKafka::Conf::CONF_OK ||
        conf->set("linger.ms", "5", err) != RdKafka::Conf::CONF_OK ||
        conf->set("acks", "all", err) != RdKafka::Conf::CONF_OK ||
        conf->set("message.timeout.ms", "10000", err) != RdKafka::Conf::CONF_OK ||
        conf->set("enable.idempotence", "true", err) != RdKafka::Conf::CONF_OK ||
        conf->set("dr_cb", &g_dr, err) != RdKafka::Conf::CONF_OK) {
        spdlog::error("Kafka producer config failed: {}", err);
        return false;
    }
    g_producer.reset(RdKafka::Producer::create(conf.get(), err));
    if (!g_producer) {
        spdlog::error("Kafka producer init failed: {}", err);
        return false;
    }
    g_polling.store(true);
    g_poller = std::thread([] {
        while (g_polling.load()) g_producer->poll(100);  // serves delivery reports
    });
    return true;
}

// Publishes the event with a W3C traceparent header so the consumer continues the trace, and
// waits for the broker's delivery report (message.timeout.ms bounds the wait). Returns true
// only when the event was acknowledged.
bool publish(const std::string& event, const std::string& traceparent) {
    for (int attempt = 0; attempt < 50; ++attempt) {
        RdKafka::Headers* headers = RdKafka::Headers::create();
        headers->add("traceparent", traceparent);
        auto* pending = new Pending;
        auto delivered = pending->result.get_future();
        auto rc = g_producer->produce("order.placed", RdKafka::Topic::PARTITION_UA,
                                      RdKafka::Producer::RK_MSG_COPY,
                                      const_cast<char*>(event.data()), event.size(),
                                      nullptr, 0, 0, headers, pending);
        if (rc == RdKafka::ERR_NO_ERROR) {  // librdkafka owns the headers and the opaque now
            return delivered.get().empty();
        }
        delete headers;
        delete pending;
        if (rc == RdKafka::ERR__QUEUE_FULL) {
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
            continue;
        }
        spdlog::error("Kafka send failed: {}", RdKafka::err2str(rc));
        return false;
    }
    spdlog::error("Kafka send failed: producer queue full");
    return false;
}

}  // namespace

int main() {
    auto logger = spdlog::stderr_color_mt("order-service");
    spdlog::set_default_logger(logger);
    spdlog::set_pattern("%Y-%m-%dT%H:%M:%S.%e [%l] %v");

    const char* env = std::getenv("PG_CONNINFO");
    g_pg = PQconnectdb(env ? env : "postgresql://appuser:apppass@postgres:5432/appdb");
    if (PQstatus(g_pg) != CONNECTION_OK) {
        spdlog::error("Postgres failed: {}", PQerrorMessage(g_pg));
        return 1;
    }

    env = std::getenv("KAFKA_BOOTSTRAP");
    if (!init_kafka(env ? env : "kafka:9094")) return 1;

    env = std::getenv("INVENTORY_ADDR");
    g_grpc_channel = grpc::CreateChannel(env ? env : "inventory:50051",
                                         grpc::InsecureChannelCredentials());
    g_inventory_stub = inventory::InventoryService::NewStub(g_grpc_channel);

    cndp::telemetry::init("order-service");
    g_orders_placed = opentelemetry::metrics::Provider::GetMeterProvider()
                          ->GetMeter("order-service")
                          ->CreateUInt64Counter("orders.placed", "Orders placed", "{order}");

    app().setLogLevel(trantor::Logger::kInfo);
    app().addListener("0.0.0.0", 8080);
    app().setUploadPath("/tmp");

    app().registerHandler("/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value r;
            r["status"] = "ok";
            callback(HttpResponse::newHttpJsonResponse(r));
        },
        {Get});

    app().registerHandler("/orders",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            auto json = req->getJsonObject();
            if (!json || !json->isMember("sku") || !json->isMember("quantity")) {
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k400BadRequest);
                resp->setBody(R"({"error":"sku and quantity required"})");
                callback(resp);
                return;
            }

            const std::string sku = (*json)["sku"].asString();
            const int quantity = (*json)["quantity"].asInt();
            const std::string order_id = generate_uuid();

            auto tracer = cndp::telemetry::tracer("order-service");
            opentelemetry::trace::StartSpanOptions root_opts;
            root_opts.kind = opentelemetry::trace::SpanKind::kServer;
            cndp::telemetry::SpanPtr root = tracer->StartSpan(
                "POST /orders",
                {{"http.method", "POST"}, {"http.target", "/orders"}}, root_opts);
            const std::string trace_id = cndp::telemetry::trace_id_of(root);

            // Child client span around the gRPC reservation; its context goes out as metadata.
            std::string status;
            {
                opentelemetry::trace::StartSpanOptions child_opts;
                child_opts.kind = opentelemetry::trace::SpanKind::kClient;
                child_opts.parent = root->GetContext();
                cndp::telemetry::SpanPtr rpc = tracer->StartSpan(
                    "reserve-stock",
                    {{"rpc.system", "grpc"},
                     {"rpc.service", "inventory.InventoryService"},
                     {"rpc.method", "ReserveStock"},
                     {"sku", sku},
                     {"quantity", std::to_string(quantity)}},
                    child_opts);

                inventory::ReserveRequest grpc_req;
                grpc_req.set_sku(sku);
                grpc_req.set_quantity(quantity);
                inventory::ReserveResponse grpc_resp;
                grpc::ClientContext ctx;
                ctx.set_deadline(std::chrono::system_clock::now() + std::chrono::seconds(5));
                ctx.AddMetadata("traceparent", cndp::telemetry::traceparent_of(rpc));
                auto grpc_status = g_inventory_stub->ReserveStock(&ctx, grpc_req, &grpc_resp);
                status = (grpc_status.ok() && grpc_resp.confirmed()) ? "confirmed" : "rejected";
                rpc->SetAttribute("stock.confirmed", status == "confirmed");
                rpc->End();
            }

            {
                const std::string quantity_s = std::to_string(quantity);
                const char* params[4] = {order_id.c_str(), sku.c_str(), quantity_s.c_str(),
                                         status.c_str()};
                std::lock_guard<std::mutex> lock(g_pg_mu);
                PGresult* res = PQexecParams(g_pg,
                    "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4)",
                    4, nullptr, params, nullptr, nullptr, 0);
                if (PQresultStatus(res) != PGRES_COMMAND_OK)
                    spdlog::error("Insert failed: {}", PQerrorMessage(g_pg));
                PQclear(res);
            }

            std::ostringstream event;
            event << R"({"id":")" << json_escape(order_id)
                  << R"(","sku":")" << json_escape(sku)
                  << R"(","quantity":)" << quantity
                  << R"(,"status":")" << json_escape(status) << R"("})";
            const bool published = publish(event.str(), cndp::telemetry::traceparent_of(root));

            root->SetAttribute("order.id", order_id);
            root->SetAttribute("sku", sku);
            root->SetAttribute("status", status);
            root->End();

            g_orders_placed->Add(1, std::map<std::string, std::string>{{"sku", sku}, {"status", status}});

            spdlog::info("order placed sku={} id={} status={} trace_id={}", sku, order_id, status,
                         trace_id);

            if (!published) {
                Json::Value err;
                err["error"] = "event not published";
                auto http_resp = HttpResponse::newHttpJsonResponse(err);
                http_resp->setStatusCode(k503ServiceUnavailable);
                callback(http_resp);
                return;
            }

            Json::Value resp;
            resp["id"] = order_id;
            resp["sku"] = sku;
            resp["quantity"] = quantity;
            resp["status"] = status;
            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            http_resp->setStatusCode(k201Created);
            callback(http_resp);
        },
        {Post});

    app().registerHandler("/orders",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            std::lock_guard<std::mutex> lock(g_pg_mu);
            PGresult* res = PQexec(g_pg,
                "SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT 50");
            if (PQresultStatus(res) != PGRES_TUPLES_OK) {
                PQclear(res);
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k500InternalServerError);
                callback(resp);
                return;
            }
            Json::Value orders(Json::arrayValue);
            for (int i = 0; i < PQntuples(res); ++i) {
                Json::Value o;
                o["id"] = PQgetvalue(res, i, 0);
                o["sku"] = PQgetvalue(res, i, 1);
                o["quantity"] = std::stoi(PQgetvalue(res, i, 2));
                o["status"] = PQgetvalue(res, i, 3);
                orders.append(o);
            }
            PQclear(res);
            callback(HttpResponse::newHttpJsonResponse(orders));
        },
        {Get});

    app().run();  // returns on SIGINT/SIGTERM

    g_polling.store(false);
    if (g_poller.joinable()) g_poller.join();
    g_producer->flush(10000);
    g_producer.reset();
    cndp::telemetry::shutdown();
    if (g_pg) PQfinish(g_pg);
    return 0;
}
