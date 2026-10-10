// stock_loader.hpp — request-scoped batching of stock lookups (the "DataLoader").
//
// The query resolvers register every SKU they return; one batch call covers all of them,
// whichever root field returned them. A query that never selects `stock` makes no
// inventory call.

#pragma once

#include <functional>
#include <map>
#include <mutex>
#include <optional>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

#include <graphqlservice/GraphQLService.h>

#include "orders.hpp"

namespace cndp {

// SKU -> available units for the whole set, or nullopt when the lookup failed.
using StockBatchFn =
    std::function<std::optional<std::unordered_map<std::string, int>>(const std::set<std::string>&)>;

// Two passes per request. Resolvers run field by field, so the first `stock` resolve can
// happen before a later root field has returned its orders; batching there would miss
// those SKUs. GraphQLApi therefore resolves the query once in Collect mode (stock resolvers
// only note that stock was asked for; every returned order registers its SKU), makes the
// ONE batch call for the whole set, then resolves again in Serve mode, where stock reads
// the batch result. The order-api reads are memoised per request so the second pass makes
// no extra REST calls.
class StockState : public graphql::service::RequestState {
public:
    explicit StockState(StockBatchFn fetch) : fetch_(std::move(fetch)) {}

    void register_sku(const std::string& sku) {
        std::lock_guard lock(mu_);
        skus_.insert(sku);
    }

    // End of the Collect pass: one batch call if any resolver asked for stock.
    void load() {
        std::set<std::string> skus;
        {
            std::lock_guard lock(mu_);
            if (!requested_) return;
            skus = skus_;
        }
        result_ = fetch_(skus);
        serving_ = true;
    }

    // nullopt in the Collect pass, when the lookup failed, and for a SKU the inventory
    // does not know (the GraphQL field is nullable, like the Python gateway).
    std::optional<int> stock(const std::string& sku) {
        if (!serving_) {
            std::lock_guard lock(mu_);
            requested_ = true;
            return std::nullopt;
        }
        if (!result_) return std::nullopt;
        auto it = result_->find(sku);
        if (it == result_->end()) return std::nullopt;
        return it->second;
    }

    // Memoised order-api reads, shared by the two passes.
    template <class F>
    std::vector<Order> list_cached(int limit, F&& read) {
        std::lock_guard lock(mu_);
        auto it = lists_.find(limit);
        if (it == lists_.end()) it = lists_.emplace(limit, read()).first;
        return it->second;
    }
    template <class F>
    std::optional<Order> find_cached(const std::string& id, F&& read) {
        std::lock_guard lock(mu_);
        auto it = finds_.find(id);
        if (it == finds_.end()) it = finds_.emplace(id, read()).first;
        return it->second;
    }

private:
    StockBatchFn fetch_;
    std::mutex mu_;
    std::set<std::string> skus_;
    bool requested_ = false;
    bool serving_ = false;
    std::optional<std::unordered_map<std::string, int>> result_;
    std::map<int, std::vector<Order>> lists_;
    std::map<std::string, std::optional<Order>> finds_;
};

}  // namespace cndp
