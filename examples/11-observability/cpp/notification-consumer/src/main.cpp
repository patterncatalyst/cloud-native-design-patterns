#include <kafka/KafkaConsumer.h>
#include <libpq-fe.h>
#include <atomic>
#include <csignal>
#include <thread>
#include <mutex>
#include <vector>
#include <sstream>
#include <iomanip>
#include <random>
#include <chrono>
#include <cstdio>
#include <iostream>

static std::atomic<bool> g_shutdown{false};
static std::string g_otel_endpoint;
static std::string g_service_name = "notification-consumer";

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

static std::mutex g_otel_mu;
static std::vector<SpanData> g_spans;

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

static void otel_flush_loop() {
    while (!g_shutdown) {
        std::this_thread::sleep_for(std::chrono::seconds(3));
        flush_spans();
    }
    flush_spans();
}

static std::pair<std::string, std::string> parse_traceparent(const std::string& tp) {
    if (tp.size() >= 55 && tp[2] == '-' && tp[35] == '-' && tp[52] == '-')
        return {tp.substr(3, 32), tp.substr(36, 16)};
    return {"", ""};
}

static std::string extract_json_string(const std::string& json, const std::string& key) {
    std::string needle = "\"" + key + "\":\"";
    auto pos = json.find(needle);
    if (pos == std::string::npos) return "";
    pos += needle.size();
    auto end = json.find('"', pos);
    if (end == std::string::npos) return "";
    return json.substr(pos, end - pos);
}

int main() {
    std::signal(SIGTERM, signal_handler);
    std::signal(SIGINT, signal_handler);

    const char* env;

    env = std::getenv("OTEL_EXPORTER_OTLP_ENDPOINT");
    g_otel_endpoint = env ? env : "http://lgtm:4318";

    env = std::getenv("PG_CONNINFO");
    const char* conninfo = env ? env : "postgresql://appuser:apppass@postgres:5432/appdb";
    PGconn* pg = PQconnectdb(conninfo);
    if (PQstatus(pg) != CONNECTION_OK) {
        std::cerr << "Postgres failed: " << PQerrorMessage(pg) << std::endl;
        return 1;
    }

    env = std::getenv("KAFKA_BOOTSTRAP");
    std::string kafka_bootstrap = env ? env : "kafka:9094";

    kafka::Properties props;
    props.put("bootstrap.servers", kafka_bootstrap);
    props.put("group.id", "notification-group");
    props.put("auto.offset.reset", "earliest");
    props.put("enable.auto.commit", "false");

    kafka::clients::consumer::KafkaConsumer consumer(props);
    consumer.subscribe({"order.placed"});

    std::thread flusher(otel_flush_loop);

    std::cerr << "notification-consumer started" << std::endl;

    while (!g_shutdown) {
        auto records = consumer.poll(std::chrono::milliseconds(1000));
        for (auto& rec : records) {
            if (rec.error()) continue;

            std::string value(static_cast<const char*>(rec.value().data()), rec.value().size());
            std::string order_id = extract_json_string(value, "id");
            if (order_id.empty()) continue;

            std::string trace_id, parent_span_id;
            for (auto& hdr : rec.headers()) {
                if (hdr.key == "traceparent") {
                    std::string tp(static_cast<const char*>(hdr.value.data()), hdr.value.size());
                    auto [tid, psid] = parse_traceparent(tp);
                    trace_id = tid;
                    parent_span_id = psid;
                    break;
                }
            }
            if (trace_id.empty()) trace_id = random_hex(16);

            int64_t span_start = now_nano();
            std::string span_id = random_hex(8);

            const char* params[1] = {order_id.c_str()};
            PGresult* res = PQexecParams(pg,
                "INSERT INTO notifications (order_id, channel) VALUES ($1, 'email')",
                1, nullptr, params, nullptr, nullptr, 0);

            bool ok = (PQresultStatus(res) == PGRES_COMMAND_OK);
            if (ok) {
                std::cerr << "notification sent order_id=" << order_id << std::endl;
            } else {
                std::string err = PQerrorMessage(pg);
                if (err.find("duplicate") != std::string::npos || err.find("unique") != std::string::npos)
                    std::cerr << "duplicate skipped order_id=" << order_id << std::endl;
                else
                    std::cerr << "insert failed: " << err << std::endl;
            }
            PQclear(res);

            int64_t span_end = now_nano();
            {
                std::lock_guard<std::mutex> lock(g_otel_mu);
                g_spans.push_back({trace_id, span_id, parent_span_id, "process_notification",
                                  1, span_start, span_end,
                                  {{"order.id", order_id},
                                   {"messaging.system", "kafka"},
                                   {"messaging.destination", "order.placed"}}});
            }

            consumer.commitSync(rec);
        }
    }

    consumer.close();
    PQfinish(pg);
    g_shutdown = true;
    flusher.join();
    std::cerr << "notification-consumer stopped" << std::endl;
    return 0;
}
