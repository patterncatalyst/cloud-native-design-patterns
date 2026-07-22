#include <drogon/drogon.h>
#include <mutex>
#include <unordered_map>
#include <iostream>

using namespace drogon;

static std::mutex g_mu;
static std::unordered_map<std::string, std::string> g_tenant_routes;
static std::string g_default_service;
static std::unordered_map<std::string, std::string> g_service_urls;

static void forward_request(const std::string& upstream, HttpMethod method,
                            const std::string& path, const std::string& body,
                            std::function<void(const HttpResponsePtr&)> cb) {
    auto client = HttpClient::newHttpClient(upstream);
    auto req = HttpRequest::newHttpRequest();
    req->setMethod(method);
    req->setPath(path);
    if (!body.empty()) {
        req->setContentTypeCode(CT_APPLICATION_JSON);
        req->setBody(body);
    }
    client->sendRequest(req,
        [cb = std::move(cb)](ReqResult result, const HttpResponsePtr& resp) {
            if (result == ReqResult::Ok) {
                auto r = HttpResponse::newHttpResponse();
                r->setStatusCode(resp->statusCode());
                r->setContentTypeCode(CT_APPLICATION_JSON);
                r->setBody(std::string(resp->body()));
                cb(r);
            } else {
                auto r = HttpResponse::newHttpResponse();
                r->setStatusCode(k502BadGateway);
                cb(r);
            }
        });
}

static std::string resolve_upstream(const std::string& tenant) {
    std::lock_guard<std::mutex> lock(g_mu);
    auto it = g_tenant_routes.find(tenant);
    std::string svc = (it != g_tenant_routes.end()) ? it->second : g_default_service;
    auto uit = g_service_urls.find(svc);
    if (uit != g_service_urls.end()) return uit->second;
    return g_service_urls[g_default_service];
}

int main() {
    auto env_m = std::getenv("MONOLITH_URL");
    auto env_n = std::getenv("NEW_SERVICE_URL");
    g_service_urls["monolith"] = env_m ? env_m : "http://monolith:8080";
    g_service_urls["new-service"] = env_n ? env_n : "http://new-service:8080";

    g_tenant_routes["acme"] = "new-service";
    g_default_service = "monolith";

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
            std::string tenant;
            if (body && body->isMember("tenant")) {
                tenant = (*body)["tenant"].asString();
            }
            std::string upstream = resolve_upstream(tenant);
            std::cerr << "routing tenant=" << tenant << " to " << upstream << std::endl;
            forward_request(upstream, Post, "/orders", std::string(req->body()), std::move(cb));
        },
        {Post});

    app().registerHandler("/orders/{order_id}",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& cb,
           const std::string& order_id) {
            std::string upstream = resolve_upstream("");
            forward_request(upstream, Get, "/orders/" + order_id, "", std::move(cb));
        },
        {Get});

    app().registerHandler("/rules",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& cb) {
            std::lock_guard<std::mutex> lock(g_mu);
            Json::Value r;
            Json::Value tr(Json::objectValue);
            for (auto& [k, v] : g_tenant_routes) tr[k] = v;
            r["tenant_routes"] = tr;
            r["default"] = g_default_service;
            cb(HttpResponse::newHttpJsonResponse(r));
        },
        {Get});

    app().registerHandler("/rules",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& cb) {
            auto body = req->getJsonObject();
            if (!body) {
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k400BadRequest);
                cb(resp);
                return;
            }
            {
                std::lock_guard<std::mutex> lock(g_mu);
                if (body->isMember("tenant_routes")) {
                    g_tenant_routes.clear();
                    auto& tr = (*body)["tenant_routes"];
                    for (auto it = tr.begin(); it != tr.end(); ++it) {
                        g_tenant_routes[it.key().asString()] = it->asString();
                    }
                }
                if (body->isMember("default")) {
                    g_default_service = (*body)["default"].asString();
                }
            }
            std::cerr << "rules updated" << std::endl;
            Json::Value r;
            r["status"] = "updated";
            cb(HttpResponse::newHttpJsonResponse(r));
        },
        {Put});

    app().run();
    return 0;
}
