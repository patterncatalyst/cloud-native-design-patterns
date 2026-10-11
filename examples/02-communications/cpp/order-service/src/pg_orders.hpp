// pg_orders.hpp — OrderRepo on libpq (direct C client). One connection behind a mutex;
// every statement is parameterised (PQexecParams), so no value is ever spliced into SQL.

#pragma once

#include <memory>
#include <cstdlib>
#include <mutex>
#include <optional>
#include <vector>
#include <stdexcept>
#include <string>

#include <libpq-fe.h>

#include "orders.hpp"

namespace cndp {

class PgOrderRepo : public OrderRepo {
public:
    explicit PgOrderRepo(const std::string& conninfo) : conninfo_(conninfo) {
        conn_.reset(PQconnectdb(conninfo_.c_str()));
        if (PQstatus(conn_.get()) != CONNECTION_OK) {
            throw std::runtime_error(std::string("pg connect failed: ") + PQerrorMessage(conn_.get()));
        }
    }

    std::vector<Order> list(int limit, const std::string& after) override {
        std::lock_guard lock(mu_);
        const std::string lim = std::to_string(limit);
        Result res = after.empty()
            ? exec("SELECT id, sku, quantity, status FROM orders ORDER BY id LIMIT $1::int",
                   {lim.c_str()})
            : exec("SELECT id, sku, quantity, status FROM orders WHERE id > $1 ORDER BY id LIMIT $2::int",
                   {after.c_str(), lim.c_str()});
        return rows(res.get());
    }

    std::optional<Order> find(const std::string& id) override {
        std::lock_guard lock(mu_);
        Result res = exec("SELECT id, sku, quantity, status FROM orders WHERE id = $1", {id.c_str()});
        auto found = rows(res.get());
        if (found.empty()) return std::nullopt;
        return found.front();
    }

    void insert(const Order& o) override {
        std::lock_guard lock(mu_);
        const std::string qty = std::to_string(o.quantity);
        Result res = exec("INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3::int, $4)",
                          {o.id.c_str(), o.sku.c_str(), qty.c_str(), o.status.c_str()}, PGRES_COMMAND_OK);
        (void)res;
    }

private:
    struct ConnDeleter { void operator()(PGconn* c) const noexcept { if (c) PQfinish(c); } };
    struct ResultDeleter { void operator()(PGresult* r) const noexcept { PQclear(r); } };
    using Result = std::unique_ptr<PGresult, ResultDeleter>;

    Result exec(const char* sql, std::initializer_list<const char*> params,
                ExecStatusType expect = PGRES_TUPLES_OK) {
        if (PQstatus(conn_.get()) != CONNECTION_OK) PQreset(conn_.get());
        Result res(PQexecParams(conn_.get(), sql, static_cast<int>(params.size()), nullptr,
                                params.begin(), nullptr, nullptr, 0));
        if (!res || PQresultStatus(res.get()) != expect) {
            throw std::runtime_error(std::string("pg query failed: ") + PQerrorMessage(conn_.get()));
        }
        return res;
    }

    static std::vector<Order> rows(const PGresult* res) {
        std::vector<Order> out;
        const int n = PQntuples(res);
        out.reserve(static_cast<size_t>(n));
        for (int i = 0; i < n; ++i) {
            out.push_back({PQgetvalue(res, i, 0), PQgetvalue(res, i, 1),
                           std::atoi(PQgetvalue(res, i, 2)), PQgetvalue(res, i, 3)});
        }
        return out;
    }

    std::string conninfo_;
    std::unique_ptr<PGconn, ConnDeleter> conn_;
    std::mutex mu_;
};

}  // namespace cndp
