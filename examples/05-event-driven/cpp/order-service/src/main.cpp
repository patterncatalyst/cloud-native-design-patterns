#include <drogon/drogon.h>
#include <kafka/KafkaProducer.h>
#include <libpq-fe.h>
#include <random>
#include <sstream>
#include <iomanip>
#include <atomic>
#include <csignal>

using namespace drogon;

std::atomic<bool> g_shutdown{false};
PGconn* g_pg_conn = nullptr;
std::unique_ptr<kafka::clients::producer::KafkaProducer> g_producer;

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

    kafka::Properties props;
    props.put("bootstrap.servers", bootstrap);
    props.put("client.id", "order-service");

    g_producer = std::make_unique<kafka::clients::producer::KafkaProducer>(props);
    LOG_INFO << "Kafka producer initialized";
}

int main() {
    std::signal(SIGTERM, signal_handler);
    std::signal(SIGINT, signal_handler);

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
                const char* params[4] = {order_id.c_str(), sku.c_str(),
                                         std::to_string(quantity).c_str(), status.c_str()};
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

                // Publish to Kafka
                std::ostringstream event;
                event << "{\"id\":\"" << json_escape(order_id) << "\","
                      << "\"sku\":\"" << json_escape(sku) << "\","
                      << "\"quantity\":" << quantity << ","
                      << "\"status\":\"" << json_escape(status) << "\"}";

                std::string event_str = event.str();
                kafka::clients::producer::ProducerRecord record(
                    kafka::Topic("order.placed"),
                    kafka::NullKey,
                    kafka::Value(event_str.c_str(), event_str.size()));

                try {
                    auto md = g_producer->syncSend(record);
                    LOG_INFO << "Event published to partition " << md.partition();
                } catch (const kafka::KafkaException& e) {
                    LOG_ERROR << "Kafka send failed: " << e.what();
                }

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

    if (g_pg_conn) PQfinish(g_pg_conn);
    return 0;
}
