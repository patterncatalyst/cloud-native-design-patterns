#include <drogon/drogon.h>
#include <libpq-fe.h>
#include <mutex>
#include <iostream>

using namespace drogon;

static PGconn* g_pg = nullptr;
static std::mutex g_pg_mu;

int main() {
    auto env_pg = std::getenv("PG_CONNINFO");
    std::string conninfo = env_pg ? env_pg : "host=postgres port=5432 dbname=appdb user=appuser password=apppass";
    g_pg = PQconnectdb(conninfo.c_str());
    if (PQstatus(g_pg) != CONNECTION_OK) {
        std::cerr << "pg connect failed: " << PQerrorMessage(g_pg) << std::endl;
        return 1;
    }
    std::cerr << "order-api started" << std::endl;

    app().setLogLevel(trantor::Logger::kInfo);
    app().addListener("0.0.0.0", 8081);

    app().registerHandler("/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& cb) {
            Json::Value r;
            r["status"] = "ok";
            cb(HttpResponse::newHttpJsonResponse(r));
        },
        {Get});

    app().registerHandler("/orders",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& cb) {
            int limit = 50;
            auto limit_str = req->getParameter("limit");
            if (!limit_str.empty()) {
                limit = std::atoi(limit_str.c_str());
                if (limit <= 0 || limit > 100) limit = 50;
            }

            Json::Value arr(Json::arrayValue);
            {
                std::lock_guard<std::mutex> lock(g_pg_mu);
                std::string sql = "SELECT id, sku, quantity, status FROM orders ORDER BY id LIMIT " + std::to_string(limit);
                PGresult* res = PQexec(g_pg, sql.c_str());
                if (PQresultStatus(res) == PGRES_TUPLES_OK) {
                    int rows = PQntuples(res);
                    for (int i = 0; i < rows; i++) {
                        Json::Value order;
                        order["id"] = PQgetvalue(res, i, 0);
                        order["sku"] = PQgetvalue(res, i, 1);
                        order["quantity"] = std::atoi(PQgetvalue(res, i, 2));
                        order["status"] = PQgetvalue(res, i, 3);
                        arr.append(order);
                    }
                }
                PQclear(res);
            }
            cb(HttpResponse::newHttpJsonResponse(arr));
        },
        {Get});

    app().registerHandler("/orders/{order_id}",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& cb,
           const std::string& order_id) {
            std::lock_guard<std::mutex> lock(g_pg_mu);
            std::string escaped;
            for (char c : order_id) {
                if (c == '\'') escaped += "''";
                else escaped += c;
            }
            std::string sql = "SELECT id, sku, quantity, status FROM orders WHERE id = '" + escaped + "'";
            PGresult* res = PQexec(g_pg, sql.c_str());
            if (PQresultStatus(res) == PGRES_TUPLES_OK && PQntuples(res) > 0) {
                Json::Value order;
                order["id"] = PQgetvalue(res, 0, 0);
                order["sku"] = PQgetvalue(res, 0, 1);
                order["quantity"] = std::atoi(PQgetvalue(res, 0, 2));
                order["status"] = PQgetvalue(res, 0, 3);
                PQclear(res);
                cb(HttpResponse::newHttpJsonResponse(order));
            } else {
                PQclear(res);
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k404NotFound);
                cb(resp);
            }
        },
        {Get});

    app().run();
    return 0;
}
