#include <drogon/drogon.h>
#include <sw/redis++/redis++.h>
#include <libpq-fe.h>
#include <algorithm>
#include <atomic>
#include <map>
#include <thread>
#include <chrono>
#include <mutex>
#include <sstream>
#include <optional>
#include <memory>
#include <vector>

using namespace drogon;
using namespace sw::redis;

// Global state
std::unique_ptr<Redis> g_redis;
std::atomic<bool> g_shutdown{false};
std::mutex g_redis_mutex;

// One libpq connection guarded by a mutex (a PGconn is not safe for concurrent use). The
// request handlers share one; the write-back flusher thread owns another. Every statement
// goes through PQexecParams: ids and body fields travel as parameters, never as SQL text.
// A dead connection is re-established with PQreset and the statement retried once.
class Db {
public:
    explicit Db(std::string conninfo) : conninfo_(std::move(conninfo)) {}
    ~Db() { if (conn_) PQfinish(conn_); }
    Db(const Db&) = delete;
    Db& operator=(const Db&) = delete;

    bool connect() {
        std::lock_guard<std::mutex> lock(mu_);
        conn_ = PQconnectdb(conninfo_.c_str());
        return conn_ && PQstatus(conn_) == CONNECTION_OK;
    }
    std::string error() {
        std::lock_guard<std::mutex> lock(mu_);
        return conn_ ? PQerrorMessage(conn_) : "no connection";
    }

    using Result = std::unique_ptr<PGresult, decltype(&PQclear)>;

    Result exec(const char* sql, const std::vector<std::string>& params) {
        std::vector<const char*> values;
        values.reserve(params.size());
        for (const auto& p : params) values.push_back(p.c_str());
        std::lock_guard<std::mutex> lock(mu_);
        for (int attempt = 0; attempt < 2; ++attempt) {
            if (!conn_) conn_ = PQconnectdb(conninfo_.c_str());
            else if (PQstatus(conn_) == CONNECTION_BAD) PQreset(conn_);
            PGresult* res = PQexecParams(conn_, sql, static_cast<int>(values.size()), nullptr,
                                         values.data(), nullptr, nullptr, 0);
            if (PQstatus(conn_) != CONNECTION_BAD) return Result(res, &PQclear);
            PQclear(res);  // connection died mid-statement: reset on the next pass and retry
            PQreset(conn_);
        }
        return Result(nullptr, &PQclear);
    }

private:
    std::string conninfo_;
    PGconn* conn_ = nullptr;
    std::mutex mu_;
};

std::unique_ptr<Db> g_db;        // request handlers
std::unique_ptr<Db> g_flush_db;  // write-back flusher thread

bool ok_rows(const Db::Result& res) {
    return res && PQresultStatus(res.get()) == PGRES_TUPLES_OK && PQntuples(res.get()) > 0;
}

// Helper: query a product by id and return it as JSON
Json::Value query_db(const std::string& id) {
    auto res = g_db->exec("SELECT id, name, price_cents FROM products WHERE id = $1", {id});
    Json::Value result;

    if (ok_rows(res)) {
        result["id"] = PQgetvalue(res.get(), 0, 0);
        result["name"] = PQgetvalue(res.get(), 0, 1);
        result["price_cents"] = std::stoi(PQgetvalue(res.get(), 0, 2));
    }
    return result;
}

// Helper: query event from DB
Json::Value query_event_db(const std::string& id) {
    auto res = g_db->exec("SELECT id, type, payload FROM events WHERE id = $1", {id});
    Json::Value result;

    if (ok_rows(res)) {
        result["id"] = PQgetvalue(res.get(), 0, 0);
        result["type"] = PQgetvalue(res.get(), 0, 1);

        Json::Reader reader;
        std::string payload_str = PQgetvalue(res.get(), 0, 2);
        Json::Value payload;
        if (reader.parse(payload_str, payload)) {
            result["payload"] = payload;
        }
    }

    return result;
}

