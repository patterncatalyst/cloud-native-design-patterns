// graphql_api.hpp — the gateway's GraphQL layer, built on cppgraphqlgen.
//
// schemagen turned src/graphql/schema.graphql into src/graphql/*Object.{h,cpp}; this file
// supplies the resolvers. Orders come from order-api; Order.stock is its own resolver, so the
// inventory service is only called when a query selects `stock`, and then once per request
// for all SKUs (StockState).

#pragma once

#include <memory>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include <graphqlservice/GraphQLParse.h>
#include <graphqlservice/GraphQLService.h>
#include <json/json.h>

#include "GatewaySchema.h"
#include "OrderObject.h"
#include "QueryObject.h"
#include "json_bridge.hpp"
#include "orders.hpp"
#include "stock_loader.hpp"

namespace cndp::gql {

namespace gateway = graphql::gateway;
namespace service = graphql::service;

class OrderModel {
public:
    OrderModel(Order order, std::shared_ptr<StockState> stock) : order_(std::move(order)), stock_(std::move(stock)) {}
    std::string getId() const { return order_.id; }
    std::string getSku() const { return order_.sku; }
    int getQuantity() const { return order_.quantity; }
    std::string getStatus() const { return order_.status; }
    std::optional<int> getStock() const { return stock_->stock(order_.sku); }

private:
    Order order_;
    std::shared_ptr<StockState> stock_;
};

class QueryModel {
public:
    explicit QueryModel(std::shared_ptr<OrderSource> source) : source_(std::move(source)) {}

    std::vector<std::shared_ptr<gateway::object::Order>> getOrders(service::FieldParams&& params,
                                                                    std::optional<int>&& limit) const {
        auto stock = state_of(params);
        std::vector<std::shared_ptr<gateway::object::Order>> out;
        for (auto& o : source_->list(limit.value_or(50))) out.push_back(wrap(std::move(o), stock));
        return out;
    }

    std::shared_ptr<gateway::object::Order> getOrder(service::FieldParams&& params, std::string&& id) const {
        auto found = source_->find(id);
        return found ? wrap(std::move(*found), state_of(params)) : nullptr;
    }

private:
    static std::shared_ptr<StockState> state_of(const service::FieldParams& params) {
        return std::static_pointer_cast<StockState>(params.state);
    }

    static std::shared_ptr<gateway::object::Order> wrap(Order order, const std::shared_ptr<StockState>& stock) {
        stock->register_sku(order.sku);
        return std::make_shared<gateway::object::Order>(std::make_shared<OrderModel>(std::move(order), stock));
    }

    std::shared_ptr<OrderSource> source_;
};

class GraphQLApi {
public:
    GraphQLApi(std::shared_ptr<OrderSource> source, StockBatchFn stock_fetch)
        : service_(std::make_shared<gateway::Operations>(std::make_shared<QueryModel>(std::move(source)))),
          stock_fetch_(std::move(stock_fetch)) {}

    // Runs one request ({"query", "operationName", "variables"}) and returns the response
    // document. Errors (syntax, validation, resolvers) come back in "errors"; never throws.
    Json::Value execute(const std::string& query, const std::string& operation_name = {},
                        const Json::Value& variables = Json::Value(Json::objectValue)) const {
        try {
            auto ast = graphql::peg::parseString(query);
            if (!ast.root) return error("empty query");
            auto vars = variables.isObject() ? from_json(variables) : graphql::response::Value(graphql::response::Type::Map);
            // A fresh StockState per request is the DataLoader scope.
            auto state = std::make_shared<StockState>(stock_fetch_);
            auto result = service_->resolve({ast, operation_name, std::move(vars), {}, state}).get();
            return to_json(result);
        } catch (service::schema_exception& ex) {
            graphql::response::Value doc(graphql::response::Type::Map);
            doc.emplace_back("errors", ex.getErrors());
            return to_json(doc);
        } catch (const std::exception& ex) {
            return error(ex.what());
        }
    }

private:
    static Json::Value error(const std::string& message) {
        Json::Value doc;
        doc["errors"][0]["message"] = message;
        return doc;
    }

    std::shared_ptr<gateway::Operations> service_;
    StockBatchFn stock_fetch_;
};

}  // namespace cndp::gql
