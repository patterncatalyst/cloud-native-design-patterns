// adapters/pg_repository.hpp — PostgreSQL adapter implementing OrderRepository.
//
// This IS an adapter — it can import libpq, use the pool, talk SQL. The domain
// layer depends on the OrderRepository interface; this adapter satisfies it.

#pragma once

#include "../domain/models.hpp"
#include "../domain/ports.hpp"
#include "../pg_pool.hpp"
#include <libpq-fe.h>
#include <chrono>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace cndp::adapters {

class PgOrderRepository : public domain::OrderRepository {
public:
    explicit PgOrderRepository(PgPool& pool) : pool_(pool) {}

    void save(const domain::Order& order) override {
        auto conn = pool_.acquire(std::chrono::milliseconds(5000));
        PGconn* pg = conn.get();

        std::string qty_str = std::to_string(order.quantity);
        const char* params[4] = {
            order.id.c_str(),
            order.sku.c_str(),
            qty_str.c_str(),
            order.status.c_str()
        };

        PGresult* res = PQexecParams(
            pg,
            "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4)",
            4, nullptr, params, nullptr, nullptr, 0);

        if (PQresultStatus(res) != PGRES_COMMAND_OK) {
            std::string err = PQerrorMessage(pg);
            PQclear(res);
            throw std::runtime_error("PgOrderRepository::save failed: " + err);
        }
        PQclear(res);
    }

    std::optional<domain::Order> find_by_id(const std::string& id) override {
        auto conn = pool_.acquire(std::chrono::milliseconds(5000));
        PGconn* pg = conn.get();

        const char* params[1] = { id.c_str() };
        PGresult* res = PQexecParams(
            pg,
            "SELECT id, sku, quantity, status FROM orders WHERE id = $1",
            1, nullptr, params, nullptr, nullptr, 0);

        if (PQresultStatus(res) != PGRES_TUPLES_OK) {
            std::string err = PQerrorMessage(pg);
            PQclear(res);
            throw std::runtime_error("PgOrderRepository::find_by_id failed: " + err);
        }

        if (PQntuples(res) == 0) {
            PQclear(res);
            return std::nullopt;
        }

        domain::Order order;
        order.id = PQgetvalue(res, 0, 0);
        order.sku = PQgetvalue(res, 0, 1);
        order.quantity = std::stoi(PQgetvalue(res, 0, 2));
        order.status = PQgetvalue(res, 0, 3);

        PQclear(res);
        return order;
    }

    std::vector<domain::Order> find_all() override {
        auto conn = pool_.acquire(std::chrono::milliseconds(5000));
        PGconn* pg = conn.get();

        PGresult* res = PQexec(pg, "SELECT id, sku, quantity, status FROM orders");

        if (PQresultStatus(res) != PGRES_TUPLES_OK) {
            std::string err = PQerrorMessage(pg);
            PQclear(res);
            throw std::runtime_error("PgOrderRepository::find_all failed: " + err);
        }

        std::vector<domain::Order> orders;
        int nrows = PQntuples(res);
        orders.reserve(nrows);

        for (int i = 0; i < nrows; ++i) {
            domain::Order order;
            order.id = PQgetvalue(res, i, 0);
            order.sku = PQgetvalue(res, i, 1);
            order.quantity = std::stoi(PQgetvalue(res, i, 2));
            order.status = PQgetvalue(res, i, 3);
            orders.push_back(order);
        }

        PQclear(res);
        return orders;
    }

private:
    PgPool& pool_;
};

}  // namespace cndp::adapters
