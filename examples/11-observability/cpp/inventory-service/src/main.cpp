// inventory-service: gRPC ReserveStock with OpenTelemetry C++ traces and metrics over OTLP/HTTP.
//
// The caller's W3C traceparent arrives as gRPC metadata; the ReserveStock server span is
// created as a child of it, so the order's trace continues here. Spans go out through the
// batch span processor and the stock.reservations counter through the periodic reader
// (telemetry.hpp); the exporters read OTEL_EXPORTER_OTLP_ENDPOINT.
#include <grpcpp/grpcpp.h>
#include <inventory.grpc.pb.h>
#include <spdlog/spdlog.h>

#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <map>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>

#include "telemetry.hpp"

static std::atomic<bool> g_shutdown{false};
static opentelemetry::nostd::unique_ptr<opentelemetry::metrics::Counter<uint64_t>> g_reservations;

void signal_handler(int) { g_shutdown = true; }

static int hex_nibble(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}

template <size_t N>
static bool parse_hex(const std::string& s, size_t off, uint8_t (&out)[N]) {
    for (size_t i = 0; i < N; ++i) {
        int hi = hex_nibble(s[off + 2 * i]), lo = hex_nibble(s[off + 2 * i + 1]);
        if (hi < 0 || lo < 0) return false;
        out[i] = static_cast<uint8_t>(hi << 4 | lo);
    }
    return true;
}

// Remote parent span context from a W3C traceparent value (00-<32 hex>-<16 hex>-<2 hex>).
static bool parse_traceparent(const std::string& tp, opentelemetry::trace::SpanContext& out) {
    if (tp.size() < 55 || tp[2] != '-' || tp[35] != '-' || tp[52] != '-') return false;
    uint8_t tid[16], sid[8];
    if (!parse_hex(tp, 3, tid) || !parse_hex(tp, 36, sid)) return false;
    out = opentelemetry::trace::SpanContext(
        opentelemetry::trace::TraceId(opentelemetry::nostd::span<const uint8_t, 16>(tid)),
        opentelemetry::trace::SpanId(opentelemetry::nostd::span<const uint8_t, 8>(sid)),
        opentelemetry::trace::TraceFlags(1), true);
    return true;
}

class InventoryServiceImpl final : public inventory::InventoryService::Service {
    std::unordered_map<std::string, int> stock_;
    std::mutex mutex_;
    int initial_stock_;

public:
    explicit InventoryServiceImpl(int initial) : initial_stock_(initial) {}

    grpc::Status ReserveStock(grpc::ServerContext* context,
                              const inventory::ReserveRequest* request,
                              inventory::ReserveResponse* response) override {
        opentelemetry::trace::StartSpanOptions so;
        so.kind = opentelemetry::trace::SpanKind::kServer;
        auto md = context->client_metadata();
        auto it = md.find("traceparent");
        if (it != md.end()) {
            opentelemetry::trace::SpanContext parent = opentelemetry::trace::SpanContext::GetInvalid();
            if (parse_traceparent(std::string(it->second.data(), it->second.size()), parent)) so.parent = parent;
        }
        auto span = cndp::telemetry::tracer("inventory-service")->StartSpan("ReserveStock", {}, so);

        const std::string& sku = request->sku();
        int quantity = request->quantity();

        bool confirmed;
        int remaining;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (stock_.find(sku) == stock_.end())
                stock_[sku] = initial_stock_;
            confirmed = stock_[sku] >= quantity;
            if (confirmed) stock_[sku] -= quantity;
            remaining = stock_[sku];
        }

        response->set_confirmed(confirmed);
        response->set_remaining(remaining);

        spdlog::info("ReserveStock sku={} qty={} confirmed={} remaining={}",
                     sku, quantity, (confirmed ? "true" : "false"), remaining);

        span->SetAttribute("rpc.system", "grpc");
        span->SetAttribute("rpc.service", "inventory.InventoryService");
        span->SetAttribute("rpc.method", "ReserveStock");
        span->SetAttribute("sku", sku);
        span->SetAttribute("quantity", std::to_string(quantity));
        span->SetAttribute("confirmed", confirmed ? "true" : "false");
        span->End();
        g_reservations->Add(1, std::map<std::string, std::string>{{"sku", sku},
                                                                    {"confirmed", confirmed ? "true" : "false"}});

        return grpc::Status::OK;
    }
};

int main() {
    std::signal(SIGTERM, signal_handler);
    std::signal(SIGINT, signal_handler);

    int initial = 100;
    const char* stock_env = std::getenv("INITIAL_STOCK");
    if (stock_env) initial = std::atoi(stock_env);

    cndp::telemetry::init("inventory-service");
    g_reservations = opentelemetry::metrics::Provider::GetMeterProvider()
                         ->GetMeter("inventory-service")
                         ->CreateUInt64Counter("stock.reservations", "Stock reservations", "{reservation}");

    std::string addr("0.0.0.0:50051");
    InventoryServiceImpl service(initial);

    grpc::ServerBuilder builder;
    builder.AddListeningPort(addr, grpc::InsecureServerCredentials());
    builder.RegisterService(&service);

    auto server = builder.BuildAndStart();
    spdlog::info("inventory-service started on {}", addr);

    while (!g_shutdown) {
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
    }

    server->Shutdown();
    cndp::telemetry::shutdown();
    return 0;
}
