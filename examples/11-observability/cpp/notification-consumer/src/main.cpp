// notification-consumer: order.placed -> notifications row, continuing the producer's trace.
//
// Manual offset commit: the offset is committed only after the INSERT, so a crash between the
// two replays the record (the notifications table has a unique key on order_id, so the replay
// is a logged duplicate, not a second email). A failed INSERT is retried, never skipped.

#include <atomic>
#include <chrono>
#include <csignal>
#include <iostream>
#include <memory>
#include <random>
#include <string>
#include <thread>

#include <libpq-fe.h>
#include <librdkafka/rdkafkacpp.h>

#include "telemetry.hpp"

namespace {

std::atomic<bool> g_shutdown{false};

void signal_handler(int) { g_shutdown = true; }

std::string extract_json_string(const std::string& json, const std::string& key) {
    std::string needle = "\"" + key + "\":\"";
    auto pos = json.find(needle);
    if (pos == std::string::npos) return "";
    pos += needle.size();
    auto end = json.find('"', pos);
    if (end == std::string::npos) return "";
    return json.substr(pos, end - pos);
}

int hex_nibble(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}

template <size_t N>
bool parse_hex(const std::string& s, size_t off, uint8_t (&out)[N]) {
    for (size_t i = 0; i < N; ++i) {
        int hi = hex_nibble(s[off + 2 * i]), lo = hex_nibble(s[off + 2 * i + 1]);
        if (hi < 0 || lo < 0) return false;
        out[i] = static_cast<uint8_t>(hi << 4 | lo);
    }
    return true;
}

// Remote parent span context from a W3C traceparent header (00-<32 hex>-<16 hex>-<2 hex>).
bool parse_traceparent(const std::string& tp, opentelemetry::trace::SpanContext& out) {
    if (tp.size() < 55 || tp[2] != '-' || tp[35] != '-' || tp[52] != '-') return false;
    uint8_t tid[16], sid[8];
    if (!parse_hex(tp, 3, tid) || !parse_hex(tp, 36, sid)) return false;
    out = opentelemetry::trace::SpanContext(
        opentelemetry::trace::TraceId(opentelemetry::nostd::span<const uint8_t, 16>(tid)),
        opentelemetry::trace::SpanId(opentelemetry::nostd::span<const uint8_t, 8>(sid)),
        opentelemetry::trace::TraceFlags(1), true);
    return true;
}

}  // namespace

int main() {
    std::signal(SIGTERM, signal_handler);
    std::signal(SIGINT, signal_handler);

    const char* env = std::getenv("PG_CONNINFO");
    PGconn* pg = PQconnectdb(env ? env : "postgresql://appuser:apppass@postgres:5432/appdb");
    if (PQstatus(pg) != CONNECTION_OK) {
        std::cerr << "Postgres failed: " << PQerrorMessage(pg) << std::endl;
        return 1;
    }

    env = std::getenv("KAFKA_BOOTSTRAP");
    const std::string bootstrap = env ? env : "kafka:9094";

    cndp::telemetry::init("notification-consumer");

    std::string err;
    std::unique_ptr<RdKafka::Conf> conf(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));
    if (conf->set("bootstrap.servers", bootstrap, err) != RdKafka::Conf::CONF_OK ||
        conf->set("group.id", "notification-group", err) != RdKafka::Conf::CONF_OK ||
        conf->set("auto.offset.reset", "earliest", err) != RdKafka::Conf::CONF_OK ||
        conf->set("enable.auto.commit", "false", err) != RdKafka::Conf::CONF_OK) {
        std::cerr << "Kafka consumer config failed: " << err << std::endl;
        return 1;
    }
    std::unique_ptr<RdKafka::KafkaConsumer> consumer(RdKafka::KafkaConsumer::create(conf.get(), err));
    if (!consumer) {
        std::cerr << "Kafka consumer init failed: " << err << std::endl;
        return 1;
    }
    if (auto rc = consumer->subscribe({"order.placed"}); rc != RdKafka::ERR_NO_ERROR) {
        std::cerr << "subscribe failed: " << RdKafka::err2str(rc) << std::endl;
        return 1;
    }

    auto tracer = cndp::telemetry::tracer("notification-consumer");
    std::cerr << "notification-consumer started" << std::endl;

    while (!g_shutdown) {
        std::unique_ptr<RdKafka::Message> msg(consumer->consume(1000));
        if (msg->err() == RdKafka::ERR__TIMED_OUT || msg->err() == RdKafka::ERR__PARTITION_EOF) continue;
        if (msg->err() != RdKafka::ERR_NO_ERROR) {
            // unknown topic before the first order is created, transient broker errors, ...
            std::cerr << "consume: " << msg->errstr() << std::endl;
            continue;
        }

        const std::string value(static_cast<const char*>(msg->payload()), msg->len());
        const std::string order_id = extract_json_string(value, "id");
        if (order_id.empty()) {
            consumer->commitSync(msg.get());
            continue;
        }

        opentelemetry::trace::StartSpanOptions so;
        so.kind = opentelemetry::trace::SpanKind::kConsumer;
        opentelemetry::trace::SpanContext parent = opentelemetry::trace::SpanContext::GetInvalid();
        if (auto* headers = msg->headers()) {
            auto h = headers->get_last("traceparent");
            if (h.err() == RdKafka::ERR_NO_ERROR && h.value_string() != nullptr) {
                std::string tp(static_cast<const char*>(h.value()), h.value_size());
                if (parse_traceparent(tp, parent)) so.parent = parent;
            }
        }
        auto span = tracer->StartSpan(
            "process_notification",
            {{"order.id", order_id}, {"messaging.system", "kafka"}, {"messaging.destination", "order.placed"}},
            so);

        // Retry until the row is written or confirmed to exist (SQLSTATE 23505, unique
        // violation). Any other failure (connection lost, database restarting) resets the
        // connection and tries again; the offset is committed only after one of the two,
        // so the event is never dropped.
        bool done = false;
        while (!done && !g_shutdown) {
            if (PQstatus(pg) != CONNECTION_OK) PQreset(pg);
            const char* params[1] = {order_id.c_str()};
            PGresult* res = PQexecParams(pg,
                "INSERT INTO notifications (order_id, channel) VALUES ($1, 'email')",
                1, nullptr, params, nullptr, nullptr, 0);
            if (PQresultStatus(res) == PGRES_COMMAND_OK) {
                std::cerr << "notification sent order_id=" << order_id << std::endl;
                done = true;
            } else {
                const char* state = PQresultErrorField(res, PG_DIAG_SQLSTATE);
                if (state && std::string(state) == "23505") {
                    std::cerr << "duplicate skipped order_id=" << order_id << std::endl;
                    done = true;
                } else {
                    std::cerr << "insert failed, retrying: " << PQerrorMessage(pg) << std::endl;
                }
            }
            PQclear(res);
            if (!done) std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        span->End();
        if (!done) break;  // shutting down: leave the offset uncommitted, the event is redelivered

        // Commit only after the side effect.
        if (auto rc = consumer->commitSync(msg.get()); rc != RdKafka::ERR_NO_ERROR)
            std::cerr << "commit failed: " << RdKafka::err2str(rc) << std::endl;
    }

    consumer->close();
    PQfinish(pg);
    cndp::telemetry::shutdown();
    std::cerr << "notification-consumer stopped" << std::endl;
    return 0;
}
