/*
 * examples/12-security/cpp — Security patterns demonstration.
 *
 * Demonstrates:
 * 1. Sidecar trust — mutual TLS via X-Forwarded-Client-Cert header
 * 2. Valet keys — HMAC-based scoped tokens for temporary resource access
 * 3. Per-tenant bulkhead — isolated resource pools per tenant
 *
 * In-memory state only; no database required.
 */

#include <drogon/HttpAppFramework.h>
#include <drogon/HttpRequest.h>
#include <drogon/HttpResponse.h>
#include <json/json.h>
#include <spdlog/spdlog.h>

#include <openssl/hmac.h>
#include <atomic>
#include <chrono>
#include <iomanip>
#include <map>
#include <mutex>
#include <sstream>
#include <string>

using namespace drogon;

// ═══════════════════════════════════════════════════════════════════════════
// HMAC Utilities for Valet Keys
// ═══════════════════════════════════════════════════════════════════════════

static const char* VALET_SECRET = std::getenv("VALET_SECRET") ?
    std::getenv("VALET_SECRET") : "demo-secret-do-not-use-in-prod";

std::string hmac_sha256(const std::string& key, const std::string& data) {
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int len = 0;
    HMAC(EVP_sha256(), key.c_str(), key.size(),
         reinterpret_cast<const unsigned char*>(data.c_str()),
         data.size(), digest, &len);

    std::ostringstream ss;
    ss << std::hex << std::setfill('0');
    for (unsigned int i = 0; i < len; ++i) {
        ss << std::setw(2) << static_cast<int>(digest[i]);
    }
    return ss.str();
}

// ═══════════════════════════════════════════════════════════════════════════
// Per-Tenant Bulkhead
// ═══════════════════════════════════════════════════════════════════════════

struct TenantBulkhead {
    static constexpr int CAPACITY = 5;
    std::atomic<int> active{0};

    bool try_acquire() {
        int current = active.load();
        while (current < CAPACITY) {
            if (active.compare_exchange_weak(current, current + 1)) {
                return true;
            }
        }
        return false;
    }

    void release() {
        active.fetch_sub(1);
    }

    int available() const {
        return CAPACITY - active.load();
    }
};

class BulkheadManager {
private:
    std::map<std::string, TenantBulkhead> bulkheads_;
    std::mutex mutex_;

public:
    TenantBulkhead& get_or_create(const std::string& tenant) {
        std::lock_guard<std::mutex> lock(mutex_);
        return bulkheads_[tenant];
    }

    Json::Value get_state() {
        std::lock_guard<std::mutex> lock(mutex_);
        Json::Value state;
        for (const auto& [tenant, bulkhead] : bulkheads_) {
            Json::Value tenant_state;
            tenant_state["available"] = bulkhead.available();
            tenant_state["capacity"] = TenantBulkhead::CAPACITY;
            state[tenant] = tenant_state;
        }
        return state;
    }
};

// Global instances
static BulkheadManager bulkhead_manager;
static std::atomic<int> order_counter{0};
static std::map<std::string, Json::Value> orders_store;
static std::mutex orders_mutex;

// ═══════════════════════════════════════════════════════════════════════════
// Middleware — Sidecar Trust
// ═══════════════════════════════════════════════════════════════════════════

void setup_sidecar_trust_middleware(HttpAppFramework& app) {
    app.registerPreHandlingAdvice(
        [](const HttpRequestPtr& req,
           AdviceCallback&& cb,
           AdviceChainCallback&& ccb) {
            auto path = req->path();

            // Bypass identity check for health endpoint
            if (path == "/healthz") {
                ccb();
                return;
            }

            // Check for X-Forwarded-Client-Cert header
            auto cert = req->getHeader("X-Forwarded-Client-Cert");
            if (cert.empty()) {
                Json::Value error;
                error["detail"] = "no validated identity";
                auto resp = HttpResponse::newHttpJsonResponse(error);
                resp->setStatusCode(k403Forbidden);
                cb(resp);
                return;
            }

            // Store identity and subject in request attributes
            req->attributes()->insert("identity", cert);

            auto jwt_sub = req->getHeader("X-Jwt-Claim-Sub");
            std::string subject = jwt_sub.empty() ? "anonymous" : jwt_sub;
            req->attributes()->insert("subject", subject);

            spdlog::debug("Authenticated: identity={}, subject={}", cert, subject);

            ccb();  // Continue to handler
        });
}

