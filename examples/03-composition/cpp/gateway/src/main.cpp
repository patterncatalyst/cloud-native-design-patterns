#include <drogon/drogon.h>
#include <grpcpp/grpcpp.h>
#include "inventory.grpc.pb.h"
#include <iostream>
#include <regex>
#include <set>

using namespace drogon;

static std::string g_order_api_url;
static std::unique_ptr<inventory::Inventory::Stub> g_inv_stub;

static std::unordered_map<std::string, int> batch_load_stock(const std::set<std::string>& skus) {
    inventory::GetStockBatchRequest req;
    for (auto& s : skus) req.add_skus(s);

    inventory::GetStockBatchReply reply;
    grpc::ClientContext ctx;
    auto status = g_inv_stub->GetStockBatch(&ctx, req, &reply);

    std::unordered_map<std::string, int> result;
    if (status.ok()) {
        for (const auto& item : reply.items()) {
            result[item.sku()] = item.available();
        }
        std::cerr << "DataLoader batched " << skus.size()
                  << " skus in one gRPC call" << std::endl;
    }
    return result;
}

static void handle_orders_query(const std::string& fields_str, int limit,
                                std::function<void(const HttpResponsePtr&)> cb) {
    bool want_stock = fields_str.find("stock") != std::string::npos;

    auto client = HttpClient::newHttpClient(g_order_api_url);
    auto req = HttpRequest::newHttpRequest();
    req->setMethod(Get);
    req->setPath("/orders?limit=" + std::to_string(limit));

    client->sendRequest(req,
        [fields_str, want_stock, cb = std::move(cb)](ReqResult result, const HttpResponsePtr& resp) {
            if (result != ReqResult::Ok) {
                Json::Value err;
                err["errors"][0]["message"] = "order-api unreachable";
                cb(HttpResponse::newHttpJsonResponse(err));
                return;
            }

            Json::CharReaderBuilder rb;
            Json::Value orders_arr;
            std::string body_str(resp->body());
            std::istringstream ss(body_str);
            Json::parseFromStream(rb, ss, &orders_arr, nullptr);

            std::unordered_map<std::string, int> stock_map;
            if (want_stock) {
                std::set<std::string> skus;
                for (const auto& o : orders_arr) skus.insert(o["sku"].asString());
                stock_map = batch_load_stock(skus);
            }

            Json::Value items(Json::arrayValue);
            for (const auto& o : orders_arr) {
                Json::Value item;
                if (fields_str.find("id") != std::string::npos) item["id"] = o["id"];
                if (fields_str.find("sku") != std::string::npos) item["sku"] = o["sku"];
                if (fields_str.find("quantity") != std::string::npos) item["quantity"] = o["quantity"];
                if (fields_str.find("status") != std::string::npos) item["status"] = o["status"];
                if (want_stock) {
                    auto it = stock_map.find(o["sku"].asString());
                    item["stock"] = (it != stock_map.end()) ? it->second : 0;
                }
                items.append(item);
            }

            Json::Value response;
            response["data"]["orders"] = items;
            cb(HttpResponse::newHttpJsonResponse(response));
        });
}

static void handle_order_query(const std::string& id, const std::string& fields_str,
                               std::function<void(const HttpResponsePtr&)> cb) {
    auto client = HttpClient::newHttpClient(g_order_api_url);
    auto req = HttpRequest::newHttpRequest();
    req->setMethod(Get);
    req->setPath("/orders/" + id);

    client->sendRequest(req,
        [fields_str, cb = std::move(cb)](ReqResult result, const HttpResponsePtr& resp) {
            Json::Value response;
            if (result != ReqResult::Ok || resp->statusCode() == k404NotFound) {
                response["data"]["order"] = Json::nullValue;
                cb(HttpResponse::newHttpJsonResponse(response));
                return;
            }

            Json::CharReaderBuilder rb;
            Json::Value o;
            std::string body_str(resp->body());
            std::istringstream ss(body_str);
            Json::parseFromStream(rb, ss, &o, nullptr);

            Json::Value item;
            if (fields_str.find("id") != std::string::npos) item["id"] = o["id"];
            if (fields_str.find("sku") != std::string::npos) item["sku"] = o["sku"];
            if (fields_str.find("quantity") != std::string::npos) item["quantity"] = o["quantity"];
            if (fields_str.find("status") != std::string::npos) item["status"] = o["status"];
            if (fields_str.find("stock") != std::string::npos) {
                std::set<std::string> skus = {o["sku"].asString()};
                auto stock_map = batch_load_stock(skus);
                auto it = stock_map.find(o["sku"].asString());
                item["stock"] = (it != stock_map.end()) ? it->second : 0;
            }
            response["data"]["order"] = item;
            cb(HttpResponse::newHttpJsonResponse(response));
        });
}

int main() {
    auto env_api = std::getenv("ORDER_API_URL");
    g_order_api_url = env_api ? env_api : "http://order-api:8081";

    auto env_inv = std::getenv("INVENTORY_ADDR");
    std::string inv_addr = env_inv ? env_inv : "inventory:50051";
    auto channel = grpc::CreateChannel(inv_addr, grpc::InsecureChannelCredentials());
    g_inv_stub = inventory::Inventory::NewStub(channel);

    std::cerr << "gateway started" << std::endl;

    app().setLogLevel(trantor::Logger::kInfo);
    app().addListener("0.0.0.0", 8080);

    app().registerHandler("/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& cb) {
            Json::Value r;
            r["status"] = "ok";
            cb(HttpResponse::newHttpJsonResponse(r));
        },
        {Get});

    app().registerHandler("/graphql",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& cb) {
            auto body = req->getJsonObject();
            if (!body || !body->isMember("query")) {
                Json::Value err;
                err["errors"][0]["message"] = "missing query field";
                cb(HttpResponse::newHttpJsonResponse(err));
                return;
            }

            std::string query = (*body)["query"].asString();

            std::regex orders_re(R"re(orders\s*(?:\(\s*limit\s*:\s*(\d+)\s*\))?\s*\{([^}]*)\})re");
            std::regex order_re(R"re(order\s*\(\s*id\s*:\s*\\?"([^"\\]+)\\?"\s*\)\s*\{([^}]*)\})re");
            std::smatch match;

            if (std::regex_search(query, match, orders_re)) {
                int limit = match[1].matched ? std::stoi(match[1].str()) : 50;
                std::string fields = match[2].str();
                handle_orders_query(fields, limit, std::move(cb));
            } else if (std::regex_search(query, match, order_re)) {
                std::string id = match[1].str();
                std::string fields = match[2].str();
                handle_order_query(id, fields, std::move(cb));
            } else {
                Json::Value err;
                err["errors"][0]["message"] = "unsupported query";
                cb(HttpResponse::newHttpJsonResponse(err));
            }
        },
        {Post});

    app().run();
    return 0;
}
