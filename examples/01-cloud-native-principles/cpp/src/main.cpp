#include <cstdlib>
#include <memory>
#include <string>

#include <drogon/drogon.h>
#include <json/json.h>
#include <spdlog/spdlog.h>

#include "pg_pool.hpp"

using namespace drogon;

namespace {

std::unique_ptr<cndp::PgPool> g_pool;
std::string g_version;

const char* env(const char* name, const char* fallback) {
    const char* v = std::getenv(name);
    return v ? v : fallback;
}

}  // namespace

int main() {
    g_version = env("SERVICE_VERSION", "1.0.0");
    const std::string pg = env("PG_CONNINFO",
        "postgresql://appuser:apppass@postgres:5432/appdb");
    const int pool_sz = std::atoi(env("PG_POOL_SIZE", "4"));

    spdlog::info("order-service {} starting, pool={}", g_version, pool_sz);
    g_pool = std::make_unique<cndp::PgPool>(pg, pool_sz);
    spdlog::info("PostgreSQL pool ready");

    app().registerHandler(
        "/",
        [](const HttpRequestPtr&,
           std::function<void(const HttpResponsePtr&)>&& cb) {
            Json::Value j;
            j["service"] = "order-service";
            j["version"] = g_version;
            j["config_source"] = "environment";
            cb(HttpResponse::newHttpJsonResponse(j));
        },
        {Get});

    app().registerHandler(
        "/healthz",
        [](const HttpRequestPtr&,
           std::function<void(const HttpResponsePtr&)>&& cb) {
            Json::Value j;
            j["status"] = "ok";
            cb(HttpResponse::newHttpJsonResponse(j));
        },
        {Get});

    app().registerHandler(
        "/readyz",
        [](const HttpRequestPtr&,
           std::function<void(const HttpResponsePtr&)>&& cb) {
            Json::Value j, checks;
            bool db_ok = false;
            // Retry up to pool size — each attempt discards one dead
            // connection, letting the pool open a fresh replacement.
            for (int attempt = 0; attempt < 5 && !db_ok; ++attempt) {
                try {
                    auto c = g_pool->acquire(std::chrono::milliseconds(2000));
                    if (PQstatus(c.get()) != CONNECTION_OK) {
                        PQreset(c.get());
                        if (PQstatus(c.get()) != CONNECTION_OK) {
                            c.invalidate();
                            continue;
                        }
                    }
                    PGresult* r = PQexec(c.get(), "SELECT 1");
                    bool ok = r && PQresultStatus(r) == PGRES_TUPLES_OK;
                    if (r) PQclear(r);
                    if (!ok) {
                        c.invalidate();
                        continue;
                    }
                    db_ok = true;
                } catch (...) {
                    // acquire timeout or other error — try again
                }
            }
            if (db_ok) {
                checks["database"] = "ok";
                j["status"] = "ready";
            } else {
                checks["database"] = "unreachable";
                j["status"] = "down";
            }
            j["checks"] = checks;
            cb(HttpResponse::newHttpJsonResponse(j));
        },
        {Get});

    app().registerHandler(
        "/orders",
        [](const HttpRequestPtr&,
           std::function<void(const HttpResponsePtr&)>&& cb) {
            try {
                auto c = g_pool->acquire(std::chrono::milliseconds(5000));
                PGresult* r = PQexec(c.get(),
                    "SELECT id, customer, total FROM orders ORDER BY id");
                if (!r || PQresultStatus(r) != PGRES_TUPLES_OK) {
                    if (r) PQclear(r);
                    throw std::runtime_error("SELECT failed");
                }
                Json::Value arr(Json::arrayValue);
                for (int i = 0; i < PQntuples(r); ++i) {
                    Json::Value row;
                    row["id"] = std::stoi(PQgetvalue(r, i, 0));
                    row["customer"] = PQgetvalue(r, i, 1);
                    row["total"] = std::stod(PQgetvalue(r, i, 2));
                    arr.append(row);
                }
                PQclear(r);
                cb(HttpResponse::newHttpJsonResponse(arr));
            } catch (const std::exception& e) {
                spdlog::error("list orders: {}", e.what());
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k500InternalServerError);
                cb(resp);
            }
        },
        {Get});

    app().registerHandler(
        "/orders",
        [](const HttpRequestPtr& req,
           std::function<void(const HttpResponsePtr&)>&& cb) {
            try {
                auto customer = req->getParameter("customer");
                auto total_s = req->getParameter("total");
                if (customer.empty() || total_s.empty()) {
                    auto resp = HttpResponse::newHttpResponse();
                    resp->setStatusCode(k400BadRequest);
                    cb(resp);
                    return;
                }
                double total = std::stod(total_s);
                auto c = g_pool->acquire(std::chrono::milliseconds(5000));
                const char* params[2] = {customer.c_str(), total_s.c_str()};
                PGresult* r = PQexecParams(c.get(),
                    "INSERT INTO orders (customer, total) VALUES ($1, $2) RETURNING id",
                    2, nullptr, params, nullptr, nullptr, 0);
                if (!r || PQresultStatus(r) != PGRES_TUPLES_OK) {
                    if (r) PQclear(r);
                    throw std::runtime_error("INSERT failed");
                }
                int id = std::stoi(PQgetvalue(r, 0, 0));
                PQclear(r);
                Json::Value j;
                j["id"] = id;
                j["customer"] = customer;
                j["total"] = total;
                auto resp = HttpResponse::newHttpJsonResponse(j);
                resp->setStatusCode(k201Created);
                cb(resp);
            } catch (const std::exception& e) {
                spdlog::error("create order: {}", e.what());
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k500InternalServerError);
                cb(resp);
            }
        },
        {Post});

    app().addListener("0.0.0.0", 8080);
    app().setThreadNum(4);
    app().setLogLevel(trantor::Logger::kInfo);

    spdlog::info("listening on 0.0.0.0:8080");
    app().run();
    return 0;
}
