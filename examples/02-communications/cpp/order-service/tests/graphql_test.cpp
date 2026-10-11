// Unit tests for the GraphQL layer against an in-memory repository (no database, no network).

#include <cstdlib>
#include <iostream>
#include <map>

#include "graphql_api.hpp"

namespace {

class FakeRepo : public cndp::OrderRepo {
public:
    std::vector<cndp::Order> list(int limit, const std::string&) override {
        last_limit = limit;
        std::vector<cndp::Order> out;
        for (const auto& [id, o] : orders) {
            if (static_cast<int>(out.size()) == limit) break;
            out.push_back(o);
        }
        return out;
    }
    std::optional<cndp::Order> find(const std::string& id) override {
        auto it = orders.find(id);
        if (it == orders.end()) return std::nullopt;
        return it->second;
    }
    void insert(const cndp::Order& o) override { orders[o.id] = o; }

    std::map<std::string, cndp::Order> orders;
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
    auto repo = std::make_shared<FakeRepo>();
    repo->insert({"a1", "widget", 3, "confirmed"});
    repo->insert({"a2", "gadget", 5, "rejected"});
    cndp::gql::GraphQLApi api(repo);

    // Only the selected fields come back.
    auto r = api.execute("{ orders(limit: 5) { id sku status } }");
    check(r["data"]["orders"].size() == 2, "two orders");
    check(r["data"]["orders"][0]["sku"] == "widget", "sku selected");
    check(!r["data"]["orders"][0].isMember("quantity"), "quantity not selected");
    check(repo->last_limit == 5, "limit argument reaches the repository");

    // The schema default (limit = 10) applies when the argument is omitted.
    api.execute("{ orders { id } }");
    check(repo->last_limit == 10, "default limit is 10");

    // Single order by id, and null for a missing one.
    r = api.execute(R"({ order(id: "a2") { id quantity status } })");
    check(r["data"]["order"]["quantity"] == 5, "order by id");
    r = api.execute(R"({ order(id: "nope") { id } })");
    check(r["data"]["order"].isNull(), "missing order is null");

    // Variables go through the JSON bridge.
    Json::Value vars;
    vars["id"] = "a1";
    r = api.execute("query ($id: String!) { order(id: $id) { sku } }", "", vars);
    check(r["data"]["order"]["sku"] == "widget", "variables");

    // A field that is not in the schema is a validation error, not a crash.
    r = api.execute("{ orders { stock } }");
    check(r.isMember("errors"), "unknown field reports errors");
    r = api.execute("{ orders { ");
    check(r.isMember("errors"), "syntax error reports errors");

    // Bridge round trip.
    Json::Value j;
    j["a"] = 1;
    j["b"][0] = "x";
    j["c"] = true;
    j["d"] = 1.5;
    check(cndp::gql::to_json(cndp::gql::from_json(j)) == j, "json bridge round trip");

    if (failures == 0) std::cout << "graphql_test: all checks passed" << std::endl;
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
