#include <drogon/drogon.h>
#include <sw/redis++/redis++.h>
#include <libpq-fe.h>
#include <atomic>
#include <thread>
#include <chrono>
#include <mutex>
#include <sstream>
#include <optional>

using namespace drogon;
using namespace sw::redis;

// Global state
std::unique_ptr<Redis> g_redis;
PGconn* g_pg = nullptr;
std::atomic<int> g_persisted_rows{0};
std::atomic<bool> g_shutdown{false};
std::mutex g_redis_mutex;

// Helper: execute SQL query and return JSON result
Json::Value query_db(const std::string& query) {
    PGresult* res = PQexec(g_pg, query.c_str());
    Json::Value result;

    if (PQresultStatus(res) == PGRES_TUPLES_OK && PQntuples(res) > 0) {
        result["id"] = PQgetvalue(res, 0, 0);
        result["name"] = PQgetvalue(res, 0, 1);
        result["price_cents"] = std::stoi(PQgetvalue(res, 0, 2));
    }

    PQclear(res);
    return result;
}

// Helper: query event from DB
Json::Value query_event_db(const std::string& id) {
    std::string query = "SELECT id, type, payload FROM events WHERE id = '" + id + "'";
    PGresult* res = PQexec(g_pg, query.c_str());
    Json::Value result;

    if (PQresultStatus(res) == PGRES_TUPLES_OK && PQntuples(res) > 0) {
        result["id"] = PQgetvalue(res, 0, 0);
        result["type"] = PQgetvalue(res, 0, 1);

        Json::Reader reader;
        std::string payload_str = PQgetvalue(res, 0, 2);
        Json::Value payload;
        if (reader.parse(payload_str, payload)) {
            result["payload"] = payload;
        }
    }

    PQclear(res);
    return result;
}

// Helper: query metric from DB
Json::Value query_metric_db(const std::string& id) {
    std::string query = "SELECT id, payload FROM metrics WHERE id = '" + id + "'";
    PGresult* res = PQexec(g_pg, query.c_str());
    Json::Value result;

    if (PQresultStatus(res) == PGRES_TUPLES_OK && PQntuples(res) > 0) {
        result["id"] = PQgetvalue(res, 0, 0);

        Json::Reader reader;
        std::string payload_str = PQgetvalue(res, 0, 1);
        Json::Value payload;
        if (reader.parse(payload_str, payload)) {
            result["payload"] = payload;
        }
    }

    PQclear(res);
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

// Background flusher thread
void writeback_flusher() {
    while (!g_shutdown) {
        std::this_thread::sleep_for(std::chrono::seconds(2));

        auto dirty_keys = redis_smembers("writeback:dirty");

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

            std::ostringstream query;
            query << "INSERT INTO metrics (id, payload) VALUES ('"
                  << id << "', '" << payload << "') "
                  << "ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload";

            PGresult* res = PQexec(g_pg, query.str().c_str());
            if (PQresultStatus(res) == PGRES_COMMAND_OK) {
                g_persisted_rows++;
                redis_srem("writeback:dirty", key);
            }
            PQclear(res);
        }
    }
}

int main() {
    // Connect to Postgres
    const char* pg_conninfo = std::getenv("PG_CONNINFO");
    if (!pg_conninfo) pg_conninfo = "postgresql://appuser:apppass@localhost:5432/appdb";

    g_pg = PQconnectdb(pg_conninfo);
    if (PQstatus(g_pg) != CONNECTION_OK) {
        LOG_ERROR << "Postgres connection failed: " << PQerrorMessage(g_pg);
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
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback,
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
            std::string query = "SELECT id, name, price_cents FROM products WHERE id = '" + id + "'";
            resp = query_db(query);

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

            std::ostringstream query;
            query << "UPDATE products SET name = '" << name
                  << "', price_cents = " << price
                  << " WHERE id = '" << id << "'";

            PGresult* res = PQexec(g_pg, query.str().c_str());
            PQclear(res);

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
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback,
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
            std::string query = "SELECT id, name, price_cents FROM products WHERE id = '" + id + "'";
            resp = query_db(query);

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
            std::ostringstream query;
            query << "UPDATE products SET name = '" << name
                  << "', price_cents = " << price
                  << " WHERE id = '" << id << "'";

            PGresult* res = PQexec(g_pg, query.str().c_str());
            PQclear(res);

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
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback,
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
            std::string query = "SELECT id, name, price_cents FROM products WHERE id = '" + id + "'";
            resp = query_db(query);
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
            std::ostringstream query;
            query << "INSERT INTO events (id, type, payload) VALUES ('"
                  << id << "', '" << type << "', '" << payload << "')";

            PGresult* res = PQexec(g_pg, query.str().c_str());
            PQclear(res);

            auto resp = HttpResponse::newHttpResponse();
            resp->setStatusCode(k200OK);
            callback(resp);
        },
        {Post});

    // GET /write-around/events/:id
    app().registerHandler("/write-around/events/{id}",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback,
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
            redis_set("metric:" + id, writer.write(cache_val));

            // Mark as dirty for background flush
            redis_sadd("writeback:dirty", "metric:" + id);

            auto resp = HttpResponse::newHttpResponse();
            resp->setStatusCode(k200OK);
            callback(resp);
        },
        {Put});

    // GET /write-back/metrics/:id
    app().registerHandler("/write-back/metrics/{id}",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback,
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
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value resp;
            resp["persisted_rows"] = g_persisted_rows.load();
            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            callback(http_resp);
        },
        {Get});

    // ======================================================================
    // 6. Refresh-ahead
    // ======================================================================

    // GET /refresh-ahead/products/:id
    app().registerHandler("/refresh-ahead/products/{id}",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback,
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
            std::string query = "SELECT id, name, price_cents FROM products WHERE id = '" + id + "'";
            resp = query_db(query);

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
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
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
    PQfinish(g_pg);

    return 0;
}
