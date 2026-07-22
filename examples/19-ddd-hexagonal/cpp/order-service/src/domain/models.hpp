// domain/models.hpp — Domain entities and value objects.
//
// ZERO framework imports. This is pure C++ — no Drogon, no libpq, no spdlog.
// The domain layer knows nothing about HTTP, databases, or logging.

#pragma once

#include <random>
#include <sstream>
#include <iomanip>
#include <string>

namespace cndp::domain {

struct Order {
    std::string id;
    std::string sku;
    int quantity;
    std::string status;
};

struct OrderPlaced {
    std::string order_id;
    std::string sku;
    int quantity;
};

// UUID generation is domain logic (ID assignment) — no external libs needed.
inline std::string generate_uuid() {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<uint32_t> dist;

    std::ostringstream ss;
    ss << std::hex << std::setfill('0');
    ss << std::setw(8) << dist(gen) << "-";
    ss << std::setw(4) << (dist(gen) & 0xFFFF) << "-";
    ss << std::setw(4) << ((dist(gen) & 0x0FFF) | 0x4000) << "-";
    ss << std::setw(4) << ((dist(gen) & 0x3FFF) | 0x8000) << "-";
    ss << std::setw(8) << dist(gen) << std::setw(4) << (dist(gen) & 0xFFFF);

    return ss.str();
}

}  // namespace cndp::domain
