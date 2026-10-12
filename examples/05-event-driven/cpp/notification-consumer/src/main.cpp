// notification-consumer: consume order.placed with librdkafka's C++ API (rdkafka++) and write a row to
// Postgres through libpq. Offsets are committed only after the row is written
// (at-least-once); the INSERT is idempotent (ON CONFLICT DO NOTHING), so a redelivery is harmless.
#include <librdkafka/rdkafkacpp.h>

#include <json/json.h>
#include <libpq-fe.h>
#include <spdlog/spdlog.h>

#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>

#include "telemetry.hpp"

namespace {

std::atomic<bool> g_shutdown{false};
PGconn* g_pg_conn = nullptr;

void signal_handler(int) { g_shutdown = true; }

void init_pg() {
    const char* conninfo = std::getenv("PG_CONNINFO");
    if (!conninfo) conninfo = "postgresql://appuser:apppass@postgres:5432/appdb";

    g_pg_conn = PQconnectdb(conninfo);
    if (PQstatus(g_pg_conn) != CONNECTION_OK) {
        spdlog::error("Postgres connection failed: {}", PQerrorMessage(g_pg_conn));
        PQfinish(g_pg_conn);
        g_pg_conn = nullptr;
        throw std::runtime_error("Postgres connection failed");
    }
    spdlog::info("Connected to Postgres");
}

enum class Outcome { Done, Skip, Retry };

// Done: row written (or already there). Skip: poison message, nothing to retry.
// Retry: the database failed; the caller must not commit the offset.
Outcome process_event(const std::string& event_json) {
    Json::Value root;
    Json::CharReaderBuilder builder;
    std::string errs;
    std::istringstream stream(event_json);

    if (!Json::parseFromStream(builder, stream, &root, &errs)) {
        spdlog::warn("JSON parse error: {}", errs);
        return Outcome::Skip;
    }
    if (!root.isObject() || !root.isMember("id")) {
        spdlog::warn("Missing 'id' field in event");
        return Outcome::Skip;
    }

    std::string order_id = root["id"].asString();
    spdlog::info("Processing order: {}", order_id);

    if (PQstatus(g_pg_conn) != CONNECTION_OK) PQreset(g_pg_conn);

    // Insert with ON CONFLICT DO NOTHING for idempotency
    const char* params[1] = {order_id.c_str()};
    PGresult* res = PQexecParams(g_pg_conn,
        "INSERT INTO notifications (order_id, channel) VALUES ($1, 'email') ON CONFLICT (order_id) DO NOTHING",
        1, nullptr, params, nullptr, nullptr, 0);

    bool ok = PQresultStatus(res) == PGRES_COMMAND_OK;
    if (!ok) {
        spdlog::error("Insert failed: {}", PQerrorMessage(g_pg_conn));
    } else {
        spdlog::info("Notification created/skipped for order: {}", order_id);
    }
    PQclear(res);
    return ok ? Outcome::Done : Outcome::Retry;
}

}  // namespace

int main() {
    std::signal(SIGTERM, signal_handler);
    std::signal(SIGINT, signal_handler);

    try {
        init_pg();
    } catch (const std::exception& e) {
        spdlog::error("Initialization failed: {}", e.what());
        return 1;
    }

    const char* svc = std::getenv("OTEL_SERVICE_NAME");
    cndp::telemetry::init(svc ? svc : "notification-consumer");

    const char* bootstrap = std::getenv("KAFKA_BOOTSTRAP");
    if (!bootstrap) bootstrap = "kafka:9094";

    std::string errstr;
    std::unique_ptr<RdKafka::Conf> conf(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));
    for (auto [key, value] : {std::pair<const char*, const char*>{"bootstrap.servers", bootstrap},
                              {"group.id", "notification-group"},
                              {"auto.offset.reset", "earliest"},
                              {"enable.auto.commit", "false"}}) {
        if (conf->set(key, value, errstr) != RdKafka::Conf::CONF_OK) {
            spdlog::error("Kafka config {}: {}", key, errstr);
            return 1;
        }
    }

    std::unique_ptr<RdKafka::KafkaConsumer> consumer(RdKafka::KafkaConsumer::create(conf.get(), errstr));
    if (!consumer) {
        spdlog::error("Failed to create consumer: {}", errstr);
        return 1;
    }

    // subscribe() does not fail when the topic is missing: the consumer keeps polling and
    // picks the partitions up once the producer has created order.placed.
    if (RdKafka::ErrorCode err = consumer->subscribe({"order.placed"}); err != RdKafka::ERR_NO_ERROR) {
        spdlog::error("Subscribe failed: {}", RdKafka::err2str(err));
        return 1;
    }
    spdlog::info("Successfully subscribed to order.placed topic");
    spdlog::info("Notification consumer started, listening to order.placed...");

    while (!g_shutdown) {
        std::unique_ptr<RdKafka::Message> msg(consumer->consume(1000));
        switch (msg->err()) {
            case RdKafka::ERR_NO_ERROR: {
                std::string event(static_cast<const char*>(msg->payload()), msg->len());
                spdlog::info("Received event: {}", event);

                std::string traceparent;
                if (auto* hdrs = msg->headers()) {
                    auto h = hdrs->get_last("traceparent");
                    if (h.err() == RdKafka::ERR_NO_ERROR && h.value_string() != nullptr)
                        traceparent.assign(static_cast<const char*>(h.value()), h.value_size());
                }
                std::string order_id;
                {
                    Json::Value root;
                    Json::CharReaderBuilder b;
                    std::string errs;
                    std::istringstream is(event);
                    if (Json::parseFromStream(b, is, &root, &errs) && root.isObject())
                        order_id = root.get("id", "").asString();
                }
                auto span = cndp::telemetry::start_consumer_span(
                    "notification-consumer", "order.placed process", traceparent, order_id);

                Outcome outcome;
                while ((outcome = process_event(event)) == Outcome::Retry && !g_shutdown) {
                    std::this_thread::sleep_for(std::chrono::seconds(1));
                }
                span->End();
                if (outcome == Outcome::Retry) break;  // shutting down: leave the offset uncommitted
                // Commit only after the side effect, so a crash redelivers rather than loses.
                if (RdKafka::ErrorCode err = consumer->commitSync(msg.get()); err != RdKafka::ERR_NO_ERROR) {
                    spdlog::error("Commit failed: {}", RdKafka::err2str(err));
                }
                break;
            }
            case RdKafka::ERR__TIMED_OUT:
            case RdKafka::ERR__PARTITION_EOF:
                break;
            default:
                // e.g. UNKNOWN_TOPIC_OR_PART before the topic exists; librdkafka retries on its own.
                spdlog::warn("Kafka error: {}", msg->errstr());
                std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    }

    consumer->close();
    consumer.reset();
    RdKafka::wait_destroyed(5000);
    if (g_pg_conn) PQfinish(g_pg_conn);

    cndp::telemetry::shutdown();
    spdlog::info("Notification consumer shutdown complete");
    return 0;
}
