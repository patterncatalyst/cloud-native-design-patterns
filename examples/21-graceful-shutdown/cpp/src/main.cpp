#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <memory>
#include <random>
#include <sstream>
#include <string>
#include <thread>
#include <iomanip>

#include <drogon/drogon.h>
#include <json/json.h>
#include <spdlog/spdlog.h>
#include <unistd.h>

#include "pg_pool.hpp"

using namespace drogon;

namespace {

std::unique_ptr<cndp::PgPool> g_pool;
std::string g_version;
// Written by the signal handler, so it must be lock-free: the handler does
// nothing but store to it.
std::atomic<bool> g_shutting_down{false};
static_assert(std::atomic<bool>::is_always_lock_free);
// Tells the watcher thread to exit when the server stops for another reason.
std::atomic<bool> g_watcher_stop{false};
std::atomic<int> g_in_flight{0};

const char* env(const char* name, const char* fallback) {
    const char* v = std::getenv(name);
    return v ? v : fallback;
}

// RAII scope guard for in-flight tracking
struct InFlightGuard {
    InFlightGuard() { ++g_in_flight; }
    ~InFlightGuard() { --g_in_flight; }
};

// Simple UUID generation using random hex
std::string generate_uuid() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<unsigned int> dist(0, 15);

    std::ostringstream oss;
    oss << std::hex << std::setfill('0');

    // Format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
    for (int i = 0; i < 8; ++i) oss << std::setw(1) << dist(gen);
    oss << "-";
    for (int i = 0; i < 4; ++i) oss << std::setw(1) << dist(gen);
    oss << "-4"; // version 4
    for (int i = 0; i < 3; ++i) oss << std::setw(1) << dist(gen);
    oss << "-";
    oss << std::setw(1) << ((dist(gen) & 0x3) | 0x8); // variant bits
    for (int i = 0; i < 3; ++i) oss << std::setw(1) << dist(gen);
    oss << "-";
    for (int i = 0; i < 12; ++i) oss << std::setw(1) << dist(gen);

    return oss.str();
}

// Async-signal-safe: a single lock-free atomic store. No logging, allocation
// or locking here; the watcher thread observes the flag and does the rest.
extern "C" void sigterm_handler(int) {
    g_shutting_down.store(true, std::memory_order_release);
}

