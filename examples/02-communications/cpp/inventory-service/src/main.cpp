#include <grpcpp/grpcpp.h>
#include "inventory.grpc.pb.h"
#include <mutex>
#include <unordered_map>
#include <iostream>

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
            std::cerr << "reserved sku=" << req->sku()
                      << " qty=" << req->quantity()
                      << " remaining=" << remaining << std::endl;
        } else {
            reply->set_reserved(false);
            reply->set_remaining(stock);
            std::cerr << "insufficient stock sku=" << req->sku()
                      << " requested=" << req->quantity()
                      << " available=" << stock << std::endl;
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
    std::cerr << "inventory gRPC server listening on " << addr << std::endl;
    server->Wait();
    return 0;
}
