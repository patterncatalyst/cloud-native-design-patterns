// pg_pool.hpp — a small connection pool with RAII checkout.
//
// PostgreSQL's C client, libpq, gives us one connection at a time
// (PGconn*) and no pool, so this is the one piece we hand-roll. It is
// process-scoped infrastructure: constructed once in main()'s composition
// root and shared across handler threads.
//
//   PgPool            owns N connections; hands them out and reclaims
//   ScopedConnection  the per-request RAII checkout — returns the
//                     connection to the pool on scope exit
//
// Exception safety: A query that timed out or hit a connection reset
// leaves the connection in an indeterminate state. The handler calls
// invalidate() on such a connection; the pool then discards it on release
// rather than handing a poisoned connection to the next request. release()
// never throws and never opens a connection (no work in a destructor); a
// discarded connection is replaced lazily on the next acquire().

#pragma once

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <libpq-fe.h>

namespace cndp {

// PGconn* owned via unique_ptr; PQfinish closes the connection.
struct PgConnDeleter {
    void operator()(PGconn* c) const noexcept {
        if (c) PQfinish(c);
    }
};
using PgConnPtr = std::unique_ptr<PGconn, PgConnDeleter>;

class PgPool;

// Per-request RAII handle. Move-only. Returns its connection to the
// pool when it goes out of scope.
class ScopedConnection {
public:
    ScopedConnection(ScopedConnection&& other) noexcept
        : pool_(other.pool_),
          conn_(std::move(other.conn_)),
          valid_(other.valid_) {
        other.pool_ = nullptr;
        other.valid_ = false;
    }
    ScopedConnection& operator=(ScopedConnection&&) = delete;
    ScopedConnection(const ScopedConnection&) = delete;
    ScopedConnection& operator=(const ScopedConnection&) = delete;

    ~ScopedConnection();  // returns conn_ to the pool (defined below)

    PGconn* get() const noexcept { return conn_.get(); }

    // Mark the connection unusable (e.g. after a reset or a timed-out
    // query whose commit state is unknown). The pool discards it on
    // release rather than returning it to the free list.
    void invalidate() noexcept { valid_ = false; }

private:
    friend class PgPool;
    ScopedConnection(PgPool* pool, PgConnPtr conn)
        : pool_(pool), conn_(std::move(conn)), valid_(true) {}

    PgPool* pool_;
    PgConnPtr conn_;
    bool valid_;
};

class PgPool {
public:
    // Eagerly opens `size` connections so the first requests don't pay
    // connection-setup latency. Throws if the database is unreachable —
    // fail fast at startup and let the orchestrator restart once the DB
    // is ready.
    PgPool(std::string conninfo, std::size_t size)
        : conninfo_(std::move(conninfo)), size_(size) {
        free_.reserve(size_);
        for (std::size_t i = 0; i < size_; ++i) {
            free_.push_back(open_one());
            ++live_;
        }
    }

    PgPool(const PgPool&) = delete;
    PgPool& operator=(const PgPool&) = delete;

    // Check out a connection, waiting up to `timeout` for one to become
    // free. Throws std::runtime_error on timeout. May open a fresh
    // connection here (not in a destructor) to replace one previously
    // discarded, so connection-setup exceptions surface here — the
    // handler maps them to an error status.
    ScopedConnection acquire(std::chrono::milliseconds timeout) {
        std::unique_lock<std::mutex> lk(mu_);
        const bool ready = cv_.wait_for(lk, timeout, [this] {
            return !free_.empty() || live_ < size_;
        });
        if (!ready) {
            throw std::runtime_error("PgPool: checkout timed out");
        }
        if (!free_.empty()) {
            auto conn = std::move(free_.back());
            free_.pop_back();
            return ScopedConnection(this, std::move(conn));
        }
        // free list empty but below capacity: a connection was
        // discarded earlier; open a replacement now.
        ++live_;
        lk.unlock();
        PgConnPtr conn;
        try {
            conn = open_one();
        } catch (...) {
            std::lock_guard<std::mutex> relk(mu_);
            --live_;            // creation failed; give the slot back
            cv_.notify_one();
            throw;
        }
        return ScopedConnection(this, std::move(conn));
    }

    std::size_t size() const noexcept { return size_; }

private:
    friend class ScopedConnection;

    PgConnPtr open_one() {
        PgConnPtr conn(PQconnectdb(conninfo_.c_str()));
        if (!conn || PQstatus(conn.get()) != CONNECTION_OK) {
            const std::string err =
                conn ? PQerrorMessage(conn.get()) : "PQconnectdb returned null";
            throw std::runtime_error("PgPool: connect failed: " + err);
        }
        return conn;
    }

    // Called only from ~ScopedConnection. noexcept: never opens a
    // connection, never throws.
    void release(PgConnPtr conn, bool valid) noexcept {
        std::lock_guard<std::mutex> lk(mu_);
        if (valid && conn) {
            free_.push_back(std::move(conn));
        } else {
            --live_;  // discard the poisoned connection; replaced lazily
        }
        cv_.notify_one();
    }

    std::string conninfo_;
    std::size_t size_;
    std::mutex mu_;
    std::condition_variable cv_;
    std::vector<PgConnPtr> free_;
    std::size_t live_ = 0;  // open connections (free + checked out)
};

inline ScopedConnection::~ScopedConnection() {
    if (pool_ && conn_) {
        pool_->release(std::move(conn_), valid_);
    }
}

}  // namespace cndp
