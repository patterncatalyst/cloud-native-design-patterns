#include <drogon/drogon.h>
#include <mutex>
#include <string>

using namespace drogon;

struct RoutingRules {
    std::mutex mu;
    int vip_threshold = 1000;
    std::string priority_topic = "orders.priority";
    std::string default_topic = "orders.default";
};

int main() {
    auto rules = std::make_shared<RoutingRules>();

    app().setLogLevel(trantor::Logger::kInfo);
    app().setUploadPath("/tmp");

    app().registerHandler("/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value resp;
            resp["status"] = "ok";
            callback(HttpResponse::newHttpJsonResponse(resp));
        },
        {Get});

    app().registerHandler("/orders",
        [rules](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            auto body = req->getJsonObject();
            if (!body) {
                auto resp = HttpResponse::newHttpJsonResponse(Json::Value("invalid json"));
                resp->setStatusCode(k400BadRequest);
                callback(resp);
                return;
            }

            std::string sku = (*body)["sku"].asString();
            double amount = (*body)["amount"].asDouble();

            std::string routedTo;
            bool vip;
            {
                std::lock_guard<std::mutex> lock(rules->mu);
                vip = amount >= rules->vip_threshold;
                routedTo = vip ? rules->priority_topic : rules->default_topic;
            }

            LOG_INFO << "ROUTED sku=" << sku << " amount=" << amount
                     << " -> " << routedTo << (vip ? " (VIP)" : "");

            Json::Value resp;
            resp["routed_to"] = routedTo;
            resp["vip"] = vip;
            resp["amount"] = amount;

            auto httpResp = HttpResponse::newHttpJsonResponse(resp);
            httpResp->setStatusCode(k201Created);
            callback(httpResp);
        },
        {Post});

    app().registerHandler("/rules",
        [rules](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value resp;
            {
                std::lock_guard<std::mutex> lock(rules->mu);
                resp["vip_threshold"] = rules->vip_threshold;
                resp["priority_topic"] = rules->priority_topic;
                resp["default_topic"] = rules->default_topic;
            }
            callback(HttpResponse::newHttpJsonResponse(resp));
        },
        {Get});

    app().registerHandler("/rules",
        [rules](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            auto body = req->getJsonObject();
            if (!body) {
                auto resp = HttpResponse::newHttpJsonResponse(Json::Value("invalid json"));
                resp->setStatusCode(k400BadRequest);
                callback(resp);
                return;
            }

            {
                std::lock_guard<std::mutex> lock(rules->mu);
                if (body->isMember("vip_threshold"))
                    rules->vip_threshold = (*body)["vip_threshold"].asInt();
                if (body->isMember("priority_topic"))
                    rules->priority_topic = (*body)["priority_topic"].asString();
                if (body->isMember("default_topic"))
                    rules->default_topic = (*body)["default_topic"].asString();
            }

            Json::Value resp;
            {
                std::lock_guard<std::mutex> lock(rules->mu);
                resp["vip_threshold"] = rules->vip_threshold;
                resp["priority_topic"] = rules->priority_topic;
                resp["default_topic"] = rules->default_topic;
                LOG_INFO << "RULES_UPDATED " << resp.toStyledString();
            }
            callback(HttpResponse::newHttpJsonResponse(resp));
        },
        {Put});

    LOG_INFO << "Router service starting on 0.0.0.0:8080";
    app().addListener("0.0.0.0", 8080).run();
}
