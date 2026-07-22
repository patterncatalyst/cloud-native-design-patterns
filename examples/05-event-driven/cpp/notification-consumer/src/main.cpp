#include <kafka/KafkaConsumer.h>
#include <json/json.h>
#include <libpq-fe.h>
#include <atomic>
#include <csignal>
#include <iostream>
#include <thread>
#include <chrono>

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

void process_event(const std::string& event_json) {
    Json::Value root;
    Json::CharReaderBuilder builder;
    std::string errs;
    std::istringstream stream(event_json);

    if (!Json::parseFromStream(builder, stream, &root, &errs)) {
        std::cerr << "JSON parse error: " << errs << "\n";
        return;
    }

    if (!root.isMember("id")) {
        std::cerr << "Missing 'id' field in event\n";
        return;
    }

    std::string order_id = root["id"].asString();
    std::cout << "Processing order: " << order_id << "\n";

    // Insert with ON CONFLICT DO NOTHING for idempotency
    const char* params[1] = {order_id.c_str()};
    PGresult* res = PQexecParams(g_pg_conn,
        "INSERT INTO notifications (order_id, channel) VALUES ($1, 'email') ON CONFLICT (order_id) DO NOTHING",
        1, nullptr, params, nullptr, nullptr, 0);

    if (PQresultStatus(res) != PGRES_COMMAND_OK) {
        std::cerr << "Insert failed: " << PQerrorMessage(g_pg_conn) << "\n";
    } else {
        std::cout << "Notification created/skipped for order: " << order_id << "\n";
    }
    PQclear(res);
}

int main() {
    std::signal(SIGTERM, signal_handler);
    std::signal(SIGINT, signal_handler);

    try {
        init_pg();
    } catch (const std::exception& e) {
        std::cerr << "Initialization failed: " << e.what() << "\n";
        return 1;
    }

    const char* bootstrap = std::getenv("KAFKA_BOOTSTRAP");
    if (!bootstrap) bootstrap = "kafka:9094";

    kafka::Properties props;
    props.put("bootstrap.servers", bootstrap);
    props.put("group.id", "notification-group");
    props.put("auto.offset.reset", "earliest");
    props.put("enable.auto.commit", "false");

    kafka::clients::consumer::KafkaConsumer consumer(props);

    // Retry subscribe with short timeout — topic may not exist at startup
    for (int attempt = 0; attempt < 60; ++attempt) {
        try {
            consumer.subscribe({"order.placed"},
                kafka::clients::consumer::NullRebalanceCallback,
                std::chrono::milliseconds(5000));
            std::cout << "Successfully subscribed to order.placed topic\n";
            break;
        } catch (const std::exception& e) {
            std::cerr << "Subscribe attempt " << (attempt + 1) << "/60 failed: " << e.what() << "\n";
            if (attempt < 59) {
                std::this_thread::sleep_for(std::chrono::seconds(1));
            } else {
                std::cerr << "Failed to subscribe after 60 attempts, exiting\n";
                return 1;
            }
        }
    }

    std::cout << "Notification consumer started, listening to order.placed...\n";

    while (!g_shutdown) {
        try {
            auto records = consumer.poll(std::chrono::milliseconds(1000));

            for (const auto& record : records) {
                std::string event(static_cast<const char*>(record.value().data()),
                                  record.value().size());
                std::cout << "Received event: " << event << "\n";

                process_event(event);
                consumer.commitSync();
            }
        } catch (const kafka::KafkaException& e) {
            std::cerr << "Kafka error: " << e.what() << "\n";
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    }

    consumer.close();
    if (g_pg_conn) PQfinish(g_pg_conn);

    std::cout << "Notification consumer shutdown complete\n";
    return 0;
}
