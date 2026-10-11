// graphql_api.hpp — the GraphQL query layer, built on cppgraphqlgen.
//
// schemagen turned src/graphql/schema.graphql into src/graphql/*Object.{h,cpp}; this file
// supplies the resolvers (OrderModel, QueryModel) and runs a request: parse, validate,
// resolve, and hand the result back as jsoncpp. A field is only read when the query
// selects it, because every field is its own resolver.

#pragma once

#include <memory>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include <graphqlservice/GraphQLParse.h>
#include <graphqlservice/GraphQLService.h>
#include <json/json.h>

#include "OrderObject.h"
#include "OrdersSchema.h"
#include "QueryObject.h"
#include "json_bridge.hpp"
#include "orders.hpp"

namespace cndp::gql {

namespace orders = graphql::orders;
namespace service = graphql::service;

// Resolvers for the Order type: one accessor per schema field.
class OrderModel {
public:
    explicit OrderModel(Order order) : order_(std::move(order)) {}
    std::string getId() const { return order_.id; }
    std::string getSku() const { return order_.sku; }
    int getQuantity() const { return order_.quantity; }
    std::string getStatus() const { return order_.status; }

private:
    Order order_;
};

inline std::shared_ptr<orders::object::Order> wrap(Order order) {
    return std::make_shared<orders::object::Order>(std::make_shared<OrderModel>(std::move(order)));
}

// Resolvers for the Query type, backed by the repository port.
class QueryModel {
public:
    explicit QueryModel(std::shared_ptr<OrderRepo> repo) : repo_(std::move(repo)) {}

    std::vector<std::shared_ptr<orders::object::Order>> getOrders(std::optional<int>&& limit) const {
        int n = limit.value_or(10);
        if (n < 1) n = 1;
        if (n > 100) n = 100;
        std::vector<std::shared_ptr<orders::object::Order>> out;
        for (auto& o : repo_->list(n, "")) out.push_back(wrap(std::move(o)));
        return out;
    }

    std::shared_ptr<orders::object::Order> getOrder(std::string&& id) const {
        auto found = repo_->find(id);
        return found ? wrap(std::move(*found)) : nullptr;
    }

private:
    std::shared_ptr<OrderRepo> repo_;
};

class GraphQLApi {
public:
    explicit GraphQLApi(std::shared_ptr<OrderRepo> repo)
        : service_(std::make_shared<orders::Operations>(std::make_shared<QueryModel>(std::move(repo)))) {}

    // Runs one request body ({"query": ..., "operationName": ..., "variables": {...}}) and
    // returns the GraphQL response document. Syntax, validation and resolver errors come
    // back in "errors", as the GraphQL spec requires; this never throws.
    Json::Value execute(const std::string& query, const std::string& operation_name = {},
                        const Json::Value& variables = Json::Value(Json::objectValue)) const {
        try {
            auto ast = graphql::peg::parseString(query);
            if (!ast.root) return error("empty query");
            auto vars = variables.isObject() ? from_json(variables) : graphql::response::Value(graphql::response::Type::Map);
            auto result = service_->resolve({ast, operation_name, std::move(vars)}).get();
            return to_json(result);
        } catch (service::schema_exception& ex) {
            return to_json(wrap_errors(ex.getErrors()));
        } catch (const std::exception& ex) {
            return error(ex.what());
        }
    }

private:
    static graphql::response::Value wrap_errors(graphql::response::Value&& errors) {
        graphql::response::Value doc(graphql::response::Type::Map);
        doc.emplace_back("errors", std::move(errors));
        return doc;
    }

    static Json::Value error(const std::string& message) {
        Json::Value doc;
        doc["errors"][0]["message"] = message;
        return doc;
    }

    std::shared_ptr<orders::Operations> service_;
};

}  // namespace cndp::gql
