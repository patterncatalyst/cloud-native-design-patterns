#include <drogon/drogon.h>
#include <grpcpp/grpcpp.h>
#include <grpcpp/impl/codegen/client_unary_call.h>
#include <grpcpp/impl/codegen/rpc_method.h>
#include <grpcpp/impl/codegen/proto_utils.h>
#include <google/protobuf/struct.pb.h>
#include "schema.pb.h"
#include <chrono>
#include <memory>
#include <string>

using namespace drogon;

// Hand-rolled gRPC stub — flagd's proto service is named "Service" which
// causes a C++ codegen collision (Service::Service inherits grpc::Service).
// We call the correct wire method directly via BlockingUnaryCall.
class FlagdClient {
public:
    FlagdClient(const std::string& host, int port)
        : channel_(grpc::CreateChannel(
              host + ":" + std::to_string(port),
              grpc::InsecureChannelCredentials())),
          method_("/flagd.evaluation.v1.Service/ResolveBoolean",
                  grpc::internal::RpcMethod::NORMAL_RPC,
                  channel_) {}

    bool evaluateBoolean(const std::string& flagKey, bool defaultValue,
                        const std::string& targetingKey,
                        const std::string& plan = "") {
        flagd::evaluation::v1::ResolveBooleanRequest request;
        request.set_flag_key(flagKey);

        auto* context = request.mutable_context();
        auto* fields = context->mutable_fields();

        google::protobuf::Value targetingKeyValue;
        targetingKeyValue.set_string_value(targetingKey);
        (*fields)["targetingKey"] = targetingKeyValue;

        if (!plan.empty()) {
            google::protobuf::Value planValue;
            planValue.set_string_value(plan);
            (*fields)["plan"] = planValue;
        }

        flagd::evaluation::v1::ResolveBooleanResponse response;
        grpc::ClientContext ctx;
        ctx.set_deadline(std::chrono::system_clock::now() + std::chrono::milliseconds(800));

        grpc::Status status = grpc::internal::BlockingUnaryCall(
            channel_.get(), method_, &ctx, request, &response);

        if (status.ok()) {
            return response.value();
        } else {
            LOG_WARN << "flagd call failed: " << status.error_message()
                     << ", using default: " << defaultValue;
            return defaultValue;
        }
    }

private:
    std::shared_ptr<grpc::Channel> channel_;
    grpc::internal::RpcMethod method_;
};

int main() {
    std::string flagdHost = std::getenv("FLAGD_HOST") ? std::getenv("FLAGD_HOST") : "flagd";
    int flagdPort = std::getenv("FLAGD_PORT") ? std::stoi(std::getenv("FLAGD_PORT")) : 8013;

    auto flagdClient = std::make_shared<FlagdClient>(flagdHost, flagdPort);

    app().setLogLevel(trantor::Logger::kInfo);
    app().setUploadPath("/tmp");

    app().registerHandler("/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value response;
            response["status"] = "ok";
            auto resp = HttpResponse::newHttpJsonResponse(response);
            callback(resp);
        },
        {Get});

    app().registerHandler("/checkout",
        [flagdClient](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            std::string user = req->getHeader("X-User");
            if (user.empty()) user = "anonymous";

            std::string plan = req->getHeader("X-Plan");
            if (plan.empty()) plan = "free";

            bool useNew = flagdClient->evaluateBoolean("new-checkout", false, user, plan);

            Json::Value response;
            response["path"] = useNew ? "new" : "legacy";
            response["user"] = user;
            response["plan"] = plan;

            auto resp = HttpResponse::newHttpJsonResponse(response);
            callback(resp);
        },
        {Post});

    app().registerHandler("/recommendations",
        [flagdClient](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            std::string user = req->getHeader("X-User");
            if (user.empty()) user = "anonymous";

            bool enabled = flagdClient->evaluateBoolean("recommendations-enabled", true, user);

            Json::Value response;
            if (enabled) {
                Json::Value recommendations(Json::arrayValue);
                recommendations.append("product-a");
                recommendations.append("product-b");
                recommendations.append("product-c");
                response["recommendations"] = recommendations;
                response["reason"] = "live";
            } else {
                response["recommendations"] = Json::Value(Json::arrayValue);
                response["reason"] = "killed";
            }

            auto resp = HttpResponse::newHttpJsonResponse(response);
            callback(resp);
        },
        {Get});

    app().registerHandler("/ui-config",
        [flagdClient](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            std::string user = req->getHeader("X-User");
            if (user.empty()) user = "anonymous";

            bool darkMode = flagdClient->evaluateBoolean("dark-mode", false, user);

            Json::Value response;
            response["dark_mode"] = darkMode;
            response["user"] = user;

            auto resp = HttpResponse::newHttpJsonResponse(response);
            callback(resp);
        },
        {Get});

    app().registerHandler("/flags",
        [flagdClient](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            std::string user = req->getHeader("X-User");
            if (user.empty()) user = "anonymous";

            std::string plan = req->getHeader("X-Plan");
            if (plan.empty()) plan = "free";

            Json::Value response;
            response["new-checkout"] = flagdClient->evaluateBoolean("new-checkout", false, user, plan);
            response["dark-mode"] = flagdClient->evaluateBoolean("dark-mode", false, user);
            response["recommendations-enabled"] = flagdClient->evaluateBoolean("recommendations-enabled", true, user);
            response["user"] = user;
            response["plan"] = plan;

            auto resp = HttpResponse::newHttpJsonResponse(response);
            callback(resp);
        },
        {Get});

    LOG_INFO << "Starting flag service on 0.0.0.0:8080";
    LOG_INFO << "Connecting to flagd at " << flagdHost << ":" << flagdPort;

    app().addListener("0.0.0.0", 8080).run();
}