// Helper: query metric from DB
Json::Value query_metric_db(const std::string& id) {
    auto res = g_db->exec("SELECT id, payload FROM metrics WHERE id = $1", {id});
    Json::Value result;

    if (ok_rows(res)) {
        result["id"] = PQgetvalue(res.get(), 0, 0);

        Json::Reader reader;
        std::string payload_str = PQgetvalue(res.get(), 0, 1);
        Json::Value payload;
        if (reader.parse(payload_str, payload)) {
            result["payload"] = payload;
        }
    }

    return result;
}

// Helper: safe Redis GET
std::optional<std::string> redis_get(const std::string& key) {
    try {
        std::lock_guard<std::mutex> lock(g_redis_mutex);
        if (!g_redis) return std::nullopt;
        auto val = g_redis->get(key);
        return val;
    } catch (...) {
        return std::nullopt;
    }
}

// Helper: safe Redis SET
bool redis_set(const std::string& key, const std::string& value, std::chrono::seconds ttl = std::chrono::seconds(60)) {
    try {
        std::lock_guard<std::mutex> lock(g_redis_mutex);
        if (!g_redis) return false;
        g_redis->set(key, value, ttl);
        return true;
    } catch (...) {
        return false;
    }
}

// Helper: safe Redis DEL
bool redis_del(const std::string& key) {
    try {
        std::lock_guard<std::mutex> lock(g_redis_mutex);
        if (!g_redis) return false;
        g_redis->del(key);
        return true;
    } catch (...) {
        return false;
    }
}

// Helper: safe Redis SADD
bool redis_sadd(const std::string& set, const std::string& member) {
    try {
        std::lock_guard<std::mutex> lock(g_redis_mutex);
        if (!g_redis) return false;
        g_redis->sadd(set, member);
        return true;
    } catch (...) {
        return false;
    }
}

// Helper: safe Redis SREM
bool redis_srem(const std::string& set, const std::string& member) {
    try {
        std::lock_guard<std::mutex> lock(g_redis_mutex);
        if (!g_redis) return false;
        g_redis->srem(set, member);
        return true;
    } catch (...) {
        return false;
    }
}

// Helper: safe Redis SMEMBERS
std::vector<std::string> redis_smembers(const std::string& set) {
    try {
        std::lock_guard<std::mutex> lock(g_redis_mutex);
        if (!g_redis) return {};
        std::vector<std::string> members;
        g_redis->smembers(set, std::back_inserter(members));
        return members;
    } catch (...) {
        return {};
    }
}

// Helper: safe Redis KEYS
std::vector<std::string> redis_keys(const std::string& pattern) {
    try {
        std::lock_guard<std::mutex> lock(g_redis_mutex);
        if (!g_redis) return {};
        std::vector<std::string> keys;
        g_redis->keys(pattern, std::back_inserter(keys));
        return keys;
    } catch (...) {
        return {};
    }
}

