// gateway (03 composition): GraphQL in front of order-api (REST) and inventory (gRPC).
//
//   Drogon          the /graphql and /healthz endpoints, and the HTTP client for order-api
//   grpc++ (sync)   GetStockBatch on the inventory service
//   cppgraphqlgen   GraphQL schema and generated resolvers (src/graphql/)
//
// Resolvers block on order-api and inventory, so each GraphQL request runs on its own
// worker thread instead of on a Drogon event-loop thread.

#include <condition_variable>
#include <cstdlib>
#include <deque>
#include <functional>
#include <mutex>
#include <iostream>
#include <memory>
#include <set>
#include <string>
#include <thread>
#include <unordered_map>

#include <drogon/drogon.h>
#include <grpcpp/grpcpp.h>

#include "graphql_api.hpp"
#include "inventory.grpc.pb.h"

using namespace drogon;

namespace {

const char* env_or(const char* name, const char* fallback) {
    const char* v = std::getenv(name);
    return v ? v : fallback;
}

cndp::Order parse_order(const Json::Value& o) {
    return {o["id"].asString(), o["sku"].asString(), o["quantity"].asInt(), o["status"].asString()};
}

Json::Value parse_json(const std::string& text) {
    Json::CharReaderBuilder rb;
    Json::Value out;
    std::string errs;
    std::istringstream ss(text);
    if (!Json::parseFromStream(rb, ss, &out, &errs)) throw std::runtime_error("order-api returned invalid JSON");
    return out;
}

// Reads orders from order-api over HTTP. Called from worker threads only: the synchronous
// sendRequest must not run on an event-loop thread.
class HttpOrderSource : public cndp::OrderSource {
public:
    explicit HttpOrderSource(std::string base_url) : base_url_(std::move(base_url)) {}

    std::vector<cndp::Order> list(int limit) override {
        auto resp = get("/orders?limit=" + std::to_string(limit));
        std::vector<cndp::Order> out;
        for (const auto& o : parse_json(std::string(resp->body()))) out.push_back(parse_order(o));
        return out;
    }

    std::optional<cndp::Order> find(const std::string& id) override {
        auto resp = get("/orders/" + drogon::utils::urlEncodeComponent(id));
        if (resp->statusCode() == k404NotFound) return std::nullopt;
        return parse_order(parse_json(std::string(resp->body())));
    }

private:
    HttpResponsePtr get(const std::string& path) {
        auto client = HttpClient::newHttpClient(base_url_);
        auto req = HttpRequest::newHttpRequest();
        req->setMethod(Get);
        req->setPath(path);
        auto [result, resp] = client->sendRequest(req, 5.0);
        if (result != ReqResult::Ok || !resp) throw std::runtime_error("order-api unreachable");
        return resp;
    }

    std::string base_url_;
};

// Fixed pool of workers for the blocking resolvers, with a bounded queue: a burst of
// requests waits briefly or is turned away with 503 instead of spawning a thread each.
class WorkerPool {
public:
    WorkerPool(std::size_t threads, std::size_t max_queue) : max_queue_(max_queue) {
        for (std::size_t i = 0; i < threads; ++i) workers_.emplace_back([this] { run(); });
    }
    ~WorkerPool() {
        {
            std::lock_guard lock(mu_);
            stop_ = true;
        }
        cv_.notify_all();
        for (auto& t : workers_) t.join();
    }
    bool submit(std::function<void()> job) {
        {
            std::lock_guard lock(mu_);
            if (stop_ || queue_.size() >= max_queue_) return false;
            queue_.push_back(std::move(job));
        }
        cv_.notify_one();
        return true;
    }

private:
    void run() {
        for (;;) {
            std::function<void()> job;
            {
                std::unique_lock lock(mu_);
                cv_.wait(lock, [this] { return stop_ || !queue_.empty(); });
                if (queue_.empty()) return;
                job = std::move(queue_.front());
                queue_.pop_front();
            }
            job();
        }
    }

    std::size_t max_queue_;
    std::mutex mu_;
    std::condition_variable cv_;
    std::deque<std::function<void()>> queue_;
    std::vector<std::thread> workers_;
    bool stop_ = false;
};

}  // namespace

int main() {
    auto channel = grpc::CreateChannel(env_or("INVENTORY_ADDR", "inventory:50051"),
                                       grpc::InsecureChannelCredentials());
    std::shared_ptr<inventory::Inventory::Stub> inventory_stub = inventory::Inventory::NewStub(channel);

    // The DataLoader's batch function: one GetStockBatch call for the whole SKU set.
    cndp::StockBatchFn fetch_stock =
        [inventory_stub](const std::set<std::string>& skus) -> std::optional<std::unordered_map<std::string, int>> {
        inventory::GetStockBatchRequest req;
        for (const auto& s : skus) req.add_skus(s);
        inventory::GetStockBatchReply reply;
        grpc::ClientContext ctx;
        auto status = inventory_stub->GetStockBatch(&ctx, req, &reply);
        if (!status.ok()) {
            std::cerr << "inventory GetStockBatch failed: " << status.error_message() << std::endl;
            return std::nullopt;
        }
        std::unordered_map<std::string, int> result;
        for (const auto& item : reply.items()) result[item.sku()] = item.available();
        std::cerr << "DataLoader batched " << skus.size() << " skus in one gRPC call" << std::endl;
        return result;
    };

    auto source = std::make_shared<HttpOrderSource>(env_or("ORDER_API_URL", "http://order-api:8081"));
    auto graphql = std::make_shared<cndp::gql::GraphQLApi>(source, fetch_stock);

    const auto workers = static_cast<std::size_t>(std::atoi(env_or("GATEWAY_WORKERS", "16")));
    auto pool = std::make_shared<WorkerPool>(workers > 0 ? workers : 16, 256);

    std::cerr << "gateway started" << std::endl;

    app().setLogLevel(trantor::Logger::kInfo);
    app().addListener("0.0.0.0", 8080);

    app().registerHandler(
        "/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& cb) {
            Json::Value r;
            r["status"] = "ok";
            cb(HttpResponse::newHttpJsonResponse(r));
        },
        {Get});

    app().registerHandler(
        "/graphql",
        [graphql, pool](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& cb) {
            auto body = req->getJsonObject();
            if (!body || !body->isMember("query")) {
                Json::Value err;
                err["errors"][0]["message"] = "missing query field";
                cb(HttpResponse::newHttpJsonResponse(err));
                return;
            }
            std::string query = (*body)["query"].asString();
            std::string operation = (*body).get("operationName", "").asString();
            Json::Value variables = (*body).get("variables", Json::Value(Json::objectValue));
            auto shared_cb = std::make_shared<std::function<void(const HttpResponsePtr&)>>(std::move(cb));
            const bool queued = pool->submit([graphql, shared_cb, query = std::move(query),
                                              operation = std::move(operation), variables = std::move(variables)]() {
                (*shared_cb)(HttpResponse::newHttpJsonResponse(graphql->execute(query, operation, variables)));
            });
            if (!queued) {
                Json::Value err;
                err["errors"][0]["message"] = "gateway busy";
                auto resp = HttpResponse::newHttpJsonResponse(err);
                resp->setStatusCode(k503ServiceUnavailable);
                (*shared_cb)(resp);
            }
        },
        {Post});

    app().run();
    return 0;
}
