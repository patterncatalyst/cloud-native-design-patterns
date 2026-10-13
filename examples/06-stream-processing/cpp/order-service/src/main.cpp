#include <drogon/drogon.h>
#include <librdkafka/rdkafkacpp.h>
#include <libpq-fe.h>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <thread>
#include <csignal>
#include <cstdlib>
#include <functional>
#include <memory>
#include <random>
#include <sstream>
#include <string>
#include <iomanip>

using namespace drogon;

static std::atomic<bool> g_shutdown{false};
static std::unique_ptr<RdKafka::Producer> g_producer;
static std::thread g_poller;
static std::atomic<bool> g_polling{false};
static PGconn* g_conn = nullptr;

std::string generate_uuid() {
    static std::random_device rd;
    static std::mt19937_64 gen(rd());
    static std::uniform_int_distribution<uint64_t> dis;

    uint64_t part1 = dis(gen);
    uint64_t part2 = dis(gen);

    std::ostringstream oss;
    oss << std::hex << std::setfill('0')
        << std::setw(8) << (part1 >> 32)
        << "-" << std::setw(4) << ((part1 >> 16) & 0xFFFF)
        << "-4" << std::setw(3) << (part1 & 0xFFF)
        << "-" << std::setw(4) << ((part2 >> 48) & 0xFFFF)
        << "-" << std::setw(12) << (part2 & 0xFFFFFFFFFFFF);
    return oss.str();
}

void signal_handler(int) {
    g_shutdown.store(true);
    app().quit();
}

bool init_postgres() {
    const char* conninfo = std::getenv("PG_CONNINFO");
    if (!conninfo) conninfo = "postgresql://appuser:apppass@localhost:5432/appdb";

    g_conn = PQconnectdb(conninfo);
    if (PQstatus(g_conn) != CONNECTION_OK) {
        LOG_ERROR << "Postgres connection failed: " << PQerrorMessage(g_conn);
        return false;
    }
    LOG_INFO << "Connected to Postgres";
    return true;
}

// One per produced message, carried as the message opaque: the request's continuation, run
// when the delivery report arrives (on the poller thread). The producer's
// message.timeout.ms guarantees a report, success or error, so the request always answers.
struct Pending {
    std::function<void(const std::string& error)> done;  // empty error = delivered
};

// Delivery reports arrive on the thread that calls poll().
class DeliveryLog : public RdKafka::DeliveryReportCb {
public:
    void dr_cb(RdKafka::Message& m) override {
        std::unique_ptr<Pending> pending(static_cast<Pending*>(m.msg_opaque()));
        if (m.err() != RdKafka::ERR_NO_ERROR) {
            LOG_ERROR << "order.placed delivery failed: " << m.errstr();
        }
        if (pending) pending->done(m.err() == RdKafka::ERR_NO_ERROR ? std::string() : m.errstr());
    }
};
static DeliveryLog g_dr;

bool init_kafka() {
    const char* bootstrap = std::getenv("KAFKA_BOOTSTRAP");
    if (!bootstrap) bootstrap = "localhost:9094";

    std::string err;
    std::unique_ptr<RdKafka::Conf> conf(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));
    if (conf->set("bootstrap.servers", bootstrap, err) != RdKafka::Conf::CONF_OK ||
        conf->set("client.id", "order-service", err) != RdKafka::Conf::CONF_OK ||
        conf->set("linger.ms", "5", err) != RdKafka::Conf::CONF_OK ||
        conf->set("acks", "all", err) != RdKafka::Conf::CONF_OK ||
        conf->set("message.timeout.ms", "10000", err) != RdKafka::Conf::CONF_OK ||
        conf->set("enable.idempotence", "true", err) != RdKafka::Conf::CONF_OK ||
        conf->set("dr_cb", &g_dr, err) != RdKafka::Conf::CONF_OK) {
        LOG_ERROR << "Kafka producer config failed: " << err;
        return false;
    }
    g_producer.reset(RdKafka::Producer::create(conf.get(), err));
    if (!g_producer) {
        LOG_ERROR << "Kafka producer init failed: " << err;
        return false;
    }
    // Serve delivery reports until shutdown.
    g_polling.store(true);
    g_poller = std::thread([] {
        while (g_polling.load()) g_producer->poll(100);
    });
    LOG_INFO << "Kafka producer initialized";
    return true;
}

// Enqueues the event. On true the delivery report will run done(); on false the message was
// not queued and done is never called (the caller answers the request itself).
bool publish_order_event(const std::string& order_json, std::function<void(const std::string&)> done) {
    if (!g_producer) return false;
    for (int attempt = 0; attempt < 50; ++attempt) {
        auto* pending = new Pending{done};
        auto rc = g_producer->produce("order.placed", RdKafka::Topic::PARTITION_UA,
                                      RdKafka::Producer::RK_MSG_COPY,
                                      const_cast<char*>(order_json.data()), order_json.size(),
                                      nullptr, 0, 0, nullptr, pending);
        if (rc == RdKafka::ERR_NO_ERROR) return true;
        delete pending;
        if (rc == RdKafka::ERR__QUEUE_FULL) {
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
            continue;
        }
        LOG_ERROR << "Failed to publish order event: " << RdKafka::err2str(rc);
        return false;
    }
    LOG_ERROR << "Failed to publish order event: producer queue full";
    return false;
}