// Background flusher thread.
// Write-back flush policy: an entry stays on the dirty set until Postgres has it, so a failed
// upsert is retried on the next cycle. Retries back off exponentially between cycles and are
// bounded per key: after kMaxFlushAttempts the key moves to writeback:failed (its value stays in
// the cache) and is logged, never dropped silently.
void writeback_flusher() {
    constexpr int kMaxFlushAttempts = 5;
    constexpr int kMaxBackoffSeconds = 8;
    std::map<std::string, int> attempts;
    int failures = 0;
    while (!g_shutdown) {
        const int wait = std::min(2 << failures, kMaxBackoffSeconds);
        for (int i = 0; i < wait * 10 && !g_shutdown; ++i)
            std::this_thread::sleep_for(std::chrono::milliseconds(100));

        auto dirty_keys = redis_smembers("writeback:dirty");
        bool any_failed = false;

        for (const auto& key : dirty_keys) {
            auto val = redis_get(key);
            if (!val) continue;

            // Parse the cached metric
            Json::Reader reader;
            Json::Value cached;
            if (!reader.parse(*val, cached)) continue;

            // Extract metric ID from key (metric:m1 -> m1)
            std::string id = key.substr(key.find(':') + 1);

            // Persist to DB
            Json::FastWriter writer;
            std::string payload = writer.write(cached["payload"]);

            auto res = g_flush_db->exec(
                "INSERT INTO metrics (id, payload) VALUES ($1, $2) "
                "ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, ts = NOW()",
                {id, payload});
            if (res && PQresultStatus(res.get()) == PGRES_COMMAND_OK) {
                redis_srem("writeback:dirty", key);
                attempts.erase(key);
                continue;
            }

            any_failed = true;
            const int n = ++attempts[key];
            LOG_ERROR << "flusher: flush failed for " << id << " (attempt " << n << "/"
                      << kMaxFlushAttempts << ")";
            if (n >= kMaxFlushAttempts) {
                redis_sadd("writeback:failed", key);
                redis_srem("writeback:dirty", key);
                attempts.erase(key);
                LOG_ERROR << "flusher: giving up on " << id << ", parked on writeback:failed";
            }
        }
        failures = any_failed ? std::min(failures + 1, 2) : 0;
    }
}

