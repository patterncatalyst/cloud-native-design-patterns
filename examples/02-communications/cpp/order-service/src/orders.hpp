// orders.hpp — the order record and the repository port the GraphQL and REST layers share.

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

class OrderRepo {
public:
    virtual ~OrderRepo() = default;
    // Orders with id > after (empty = from the start), ordered by id, at most `limit`.
    virtual std::vector<Order> list(int limit, const std::string& after) = 0;
    virtual std::optional<Order> find(const std::string& id) = 0;
    virtual void insert(const Order& order) = 0;
};

}  // namespace cndp