// Runs the shutdown sequence outside signal context, driven by the single
// SIGTERM. Readiness already reads g_shutting_down, so /readyz returns 503 from
// the moment the handler ran. The watcher then keeps serving for the pre-stop
// delay (so endpoints update), waits for in-flight requests (bounded to fit the
// stop grace period) and asks Drogon to quit: it stops the listeners and
// app().run() returns.
void shutdown_watcher() {
    using namespace std::chrono_literals;
    while (!g_shutting_down.load(std::memory_order_acquire)) {
        if (g_watcher_stop.load(std::memory_order_acquire)) return;
        std::this_thread::sleep_for(50ms);
    }
    const int delay = std::atoi(env("DRAIN_DELAY_SECONDS", "5"));
    spdlog::info("SIGTERM received, readiness flipped, waiting {}s for endpoints to update", delay);
    std::this_thread::sleep_for(std::chrono::seconds(delay));

    spdlog::info("draining in-flight requests (in_flight={})", g_in_flight.load());
    const auto deadline = std::chrono::steady_clock::now() + 20s;
    while (g_in_flight.load(std::memory_order_acquire) > 0 &&
           std::chrono::steady_clock::now() < deadline) {
        std::this_thread::sleep_for(100ms);
    }
    spdlog::info("shutting down HTTP server (in_flight={})", g_in_flight.load());
    app().quit();
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

    // Suppress Drogon's upload-dir creation (we don't use file uploads)
    app().setUploadPath("/tmp");

    // Re-install SIGTERM handler AFTER Drogon's init — Drogon's run() installs
    // its own SIGTERM handler that calls quit(). We override it with one that
    // only sets an atomic flag, so the process stays alive and keeps serving
    // while readyz flips to 503. SIGINT keeps Drogon's handler (quit).
    app().registerBeginningAdvice([]() {
        std::signal(SIGTERM, sigterm_handler);
        spdlog::info("SIGTERM handler installed (graceful shutdown mode)");
    });

    // Root endpoint
    app().registerHandler(
        "/",
        [](const HttpRequestPtr&,
           std::function<void(const HttpResponsePtr&)>&& cb) {
            Json::Value j;
            j["service"] = "order-service";
            j["version"] = g_version;
            j["graceful_shutdown"] = "enabled";
            cb(HttpResponse::newHttpJsonResponse(j));
        },
        {Get});

    // Health check
    app().registerHandler(
        "/healthz",
        [](const HttpRequestPtr&,
           std::function<void(const HttpResponsePtr&)>&& cb) {
            Json::Value j;
            j["status"] = "ok";
            cb(HttpResponse::newHttpJsonResponse(j));
        },
        {Get});

    // Readiness check — returns 503 when shutting down
    app().registerHandler(
        "/readyz",
        [](const HttpRequestPtr&,
           std::function<void(const HttpResponsePtr&)>&& cb) {
            if (g_shutting_down.load(std::memory_order_acquire)) {
                Json::Value j;
                j["ready"] = false;
                j["reason"] = "shutting down";
                auto resp = HttpResponse::newHttpJsonResponse(j);
                resp->setStatusCode(k503ServiceUnavailable);
                cb(resp);
                return;
            }

            // Normal readiness check with DB validation
            Json::Value j;
            bool db_ok = false;
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
                j["ready"] = true;
                j["checks"] = Json::objectValue;
                j["checks"]["database"] = "ok";
                cb(HttpResponse::newHttpJsonResponse(j));
            } else {
                j["ready"] = false;
                j["reason"] = "database check failed";
                auto resp = HttpResponse::newHttpJsonResponse(j);
                resp->setStatusCode(k503ServiceUnavailable);
                cb(resp);
            }
        },
        {Get});

    // Debug state endpoint
    app().registerHandler(
        "/debug/state",
        [](const HttpRequestPtr&,
           std::function<void(const HttpResponsePtr&)>&& cb) {
            Json::Value j;
            j["shutting_down"] = g_shutting_down.load(std::memory_order_acquire);
            j["in_flight"] = g_in_flight.load(std::memory_order_acquire);
            j["pid"] = static_cast<int>(getpid());
            cb(HttpResponse::newHttpJsonResponse(j));
        },
        {Get});

    // GET /orders — list all orders
    app().registerHandler(
        "/orders",
        [](const HttpRequestPtr&,
           std::function<void(const HttpResponsePtr&)>&& cb) {
            InFlightGuard guard;
            try {
                auto c = g_pool->acquire(std::chrono::milliseconds(5000));
                PGresult* r = PQexec(c.get(),
                    "SELECT id, sku, quantity, status, created_at FROM orders ORDER BY created_at");
                if (!r || PQresultStatus(r) != PGRES_TUPLES_OK) {
                    if (r) PQclear(r);
                    throw std::runtime_error("SELECT failed");
                }
                Json::Value arr(Json::arrayValue);
                for (int i = 0; i < PQntuples(r); ++i) {
                    Json::Value row;
                    row["id"] = PQgetvalue(r, i, 0);
                    row["sku"] = PQgetvalue(r, i, 1);
                    row["quantity"] = std::stoi(PQgetvalue(r, i, 2));
                    row["status"] = PQgetvalue(r, i, 3);
                    row["created_at"] = PQgetvalue(r, i, 4);
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

    // POST /orders — create order
    app().registerHandler(
        "/orders",
        [](const HttpRequestPtr& req,
           std::function<void(const HttpResponsePtr&)>&& cb) {
            InFlightGuard guard;
            try {
                auto json = req->getJsonObject();
                if (!json || !json->isMember("sku") || !json->isMember("quantity")) {
                    auto resp = HttpResponse::newHttpResponse();
                    resp->setStatusCode(k400BadRequest);
                    cb(resp);
                    return;
                }

                std::string sku = (*json)["sku"].asString();
                int quantity = (*json)["quantity"].asInt();
                std::string id = generate_uuid();
                std::string status = "confirmed";

                auto c = g_pool->acquire(std::chrono::milliseconds(5000));
                std::string qty_str = std::to_string(quantity);
                const char* params[4] = {id.c_str(), sku.c_str(),
                                        qty_str.c_str(),
                                        status.c_str()};
                PGresult* r = PQexecParams(c.get(),
                    "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4) RETURNING id, created_at",
                    4, nullptr, params, nullptr, nullptr, 0);
                if (!r || PQresultStatus(r) != PGRES_TUPLES_OK) {
                    if (r) PQclear(r);
                    throw std::runtime_error("INSERT failed");
                }

                std::string created_at = PQgetvalue(r, 0, 1);
                PQclear(r);

                Json::Value resp_json;
                resp_json["id"] = id;
                resp_json["sku"] = sku;
                resp_json["quantity"] = quantity;
                resp_json["status"] = status;
                resp_json["created_at"] = created_at;

                auto resp = HttpResponse::newHttpJsonResponse(resp_json);
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

    std::thread watcher(shutdown_watcher);

    spdlog::info("listening on 0.0.0.0:8080");
    app().run();

    g_watcher_stop.store(true, std::memory_order_release);
    watcher.join();

    // After app().run() returns (e.g., from SIGINT or explicit quit)
    spdlog::info("waiting for in-flight requests to complete...");
    while (g_in_flight.load(std::memory_order_acquire) > 0) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    g_pool.reset();  // close the database connections
    spdlog::info("graceful shutdown complete");

    return 0;
}
