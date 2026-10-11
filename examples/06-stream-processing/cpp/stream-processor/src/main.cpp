// stream-processor: order.placed -> tumbling window per merchant -> revenue.by-merchant,
// written directly on librdkafka's C++ API.
//
// The C++ lock has no Kafka Streams equivalent, so the topology is explicit. It mirrors the
// Go (goka) version and the Kafka Streams one:
//
//   1. rekey:     order.placed -> parse -> stream-processor-by-merchant (key = merchant_id,
//                 the record time is carried over so event time survives the hop)
//   2. aggregate: stream-processor-by-merchant -> per-merchant tumbling windows (no grace)
//                 -> revenue.by-merchant (one record per update)
//
// One KafkaConsumer in group "stream-processor" reads both input topics, so the repartition
// topic puts every merchant on one partition and therefore one instance. Delivery and commit
// order: a batch of records is processed, the producer is flushed (every output record
// delivery-reported), and only then are the input offsets committed. A crash replays the
// uncommitted batch (at-least-once); consumers of revenue.by-merchant keep the latest record
// per (merchant_id, window_start). Delivery is at-least-once, not exactly-once: window state
// is in memory, so after a restart (or a rebalance) a window that was open restarts from the
// committed offset and its first re-emitted update carries a PARTIAL value that overwrites
// the earlier, fuller one until the rest is replayed; and a replayed order.placed batch is
// rekeyed again, so records that were already forwarded to the repartition topic before a
// crash are counted twice in their window. A failed delivery or commit makes the process
// close its clients and exit non-zero so a supervisor restarts it.

#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <memory>
#include <optional>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include <librdkafka/rdkafka.h>
#include <librdkafka/rdkafkacpp.h>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/spdlog.h>

#include "aggregation.hpp"

namespace {

constexpr const char* kOrders = "order.placed";
constexpr const char* kByMerchant = "stream-processor-by-merchant";
constexpr const char* kRevenue = "revenue.by-merchant";
constexpr int kDefaultPartitions = 3;

std::atomic<bool> g_shutdown{false};
void on_signal(int) { g_shutdown = true; }

// Delivery reports: count failures so the batch is not committed over a lost record.
class DeliveryReports : public RdKafka::DeliveryReportCb {
public:
    void dr_cb(RdKafka::Message& m) override {
        if (m.err() != RdKafka::ERR_NO_ERROR) {
            spdlog::error("delivery to {} failed: {}", m.topic_name(), m.errstr());
            failed_.fetch_add(1);
        }
    }
    int failed() const { return failed_.load(); }

private:
    std::atomic<int> failed_{0};
};

std::string env_or(const char* name, const char* fallback) {
    const char* v = std::getenv(name);
    return v && *v ? v : fallback;
}

bool set_all(RdKafka::Conf& conf, std::initializer_list<std::pair<const char*, std::string>> kv) {
    std::string err;
    for (auto& [k, v] : kv) {
        if (conf.set(k, v, err) != RdKafka::Conf::CONF_OK) {
            spdlog::error("kafka config {}={}: {}", k, v, err);
            return false;
        }
    }
    return true;
}

// Creates a topic through the admin API (the C++ wrapper has none); already existing is fine.
bool ensure_topic(RdKafka::Handle& handle, const std::string& name, int partitions) {
    rd_kafka_t* rk = handle.c_ptr();
    char errstr[256];
    rd_kafka_NewTopic_t* nt = rd_kafka_NewTopic_new(name.c_str(), partitions, 1, errstr, sizeof errstr);
    if (!nt) {
        spdlog::error("new topic {}: {}", name, errstr);
        return false;
    }
    rd_kafka_queue_t* q = rd_kafka_queue_new(rk);
    rd_kafka_CreateTopics(rk, &nt, 1, nullptr, q);
    rd_kafka_NewTopic_destroy(nt);
    rd_kafka_event_t* ev = rd_kafka_queue_poll(q, 15000);
    bool ok = false;
    if (ev) {
        if (rd_kafka_event_error(ev) == RD_KAFKA_RESP_ERR_NO_ERROR) {
            size_t n = 0;
            const rd_kafka_topic_result_t** res =
                rd_kafka_CreateTopics_result_topics(rd_kafka_event_CreateTopics_result(ev), &n);
            ok = n == 1;
            if (n == 1 && rd_kafka_topic_result_error(res[0]) != RD_KAFKA_RESP_ERR_NO_ERROR &&
                rd_kafka_topic_result_error(res[0]) != RD_KAFKA_RESP_ERR_TOPIC_ALREADY_EXISTS) {
                spdlog::warn("create topic {}: {}", name, rd_kafka_topic_result_error_string(res[0]));
                ok = false;
            }
        } else {
            spdlog::warn("create topic {}: {}", name, rd_kafka_event_error_string(ev));
        }
        rd_kafka_event_destroy(ev);
    }
    rd_kafka_queue_destroy(q);
    return ok;
}

// Partition count of an existing topic, or 0 when it cannot be read.
int partition_count(RdKafka::Handle& handle, const std::string& name) {
    std::string err;
    std::unique_ptr<RdKafka::Topic> topic(RdKafka::Topic::create(&handle, name, nullptr, err));
    if (!topic) return 0;
    RdKafka::Metadata* md = nullptr;
    if (handle.metadata(false, topic.get(), &md, 5000) != RdKafka::ERR_NO_ERROR || !md) return 0;
    std::unique_ptr<RdKafka::Metadata> owned(md);
    for (auto* t : *md->topics())
        if (t->topic() == name && t->err() == RdKafka::ERR_NO_ERROR)
            return static_cast<int>(t->partitions()->size());
    return 0;
}

class Processor : public RdKafka::RebalanceCb {
public:
    Processor(std::string bootstrap, int64_t window_seconds)
        : bootstrap_(std::move(bootstrap)), window_seconds_(window_seconds) {}

