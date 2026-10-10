// Unit tests for the gateway's GraphQL layer: field selection, request-scoped stock
// batching, and the "no stock selected, no inventory call" rule. No network involved.

#include <cstdlib>
#include <iostream>

#include "graphql_api.hpp"

namespace {

class FakeSource : public cndp::OrderSource {
public:
    std::vector<cndp::Order> list(int limit) override {
        last_limit = limit;
        return orders;
    }
    std::optional<cndp::Order> find(const std::string& id) override {
        for (const auto& o : orders)
            if (o.id == id) return o;
        return std::nullopt;
    }
    std::vector<cndp::Order> orders{{"o1", "widget-a", 1, "confirmed"},
                                    {"o2", "widget-b", 2, "confirmed"},
                                    {"o3", "widget-a", 4, "rejected"}};
    int last_limit = 0;
};

int failures = 0;

void check(bool ok, const char* what) {
    if (!ok) {
        std::cerr << "FAIL: " << what << std::endl;
        ++failures;
    }
}

}  // namespace

int main() {
    auto source = std::make_shared<FakeSource>();
    int batch_calls = 0;
    std::set<std::string> last_batch;
    bool inventory_down = false;
    cndp::StockBatchFn fetch = [&](const std::set<std::string>& skus)
        -> std::optional<std::unordered_map<std::string, int>> {
        ++batch_calls;
        last_batch = skus;
        if (inventory_down) return std::nullopt;
        return std::unordered_map<std::string, int>{{"widget-a", 42}, {"widget-b", 7}};
    };
    cndp::gql::GraphQLApi api(source, fetch);

    // No stock selected: no inventory call, and no stock key in the response.
    auto r = api.execute("{ orders { id sku status } }");
    check(batch_calls == 0, "stock not selected -> no batch call");
    check(r["data"]["orders"].size() == 3, "three orders");
    check(!r["data"]["orders"][0].isMember("stock"), "no stock key");
    check(source->last_limit == 50, "default limit 50");

    // Stock selected on 3 orders over 2 SKUs: exactly one batch call with both SKUs.
    r = api.execute("{ orders { id sku stock } }");
    check(batch_calls == 1, "stock selected -> exactly one batch call");
    check(last_batch == std::set<std::string>({"widget-a", "widget-b"}), "batch holds the unique SKUs");
    check(r["data"]["orders"][0]["stock"] == 42, "widget-a stock is 42");
    check(r["data"]["orders"][1]["stock"] == 7, "widget-b stock is 7");
    check(r["data"]["orders"][2]["stock"] == 42, "third order reuses the batch");

    // Each request gets its own loader.
    api.execute("{ orders { stock } }");
    check(batch_calls == 2, "a new request batches again");

    // Single order: a batch of one.
    r = api.execute(R"({ order(id: "o2") { id sku stock } })");
    check(batch_calls == 3 && last_batch.size() == 1, "single order batches one SKU");
    check(r["data"]["order"]["stock"] == 7, "single order stock");
    r = api.execute(R"({ order(id: "zzz") { id } })");
    check(r["data"]["order"].isNull(), "missing order is null");

    // Inventory failure: stock is null, the rest of the order still resolves.
    inventory_down = true;
    r = api.execute("{ orders { id stock } }");
    check(r["data"]["orders"][0]["stock"].isNull() && r["data"]["orders"][0]["id"] == "o1", "lookup failure -> null stock");

    if (failures == 0) std::cout << "graphql_test: all checks passed" << std::endl;
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
