// stock_loader.hpp — request-scoped batching of stock lookups (the "DataLoader").
//
// The query resolvers register every SKU they return; the first Order.stock resolver that
// runs triggers ONE batch call for all of them, and the rest read the cached result. A query
// that never selects `stock` never reaches the loader, so no inventory call is made.

#pragma once

#include <functional>
#include <mutex>
#include <optional>
#include <set>
#include <string>
#include <unordered_map>

#include <graphqlservice/GraphQLService.h>

namespace cndp {

// SKU -> available units for the whole set, or nullopt when the lookup failed.
using StockBatchFn =
    std::function<std::optional<std::unordered_map<std::string, int>>(const std::set<std::string>&)>;

class StockState : public graphql::service::RequestState {
public:
    explicit StockState(StockBatchFn fetch) : fetch_(std::move(fetch)) {}

    void register_sku(const std::string& sku) {
        std::lock_guard lock(mu_);
        skus_.insert(sku);
    }

    // nullopt = the inventory lookup failed; unknown SKUs report 0 units.
    std::optional<int> stock(const std::string& sku) {
        std::call_once(loaded_, [this] {
            std::set<std::string> skus;
            {
                std::lock_guard lock(mu_);
                skus = skus_;
            }
            result_ = fetch_(skus);
        });
        if (!result_) return std::nullopt;
        auto it = result_->find(sku);
        return it == result_->end() ? 0 : it->second;
    }

private:
    StockBatchFn fetch_;
    std::mutex mu_;
    std::set<std::string> skus_;
    std::once_flag loaded_;
    std::optional<std::unordered_map<std::string, int>> result_;
};

}  // namespace cndp
