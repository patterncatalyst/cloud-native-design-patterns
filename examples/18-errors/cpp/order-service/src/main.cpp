#include <drogon/drogon.h>
#include <grpcpp/grpcpp.h>
#include <inventory.grpc.pb.h>
#include <chrono>
#include <random>
#include <sstream>
#include <iomanip>

using namespace drogon;

// Generate a simple hex trace ID
std::string generateTraceId() {
    static std::random_device rd;
    static std::mt19937_64 gen(rd());
    static std::uniform_int_distribution<uint64_t> dis;

    std::ostringstream oss;
    oss << std::hex << std::setfill('0') << std::setw(16) << dis(gen);
    return oss.str();
}

// Global gRPC stub (initialized in main)
std::unique_ptr<inventory::InventoryService::Stub> inventoryStub;

class OrderController {
public:
    static void healthz(const HttpRequestPtr& req,
                       std::function<void(const HttpResponsePtr&)>&& callback) {
        Json::Value resp;
        resp["status"] = "ok";
        auto httpResp = HttpResponse::newHttpJsonResponse(resp);
        callback(httpResp);
    }

    static void createOrder(const HttpRequestPtr& req,
                           std::function<void(const HttpResponsePtr&)>&& callback) {
        auto traceId = generateTraceId();

        // Parse JSON body
        auto jsonPtr = req->getJsonObject();
        if (!jsonPtr) {
            Json::Value error;
            error["code"] = "VALIDATION_ERROR";
            error["detail"] = "invalid JSON body";
            error["traceId"] = traceId;
            auto resp = HttpResponse::newHttpJsonResponse(error);
            resp->setStatusCode(k422UnprocessableEntity);
            callback(resp);
            return;
        }

        std::string sku = (*jsonPtr).get("sku", "").asString();
        int quantity = (*jsonPtr).get("quantity", 0).asInt();

        // Validate input
        if (sku.empty() || quantity <= 0) {
            Json::Value error;
            error["code"] = "VALIDATION_ERROR";
            std::string detail;
            if (sku.empty() && quantity <= 0) {
                detail = "sku is required; quantity must be > 0";
            } else if (sku.empty()) {
                detail = "sku is required";
            } else {
                detail = "quantity must be > 0";
            }
            error["detail"] = detail;
            error["traceId"] = traceId;
            auto resp = HttpResponse::newHttpJsonResponse(error);
            resp->setStatusCode(k422UnprocessableEntity);
            callback(resp);
            return;
        }

        // Call gRPC inventory service
        grpc::ClientContext context;
        context.set_deadline(std::chrono::system_clock::now() + std::chrono::seconds(5));

        inventory::ReserveRequest grpcReq;
        grpcReq.set_sku(sku);
        grpcReq.set_quantity(quantity);

        inventory::ReserveResponse grpcResp;
        grpc::Status status = inventoryStub->ReserveStock(&context, grpcReq, &grpcResp);

        if (!status.ok()) {
            // gRPC call failed - inventory service unavailable
            Json::Value error;
            error["code"] = "INVENTORY_UNAVAILABLE";
            error["detail"] = "inventory service unavailable";
            error["retryable"] = true;
            error["retryAfter"] = 5;
            error["traceId"] = traceId;
            auto resp = HttpResponse::newHttpJsonResponse(error);
            resp->setStatusCode(k503ServiceUnavailable);
            resp->addHeader("Retry-After", "5");
            callback(resp);
            return;
        }

        if (!grpcResp.confirmed()) {
            // Stock unavailable
            Json::Value error;
            error["code"] = "STOCK_UNAVAILABLE";
            error["detail"] = "insufficient stock for " + sku;
            error["retryable"] = false;
            error["traceId"] = traceId;
            auto resp = HttpResponse::newHttpJsonResponse(error);
            resp->setStatusCode(k409Conflict);
            callback(resp);
            return;
        }

        // Success - return created order
        Json::Value order;
        order["orderId"] = traceId;
        order["sku"] = sku;
        order["quantity"] = quantity;
        order["status"] = "confirmed";
        auto resp = HttpResponse::newHttpJsonResponse(order);
        resp->setStatusCode(k201Created);
        callback(resp);
    }
};

int main() {
    // Initialize gRPC stub
    std::string inventoryHost = std::getenv("INVENTORY_HOST")
        ? std::getenv("INVENTORY_HOST")
        : "localhost:50051";

    auto channel = grpc::CreateChannel(inventoryHost, grpc::InsecureChannelCredentials());
    inventoryStub = inventory::InventoryService::NewStub(channel);

    // Configure Drogon
    app().setLogLevel(trantor::Logger::kInfo);
    app().addListener("0.0.0.0", 8080);
    app().setUploadPath("/tmp");

    // Register routes using lambdas
    app().registerHandler("/healthz",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            OrderController::healthz(req, std::move(callback));
        },
        {Get});

    app().registerHandler("/orders",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            OrderController::createOrder(req, std::move(callback));
        },
        {Post});

    LOG_INFO << "Order service starting on port 8080, inventory at " << inventoryHost;
    app().run();
    return 0;
}
