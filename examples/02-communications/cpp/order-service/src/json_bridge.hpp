// json_bridge.hpp — converts between jsoncpp (what Drogon speaks) and cppgraphqlgen's
// response::Value, so the GraphQL runtime needs no second JSON library (no RapidJSON).

#pragma once

#include <string>
#include <utility>

#include <graphqlservice/GraphQLResponse.h>
#include <json/json.h>

namespace cndp::gql {

namespace response = graphql::response;

// response::Value -> Json::Value. Enum values and IDs would be strings in JSON; the
// schemas in this example only use String, Int, Float, Boolean, lists and objects.
inline Json::Value to_json(const response::Value& v) {
    switch (v.type()) {
        case response::Type::Map: {
            Json::Value obj(Json::objectValue);
            for (const auto& [name, member] : v.get<response::MapType>()) obj[name] = to_json(member);
            return obj;
        }
        case response::Type::List: {
            Json::Value arr(Json::arrayValue);
            for (const auto& item : v.get<response::ListType>()) arr.append(to_json(item));
            return arr;
        }
        case response::Type::String:
        case response::Type::EnumValue:
            return Json::Value(v.get<response::StringType>());
        case response::Type::Boolean:
            return Json::Value(v.get<response::BooleanType>());
        case response::Type::Int:
            return Json::Value(v.get<response::IntType>());
        case response::Type::Float:
            return Json::Value(v.get<response::FloatType>());
        case response::Type::Scalar:
            return to_json(v.get<response::ScalarType>());
        case response::Type::ID:
        case response::Type::Null:
            break;
    }
    return Json::Value(Json::nullValue);
}

// Json::Value -> response::Value, for the request's "variables" object.
inline response::Value from_json(const Json::Value& j) {
    switch (j.type()) {
        case Json::objectValue: {
            response::Value map(response::Type::Map);
            for (const auto& name : j.getMemberNames()) map.emplace_back(std::string(name), from_json(j[name]));
            return map;
        }
        case Json::arrayValue: {
            response::Value list(response::Type::List);
            for (const auto& item : j) list.emplace_back(from_json(item));
            return list;
        }
        case Json::stringValue:
            return std::move(response::Value(j.asString()).from_json());
        case Json::booleanValue:
            return response::Value(j.asBool());
        case Json::intValue:
        case Json::uintValue:
            return response::Value(j.asInt());
        case Json::realValue:
            return response::Value(j.asDouble());
        case Json::nullValue:
            break;
    }
    return response::Value(response::Type::Null);
}

}  // namespace cndp::gql
