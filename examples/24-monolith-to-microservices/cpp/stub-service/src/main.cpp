#include <drogon/drogon.h>
#include <mutex>
#include <unordered_map>
#include <atomic>

using namespace drogon;

static std::string g_service_name;
static std::mutex g_mu;
static std::unordered_map<std::string, Json::Value> g_orders;
static std::unordered_map<std::string, int> g_access_counts;
static std::atomic<int> g_counter{0};

int main() {
    const char* env = std::getenv("SERVICE_NAME");
    g_service_name = env ? env : "unknown";

    app().setLogLevel(trantor::Logger::kInfo);
    app().addListener("0.0.0.0", 8080);
    app().setUploadPath("/tmp");

    app().registerHandler("/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value r;
            r["status"] = "ok";
            r["source"] = g_service_name;
            callback(HttpResponse::newHttpJsonResponse(r));
        },
        {Get});

    app().registerHandler("/orders",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            auto body = req->getJsonObject();
            if (!body) {
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k400BadRequest);
                callback(resp);
                return;
            }

            int id = ++g_counter;
            std::string oid = std::to_string(id);

            Json::Value order;
            order["id"] = oid;
            order["sku"] = (*body).get("sku", "").asString();
            order["quantity"] = (*body).get("quantity", 0).asInt();
            order["tenant"] = (*body).get("tenant", "").asString();
            order["source"] = g_service_name;

            {
                std::lock_guard<std::mutex> lock(g_mu);
                g_orders[oid] = order;
            }

            auto resp = HttpResponse::newHttpJsonResponse(order);
            resp->setStatusCode(k201Created);
            callback(resp);
        },
        {Post});

    app().registerHandler("/orders/{order_id}",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback,
           const std::string& order_id) {
            std::lock_guard<std::mutex> lock(g_mu);
            g_access_counts[order_id]++;

            auto it = g_orders.find(order_id);
            if (it != g_orders.end()) {
                callback(HttpResponse::newHttpJsonResponse(it->second));
            } else {
                Json::Value r;
                r["id"] = order_id;
                r["source"] = g_service_name;
                r["status"] = "stub";
                callback(HttpResponse::newHttpJsonResponse(r));
            }
        },
        {Get});

    app().registerHandler("/access-count/{order_id}",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback,
           const std::string& order_id) {
            std::lock_guard<std::mutex> lock(g_mu);
            Json::Value r;
            r["order_id"] = order_id;
            r["count"] = g_access_counts[order_id];
            callback(HttpResponse::newHttpJsonResponse(r));
        },
        {Get});

    app().run();
    return 0;
}
