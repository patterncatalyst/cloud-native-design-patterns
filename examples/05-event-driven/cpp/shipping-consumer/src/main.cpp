// shipping-consumer: consume order.placed with librdkafka's C++ API (rdkafka++) and write a row to
// Postgres through libpq. Offsets are committed only after the row is written
// (at-least-once); the INSERT is idempotent (ON CONFLICT DO NOTHING), so a redelivery is harmless.
#include <librdkafka/rdkafkacpp.h>

#include <json/json.h>
#include <libpq-fe.h>

#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <iostream>
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
        std::cerr << "Postgres connection failed: " << PQerrorMessage(g_pg_conn) << "\n";
        PQfinish(g_pg_conn);
        g_pg_conn = nullptr;
        throw std::runtime_error("Postgres connection failed");
    }
    std::cout << "Connected to Postgres\n";
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
        std::cerr << "JSON parse error: " << errs << "\n";
        return Outcome::Skip;
    }
    if (!root.isObject() || !root.isMember("id")) {
        std::cerr << "Missing 'id' field in event\n";
        return Outcome::Skip;
    }

    std::string order_id = root["id"].asString();
    std::cout << "Processing order: " << order_id << "\n";

    if (PQstatus(g_pg_conn) != CONNECTION_OK) PQreset(g_pg_conn);

    // Insert with ON CONFLICT DO NOTHING for idempotency
    const char* params[1] = {order_id.c_str()};
    PGresult* res = PQexecParams(g_pg_conn,
        "INSERT INTO shipments (order_id, status) VALUES ($1, 'scheduled') ON CONFLICT (order_id) DO NOTHING",
        1, nullptr, params, nullptr, nullptr, 0);

    bool ok = PQresultStatus(res) == PGRES_COMMAND_OK;
    if (!ok) {
        std::cerr << "Insert failed: " << PQerrorMessage(g_pg_conn) << "\n";
    } else {
        std::cout << "Shipment created/skipped for order: " << order_id << "\n";
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
        std::cerr << "Initialization failed: " << e.what() << "\n";
        return 1;
    }

    const char* svc = std::getenv("OTEL_SERVICE_NAME");
    cndp::telemetry::init(svc ? svc : "shipping-consumer");

    const char* bootstrap = std::getenv("KAFKA_BOOTSTRAP");
    if (!bootstrap) bootstrap = "kafka:9094";

    std::string errstr;
    std::unique_ptr<RdKafka::Conf> conf(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));
    for (auto [key, value] : {std::pair<const char*, const char*>{"bootstrap.servers", bootstrap},
                              {"group.id", "shipping-group"},
                              {"auto.offset.reset", "earliest"},
                              {"enable.auto.commit", "false"}}) {
        if (conf->set(key, value, errstr) != RdKafka::Conf::CONF_OK) {
            std::cerr << "Kafka config " << key << ": " << errstr << "\n";
            return 1;
        }
    }

    std::unique_ptr<RdKafka::KafkaConsumer> consumer(RdKafka::KafkaConsumer::create(conf.get(), errstr));
    if (!consumer) {
        std::cerr << "Failed to create consumer: " << errstr << "\n";
        return 1;
    }

    // subscribe() does not fail when the topic is missing: the consumer keeps polling and
    // picks the partitions up once the producer has created order.placed.
    if (RdKafka::ErrorCode err = consumer->subscribe({"order.placed"}); err != RdKafka::ERR_NO_ERROR) {
        std::cerr << "Subscribe failed: " << RdKafka::err2str(err) << "\n";
        return 1;
    }
    std::cout << "Successfully subscribed to order.placed topic\n";
    std::cout << "Shipping consumer started, listening to order.placed...\n";

    while (!g_shutdown) {
        std::unique_ptr<RdKafka::Message> msg(consumer->consume(1000));
        switch (msg->err()) {
            case RdKafka::ERR_NO_ERROR: {
                std::string event(static_cast<const char*>(msg->payload()), msg->len());
                std::cout << "Received event: " << event << "\n";

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
                    "shipping-consumer", "order.placed process", traceparent, order_id);

                Outcome outcome;
                while ((outcome = process_event(event)) == Outcome::Retry && !g_shutdown) {
                    std::this_thread::sleep_for(std::chrono::seconds(1));
                }
                span->End();
                if (outcome == Outcome::Retry) break;  // shutting down: leave the offset uncommitted
                // Commit only after the side effect, so a crash redelivers rather than loses.
                if (RdKafka::ErrorCode err = consumer->commitSync(msg.get()); err != RdKafka::ERR_NO_ERROR) {
                    std::cerr << "Commit failed: " << RdKafka::err2str(err) << "\n";
                }
                break;
            }
            case RdKafka::ERR__TIMED_OUT:
            case RdKafka::ERR__PARTITION_EOF:
                break;
            default:
                // e.g. UNKNOWN_TOPIC_OR_PART before the topic exists; librdkafka retries on its own.
                std::cerr << "Kafka error: " << msg->errstr() << "\n";
                std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    }

    consumer->close();
    consumer.reset();
    RdKafka::wait_destroyed(5000);
    if (g_pg_conn) PQfinish(g_pg_conn);

    cndp::telemetry::shutdown();
    std::cout << "Shipping consumer shutdown complete\n";
    return 0;
}
