// kafka_publisher.hpp — order.placed producer on librdkafka's C++ API (rdkafka++).
//
// produce() is asynchronous: librdkafka batches and retries in its own threads, and the
// outcome of every message arrives in the delivery-report callback, which a small poll
// thread serves. The destructor flushes, so no accepted event is lost on SIGTERM.

#pragma once

#include <atomic>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>

#include <librdkafka/rdkafkacpp.h>
#include <trantor/utils/Logger.h>

namespace cndp {

class OrderPublisher {
public:
    OrderPublisher(const std::string& bootstrap, std::string topic) : topic_(std::move(topic)) {
        std::string err;
        std::unique_ptr<RdKafka::Conf> conf(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));
        if (conf->set("bootstrap.servers", bootstrap, err) != RdKafka::Conf::CONF_OK ||
            conf->set("acks", "all", err) != RdKafka::Conf::CONF_OK ||
            conf->set("enable.idempotence", "true", err) != RdKafka::Conf::CONF_OK ||
            conf->set("dr_cb", &report_, err) != RdKafka::Conf::CONF_OK) {
            throw std::runtime_error("kafka config: " + err);
        }
        producer_.reset(RdKafka::Producer::create(conf.get(), err));
        if (!producer_) throw std::runtime_error("kafka producer: " + err);
        poller_ = std::thread([this] {
            while (!stop_.load()) producer_->poll(100);
        });
    }

    OrderPublisher(const OrderPublisher&) = delete;
    OrderPublisher& operator=(const OrderPublisher&) = delete;

    ~OrderPublisher() {
        stop_.store(true);
        if (poller_.joinable()) poller_.join();
        producer_->flush(10'000);  // serves the remaining delivery reports
    }

    // Queues one message (no key: the event is not partition-ordered). Returns false if the
    // local queue refused it; the broker's verdict arrives later in the delivery report.
    bool publish(const std::string& payload) {
        RdKafka::ErrorCode rc = producer_->produce(
            topic_, RdKafka::Topic::PARTITION_UA, RdKafka::Producer::RK_MSG_COPY,
            const_cast<char*>(payload.data()), payload.size(), nullptr, 0, 0, nullptr);
        if (rc != RdKafka::ERR_NO_ERROR) {
            LOG_ERROR << "kafka produce failed: " << RdKafka::err2str(rc);
            return false;
        }
        return true;
    }

private:
    class Report : public RdKafka::DeliveryReportCb {
    public:
        void dr_cb(RdKafka::Message& m) override {
            if (m.err() != RdKafka::ERR_NO_ERROR) {
                LOG_ERROR << "kafka delivery failed topic=" << m.topic_name() << ": " << m.errstr();
            }
        }
    };

    std::string topic_;
    Report report_;
    std::unique_ptr<RdKafka::Producer> producer_;
    std::atomic<bool> stop_{false};
    std::thread poller_;
};

}  // namespace cndp
