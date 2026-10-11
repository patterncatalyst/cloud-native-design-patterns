// orders.hpp — the order record and the port to the order-api REST service.

#pragma once

#include <optional>
#include <string>
#include <vector>

namespace cndp {

struct Order {
    std::string id;
    std::string sku;
    int quantity = 0;
    std::string status;
};

class OrderSource {
public:
    virtual ~OrderSource() = default;
    // Both throw std::runtime_error when order-api is unreachable.
    virtual std::vector<Order> list(int limit) = 0;
    virtual std::optional<Order> find(const std::string& id) = 0;
};

}  // namespace cndp
