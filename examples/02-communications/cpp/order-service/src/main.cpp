#include <drogon/drogon.h>
#include <grpcpp/grpcpp.h>
#include "inventory.grpc.pb.h"
#include <kafka/KafkaProducer.h>
#include <libpq-fe.h>
#include <mutex>
#include <iostream>
#include <sstream>
#include <random>
#include <regex>

using namespace drogon;

static PGconn* g_pg = nullptr;
static std::unique_ptr<inventory::Inventory::Stub> g_inv_stub;
static std::unique_ptr<kafka::clients::producer::KafkaProducer> g_producer;
static std::mutex g_pg_mu;

static std::string generate_uuid() {
    static thread_local std::mt19937 gen(std::random_device{}());
    std::uniform_int_distribution<uint32_t> dist(0, 0xFFFFFFFF);
    auto r = [&]() { return dist(gen); };
    char buf[37];
    uint32_t a = r(), b = r(), c = r(), d = r();
    snprintf(buf, sizeof(buf),
             "%08x-%04x-%04x-%04x-%04x%08x",
             a, (b >> 16) & 0xFFFF, 0x4000 | ((b >> 4) & 0x0FFF),
             0x8000 | (c & 0x3FFF), (c >> 16) & 0xFFFF, d);
    return std::string(buf);
}

static void pg_exec(const std::string& sql) {
    PGresult* res = PQexec(g_pg, sql.c_str());
    PQclear(res);
}

static std::vector<Json::Value> pg_query_orders(const std::string& where_clause, int limit) {
    std::ostringstream sql;
    sql << "SELECT id, sku, quantity, status FROM orders";
    if (!where_clause.empty()) sql << " WHERE " << where_clause;
    sql << " ORDER BY id LIMIT " << limit;

    std::vector<Json::Value> result;
    std::lock_guard<std::mutex> lock(g_pg_mu);
    PGresult* res = PQexec(g_pg, sql.str().c_str());
    if (PQresultStatus(res) == PGRES_TUPLES_OK) {
        int rows = PQntuples(res);
        for (int i = 0; i < rows; i++) {
            Json::Value order;
            order["id"] = PQgetvalue(res, i, 0);
            order["sku"] = PQgetvalue(res, i, 1);
            order["quantity"] = std::atoi(PQgetvalue(res, i, 2));
            order["status"] = PQgetvalue(res, i, 3);
            result.push_back(order);
        }
    }
    PQclear(res);
    return result;
}

static Json::Value handle_graphql(const std::string& query) {
    Json::Value response;

    std::regex orders_re(R"re(orders\s*\(\s*limit\s*:\s*(\d+)\s*\)\s*\{([^}]*)\})re");
    std::regex order_re(R"re(order\s*\(\s*id\s*:\s*"([^"]+)"\s*\)\s*\{([^}]*)\})re");
    std::smatch match;

    if (std::regex_search(query, match, orders_re)) {
        int limit = std::stoi(match[1].str());
        std::string fields_str = match[2].str();

        auto orders = pg_query_orders("", limit);
        Json::Value arr(Json::arrayValue);
        for (auto& o : orders) {
            Json::Value item;
            if (fields_str.find("id") != std::string::npos) item["id"] = o["id"];
            if (fields_str.find("sku") != std::string::npos) item["sku"] = o["sku"];
            if (fields_str.find("quantity") != std::string::npos) item["quantity"] = o["quantity"];
            if (fields_str.find("status") != std::string::npos) item["status"] = o["status"];
            arr.append(item);
        }
        response["data"]["orders"] = arr;
    } else if (std::regex_search(query, match, order_re)) {
        std::string id = match[1].str();
        std::string fields_str = match[2].str();

        std::string escaped_id;
        for (char c : id) {
            if (c == '\'') escaped_id += "''";
            else escaped_id += c;
        }
        auto orders = pg_query_orders("id = '" + escaped_id + "'", 1);
        if (!orders.empty()) {
            Json::Value item;
            auto& o = orders[0];
            if (fields_str.find("id") != std::string::npos) item["id"] = o["id"];
            if (fields_str.find("sku") != std::string::npos) item["sku"] = o["sku"];
            if (fields_str.find("quantity") != std::string::npos) item["quantity"] = o["quantity"];
            if (fields_str.find("status") != std::string::npos) item["status"] = o["status"];
            response["data"]["order"] = item;
        } else {
            response["data"]["order"] = Json::nullValue;
        }
    } else {
        response["errors"][0]["message"] = "unsupported query";
    }
    return response;
}

