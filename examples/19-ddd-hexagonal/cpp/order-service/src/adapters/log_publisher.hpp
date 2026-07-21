// adapters/log_publisher.hpp — Log-based event publisher.
//
// This IS an adapter — it can import spdlog or any logging framework. The
// domain layer depends on the EventPublisher interface; this adapter logs
// domain events rather than sending them to Kafka (that's for a different
// example).

#pragma once

#include "../domain/models.hpp"
#include "../domain/ports.hpp"
#include <spdlog/spdlog.h>

namespace cndp::adapters {

class LogEventPublisher : public domain::EventPublisher {
public:
    void publish(const domain::OrderPlaced& event) override {
        spdlog::info("EVENT OrderPlaced order_id={} sku={} qty={}",
                     event.order_id, event.sku, event.quantity);
    }
};

}  // namespace cndp::adapters
