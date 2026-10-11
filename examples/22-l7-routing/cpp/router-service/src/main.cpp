#include <drogon/drogon.h>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <memory>
#include <mutex>
#include <sstream>
#include <string>

#include "routing_engine.hpp"

using namespace drogon;

// Live rule inputs (GET/PUT /rules). The policy itself is the Lua script.
struct RoutingRules {
    std::mutex mu;
    cndp::routing::Rules values;

    cndp::routing::Rules snapshot() {
        std::lock_guard<std::mutex> lock(mu);
        return values;
    }
};

// JSON numbers that are whole print without a fraction (1000, not 1000.0).
static Json::Value number(double v) {
    if (std::floor(v) == v && std::fabs(v) < 9e15) return Json::Value(static_cast<Json::Int64>(v));
    return Json::Value(v);
}

static Json::Value rules_json(const cndp::routing::Rules& r) {
    Json::Value j;
    j["vip_threshold"] = number(r.vip_threshold);
    j["priority_topic"] = r.priority_topic;
    j["default_topic"] = r.default_topic;
    return j;
}

static std::string load_script() {
    const char* path = std::getenv("ROUTING_RULES_FILE");
    if (!path) path = "/usr/share/router-service/routing.lua";
    std::ifstream in(path);
    if (!in) throw std::runtime_error(std::string("cannot read rules file ") + path);
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

int main() {
    auto rules = std::make_shared<RoutingRules>();

    std::shared_ptr<cndp::routing::RoutingEngine> engine;
    try {
        // Compiles the script once at startup: a bad rules file stops the service here.
        engine = std::make_shared<cndp::routing::RoutingEngine>(load_script());
    } catch (const std::exception& e) {
        std::cerr << "invalid rules script: " << e.what() << std::endl;
        return 1;
    }

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
        [rules, engine](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            auto body = req->getJsonObject();
            if (!body) {
                auto resp = HttpResponse::newHttpJsonResponse(Json::Value("invalid json"));
                resp->setStatusCode(k400BadRequest);
                callback(resp);
                return;
            }

            const std::string sku = (*body)["sku"].asString();
            const int quantity = (*body)["quantity"].asInt();
            const double amount = (*body)["amount"].asDouble();

            cndp::routing::Decision d;
            try {
                d = engine->route(sku, quantity, amount, rules->snapshot());
            } catch (const std::exception& e) {
                LOG_ERROR << "rule evaluation failed: " << e.what();
                Json::Value err;
                err["detail"] = "rule evaluation failed";
                auto resp = HttpResponse::newHttpJsonResponse(err);
                resp->setStatusCode(k500InternalServerError);
                callback(resp);
                return;
            }

            LOG_INFO << "ROUTED sku=" << sku << " amount=" << amount
                     << " -> " << d.topic << (d.vip ? " (VIP)" : "");

            Json::Value resp;
            resp["routed_to"] = d.topic;
            resp["vip"] = d.vip;
            resp["amount"] = number(amount);

            auto httpResp = HttpResponse::newHttpJsonResponse(resp);
            httpResp->setStatusCode(k201Created);
            callback(httpResp);
        },
        {Post});

    app().registerHandler("/rules",
        [rules](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            callback(HttpResponse::newHttpJsonResponse(rules_json(rules->snapshot())));
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

            cndp::routing::Rules now;
            {
                std::lock_guard<std::mutex> lock(rules->mu);
                auto& v = rules->values;
                if ((*body)["vip_threshold"].isNumeric()) v.vip_threshold = (*body)["vip_threshold"].asDouble();
                if ((*body)["priority_topic"].isString()) v.priority_topic = (*body)["priority_topic"].asString();
                if ((*body)["default_topic"].isString()) v.default_topic = (*body)["default_topic"].asString();
                now = v;
            }
            LOG_INFO << "RULES_UPDATED vip_threshold=" << now.vip_threshold;
            callback(HttpResponse::newHttpJsonResponse(rules_json(now)));
        },
        {Put});

    LOG_INFO << "Router service starting on 0.0.0.0:8080 (rules engine: " << LUA_RELEASE << ")";
    app().addListener("0.0.0.0", 8080).run();
}
