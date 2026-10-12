#include <grpcpp/grpcpp.h>
#include <spdlog/spdlog.h>
#include "inventory.grpc.pb.h"
#include <mutex>
#include <unordered_map>

static std::mutex g_mu;
static std::unordered_map<std::string, int> g_stock;
static int g_initial_stock = 100;

class InventoryServiceImpl final : public inventory::Inventory::Service {
    grpc::Status ReserveStock(grpc::ServerContext*,
                              const inventory::ReserveRequest* req,
                              inventory::ReserveReply* reply) override {
        std::lock_guard<std::mutex> lock(g_mu);
        auto& stock = g_stock[req->sku()];
        if (stock == 0) stock = g_initial_stock;

        int remaining = stock - req->quantity();
        if (remaining >= 0) {
            stock = remaining;
            reply->set_reserved(true);
            reply->set_remaining(remaining);
            spdlog::info("reserved sku={} qty={} remaining={}", req->sku(), req->quantity(), remaining);
        } else {
            reply->set_reserved(false);
            reply->set_remaining(stock);
            spdlog::info("insufficient stock sku={} requested={} available={}",
                         req->sku(), req->quantity(), stock);
        }
        return grpc::Status::OK;
    }
};

int main() {
    auto env = std::getenv("INITIAL_STOCK");
    if (env) g_initial_stock = std::atoi(env);

    std::string addr("0.0.0.0:50051");
    InventoryServiceImpl service;
    grpc::ServerBuilder builder;
    builder.AddListeningPort(addr, grpc::InsecureServerCredentials());
    builder.RegisterService(&service);
    auto server = builder.BuildAndStart();
    spdlog::info("inventory gRPC server listening on {}", addr);
    server->Wait();
    return 0;
}
