#include <drogon/drogon.h>
#include <libpq-fe.h>
#include <random>
#include <iomanip>
#include <sstream>
#include <csignal>
#include <atomic>

using namespace drogon;

std::atomic<bool> shutdown_requested{false};

std::string generate_uuid() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> hex(0, 15);

    std::ostringstream oss;
    oss << std::hex;

    for (int i = 0; i < 8; i++) oss << hex(gen);
    oss << '-';
    for (int i = 0; i < 4; i++) oss << hex(gen);
    oss << "-4";
    for (int i = 0; i < 3; i++) oss << hex(gen);
    oss << '-';
    oss << (hex(gen) & 0x3 | 0x8);
    for (int i = 0; i < 3; i++) oss << hex(gen);
    oss << '-';
    for (int i = 0; i < 12; i++) oss << hex(gen);

    return oss.str();
}

std::string pg_conninfo() {
    const char* env = std::getenv("PG_CONNINFO");
    return env ? env : "postgresql://appuser:apppass@postgres:5432/appdb";
}

void handle_healthz(const HttpRequestPtr& req,
                    std::function<void(const HttpResponsePtr&)>&& callback) {
    Json::Value resp;
    resp["status"] = "ok";
    auto http_resp = HttpResponse::newHttpJsonResponse(resp);
    callback(http_resp);
}

void handle_post_orders(const HttpRequestPtr& req,
                       std::function<void(const HttpResponsePtr&)>&& callback) {
    auto json = req->getJsonObject();
    if (!json || !json->isMember("sku") || !json->isMember("quantity")) {
        auto resp = HttpResponse::newHttpResponse();
        resp->setStatusCode(k400BadRequest);
        resp->setBody(R"({"error":"missing sku or quantity"})");
        resp->setContentTypeCode(CT_APPLICATION_JSON);
        callback(resp);
        return;
    }

    std::string sku = (*json)["sku"].asString();
    int quantity = (*json)["quantity"].asInt();
    std::string id = generate_uuid();
    std::string status = "confirmed";

    // Build JSON payload for outbox
    Json::Value payload;
    payload["id"] = id;
    payload["sku"] = sku;
    payload["quantity"] = quantity;
    payload["status"] = status;
    Json::StreamWriterBuilder builder;
    builder["indentation"] = "";
    std::string payload_str = Json::writeString(builder, payload);

    // Transactional outbox pattern: single transaction for both tables
    PGconn* conn = PQconnectdb(pg_conninfo().c_str());
    if (PQstatus(conn) != CONNECTION_OK) {
        LOG_ERROR << "DB connection failed: " << PQerrorMessage(conn);
        PQfinish(conn);
        auto resp = HttpResponse::newHttpResponse();
        resp->setStatusCode(k500InternalServerError);
        resp->setBody(R"({"error":"database connection failed"})");
        resp->setContentTypeCode(CT_APPLICATION_JSON);
        callback(resp);
        return;
    }

    PGresult* res = PQexec(conn, "BEGIN");
    if (PQresultStatus(res) != PGRES_COMMAND_OK) {
        LOG_ERROR << "BEGIN failed: " << PQerrorMessage(conn);
        PQclear(res);
        PQfinish(conn);
        auto resp = HttpResponse::newHttpResponse();
        resp->setStatusCode(k500InternalServerError);
        resp->setBody(R"({"error":"transaction begin failed"})");
        resp->setContentTypeCode(CT_APPLICATION_JSON);
        callback(resp);
        return;
    }
    PQclear(res);

    // Insert into orders
    const char* params_order[4] = {id.c_str(), sku.c_str(),
                                    std::to_string(quantity).c_str(), status.c_str()};
    res = PQexecParams(conn,
        "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4)",
        4, nullptr, params_order, nullptr, nullptr, 0);

    if (PQresultStatus(res) != PGRES_COMMAND_OK) {
        LOG_ERROR << "INSERT orders failed: " << PQerrorMessage(conn);
        PQclear(res);
        PQexec(conn, "ROLLBACK");
        PQfinish(conn);
        auto resp = HttpResponse::newHttpResponse();
        resp->setStatusCode(k500InternalServerError);
        resp->setBody(R"({"error":"order insert failed"})");
        resp->setContentTypeCode(CT_APPLICATION_JSON);
        callback(resp);
        return;
    }
    PQclear(res);

    // Insert into outbox
    const char* params_outbox[3] = {id.c_str(), "order.placed", payload_str.c_str()};
    res = PQexecParams(conn,
        "INSERT INTO outbox (aggregate_id, event_type, payload) VALUES ($1, $2, $3::jsonb)",
        3, nullptr, params_outbox, nullptr, nullptr, 0);

    if (PQresultStatus(res) != PGRES_COMMAND_OK) {
        LOG_ERROR << "INSERT outbox failed: " << PQerrorMessage(conn);
        PQclear(res);
        PQexec(conn, "ROLLBACK");
        PQfinish(conn);
        auto resp = HttpResponse::newHttpResponse();
        resp->setStatusCode(k500InternalServerError);
        resp->setBody(R"({"error":"outbox insert failed"})");
        resp->setContentTypeCode(CT_APPLICATION_JSON);
        callback(resp);
        return;
    }
    PQclear(res);

    // Commit transaction
    res = PQexec(conn, "COMMIT");
    if (PQresultStatus(res) != PGRES_COMMAND_OK) {
        LOG_ERROR << "COMMIT failed: " << PQerrorMessage(conn);
        PQclear(res);
        PQexec(conn, "ROLLBACK");
        PQfinish(conn);
        auto resp = HttpResponse::newHttpResponse();
        resp->setStatusCode(k500InternalServerError);
        resp->setBody(R"({"error":"commit failed"})");
        resp->setContentTypeCode(CT_APPLICATION_JSON);
        callback(resp);
        return;
    }
    PQclear(res);
    PQfinish(conn);

    // Return success with order details
    auto http_resp = HttpResponse::newHttpJsonResponse(payload);
    http_resp->setStatusCode(k201Created);
    callback(http_resp);
}

