#include <grpcpp/grpcpp.h>
#include <inventory.grpc.pb.h>
#include <unordered_map>
#include <mutex>
#include <random>
#include <sstream>
#include <iomanip>
#include <thread>
#include <chrono>
#include <cstdio>
#include <atomic>
#include <csignal>
#include <iostream>

static std::string g_otel_endpoint;
static std::string g_service_name = "inventory-service";
static std::atomic<bool> g_shutdown{false};

void signal_handler(int) { g_shutdown = true; }

static std::string random_hex(int bytes) {
    static thread_local std::mt19937_64 rng(std::random_device{}());
    std::uniform_int_distribution<uint64_t> dist;
    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    uint64_t v1 = dist(rng);
    for (int i = 0; i < std::min(bytes, 8); ++i)
        oss << std::setw(2) << ((v1 >> (i * 8)) & 0xFF);
    if (bytes > 8) {
        uint64_t v2 = dist(rng);
        for (int i = 0; i < bytes - 8; ++i)
            oss << std::setw(2) << ((v2 >> (i * 8)) & 0xFF);
    }
    return oss.str();
}

static int64_t now_nano() {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

static std::string json_escape(const std::string& s) {
    std::ostringstream oss;
    for (char c : s) {
        if (c == '"' || c == '\\') oss << '\\';
        oss << c;
    }
    return oss.str();
}

struct SpanData {
    std::string trace_id, span_id, parent_span_id, name;
    int kind;
    int64_t start_nano, end_nano;
    std::vector<std::pair<std::string, std::string>> attrs;
};

struct MetricAccum {
    std::string name;
    std::map<std::string, int64_t> series;
    int64_t start_nano = 0;
};

static std::mutex g_otel_mu;
static std::vector<SpanData> g_spans;
static MetricAccum g_reservations_metric{"stock.reservations", {}, 0};

static void otlp_post(const std::string& path, const std::string& json) {
    std::string cmd = "curl -sf -X POST -H 'Content-Type: application/json' -d @- "
                      + g_otel_endpoint + path + " >/dev/null 2>&1";
    FILE* pipe = popen(cmd.c_str(), "w");
    if (pipe) {
        fwrite(json.c_str(), 1, json.size(), pipe);
        pclose(pipe);
    }
}

static void flush_spans() {
    std::vector<SpanData> spans;
    {
        std::lock_guard<std::mutex> lock(g_otel_mu);
        spans.swap(g_spans);
    }
    if (spans.empty()) return;

    std::ostringstream json;
    json << R"({"resourceSpans":[{"resource":{"attributes":[)"
         << R"({"key":"service.name","value":{"stringValue":")" << g_service_name << R"("}}]},)"
         << R"("scopeSpans":[{"scope":{"name":")" << g_service_name << R"("},"spans":[)";

    for (size_t i = 0; i < spans.size(); ++i) {
        auto& s = spans[i];
        if (i > 0) json << ",";
        json << R"({"traceId":")" << s.trace_id
             << R"(","spanId":")" << s.span_id << R"(")";
        if (!s.parent_span_id.empty())
            json << R"(,"parentSpanId":")" << s.parent_span_id << R"(")";
        json << R"(,"name":")" << json_escape(s.name)
             << R"(","kind":)" << s.kind
             << R"(,"startTimeUnixNano":")" << s.start_nano
             << R"(","endTimeUnixNano":")" << s.end_nano << R"(")";
        if (!s.attrs.empty()) {
            json << R"(,"attributes":[)";
            for (size_t j = 0; j < s.attrs.size(); ++j) {
                if (j > 0) json << ",";
                json << R"({"key":")" << json_escape(s.attrs[j].first)
                     << R"(","value":{"stringValue":")" << json_escape(s.attrs[j].second) << R"("}})";
            }
            json << "]";
        }
        json << R"(,"status":{"code":0}})";
    }
    json << "]}]}]}";
    otlp_post("/v1/traces", json.str());
}