int main() {
    // Connect to Postgres
    const char* pg_conninfo = std::getenv("PG_CONNINFO");
    if (!pg_conninfo) pg_conninfo = "postgresql://appuser:apppass@localhost:5432/appdb";

    g_db = std::make_unique<Db>(pg_conninfo);
    g_flush_db = std::make_unique<Db>(pg_conninfo);
    if (!g_db->connect() || !g_flush_db->connect()) {
        LOG_ERROR << "Postgres connection failed: " << g_db->error() << g_flush_db->error();
        return 1;
    }
    LOG_INFO << "Connected to Postgres";

    // Connect to Redis
    const char* redis_url = std::getenv("REDIS_URL");
    if (!redis_url) redis_url = "redis://localhost:6379";

    try {
        g_redis = std::make_unique<Redis>(redis_url);
        LOG_INFO << "Connected to Redis";
    } catch (const std::exception& e) {
        LOG_WARN << "Redis connection failed: " << e.what() << " (continuing without cache)";
    }

    // Start background flusher
    std::thread flusher(writeback_flusher);

    app().setUploadPath("/tmp");

    // --- healthz ---
    app().registerHandler("/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value resp;
            resp["status"] = "ok";
            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            callback(http_resp);
        },
        {Get});

    // ======================================================================
    // 1. Cache-aside
    // ======================================================================

    // GET /cache-aside/products/:id
    app().registerHandler("/cache-aside/products/{id}",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback,
           const std::string& id) {
            Json::Value resp;

            // Try cache first
            auto cached = redis_get("product:" + id);
            if (cached) {
                Json::Reader reader;
                if (reader.parse(*cached, resp)) {
                    resp["source"] = "cache";
                    auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                    callback(http_resp);
                    return;
                }
            }

            // Cache miss - query DB
            resp = query_db(id);

            if (!resp.empty()) {
                resp["source"] = "db";

                // Populate cache
                Json::FastWriter writer;
                Json::Value cache_val = resp;
                cache_val.removeMember("source");
                redis_set("product:" + id, writer.write(cache_val));
            }

            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            callback(http_resp);
        },
        {Get});

    // PUT /cache-aside/products/:id
    app().registerHandler("/cache-aside/products/{id}",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback,
           const std::string& id) {
            auto json = req->getJsonObject();
            if (!json) {
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k400BadRequest);
                callback(resp);
                return;
            }

            std::string name = (*json)["name"].asString();
            int price = (*json)["price_cents"].asInt();

            g_db->exec("UPDATE products SET name = $1, price_cents = $2 WHERE id = $3",
                       {name, std::to_string(price), id});

            // Invalidate cache
            redis_del("product:" + id);

            auto resp = HttpResponse::newHttpResponse();
            resp->setStatusCode(k200OK);
            callback(resp);
        },
        {Put});

    // ======================================================================
    // 2. Read-through
    // ======================================================================

    // GET /read-through/products/:id
    app().registerHandler("/read-through/products/{id}",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback,
           const std::string& id) {
            Json::Value resp;

            // Try cache first
            auto cached = redis_get("product:" + id);
            if (cached) {
                Json::Reader reader;
                if (reader.parse(*cached, resp)) {
                    resp["source"] = "cache";
                    auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                    callback(http_resp);
                    return;
                }
            }

            // Transparent cache layer loads from DB
            resp = query_db(id);

            if (!resp.empty()) {
                resp["source"] = "db";

                // Auto-populate cache
                Json::FastWriter writer;
                Json::Value cache_val = resp;
                cache_val.removeMember("source");
                redis_set("product:" + id, writer.write(cache_val));
            }

            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            callback(http_resp);
        },
        {Get});

    // ======================================================================
    // 3. Write-through
    // ======================================================================

    // PUT /write-through/products/:id
    app().registerHandler("/write-through/products/{id}",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback,
           const std::string& id) {
            auto json = req->getJsonObject();
            if (!json) {
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k400BadRequest);
                callback(resp);
                return;
            }

            std::string name = (*json)["name"].asString();
            int price = (*json)["price_cents"].asInt();

            // Write to DB
            g_db->exec("UPDATE products SET name = $1, price_cents = $2 WHERE id = $3",
                       {name, std::to_string(price), id});

            // Write to cache synchronously
            Json::Value cache_val;
            cache_val["id"] = id;
            cache_val["name"] = name;
            cache_val["price_cents"] = price;

            Json::FastWriter writer;
            redis_set("product:" + id, writer.write(cache_val));

            auto resp = HttpResponse::newHttpResponse();
            resp->setStatusCode(k200OK);
            callback(resp);
        },
        {Put});

    // GET /write-through/products/:id
    app().registerHandler("/write-through/products/{id}",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback,
           const std::string& id) {
            Json::Value resp;

            // Try cache first
            auto cached = redis_get("product:" + id);
            if (cached) {
                Json::Reader reader;
                if (reader.parse(*cached, resp)) {
                    resp["source"] = "cache";
                    auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                    callback(http_resp);
                    return;
                }
            }

            // Fallback to DB
            resp = query_db(id);
            resp["source"] = "db";

            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            callback(http_resp);
        },
        {Get});

    // ======================================================================
    // 4. Write-around
    // ======================================================================

    // POST /write-around/events
    app().registerHandler("/write-around/events",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            auto json = req->getJsonObject();
            if (!json) {
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k400BadRequest);
                callback(resp);
                return;
            }

            std::string id = (*json)["id"].asString();
            std::string type = (*json)["type"].asString();
            Json::FastWriter writer;
            std::string payload = writer.write((*json)["payload"]);

            // Write to DB only (skip cache)
            g_db->exec("INSERT INTO events (id, type, payload) VALUES ($1, $2, $3)",
                       {id, type, payload});

            auto resp = HttpResponse::newHttpResponse();
            resp->setStatusCode(k200OK);
            callback(resp);
        },
        {Post});

    // GET /write-around/events/:id
    app().registerHandler("/write-around/events/{id}",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback,
           const std::string& id) {
            Json::Value resp;

            // Try cache first
            auto cached = redis_get("event:" + id);
            if (cached) {
                Json::Reader reader;
                if (reader.parse(*cached, resp)) {
                    resp["source"] = "cache";
                    auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                    callback(http_resp);
                    return;
                }
            }

            // Query DB
            resp = query_event_db(id);

            if (!resp.empty()) {
                resp["source"] = "db";

                // Populate cache on read
                Json::FastWriter writer;
                Json::Value cache_val = resp;
                cache_val.removeMember("source");
                redis_set("event:" + id, writer.write(cache_val));
            }

            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            callback(http_resp);
        },
        {Get});

    // ======================================================================
    // 5. Write-back (write-behind)
    // ======================================================================

    // PUT /write-back/metrics/:id
    app().registerHandler("/write-back/metrics/{id}",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback,
           const std::string& id) {
            auto json = req->getJsonObject();
            if (!json) {
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k400BadRequest);
                callback(resp);
                return;
            }

            // Write to cache immediately
            Json::Value cache_val;
            cache_val["id"] = id;
            cache_val["payload"] = *json;

            Json::FastWriter writer;
            // A queued write must outlive a database outage, so no 60 s default TTL here.
            redis_set("metric:" + id, writer.write(cache_val), std::chrono::hours(1));

            // Mark as dirty for background flush
            redis_sadd("writeback:dirty", "metric:" + id);

            // 202: queued in the cache, not yet durable in Postgres
            Json::Value body;
            body["ok"] = true;
            body["pattern"] = "write-back";
            body["action"] = "cached-for-flush";
            auto resp = HttpResponse::newHttpJsonResponse(body);
            resp->setStatusCode(k202Accepted);
            callback(resp);
        },
        {Put});

    // GET /write-back/metrics/:id
    app().registerHandler("/write-back/metrics/{id}",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback,
           const std::string& id) {
            Json::Value resp;

            // Try cache first
            auto cached = redis_get("metric:" + id);
            if (cached) {
                Json::Reader reader;
                if (reader.parse(*cached, resp)) {
                    resp["source"] = "cache";
                    auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                    callback(http_resp);
                    return;
                }
            }

            // Fallback to DB
            resp = query_metric_db(id);
            if (!resp.empty()) {
                resp["source"] = "db";
            }

            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            callback(http_resp);
        },
        {Get});

    // GET /write-back/flush-status
    app().registerHandler("/write-back/flush-status",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value resp;
            auto res = g_db->exec("SELECT count(*) FROM metrics", {});
            resp["persisted_rows"] = ok_rows(res) ? std::atoi(PQgetvalue(res.get(), 0, 0)) : -1;
            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            callback(http_resp);
        },
        {Get});

    // ======================================================================
    // 6. Refresh-ahead
    // ======================================================================

    // GET /refresh-ahead/products/:id
    app().registerHandler("/refresh-ahead/products/{id}",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback,
           const std::string& id) {
            Json::Value resp;

            // Try cache first
            auto cached = redis_get("product:hot:" + id);
            if (cached) {
                Json::Reader reader;
                if (reader.parse(*cached, resp)) {
                    resp["source"] = "cache";
                    auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                    callback(http_resp);
                    return;
                }
            }

            // Query DB
            resp = query_db(id);

            if (!resp.empty()) {
                resp["source"] = "db";

                // Populate cache with proactive refresh
                Json::FastWriter writer;
                Json::Value cache_val = resp;
                cache_val.removeMember("source");
                redis_set("product:hot:" + id, writer.write(cache_val), std::chrono::seconds(300));
            }

            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            callback(http_resp);
        },
        {Get});

    // ======================================================================
    // Cache keys endpoint
    // ======================================================================

    // GET /cache-keys
    app().registerHandler("/cache-keys",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value resp(Json::arrayValue);

            auto product_keys = redis_keys("product:*");
            for (const auto& key : product_keys) {
                resp.append(key);
            }

            auto event_keys = redis_keys("event:*");
            for (const auto& key : event_keys) {
                resp.append(key);
            }

            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            callback(http_resp);
        },
        {Get});

    // Start server
    LOG_INFO << "Starting cache-service on :8080";
    app().addListener("0.0.0.0", 8080).run();

    // Cleanup
    g_shutdown = true;
    flusher.join();

    return 0;
}
