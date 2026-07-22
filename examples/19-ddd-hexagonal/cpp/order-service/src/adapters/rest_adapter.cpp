// adapters/rest_adapter.cpp — Drogon REST driving adapter.
//
// HTTP handlers that drive the use case. This is an adapter — it depends on
// the domain (use cases, commands) and on Drogon (HttpRequest, HttpResponse).

#include "../domain/service.hpp"
#include "../domain/ports.hpp"
#include <drogon/HttpAppFramework.h>
#include <drogon/HttpRequest.h>
#include <drogon/HttpResponse.h>
#include <json/json.h>
#include <spdlog/spdlog.h>

using namespace drogon;

namespace cndp::adapters {

void register_rest_handlers(domain::PlaceOrderUseCase& use_case,
                            domain::OrderRepository& repository) {
    auto& drogon_app = app();

    // Healthcheck
    drogon_app.registerHandler("/healthz",
        [](const HttpRequestPtr& req,
           std::function<void(const HttpResponsePtr&)>&& cb) {
            Json::Value resp;
            resp["status"] = "ok";
            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            cb(http_resp);
        },
        {Get});

    // POST /orders — create an order
    drogon_app.registerHandler("/orders",
        [&use_case](const HttpRequestPtr& req,
                    std::function<void(const HttpResponsePtr&)>&& cb) {
            try {
                auto body = req->getJsonObject();
                if (!body) {
                    auto resp = HttpResponse::newHttpResponse();
                    resp->setStatusCode(k400BadRequest);
                    cb(resp);
                    return;
                }

                domain::PlaceOrderCmd cmd;
                cmd.sku = (*body).get("sku", "").asString();
                cmd.quantity = (*body).get("quantity", 0).asInt();

                // Execute the use case
                auto order = use_case.execute(cmd);

                Json::Value resp;
                resp["id"] = order.id;
                resp["sku"] = order.sku;
                resp["quantity"] = order.quantity;
                resp["status"] = order.status;

                auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                http_resp->setStatusCode(k201Created);
                cb(http_resp);
            } catch (const std::invalid_argument& e) {
                // Domain validation failure → 422 Unprocessable Entity
                Json::Value resp;
                resp["error"] = e.what();
                auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                http_resp->setStatusCode(k422UnprocessableEntity);
                cb(http_resp);
            } catch (const std::exception& e) {
                spdlog::error("POST /orders failed: {}", e.what());
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k500InternalServerError);
                cb(resp);
            }
        },
        {Post});

    // GET /orders/{id} — retrieve a single order
    drogon_app.registerHandler("/orders/{1}",
        [&repository](const HttpRequestPtr& req,
                      std::function<void(const HttpResponsePtr&)>&& cb,
                      const std::string& id) {
            try {
                auto order_opt = repository.find_by_id(id);
                if (!order_opt) {
                    auto resp = HttpResponse::newHttpResponse();
                    resp->setStatusCode(k404NotFound);
                    cb(resp);
                    return;
                }

                auto& order = *order_opt;
                Json::Value resp;
                resp["id"] = order.id;
                resp["sku"] = order.sku;
                resp["quantity"] = order.quantity;
                resp["status"] = order.status;

                auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                cb(http_resp);
            } catch (const std::exception& e) {
                spdlog::error("GET /orders/{{id}} failed: {}", e.what());
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k500InternalServerError);
                cb(resp);
            }
        },
        {Get});

    // GET /orders — list all orders
    drogon_app.registerHandler("/orders",
        [&repository](const HttpRequestPtr& req,
                      std::function<void(const HttpResponsePtr&)>&& cb) {
            try {
                auto orders = repository.find_all();
                Json::Value resp(Json::arrayValue);
                for (const auto& order : orders) {
                    Json::Value order_json;
                    order_json["id"] = order.id;
                    order_json["sku"] = order.sku;
                    order_json["quantity"] = order.quantity;
                    order_json["status"] = order.status;
                    resp.append(order_json);
                }

                auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                cb(http_resp);
            } catch (const std::exception& e) {
                spdlog::error("GET /orders failed: {}", e.what());
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k500InternalServerError);
                cb(resp);
            }
        },
        {Get});
}

}  // namespace cndp::adapters