int main() {
    auto env_pg = std::getenv("PG_CONNINFO");
    std::string conninfo = env_pg ? env_pg : "host=postgres port=5432 dbname=appdb user=appuser password=apppass";
    g_pg = PQconnectdb(conninfo.c_str());
    if (PQstatus(g_pg) != CONNECTION_OK) {
        std::cerr << "pg connect failed: " << PQerrorMessage(g_pg) << std::endl;
        return 1;
    }

    auto env_inv = std::getenv("INVENTORY_ADDR");
    std::string inv_addr = env_inv ? env_inv : "inventory:50051";
    auto channel = grpc::CreateChannel(inv_addr, grpc::InsecureChannelCredentials());
    g_inv_stub = inventory::Inventory::NewStub(channel);

    auto env_kafka = std::getenv("KAFKA_BOOTSTRAP");
    std::string kafka_bs = env_kafka ? env_kafka : "kafka:9094";
    kafka::Properties props;
    props.put("bootstrap.servers", kafka_bs);
    props.put("acks", "all");
    g_producer = std::make_unique<kafka::clients::producer::KafkaProducer>(props);

    app().setLogLevel(trantor::Logger::kInfo);
    app().addListener("0.0.0.0", 8080);

    app().registerHandler("/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& cb) {
            Json::Value r;
            r["status"] = "ok";
            cb(HttpResponse::newHttpJsonResponse(r));
        },
        {Get});

    app().registerHandler("/orders",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& cb) {
            auto body = req->getJsonObject();
            if (!body) {
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k400BadRequest);
                cb(resp);
                return;
            }

            std::string sku = (*body).get("sku", "").asString();
            int quantity = (*body).get("quantity", 0).asInt();

            if (sku.empty() || quantity <= 0) {
                Json::Value err;
                err["error"] = "sku must be non-empty and quantity must be positive";
                auto resp = HttpResponse::newHttpJsonResponse(err);
                resp->setStatusCode(k422UnprocessableEntity);
                cb(resp);
                return;
            }

            inventory::ReserveRequest greq;
            greq.set_sku(sku);
            greq.set_quantity(quantity);
            inventory::ReserveReply greply;
            grpc::ClientContext ctx;
            auto grpc_status = g_inv_stub->ReserveStock(&ctx, greq, &greply);

            std::string status = "rejected";
            if (grpc_status.ok() && greply.reserved()) status = "confirmed";

            std::string order_id = generate_uuid();

            {
                std::lock_guard<std::mutex> lock(g_pg_mu);
                std::string sql = "INSERT INTO orders (id, sku, quantity, status) VALUES ('" +
                    order_id + "', '" + sku + "', " + std::to_string(quantity) + ", '" + status + "')";
                PGresult* res = PQexec(g_pg, sql.c_str());
                PQclear(res);
            }

            Json::Value order;
            order["id"] = order_id;
            order["sku"] = sku;
            order["quantity"] = quantity;
            order["status"] = status;

            try {
                Json::StreamWriterBuilder wb;
                wb["indentation"] = "";
                std::string event_str = Json::writeString(wb, order);
                kafka::clients::producer::ProducerRecord record(
                    kafka::Topic("order.placed"),
                    kafka::NullKey,
                    kafka::Value(event_str.data(), event_str.size()));
                g_producer->syncSend(record);
            } catch (...) {}

            std::cerr << "order created id=" << order_id << " status=" << status << std::endl;
            auto resp = HttpResponse::newHttpJsonResponse(order);
            resp->setStatusCode(k201Created);
            cb(resp);
        },
        {Post});

    app().registerHandler("/orders",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& cb) {
            std::string after = req->getParameter("after");
            int limit = 50;
            auto limit_str = req->getParameter("limit");
            if (!limit_str.empty()) {
                limit = std::atoi(limit_str.c_str());
                if (limit <= 0 || limit > 100) limit = 50;
            }

            std::string where;
            if (!after.empty()) {
                std::string escaped;
                for (char c : after) {
                    if (c == '\'') escaped += "''";
                    else escaped += c;
                }
                where = "id > '" + escaped + "'";
            }

            auto orders = pg_query_orders(where, limit);

            Json::Value items(Json::arrayValue);
            for (auto& o : orders) items.append(o);

            Json::Value result;
            result["items"] = items;
            if (static_cast<int>(orders.size()) == limit && !orders.empty()) {
                result["next_cursor"] = orders.back()["id"].asString();
            }
            cb(HttpResponse::newHttpJsonResponse(result));
        },
        {Get});

    app().registerHandler("/graphql",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& cb) {
            auto body = req->getJsonObject();
            if (!body || !body->isMember("query")) {
                Json::Value err;
                err["errors"][0]["message"] = "missing query field";
                cb(HttpResponse::newHttpJsonResponse(err));
                return;
            }

            std::string query = (*body)["query"].asString();
            Json::Value result = handle_graphql(query);
            cb(HttpResponse::newHttpJsonResponse(result));
        },
        {Post});

    app().run();
    return 0;
}
