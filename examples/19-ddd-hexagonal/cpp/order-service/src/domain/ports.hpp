// domain/ports.hpp — Abstract interfaces (dependency inversion).
//
// ZERO framework imports. Ports define the shape of what the domain needs,
// but know nothing about how those needs are satisfied (PostgreSQL? In-memory?
// Kafka? Logs?). Adapters implement these interfaces.

#pragma once

#include "models.hpp"
#include <optional>
#include <vector>

namespace cndp::domain {

// Repository port — the domain needs persistence.
struct OrderRepository {
    virtual ~OrderRepository() = default;
    virtual void save(const Order& order) = 0;
    virtual std::optional<Order> find_by_id(const std::string& id) = 0;
    virtual std::vector<Order> find_all() = 0;
};

// Event publisher port — the domain publishes domain events.
struct EventPublisher {
    virtual ~EventPublisher() = default;
    virtual void publish(const OrderPlaced& event) = 0;
};

}  // namespace cndp::domain