void handle_get_orders(const HttpRequestPtr& req,
                      std::function<void(const HttpResponsePtr&)>&& callback) {
    PGconn* conn = PQconnectdb(pg_conninfo().c_str());
    if (PQstatus(conn) != CONNECTION_OK) {
        LOG_ERROR << "DB connection failed: " << PQerrorMessage(conn);
        PQfinish(conn);
        auto resp = HttpResponse::newHttpResponse();
        resp->setStatusCode(k500InternalServerError);
        resp->setBody(R"({"error":"database connection failed"})");
        resp->setContentTypeCode(CT_APPLICATION_JSON);
        callback(resp);
        return;
    }

    PGresult* res = PQexec(conn,
        "SELECT id, sku, quantity, status, created_at FROM orders ORDER BY created_at DESC");

    if (PQresultStatus(res) != PGRES_TUPLES_OK) {
        LOG_ERROR << "SELECT orders failed: " << PQerrorMessage(conn);
        PQclear(res);
        PQfinish(conn);
        auto resp = HttpResponse::newHttpResponse();
        resp->setStatusCode(k500InternalServerError);
        resp->setBody(R"({"error":"query failed"})");
        resp->setContentTypeCode(CT_APPLICATION_JSON);
        callback(resp);
        return;
    }

    Json::Value orders(Json::arrayValue);
    int rows = PQntuples(res);
    for (int i = 0; i < rows; i++) {
        Json::Value order;
        order["id"] = PQgetvalue(res, i, 0);
        order["sku"] = PQgetvalue(res, i, 1);
        order["quantity"] = std::stoi(PQgetvalue(res, i, 2));
        order["status"] = PQgetvalue(res, i, 3);
        order["created_at"] = PQgetvalue(res, i, 4);
        orders.append(order);
    }

    PQclear(res);
    PQfinish(conn);

    auto http_resp = HttpResponse::newHttpJsonResponse(orders);
    callback(http_resp);
}

void handle_get_outbox(const HttpRequestPtr& req,
                      std::function<void(const HttpResponsePtr&)>&& callback) {
    PGconn* conn = PQconnectdb(pg_conninfo().c_str());
    if (PQstatus(conn) != CONNECTION_OK) {
        LOG_ERROR << "DB connection failed: " << PQerrorMessage(conn);
        PQfinish(conn);
        auto resp = HttpResponse::newHttpResponse();
        resp->setStatusCode(k500InternalServerError);
        resp->setBody(R"({"error":"database connection failed"})");
        resp->setContentTypeCode(CT_APPLICATION_JSON);
        callback(resp);
        return;
    }

    PGresult* res = PQexec(conn,
        "SELECT id, aggregate_id, event_type, payload::text, created_at FROM outbox ORDER BY created_at DESC");

    if (PQresultStatus(res) != PGRES_TUPLES_OK) {
        LOG_ERROR << "SELECT outbox failed: " << PQerrorMessage(conn);
        PQclear(res);
        PQfinish(conn);
        auto resp = HttpResponse::newHttpResponse();
        resp->setStatusCode(k500InternalServerError);
        resp->setBody(R"({"error":"query failed"})");
        resp->setContentTypeCode(CT_APPLICATION_JSON);
        callback(resp);
        return;
    }

    Json::Value outbox(Json::arrayValue);
    int rows = PQntuples(res);
    for (int i = 0; i < rows; i++) {
        Json::Value entry;
        entry["id"] = static_cast<Json::Int64>(std::stoll(PQgetvalue(res, i, 0)));
        entry["aggregate_id"] = PQgetvalue(res, i, 1);
        entry["event_type"] = PQgetvalue(res, i, 2);

        // Parse payload JSON string
        Json::CharReaderBuilder reader_builder;
        Json::Value payload_json;
        std::string payload_str = PQgetvalue(res, i, 3);
        std::istringstream payload_stream(payload_str);
        std::string errs;
        if (Json::parseFromStream(reader_builder, payload_stream, &payload_json, &errs)) {
            entry["payload"] = payload_json;
        } else {
            entry["payload"] = payload_str;
        }

        entry["created_at"] = PQgetvalue(res, i, 4);
        outbox.append(entry);
    }

    PQclear(res);
    PQfinish(conn);

    auto http_resp = HttpResponse::newHttpJsonResponse(outbox);
    callback(http_resp);
}

void signal_handler(int sig) {
    LOG_INFO << "Received signal " << sig << ", shutting down...";
    shutdown_requested = true;
    app().quit();
}

int main() {
    // Set up custom signal handler
    app().registerBeginningAdvice([]() {
        std::signal(SIGTERM, signal_handler);
        std::signal(SIGINT, signal_handler);
    });

    // Register handlers (must use lambdas, not function pointers)
    app().registerHandler("/healthz",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            handle_healthz(req, std::move(callback));
        }, {Get});

    app().registerHandler("/orders",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            if (req->method() == Post) {
                handle_post_orders(req, std::move(callback));
            } else if (req->method() == Get) {
                handle_get_orders(req, std::move(callback));
            } else {
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k405MethodNotAllowed);
                callback(resp);
            }
        }, {Get, Post});

    app().registerHandler("/outbox",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            handle_get_outbox(req, std::move(callback));
        }, {Get});

    app().setUploadPath("/tmp");
    app().addListener("0.0.0.0", 8080);
    app().setLogLevel(trantor::Logger::kInfo);

    LOG_INFO << "Order service starting on port 8080...";
    app().run();

    return 0;
}
