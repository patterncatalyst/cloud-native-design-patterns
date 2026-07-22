#include <drogon/drogon.h>
#include <grpcpp/grpcpp.h>
#include <inventory.grpc.pb.h>
#include <kafka/KafkaProducer.h>
#include <libpq-fe.h>
#include <random>
#include <sstream>
#include <iomanip>
#include <atomic>
#include <csignal>
#include <thread>
#include <mutex>
#include <chrono>
#include <cstdio>

using namespace drogon;

static std::atomic<bool> g_shutdown{false};
static PGconn* g_pg = nullptr;
static std::unique_ptr<kafka::clients::producer::KafkaProducer> g_producer;
static std::shared_ptr<grpc::Channel> g_grpc_channel;
static std::unique_ptr<inventory::InventoryService::Stub> g_inventory_stub;
static std::string g_otel_endpoint;
static std::string g_service_name = "order-service";

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

static std::string generate_uuid() {
    std::random_device rd;
    std::mt19937_64 gen(rd());
    std::uniform_int_distribution<uint64_t> dis;
    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    uint64_t p1 = dis(gen), p2 = dis(gen);
    oss << std::setw(8) << (p1 & 0xFFFFFFFF) << "-"
        << std::setw(4) << ((p1 >> 32) & 0xFFFF) << "-"
        << std::setw(4) << (0x4000 | ((p1 >> 48) & 0x0FFF)) << "-"
        << std::setw(4) << (0x8000 | ((p2 >> 48) & 0x3FFF)) << "-"
        << std::setw(12) << (p2 & 0xFFFFFFFFFFFF);
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

struct MetricSeries {
    std::map<std::string, int64_t> series;
    int64_t start_nano = 0;
};

static std::mutex g_otel_mu;
static std::vector<SpanData> g_spans;
static MetricSeries g_orders_metric;

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
        if (g_orders_metric.series.empty()) return;
        series = g_orders_metric.series;
        start_nano = g_orders_metric.start_nano;
    }

    int64_t now = now_nano();
    std::ostringstream json;
    json << R"({"resourceMetrics":[{"resource":{"attributes":[)"
         << R"({"key":"service.name","value":{"stringValue":")" << g_service_name << R"("}}]},)"
         << R"("scopeMetrics":[{"scope":{"name":")" << g_service_name << R"("},"metrics":[)"
         << R"({"name":"orders.placed","sum":{)"
         << R"("dataPoints":[)";

    bool first = true;
    for (auto& [key, count] : series) {
        if (!first) json << ",";
        first = false;
        auto sep = key.find('|');
        std::string sku = key.substr(0, sep);
        std::string status = key.substr(sep + 1);
        json << R"({"asInt":")" << count
             << R"(","startTimeUnixNano":")" << start_nano
             << R"(","timeUnixNano":")" << now
             << R"(","attributes":[)"
             << R"({"key":"sku","value":{"stringValue":")" << json_escape(sku) << R"("}},)"
             << R"({"key":"status","value":{"stringValue":")" << json_escape(status) << R"("}}]})";
    }
    json << R"(],"aggregationTemporality":2,"isMonotonic":true}}]}]}]})";
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