    // Topics are created up front (3 partitions for the source if nobody did yet, the same
    // count for the repartition and sink topics so keys stay co-partitioned).
    int prepare_topics() {
        std::string err;
        std::unique_ptr<RdKafka::Conf> conf(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));
        if (!set_all(*conf, {{"bootstrap.servers", bootstrap_}})) return 0;
        std::unique_ptr<RdKafka::Producer> admin(RdKafka::Producer::create(conf.get(), err));
        if (!admin) {
            spdlog::warn("kafka client: {}", err);
            return 0;
        }
        if (!ensure_topic(*admin, kOrders, kDefaultPartitions)) return 0;
        int n = partition_count(*admin, kOrders);
        if (n <= 0) return 0;
        if (!ensure_topic(*admin, kRevenue, n) || !ensure_topic(*admin, kByMerchant, n)) return 0;
        return n;
    }

    bool start() {
        std::string err;
        std::unique_ptr<RdKafka::Conf> pconf(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));
        if (!set_all(*pconf, {{"bootstrap.servers", bootstrap_},
                              {"client.id", "stream-processor"},
                              {"acks", "all"},
                              {"enable.idempotence", "true"},
                              {"linger.ms", "5"}}) ||
            pconf->set("dr_cb", &reports_, err) != RdKafka::Conf::CONF_OK)
            return false;
        producer_.reset(RdKafka::Producer::create(pconf.get(), err));
        if (!producer_) {
            spdlog::error("producer: {}", err);
            return false;
        }