// ═══════════════════════════════════════════════════════════════════════════
// Handlers
// ═══════════════════════════════════════════════════════════════════════════

int main() {
    spdlog::set_level(spdlog::level::info);
    spdlog::info("Starting order-service (example 12: Security)");

    auto& app = HttpAppFramework::instance();

    // Suppress upload directory warning
    app.setUploadPath("/tmp");

    // Register middleware
    setup_sidecar_trust_middleware(app);

    // ───────────────────────────────────────────────────────────────────────
    // GET /healthz — Health check (bypasses identity)
    // ───────────────────────────────────────────────────────────────────────
    app.registerHandler(
        "/healthz",
        [](const HttpRequestPtr& req,
           std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value resp;
            resp["status"] = "ok";
            callback(HttpResponse::newHttpJsonResponse(resp));
        },
        {Get});

    // ───────────────────────────────────────────────────────────────────────
    // POST /orders — Create order (requires identity, uses bulkhead)
    // ───────────────────────────────────────────────────────────────────────
    app.registerHandler(
        "/orders",
        [](const HttpRequestPtr& req,
           std::function<void(const HttpResponsePtr&)>&& callback) {
            try {
                auto json = req->getJsonObject();
                if (!json) {
                    Json::Value error;
                    error["detail"] = "invalid JSON";
                    auto resp = HttpResponse::newHttpJsonResponse(error);
                    resp->setStatusCode(k400BadRequest);
                    callback(resp);
                    return;
                }

                std::string sku = (*json).get("sku", "").asString();
                int quantity = (*json).get("quantity", 0).asInt();
                std::string tenant = (*json).get("tenant", "").asString();

                if (sku.empty() || tenant.empty()) {
                    Json::Value error;
                    error["detail"] = "missing required fields";
                    auto resp = HttpResponse::newHttpJsonResponse(error);
                    resp->setStatusCode(k400BadRequest);
                    callback(resp);
                    return;
                }

                // Try to acquire bulkhead slot
                auto& bulkhead = bulkhead_manager.get_or_create(tenant);
                if (!bulkhead.try_acquire()) {
                    Json::Value error;
                    error["detail"] = "tenant capacity exceeded";
                    auto resp = HttpResponse::newHttpJsonResponse(error);
                    resp->setStatusCode(k429TooManyRequests);
                    callback(resp);
                    return;
                }

                // Build response
                std::string order_id = std::to_string(++order_counter);

                Json::Value resp_json;
                resp_json["id"] = order_id;
                resp_json["sku"] = sku;
                resp_json["quantity"] = quantity;
                resp_json["tenant"] = tenant;

                // Add identity and subject from request attributes
                auto identity = req->attributes()->get<std::string>("identity");
                auto subject = req->attributes()->get<std::string>("subject");
                resp_json["identity"] = identity;
                resp_json["subject"] = subject;

                // Store order
                {
                    std::lock_guard<std::mutex> lock(orders_mutex);
                    orders_store[order_id] = resp_json;
                }

                spdlog::info("Order created: id={}, tenant={}, sku={}",
                            order_id, tenant, sku);

                // Release bulkhead after processing
                bulkhead.release();

                auto resp = HttpResponse::newHttpJsonResponse(resp_json);
                resp->setStatusCode(k201Created);
                callback(resp);

            } catch (const std::exception& e) {
                spdlog::error("Error creating order: {}", e.what());
                Json::Value error;
                error["detail"] = "internal server error";
                auto resp = HttpResponse::newHttpJsonResponse(error);
                resp->setStatusCode(k500InternalServerError);
                callback(resp);
            }
        },
        {Post});

    // ───────────────────────────────────────────────────────────────────────
    // POST /valet-key — Mint a scoped HMAC token
    // ───────────────────────────────────────────────────────────────────────
    app.registerHandler(
        "/valet-key",
        [](const HttpRequestPtr& req,
           std::function<void(const HttpResponsePtr&)>&& callback) {
            auto resource = req->getParameter("resource");
            auto operation = req->getParameter("operation");

            if (resource.empty() || operation.empty()) {
                Json::Value error;
                error["detail"] = "missing resource or operation parameter";
                auto resp = HttpResponse::newHttpJsonResponse(error);
                resp->setStatusCode(k400BadRequest);
                callback(resp);
                return;
            }

            // Generate expiration (5 minutes from now)
            auto now = std::chrono::system_clock::now();
            auto expires_time = now + std::chrono::minutes(5);
            auto expires = std::chrono::duration_cast<std::chrono::seconds>(
                expires_time.time_since_epoch()).count();

            // Build message to sign: resource|operation|expires
            std::ostringstream message;
            message << resource << "|" << operation << "|" << expires;

            std::string token = hmac_sha256(VALET_SECRET, message.str());

            Json::Value resp_json;
            resp_json["resource"] = resource;
            resp_json["operation"] = operation;
            resp_json["expires"] = static_cast<Json::Int64>(expires);
            resp_json["token"] = token;

            spdlog::info("Valet key minted: resource={}, operation={}, expires={}",
                        resource, operation, expires);

            callback(HttpResponse::newHttpJsonResponse(resp_json));
        },
        {Post});

    // ───────────────────────────────────────────────────────────────────────
    // GET /verify-valet — Verify a valet key
    // ───────────────────────────────────────────────────────────────────────
    app.registerHandler(
        "/verify-valet",
        [](const HttpRequestPtr& req,
           std::function<void(const HttpResponsePtr&)>&& callback) {
            auto resource = req->getParameter("resource");
            auto operation = req->getParameter("operation");
            auto expires_str = req->getParameter("expires");
            auto token = req->getParameter("token");

            if (resource.empty() || operation.empty() ||
                expires_str.empty() || token.empty()) {
                Json::Value error;
                error["detail"] = "missing parameters";
                auto resp = HttpResponse::newHttpJsonResponse(error);
                resp->setStatusCode(k400BadRequest);
                callback(resp);
                return;
            }

            // Check expiration
            try {
                long long expires = std::stoll(expires_str);
                auto now = std::chrono::system_clock::now();
                auto now_epoch = std::chrono::duration_cast<std::chrono::seconds>(
                    now.time_since_epoch()).count();

                if (now_epoch > expires) {
                    Json::Value error;
                    error["detail"] = "token expired";
                    auto resp = HttpResponse::newHttpJsonResponse(error);
                    resp->setStatusCode(k403Forbidden);
                    callback(resp);
                    return;
                }

                // Reconstruct message and verify HMAC
                std::ostringstream message;
                message << resource << "|" << operation << "|" << expires;
                std::string expected_token = hmac_sha256(VALET_SECRET, message.str());

                if (token != expected_token) {
                    Json::Value error;
                    error["detail"] = "invalid token";
                    auto resp = HttpResponse::newHttpJsonResponse(error);
                    resp->setStatusCode(k403Forbidden);
                    callback(resp);
                    return;
                }

                // Valid token
                Json::Value resp_json;
                resp_json["valid"] = true;
                resp_json["resource"] = resource;
                resp_json["operation"] = operation;

                spdlog::debug("Valet key verified: resource={}, operation={}",
                             resource, operation);

                callback(HttpResponse::newHttpJsonResponse(resp_json));

            } catch (const std::exception& e) {
                spdlog::error("Error verifying valet key: {}", e.what());
                Json::Value error;
                error["detail"] = "invalid parameters";
                auto resp = HttpResponse::newHttpJsonResponse(error);
                resp->setStatusCode(k400BadRequest);
                callback(resp);
            }
        },
        {Get});

    // ───────────────────────────────────────────────────────────────────────
    // GET /bulkhead-state — Show bulkhead state for all tenants
    // ───────────────────────────────────────────────────────────────────────
    app.registerHandler(
        "/bulkhead-state",
        [](const HttpRequestPtr& req,
           std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value state = bulkhead_manager.get_state();
            callback(HttpResponse::newHttpJsonResponse(state));
        },
        {Get});

    // ───────────────────────────────────────────────────────────────────────
    // Start server
    // ───────────────────────────────────────────────────────────────────────
    app.addListener("0.0.0.0", 8080)
       .setThreadNum(4)
       .run();

    return 0;
}