int main() {
    std::signal(SIGTERM, signal_handler);
    std::signal(SIGINT, signal_handler);

    const char* env;

    env = std::getenv("OTEL_EXPORTER_OTLP_ENDPOINT");
    g_otel_endpoint = env ? env : "http://lgtm:4318";

    env = std::getenv("PG_CONNINFO");
    const char* conninfo = env ? env : "postgresql://appuser:apppass@postgres:5432/appdb";
    g_pg = PQconnectdb(conninfo);
    if (PQstatus(g_pg) != CONNECTION_OK) {
        LOG_ERROR << "Postgres failed: " << PQerrorMessage(g_pg);
        return 1;
    }

    env = std::getenv("KAFKA_BOOTSTRAP");
    std::string kafka_bootstrap = env ? env : "kafka:9094";
    kafka::Properties props;
    props.put("bootstrap.servers", kafka_bootstrap);
    props.put("client.id", "order-service");
    g_producer = std::make_unique<kafka::clients::producer::KafkaProducer>(props);

    env = std::getenv("INVENTORY_ADDR");
    std::string inventory_addr = env ? env : "inventory:50051";
    g_grpc_channel = grpc::CreateChannel(inventory_addr, grpc::InsecureChannelCredentials());
    g_inventory_stub = inventory::InventoryService::NewStub(g_grpc_channel);

    std::thread flusher(otel_flush_loop);

    app().setLogLevel(trantor::Logger::kInfo);
    app().addListener("0.0.0.0", 8080);
    app().setUploadPath("/tmp");

    app().registerHandler("/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value r;
            r["status"] = "ok";
            callback(HttpResponse::newHttpJsonResponse(r));
        },
        {Get});

    app().registerHandler("/orders",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            auto json = req->getJsonObject();
            if (!json || !json->isMember("sku") || !json->isMember("quantity")) {
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k400BadRequest);
                resp->setBody(R"({"error":"sku and quantity required"})");
                callback(resp);
                return;
            }

            std::string sku = (*json)["sku"].asString();
            int quantity = (*json)["quantity"].asInt();
            std::string order_id = generate_uuid();

            std::string trace_id = random_hex(16);
            std::string root_span_id = random_hex(8);
            int64_t root_start = now_nano();

            std::string status;
            {
                std::string grpc_span_id = random_hex(8);
                int64_t grpc_start = now_nano();

                inventory::ReserveRequest grpc_req;
                grpc_req.set_sku(sku);
                grpc_req.set_quantity(quantity);

                inventory::ReserveResponse grpc_resp;
                grpc::ClientContext ctx;
                ctx.set_deadline(std::chrono::system_clock::now() + std::chrono::seconds(5));
                std::string traceparent = "00-" + trace_id + "-" + grpc_span_id + "-01";
                ctx.AddMetadata("traceparent", traceparent);

                auto grpc_status = g_inventory_stub->ReserveStock(&ctx, grpc_req, &grpc_resp);
                status = (grpc_status.ok() && grpc_resp.confirmed()) ? "confirmed" : "rejected";

                int64_t grpc_end = now_nano();
                std::lock_guard<std::mutex> lock(g_otel_mu);
                g_spans.push_back({trace_id, grpc_span_id, root_span_id, "reserve-stock",
                                  3, grpc_start, grpc_end,
                                  {{"rpc.system", "grpc"},
                                   {"rpc.service", "inventory.InventoryService"},
                                   {"rpc.method", "ReserveStock"},
                                   {"sku", sku},
                                   {"quantity", std::to_string(quantity)},
                                   {"stock.confirmed", status == "confirmed" ? "true" : "false"}}});
            }

            const char* params[4] = {order_id.c_str(), sku.c_str(),
                                     std::to_string(quantity).c_str(), status.c_str()};
            PGresult* res = PQexecParams(g_pg,
                "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4)",
                4, nullptr, params, nullptr, nullptr, 0);
            if (PQresultStatus(res) != PGRES_COMMAND_OK)
                LOG_ERROR << "Insert failed: " << PQerrorMessage(g_pg);
            PQclear(res);

            std::ostringstream event;
            event << R"({"id":")" << json_escape(order_id)
                  << R"(","sku":")" << json_escape(sku)
                  << R"(","quantity":)" << quantity
                  << R"(,"status":")" << json_escape(status) << R"("})";

            std::string event_str = event.str();
            std::string traceparent = "00-" + trace_id + "-" + root_span_id + "-01";

            kafka::clients::producer::ProducerRecord record(
                kafka::Topic("order.placed"),
                kafka::NullKey,
                kafka::Value(event_str.c_str(), event_str.size()));
            record.headers().push_back(
                kafka::Header(kafka::Header::Key("traceparent"),
                              kafka::Header::Value(traceparent.c_str(), traceparent.size())));

            try {
                g_producer->syncSend(record);
            } catch (const kafka::KafkaException& e) {
                LOG_ERROR << "Kafka send failed: " << e.what();
            }

            int64_t root_end = now_nano();
            {
                std::lock_guard<std::mutex> lock(g_otel_mu);
                g_spans.push_back({trace_id, root_span_id, "", "POST /orders",
                                  2, root_start, root_end,
                                  {{"http.method", "POST"},
                                   {"http.target", "/orders"},
                                   {"order.id", order_id},
                                   {"sku", sku},
                                   {"status", status}}});

                std::string metric_key = sku + "|" + status;
                if (g_orders_metric.start_nano == 0)
                    g_orders_metric.start_nano = now_nano();
                g_orders_metric.series[metric_key]++;
            }

            std::cerr << "order placed sku=" << sku << " id=" << order_id
                      << " status=" << status << " trace_id=" << trace_id << std::endl;

            Json::Value resp;
            resp["id"] = order_id;
            resp["sku"] = sku;
            resp["quantity"] = quantity;
            resp["status"] = status;
            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            http_resp->setStatusCode(k201Created);
            callback(http_resp);
        },
        {Post});

    app().registerHandler("/orders",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            PGresult* res = PQexec(g_pg,
                "SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT 50");
            if (PQresultStatus(res) != PGRES_TUPLES_OK) {
                PQclear(res);
                auto resp = HttpResponse::newHttpResponse();
                resp->setStatusCode(k500InternalServerError);
                callback(resp);
                return;
            }
            Json::Value orders(Json::arrayValue);
            for (int i = 0; i < PQntuples(res); ++i) {
                Json::Value o;
                o["id"] = PQgetvalue(res, i, 0);
                o["sku"] = PQgetvalue(res, i, 1);
                o["quantity"] = std::stoi(PQgetvalue(res, i, 2));
                o["status"] = PQgetvalue(res, i, 3);
                orders.append(o);
            }
            PQclear(res);
            callback(HttpResponse::newHttpJsonResponse(orders));
        },
        {Get});

    app().run();

    g_shutdown = true;
    flusher.join();
    if (g_pg) PQfinish(g_pg);
    return 0;
}
