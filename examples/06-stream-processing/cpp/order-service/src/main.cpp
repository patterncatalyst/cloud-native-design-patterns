#include <drogon/drogon.h>
#include <kafka/KafkaProducer.h>
#include <libpq-fe.h>
#include <atomic>
#include <csignal>
#include <cstdlib>
#include <memory>
#include <random>
#include <sstream>
#include <string>
#include <iomanip>

using namespace drogon;

static std::atomic<bool> g_shutdown{false};
static std::unique_ptr<kafka::clients::producer::KafkaProducer> g_producer;
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

bool init_kafka() {
    const char* bootstrap = std::getenv("KAFKA_BOOTSTRAP");
    if (!bootstrap) bootstrap = "localhost:9094";

    kafka::Properties props;
    props.put("bootstrap.servers", bootstrap);
    props.put("client.id", "order-service");
    props.put("linger.ms", "100");
    props.put("acks", "1");

    try {
        g_producer = std::make_unique<kafka::clients::producer::KafkaProducer>(props);
        LOG_INFO << "Kafka producer initialized";
        return true;
    } catch (const std::exception& e) {
        LOG_ERROR << "Kafka producer init failed: " << e.what();
        return false;
    }
}

void publish_order_event(const std::string& order_json) {
    if (!g_producer) return;

    try {
        kafka::clients::producer::ProducerRecord record{
            "order.placed",
            kafka::NullKey,
            kafka::Value(order_json.c_str(), order_json.size())
        };
        // Use syncSend to avoid use-after-free (send() is async and returns before buffer is sent)
        g_producer->syncSend(record);
    } catch (const std::exception& e) {
        LOG_ERROR << "Failed to publish order event: " << e.what();
    }
}

int main() {
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
            const char* paramValues[5] = {
                id.c_str(),
                merchant_id.c_str(),
                sku.c_str(),
                std::to_string(quantity).c_str(),
                std::to_string(total).c_str()
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

            // Publish to Kafka
            publish_order_event(event_json);

            // Return response
            auto resp = HttpResponse::newHttpJsonResponse(event);
            resp->setStatusCode(k201Created);
            callback(resp);
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
        g_producer->close();
        g_producer.reset();
    }
    if (g_conn) {
        PQfinish(g_conn);
    }

    return 0;
}