        std::unique_ptr<RdKafka::Conf> cconf(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));
        if (!set_all(*cconf, {{"bootstrap.servers", bootstrap_},
                              {"group.id", "stream-processor"},
                              {"auto.offset.reset", "earliest"},
                              {"enable.auto.commit", "false"},
                              {"session.timeout.ms", "10000"},
                              {"heartbeat.interval.ms", "3000"}}) ||
            cconf->set("rebalance_cb", this, err) != RdKafka::Conf::CONF_OK)
            return false;
        consumer_.reset(RdKafka::KafkaConsumer::create(cconf.get(), err));
        if (!consumer_) {
            spdlog::error("consumer: {}", err);
            return false;
        }
        if (auto rc = consumer_->subscribe({kOrders, kByMerchant}); rc != RdKafka::ERR_NO_ERROR) {
            spdlog::error("subscribe: {}", RdKafka::err2str(rc));
            return false;
        }
        return true;
    }

    // Window state belongs to the partitions it was built from: drop it on rebalance, and
    // replay from the committed offsets.
    void rebalance_cb(RdKafka::KafkaConsumer* consumer, RdKafka::ErrorCode err,
                      std::vector<RdKafka::TopicPartition*>& partitions) override {
        if (err == RdKafka::ERR__ASSIGN_PARTITIONS) {
            spdlog::info("assigned {} partitions", partitions.size());
            consumer->assign(partitions);
        } else {
            spdlog::info("revoked {} partitions", partitions.size());
            merchants_.clear();
            consumer->unassign();
        }
    }

    // Returns false when it stopped because output could not be delivered (exit non-zero).
    bool run() {
        bool ok = true;
        spdlog::info("stream-processor started window_seconds={}", window_seconds_);
        const int batch_max = 500;
        while (!g_shutdown) {
            int handled = 0;
            auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(1000);
            while (handled < batch_max && std::chrono::steady_clock::now() < deadline && !g_shutdown) {
                std::unique_ptr<RdKafka::Message> msg(consumer_->consume(200));
                switch (msg->err()) {
                    case RdKafka::ERR_NO_ERROR:
                        handle(*msg);
                        ++handled;
                        break;
                    case RdKafka::ERR__TIMED_OUT:
                    case RdKafka::ERR__PARTITION_EOF:
                        break;
                    default:
                        spdlog::warn("consume: {}", msg->errstr());
                }
            }
            if (handled > 0 && !commit_batch()) {
                ok = false;
                break;
            }
            producer_->poll(0);
        }
        // Close the clients cleanly on every path (flush what is queued, leave the group).
        producer_->flush(10000);
        consumer_->close();
        spdlog::info("stream-processor stopped");
        return ok;
    }

