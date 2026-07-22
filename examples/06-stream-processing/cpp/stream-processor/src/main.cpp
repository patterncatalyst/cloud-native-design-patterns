#include <kafka/KafkaConsumer.h>
#include <kafka/KafkaProducer.h>
#include <json/json.h>
#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <thread>

using namespace std::chrono;

static std::atomic<bool> g_shutdown{false};

void signal_handler(int) {
    g_shutdown.store(true);
}

struct WindowKey {
    int64_t window_start;
    std::string merchant_id;

    bool operator<(const WindowKey& other) const {
        if (window_start != other.window_start) return window_start < other.window_start;
        return merchant_id < other.merchant_id;
    }
};

struct WindowAggregate {
    int order_count = 0;
    double revenue = 0.0;
};

class StreamProcessor {
private:
    std::unique_ptr<kafka::clients::consumer::KafkaConsumer> consumer_;
    std::unique_ptr<kafka::clients::producer::KafkaProducer> producer_;
    std::map<WindowKey, WindowAggregate> windows_;
    int64_t window_seconds_;

    int64_t get_current_time_seconds() {
        return duration_cast<seconds>(system_clock::now().time_since_epoch()).count();
    }

    int64_t compute_window_start(int64_t timestamp) {
        return (timestamp / window_seconds_) * window_seconds_;
    }

    bool parse_order_event(const std::string& json_str, std::string& merchant_id, double& total) {
        // Find the start of JSON (skip any leading binary/non-JSON characters)
        size_t json_start = json_str.find('{');
        if (json_start == std::string::npos) {
            std::cerr << "No JSON object found in message" << std::endl;
            return false;
        }

        std::string clean_json = json_str.substr(json_start);

        Json::CharReaderBuilder builder;
        Json::Value root;
        std::string errs;
        std::istringstream stream(clean_json);

        if (!Json::parseFromStream(builder, stream, &root, &errs)) {
            std::cerr << "JSON parse error: " << errs << std::endl;
            return false;
        }

        if (!root.isMember("merchant_id") || !root.isMember("total")) {
            return false;
        }

        merchant_id = root["merchant_id"].asString();
        total = root["total"].asDouble();
        return true;
    }

    std::string build_revenue_json(const WindowKey& key, const WindowAggregate& agg) {
        Json::Value event;
        event["window_start"] = Json::Int64(key.window_start);
        event["window_end"] = Json::Int64(key.window_start + window_seconds_);
        event["merchant_id"] = key.merchant_id;
        event["order_count"] = agg.order_count;
        event["revenue"] = agg.revenue;

        Json::StreamWriterBuilder builder;
        builder["indentation"] = "";
        return Json::writeString(builder, event);
    }

    void flush_expired_windows(int64_t current_time) {
        std::vector<WindowKey> expired;

        for (const auto& [key, agg] : windows_) {
            int64_t window_end = key.window_start + window_seconds_;
            if (current_time >= window_end) {
                expired.push_back(key);
            }
        }

        for (const auto& key : expired) {
            const auto& agg = windows_[key];
            std::string revenue_json = build_revenue_json(key, agg);

            try {
                kafka::clients::producer::ProducerRecord record{
                    "revenue.by-merchant",
                    kafka::NullKey,
                    kafka::Value(revenue_json.c_str(), revenue_json.size())
                };
                producer_->syncSend(record);
                std::cout << "Emitted window: " << revenue_json << std::endl;
            } catch (const std::exception& e) {
                std::cerr << "Failed to produce revenue event: " << e.what() << std::endl;
            }

            windows_.erase(key);
        }
    }