int main() {
    // docker logs reads a pipe: line-buffer stdout so LOG_* lines show up as they are written.
    std::setvbuf(stdout, nullptr, _IOLBF, 0);
    std::signal(SIGTERM, signal_handler);
    std::signal(SIGINT, signal_handler);

    app().registerBeginningAdvice([]() {
        if (!init_postgres() || !init_kafka()) {
            LOG_ERROR << "Initialization failed";
            app().quit();
            return;
        }
    });

    // Health check
    app().registerHandler("/healthz",
        [](const HttpRequestPtr&,
           std::function<void(const HttpResponsePtr&)>&& callback) {
            auto resp = HttpResponse::newHttpJsonResponse(Json::Value{Json::objectValue});
            (*resp->getJsonObject())["status"] = "ok";
            callback(resp);
        },
        {Get});

    // POST /orders
    app().registerHandler("/orders",
        [](const HttpRequestPtr& req,
           std::function<void(const HttpResponsePtr&)>&& callback) {
            if (!g_conn) {
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k503ServiceUnavailable);
                callback(resp);
                return;
            }

            auto json = req->getJsonObject();
            if (!json || !json->isMember("merchant_id") || !json->isMember("sku") ||
                !json->isMember("quantity") || !json->isMember("total")) {
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k400BadRequest);
                callback(resp);
                return;
            }

            std::string id = generate_uuid();
            std::string merchant_id = (*json)["merchant_id"].asString();
            std::string sku = (*json)["sku"].asString();
            int quantity = (*json)["quantity"].asInt();
            double total = (*json)["total"].asDouble();

            // Insert into Postgres
            const std::string quantity_s = std::to_string(quantity);
            const std::string total_s = std::to_string(total);
            const char* paramValues[5] = {
                id.c_str(), merchant_id.c_str(), sku.c_str(),
                quantity_s.c_str(), total_s.c_str()
            };

            PGresult* res = PQexecParams(g_conn,
                "INSERT INTO orders (id, merchant_id, sku, quantity, total) VALUES ($1, $2, $3, $4, $5)",
                5, nullptr, paramValues, nullptr, nullptr, 0);

            if (PQresultStatus(res) != PGRES_COMMAND_OK) {
                LOG_ERROR << "Insert failed: " << PQerrorMessage(g_conn);
                PQclear(res);
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k500InternalServerError);
                callback(resp);
                return;
            }
            PQclear(res);

            // Build event JSON
            Json::Value event;
            event["id"] = id;
            event["merchant_id"] = merchant_id;
            event["sku"] = sku;
            event["quantity"] = quantity;
            event["total"] = total;
            event["status"] = "confirmed";

            Json::StreamWriterBuilder builder;
            builder["indentation"] = "";
            std::string event_json = Json::writeString(builder, event);

            // Publish to Kafka; answer 201 only once the broker has acknowledged the event.
            auto reply = [callback = std::move(callback), event](const std::string& error) {
                if (!error.empty()) {
                    Json::Value err;
                    err["error"] = "event not published";
                    auto resp = HttpResponse::newHttpJsonResponse(err);
                    resp->setStatusCode(k503ServiceUnavailable);
                    callback(resp);
                    return;
                }
                auto resp = HttpResponse::newHttpJsonResponse(event);
                resp->setStatusCode(k201Created);
                callback(resp);
            };
            auto shared_reply = std::make_shared<decltype(reply)>(std::move(reply));
            if (!publish_order_event(event_json, [shared_reply](const std::string& e) { (*shared_reply)(e); }))
                (*shared_reply)("not queued");
        },
        {Post});

    // GET /orders
    app().registerHandler("/orders",
        [](const HttpRequestPtr&,
           std::function<void(const HttpResponsePtr&)>&& callback) {
            if (!g_conn) {
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k503ServiceUnavailable);
                callback(resp);
                return;
            }

            PGresult* res = PQexec(g_conn,
                "SELECT id, merchant_id, sku, quantity, total, status FROM orders ORDER BY created_at DESC");

            if (PQresultStatus(res) != PGRES_TUPLES_OK) {
                LOG_ERROR << "Query failed: " << PQerrorMessage(g_conn);
                PQclear(res);
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k500InternalServerError);
                callback(resp);
                return;
            }

            Json::Value orders(Json::arrayValue);
            int rows = PQntuples(res);

            for (int i = 0; i < rows; i++) {
                Json::Value order;
                order["id"] = PQgetvalue(res, i, 0);
                order["merchant_id"] = PQgetvalue(res, i, 1);
                order["sku"] = PQgetvalue(res, i, 2);
                order["quantity"] = std::atoi(PQgetvalue(res, i, 3));
                order["total"] = std::atof(PQgetvalue(res, i, 4));
                order["status"] = PQgetvalue(res, i, 5);
                orders.append(order);
            }

            PQclear(res);

            auto resp = HttpResponse::newHttpJsonResponse(orders);
            callback(resp);
        },
        {Get});

    app().setUploadPath("/tmp");
    app().addListener("0.0.0.0", 8080);

    LOG_INFO << "Starting order-service on :8080";
    app().run();

    // Cleanup
    if (g_producer) {
        g_polling.store(false);
        if (g_poller.joinable()) g_poller.join();
        g_producer->flush(10000);  // deliver what is queued before exiting
        g_producer.reset();
    }
    if (g_conn) {
        PQfinish(g_conn);
    }

    return 0;
}
