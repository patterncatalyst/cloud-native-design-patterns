// order-service (02 communications): REST + GraphQL in, gRPC out to inventory, order.placed
// events out to Kafka.
//
//   Drogon          REST and the /graphql endpoint
//   grpc++ (sync)   ReserveStock call to the inventory service
//   libpq           orders table, parameterised statements
//   cppgraphqlgen   GraphQL schema, generated resolvers (src/graphql/)
//   rdkafka++       order.placed producer with delivery reports

#include <cstdlib>
#include <iostream>
#include <memory>
#include <random>
#include <string>

#include <drogon/drogon.h>
#include <grpcpp/grpcpp.h>

#include "graphql_api.hpp"
#include "inventory.grpc.pb.h"
#include "kafka_publisher.hpp"
#include "pg_orders.hpp"

using namespace drogon;

namespace {

std::string generate_uuid() {
    static thread_local std::mt19937 gen(std::random_device{}());
    std::uniform_int_distribution<uint32_t> dist(0, 0xFFFFFFFF);
    auto r = [&]() { return dist(gen); };
    char buf[37];
    uint32_t a = r(), b = r(), c = r(), d = r();
    snprintf(buf, sizeof(buf), "%08x-%04x-%04x-%04x-%04x%08x", a, (b >> 16) & 0xFFFF,
             0x4000 | ((b >> 4) & 0x0FFF), 0x8000 | (c & 0x3FFF), (c >> 16) & 0xFFFF, d);
    return std::string(buf);
}

Json::Value to_json(const cndp::Order& o) {
    Json::Value j;
    j["id"] = o.id;
    j["sku"] = o.sku;
    j["quantity"] = o.quantity;
    j["status"] = o.status;
    return j;
}

HttpResponsePtr status_only(HttpStatusCode code) {
    auto resp = HttpResponse::newHttpResponse();
    resp->setStatusCode(code);
    return resp;
}

const char* env_or(const char* name, const char* fallback) {
    const char* v = std::getenv(name);
    return v ? v : fallback;
}

}  // namespace

int main() {
    std::shared_ptr<cndp::OrderRepo> repo;
    try {
        repo = std::make_shared<cndp::PgOrderRepo>(
            env_or("PG_CONNINFO", "host=postgres port=5432 dbname=appdb user=appuser password=apppass"));
    } catch (const std::exception& e) {
        std::cerr << e.what() << std::endl;
        return 1;
    }

    auto channel = grpc::CreateChannel(env_or("INVENTORY_ADDR", "inventory:50051"),
                                       grpc::InsecureChannelCredentials());
    auto inventory_stub = inventory::Inventory::NewStub(channel);

    std::unique_ptr<cndp::OrderPublisher> publisher;
    try {
        publisher = std::make_unique<cndp::OrderPublisher>(env_or("KAFKA_BOOTSTRAP", "kafka:9094"),
                                                           "order.placed");
    } catch (const std::exception& e) {
        std::cerr << e.what() << std::endl;
        return 1;
    }

    auto graphql = std::make_shared<cndp::gql::GraphQLApi>(repo);

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
        "/orders",
        [repo, &inventory_stub, &publisher](const HttpRequestPtr& req,
                                            std::function<void(const HttpResponsePtr&)>&& cb) {
            auto body = req->getJsonObject();
            if (!body) {
                cb(status_only(k400BadRequest));
                return;
            }

            std::string sku = (*body).get("sku", "").asString();
            int quantity = (*body).get("quantity", 0).asInt();

            if (sku.empty() || quantity <= 0) {
                Json::Value err;
                err["error"] = "sku must be non-empty and quantity must be positive";
                auto resp = HttpResponse::newHttpJsonResponse(err);
                resp->setStatusCode(k422UnprocessableEntity);
                cb(resp);
                return;
            }

            inventory::ReserveRequest greq;
            greq.set_sku(sku);
            greq.set_quantity(quantity);
            inventory::ReserveReply greply;
            grpc::ClientContext ctx;
            auto grpc_status = inventory_stub->ReserveStock(&ctx, greq, &greply);

            cndp::Order order{generate_uuid(), sku, quantity,
                              (grpc_status.ok() && greply.reserved()) ? "confirmed" : "rejected"};

            try {
                repo->insert(order);
            } catch (const std::exception& e) {
                std::cerr << "order insert failed: " << e.what() << std::endl;
                cb(status_only(k500InternalServerError));
                return;
            }

            Json::StreamWriterBuilder wb;
            wb["indentation"] = "";
            publisher->publish(Json::writeString(wb, to_json(order)));

            std::cerr << "order created id=" << order.id << " status=" << order.status << std::endl;
            auto resp = HttpResponse::newHttpJsonResponse(to_json(order));
            resp->setStatusCode(k201Created);
            cb(resp);
        },
        {Post});

    app().registerHandler(
        "/orders",
        [repo](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& cb) {
            int limit = 50;
            auto limit_str = req->getParameter("limit");
            if (!limit_str.empty()) {
                limit = std::atoi(limit_str.c_str());
                if (limit <= 0 || limit > 100) limit = 50;
            }

            std::vector<cndp::Order> orders;
            try {
                orders = repo->list(limit, req->getParameter("after"));
            } catch (const std::exception& e) {
                std::cerr << "order query failed: " << e.what() << std::endl;
                cb(status_only(k500InternalServerError));
                return;
            }

            Json::Value items(Json::arrayValue);
            for (const auto& o : orders) items.append(to_json(o));

            Json::Value result;
            result["items"] = items;
            if (static_cast<int>(orders.size()) == limit && !orders.empty()) {
                result["next_cursor"] = orders.back().id;
            }
            cb(HttpResponse::newHttpJsonResponse(result));
        },
        {Get});

    app().registerHandler(
        "/graphql",
        [graphql](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& cb) {
            auto body = req->getJsonObject();
            if (!body || !body->isMember("query")) {
                Json::Value err;
                err["errors"][0]["message"] = "missing query field";
                cb(HttpResponse::newHttpJsonResponse(err));
                return;
            }
            cb(HttpResponse::newHttpJsonResponse(graphql->execute(
                (*body)["query"].asString(), (*body).get("operationName", "").asString(),
                (*body).get("variables", Json::Value(Json::objectValue)))));
        },
        {Post});

    app().run();

    // The event loop has stopped (SIGTERM/SIGINT): flush the producer before exiting.
    publisher.reset();
    return 0;
}