private:
    void handle(RdKafka::Message& msg) {
        const std::string topic = msg.topic_name();
        const std::string value(static_cast<const char*>(msg.payload()), msg.len());
        if (topic == kOrders) rekey(msg, value);
        else aggregate(msg, value);
    }

    // order.placed -> stream-processor-by-merchant
    void rekey(RdKafka::Message& msg, const std::string& value) {
        auto ev = cndp::parse_order_event(value);
        if (!ev) {
            spdlog::warn("skipping unreadable order record");
            return;
        }
        if (!cndp::parse_decimal(ev->total_text)) {
            spdlog::warn("skipping order with invalid total merchant={} total={}", ev->merchant,
                         ev->total_text);
            return;
        }
        int64_t ts = msg.timestamp().type == RdKafka::MessageTimestamp::MSG_TIMESTAMP_NOT_AVAILABLE
                         ? now_millis()
                         : msg.timestamp().timestamp;
        nlohmann::json body = {{"ts", ts}, {"total", ev->total_text}};
        send(kByMerchant, ev->merchant, body.dump(), ts);
    }

    // stream-processor-by-merchant -> revenue.by-merchant
    void aggregate(RdKafka::Message& msg, const std::string& value) {
        if (!msg.key()) return;
        const std::string merchant = *msg.key();
        // A malformed repartition record is skipped (WARN); the batch still commits past it.
        auto body = nlohmann::json::parse(value, nullptr, false);
        if (body.is_discarded() || !body.is_object() || !body.contains("ts") || !body.contains("total")) {
            spdlog::warn("skipping malformed repartition record merchant={}", merchant);
            return;
        }
        std::optional<cndp::Decimal> amount;
        int64_t ts = 0;
        try {
            amount = cndp::parse_decimal(body["total"].get<std::string>());
            ts = body["ts"].get<int64_t>();
        } catch (const nlohmann::json::exception& e) {
            spdlog::warn("skipping repartition record with wrong field types merchant={}: {}", merchant, e.what());
            return;
        }
        if (!amount) {
            spdlog::warn("skipping repartition record with invalid total merchant={}", merchant);
            return;
        }

        auto it = merchants_.try_emplace(merchant, cndp::MerchantWindows(window_seconds_)).first;
        auto update = it->second.apply(ts, *amount);
        if (!update) {
            if (it->second.overflowed())
                spdlog::warn("skipping order: window total out of range merchant={}", merchant);
            else
                spdlog::debug("dropping late record merchant={}", merchant);
            return;
        }
        spdlog::info("emitted revenue window={} merchant={} count={} revenue={}", update->start,
                     merchant, update->count, cndp::money(update->total));
        send(kRevenue, merchant, cndp::revenue_json(merchant, *update), 0);
    }

    void send(const char* topic, const std::string& key, const std::string& payload, int64_t ts) {
        for (;;) {
            auto rc = producer_->produce(topic, RdKafka::Topic::PARTITION_UA, RdKafka::Producer::RK_MSG_COPY,
                                         const_cast<char*>(payload.data()), payload.size(), key.data(),
                                         key.size(), ts, nullptr, nullptr);
            if (rc == RdKafka::ERR_NO_ERROR) return;
            if (rc == RdKafka::ERR__QUEUE_FULL) {
                producer_->poll(100);
                continue;
            }
            spdlog::error("produce to {}: {}", topic, RdKafka::err2str(rc));
            reports_failed_extra_++;
            return;
        }
    }

    // Everything produced for this batch must be delivered before its input offsets are
    // committed.
    bool commit_batch() {
        producer_->flush(30000);
        if (reports_.failed() > 0 || reports_failed_extra_ > 0 || producer_->outq_len() > 0) {
            spdlog::error("output not delivered; not committing, exiting to replay from the last commit");
            return false;
        }
        if (auto rc = consumer_->commitSync(); rc != RdKafka::ERR_NO_ERROR && rc != RdKafka::ERR__NO_OFFSET)
            spdlog::warn("commit failed: {}", RdKafka::err2str(rc));
        return true;
    }

    static int64_t now_millis() {
        return std::chrono::duration_cast<std::chrono::milliseconds>(
                   std::chrono::system_clock::now().time_since_epoch())
            .count();
    }

    std::string bootstrap_;
    int64_t window_seconds_;
    DeliveryReports reports_;
    int reports_failed_extra_ = 0;
    std::unique_ptr<RdKafka::Producer> producer_;
    std::unique_ptr<RdKafka::KafkaConsumer> consumer_;
    std::unordered_map<std::string, cndp::MerchantWindows> merchants_;
};

}  // namespace

int main() {
    spdlog::set_default_logger(spdlog::stderr_color_mt("stream-processor"));
    spdlog::set_pattern("%Y-%m-%dT%H:%M:%S.%e %^%l%$ %v");
    std::signal(SIGTERM, on_signal);
    std::signal(SIGINT, on_signal);

    int64_t window_seconds = 10;
    if (const char* w = std::getenv("WINDOW_SECONDS")) {
        long n = std::atol(w);
        if (n > 0) window_seconds = n;
    }

    Processor processor(env_or("KAFKA_BOOTSTRAP", "kafka:9094"), window_seconds);
    int partitions = 0;
    for (int attempt = 1; attempt <= 30 && !g_shutdown; ++attempt) {
        partitions = processor.prepare_topics();
        if (partitions > 0) break;
        spdlog::warn("Kafka not ready, retry {}/30", attempt);
        std::this_thread::sleep_for(std::chrono::seconds(2));
    }
    if (partitions <= 0) {
        spdlog::error("could not prepare topics");
        return 1;
    }
    spdlog::info("topics ready partitions={}", partitions);
    if (!processor.start()) return 1;
    return processor.run() ? 0 : 1;
}