static void flush_metrics() {
    std::map<std::string, int64_t> series;
    int64_t start_nano;
    {
        std::lock_guard<std::mutex> lock(g_otel_mu);
        if (g_reservations_metric.series.empty()) return;
        series = g_reservations_metric.series;
        start_nano = g_reservations_metric.start_nano;
    }

    int64_t now = now_nano();
    std::ostringstream json;
    json << R"({"resourceMetrics":[{"resource":{"attributes":[)"
         << R"({"key":"service.name","value":{"stringValue":")" << g_service_name << R"("}}]},)"
         << R"("scopeMetrics":[{"scope":{"name":")" << g_service_name << R"("},"metrics":[)"
         << R"({"name":")" << g_reservations_metric.name << R"(","sum":{)"
         << R"("dataPoints":[)";

    bool first = true;
    for (auto& [key, count] : series) {
        if (!first) json << ",";
        first = false;
        auto sep = key.find('|');
        std::string sku = key.substr(0, sep);
        std::string confirmed = key.substr(sep + 1);
        json << R"({"asInt":")" << count
             << R"(","startTimeUnixNano":")" << start_nano
             << R"(","timeUnixNano":")" << now
             << R"(","attributes":[)"
             << R"({"key":"sku","value":{"stringValue":")" << json_escape(sku) << R"("}},)"
             << R"({"key":"confirmed","value":{"stringValue":")" << json_escape(confirmed) << R"("}}]})";
    }
    json << R"(],"aggregationTemporality":2,"isMonotonic":true}}]}]}]})" ;
    otlp_post("/v1/metrics", json.str());
}

static void otel_flush_loop() {
    while (!g_shutdown) {
        std::this_thread::sleep_for(std::chrono::seconds(3));
        flush_spans();
        flush_metrics();
    }
    flush_spans();
    flush_metrics();
}

static std::pair<std::string, std::string> parse_traceparent(const std::string& tp) {
    if (tp.size() >= 55 && tp[2] == '-' && tp[35] == '-' && tp[52] == '-') {
        return {tp.substr(3, 32), tp.substr(36, 16)};
    }
    return {"", ""};
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
        int64_t start = now_nano();
        std::string span_id = random_hex(8);

        std::string trace_id, parent_span_id;
        auto md = context->client_metadata();
        auto it = md.find("traceparent");
        if (it != md.end()) {
            auto tp = std::string(it->second.data(), it->second.size());
            auto [tid, psid] = parse_traceparent(tp);
            trace_id = tid;
            parent_span_id = psid;
        }
        if (trace_id.empty()) trace_id = random_hex(16);

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

        std::cerr << "ReserveStock sku=" << sku << " qty=" << quantity
                  << " confirmed=" << (confirmed ? "true" : "false")
                  << " remaining=" << remaining << std::endl;

        int64_t end = now_nano();
        {
            std::lock_guard<std::mutex> lock(g_otel_mu);
            g_spans.push_back({trace_id, span_id, parent_span_id, "ReserveStock",
                              2, start, end,
                              {{"rpc.system", "grpc"},
                               {"rpc.service", "inventory.InventoryService"},
                               {"rpc.method", "ReserveStock"},
                               {"sku", sku},
                               {"quantity", std::to_string(quantity)},
                               {"confirmed", confirmed ? "true" : "false"}}});

            std::string metric_key = sku + "|" + (confirmed ? "true" : "false");
            if (g_reservations_metric.start_nano == 0)
                g_reservations_metric.start_nano = now_nano();
            g_reservations_metric.series[metric_key]++;
        }

        return grpc::Status::OK;
    }
};

int main() {
    std::signal(SIGTERM, signal_handler);
    std::signal(SIGINT, signal_handler);

    const char* env = std::getenv("OTEL_EXPORTER_OTLP_ENDPOINT");
    g_otel_endpoint = env ? env : "http://lgtm:4318";

    int initial = 100;
    const char* stock_env = std::getenv("INITIAL_STOCK");
    if (stock_env) initial = std::atoi(stock_env);

    std::thread flusher(otel_flush_loop);

    std::string addr("0.0.0.0:50051");
    InventoryServiceImpl service(initial);

    grpc::ServerBuilder builder;
    builder.AddListeningPort(addr, grpc::InsecureServerCredentials());
    builder.RegisterService(&service);

    auto server = builder.BuildAndStart();
    std::cerr << "inventory-service started on " << addr << std::endl;

    while (!g_shutdown) {
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
    }

    server->Shutdown();
    flusher.join();
    return 0;
}
