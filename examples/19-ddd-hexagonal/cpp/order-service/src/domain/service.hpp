// domain/service.hpp — Application use cases (domain service layer).
//
// ZERO framework imports. Use cases orchestrate domain logic. They depend
// ONLY on domain models and ports — never on concrete adapters or infra.

#pragma once

#include "models.hpp"
#include "ports.hpp"
#include <stdexcept>
#include <string>

namespace cndp::domain {

struct PlaceOrderCmd {
    std::string sku;
    int quantity;
};

class PlaceOrderUseCase {
public:
    PlaceOrderUseCase(OrderRepository& repo, EventPublisher& publisher)
        : repo_(repo), publisher_(publisher) {}

    // Execute the use case: validate, create order, persist, publish event.
    // Throws std::invalid_argument on validation failure.
    Order execute(const PlaceOrderCmd& cmd) {
        // Domain invariant: sku must not be empty, quantity must be positive
        if (cmd.sku.empty()) {
            throw std::invalid_argument("sku cannot be empty");
        }
        if (cmd.quantity <= 0) {
            throw std::invalid_argument("quantity must be positive");
        }

        // Create the order (domain logic)
        Order order;
        order.id = generate_uuid();
        order.sku = cmd.sku;
        order.quantity = cmd.quantity;
        order.status = "placed";

        // Persist via repository port
        repo_.save(order);

        // Publish domain event via event publisher port
        OrderPlaced event;
        event.order_id = order.id;
        event.sku = order.sku;
        event.quantity = order.quantity;
        publisher_.publish(event);

        return order;
    }

private:
    OrderRepository& repo_;
    EventPublisher& publisher_;
};

}  // namespace cndp::domain
