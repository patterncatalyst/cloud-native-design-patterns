#include <drogon/drogon.h>
#include <cstdio>
#include <string>

using namespace drogon;

int main() {
    // docker logs reads a pipe: line-buffer stdout so LOG_* lines show up as they are written.
    std::setvbuf(stdout, nullptr, _IOLBF, 0);
    std::string version = std::getenv("APP_VERSION") ? std::getenv("APP_VERSION") : "v1";

    app().setLogLevel(trantor::Logger::kInfo);
    app().setUploadPath("/tmp");

    app().registerHandler("/healthz",
        [version](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value resp;
            resp["status"] = "ok";
            resp["version"] = version;
            callback(HttpResponse::newHttpJsonResponse(resp));
        },
        {Get});

    app().registerHandler("/orders",
        [version](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value resp;
            resp["orders"] = Json::Value(Json::arrayValue);
            resp["version"] = version;
            callback(HttpResponse::newHttpJsonResponse(resp));
        },
        {Get});

    app().registerHandler("/orders",
        [version](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            auto body = req->getJsonObject();
            if (!body) {
                auto resp = HttpResponse::newHttpJsonResponse(Json::Value("invalid json"));
                resp->setStatusCode(k400BadRequest);
                callback(resp);
                return;
            }

            Json::Value resp;
            resp["id"] = "1";
            resp["sku"] = (*body)["sku"].asString();
            resp["quantity"] = (*body)["quantity"].asInt();
            resp["version"] = version;

            auto httpResp = HttpResponse::newHttpJsonResponse(resp);
            httpResp->setStatusCode(k201Created);
            callback(httpResp);
        },
        {Post});

    LOG_INFO << "Order service (" << version << ") starting on 0.0.0.0:8080";
    app().addListener("0.0.0.0", 8080).run();
}