    void flush_all_windows() {
        for (const auto& [key, agg] : windows_) {
            std::string revenue_json = build_revenue_json(key, agg);

            try {
                kafka::clients::producer::ProducerRecord record{
                    "revenue.by-merchant",
                    kafka::NullKey,
                    kafka::Value(revenue_json.c_str(), revenue_json.size())
                };
                producer_->syncSend(record);
                std::cout << "Flushed window on shutdown: " << revenue_json << std::endl;
            } catch (const std::exception& e) {
                std::cerr << "Failed to produce revenue event on shutdown: " << e.what() << std::endl;
            }
        }
        windows_.clear();

        if (producer_) {
            producer_->close();
        }
    }

public:
    StreamProcessor(const std::string& bootstrap, int64_t window_seconds)
        : window_seconds_(window_seconds) {

        kafka::Properties consumer_props;
        consumer_props.put("bootstrap.servers", bootstrap);
        consumer_props.put("group.id", "stream-processor");
        consumer_props.put("auto.offset.reset", "earliest");
        consumer_props.put("enable.auto.commit", "false");

        kafka::Properties producer_props;
        producer_props.put("bootstrap.servers", bootstrap);
        producer_props.put("client.id", "stream-processor");
        producer_props.put("linger.ms", "100");
        producer_props.put("acks", "1");

        consumer_ = std::make_unique<kafka::clients::consumer::KafkaConsumer>(consumer_props);
        producer_ = std::make_unique<kafka::clients::producer::KafkaProducer>(producer_props);

        // Retry subscribe with short timeout — topic may not exist at startup
        for (int attempt = 0; attempt < 60; ++attempt) {
            try {
                consumer_->subscribe({"order.placed"},
                    kafka::clients::consumer::NullRebalanceCallback,
                    std::chrono::milliseconds(5000));
                std::cout << "Stream processor started, window=" << window_seconds_ << "s" << std::endl;
                return;
            } catch (const std::exception& e) {
                std::cerr << "Subscribe attempt " << (attempt+1) << "/60 failed: " << e.what() << std::endl;
                std::this_thread::sleep_for(std::chrono::seconds(1));
            }
        }
        throw std::runtime_error("Failed to subscribe after 60 attempts");
    }

    void run() {
        while (!g_shutdown.load()) {
            auto records = consumer_->poll(std::chrono::milliseconds(1000));

            for (const auto& record : records) {
                std::string value_str(static_cast<const char*>(record.value().data()), record.value().size());

                std::string merchant_id;
                double total;

                if (!parse_order_event(value_str, merchant_id, total)) {
                    std::cerr << "Failed to parse order event: " << value_str << std::endl;
                    continue;
                }

                // Use current time as event time (simplified - production would use record timestamp)
                int64_t event_time = get_current_time_seconds();
                int64_t window_start = compute_window_start(event_time);

                WindowKey key{window_start, merchant_id};
                windows_[key].order_count++;
                windows_[key].revenue += total;

                std::cout << "Processed order for " << merchant_id
                          << ", total=" << total
                          << ", window_start=" << window_start << std::endl;
            }

            // Commit offsets after processing batch
            if (!records.empty()) {
                try {
                    consumer_->commitSync();
                } catch (const std::exception& e) {
                    std::cerr << "Commit failed: " << e.what() << std::endl;
                }
            }

            // Check for expired windows
            int64_t current_time = get_current_time_seconds();
            flush_expired_windows(current_time);
        }

        // On shutdown, flush all remaining windows
        flush_all_windows();
        consumer_->close();
    }
};

int main() {
    std::signal(SIGTERM, signal_handler);
    std::signal(SIGINT, signal_handler);

    const char* bootstrap = std::getenv("KAFKA_BOOTSTRAP");
    if (!bootstrap) bootstrap = "localhost:9094";

    const char* window_env = std::getenv("WINDOW_SECONDS");
    int64_t window_seconds = window_env ? std::atol(window_env) : 10;

    try {
        StreamProcessor processor(bootstrap, window_seconds);
        processor.run();
    } catch (const std::exception& e) {
        std::cerr << "Fatal error: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "Stream processor shutdown complete" << std::endl;
    return 0;
}
