#include <drogon/drogon.h>
#include <sw/redis++/redis++.h>
#include <kafka/KafkaProducer.h>
#include <mutex>
#include <vector>
#include <iostream>
#include <chrono>

using namespace drogon;

static std::string g_legacy_url;
static std::unique_ptr<sw::redis::Redis> g_redis;
static std::unique_ptr<kafka::clients::producer::KafkaProducer> g_producer;
static std::mutex g_events_mu;
static std::vector<Json::Value> g_events;

static void forward_post(const std::string& body,
                         std::function<void(const HttpResponsePtr&)> cb) {
    auto client = HttpClient::newHttpClient(g_legacy_url);
    auto req = HttpRequest::newHttpRequest();
    req->setMethod(Post);
    req->setPath("/orders");
    req->setContentTypeCode(CT_APPLICATION_JSON);
    req->setBody(body);
    client->sendRequest(req,
        [cb = std::move(cb)](ReqResult result, const HttpResponsePtr& resp) {
            if (result == ReqResult::Ok) {
                auto r = HttpResponse::newHttpResponse();
                r->setStatusCode(resp->statusCode());
                r->setContentTypeCode(CT_APPLICATION_JSON);
                r->setBody(std::string(resp->body()));
                cb(r);
            } else {
                auto r = HttpResponse::newHttpResponse();
                r->setStatusCode(k502BadGateway);
                cb(r);
            }
        });
}

static void forward_get(const std::string& order_id,
                        std::function<void(std::string)> on_result) {
    auto client = HttpClient::newHttpClient(g_legacy_url);
    auto req = HttpRequest::newHttpRequest();
    req->setMethod(Get);
    req->setPath("/orders/" + order_id);
    client->sendRequest(req,
        [on_result = std::move(on_result)](ReqResult result, const HttpResponsePtr& resp) {
            if (result == ReqResult::Ok) {
                on_result(std::string(resp->body()));
            } else {
                on_result("");
            }
        });
}

static void publish_event(const std::string& order_id, const std::string& order_json) {
    Json::Value evt;
    evt["type"] = "order.placed";
    evt["order_id"] = order_id;
    {
        std::lock_guard<std::mutex> lock(g_events_mu);
        g_events.push_back(evt);
    }

    try {
        Json::Value envelope;
        envelope["type"] = "order.placed";
        envelope["order_id"] = order_id;
        envelope["data"] = order_json;
        Json::StreamWriterBuilder wb;
        wb["indentation"] = "";
        std::string msg = Json::writeString(wb, envelope);
        kafka::clients::producer::ProducerRecord record(
            kafka::Topic("order.placed"),
            kafka::NullKey,
            kafka::Value(msg.data(), msg.size()));
        g_producer->syncSend(record);
        std::cerr << "EVENT order.placed order_id=" << order_id << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "kafka send failed: " << e.what() << std::endl;
    }
}

int main() {
    auto env_legacy = std::getenv("LEGACY_URL");
    g_legacy_url = env_legacy ? env_legacy : "http://legacy:8080";

    auto env_redis = std::getenv("REDIS_URL");
    std::string redis_url = env_redis ? env_redis : "redis://redis:6379";
    g_redis = std::make_unique<sw::redis::Redis>(redis_url);

    auto env_kafka = std::getenv("KAFKA_BOOTSTRAP");
    std::string kafka_bs = env_kafka ? env_kafka : "kafka:9094";
    kafka::Properties props;
    props.put("bootstrap.servers", kafka_bs);
    props.put("acks", "all");
    g_producer = std::make_unique<kafka::clients::producer::KafkaProducer>(props);

    app().setLogLevel(trantor::Logger::kInfo);
    app().addListener("0.0.0.0", 8080);

    app().registerHandler("/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& cb) {
            Json::Value r;
            r["status"] = "ok";
            cb(HttpResponse::newHttpJsonResponse(r));
        },
        {Get});

    app().registerHandler("/orders",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& cb) {
            std::string body_str(req->body());

            forward_post(body_str,
                [cb = std::move(cb)](const HttpResponsePtr& resp) {
                    std::string resp_body(resp->body());
                    Json::CharReaderBuilder rbuilder;
                    Json::Value parsed;
                    std::istringstream ss(resp_body);
                    if (Json::parseFromStream(rbuilder, ss, &parsed, nullptr) &&
                        parsed.isMember("id")) {
                        std::string oid = parsed["id"].asString();
                        publish_event(oid, resp_body);
                    }
                    cb(resp);
                });
        },
        {Post});

    app().registerHandler("/orders/{order_id}",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& cb,
           const std::string& order_id) {
            std::string cache_key = "order:" + order_id;
            try {
                auto cached = g_redis->get(cache_key);
                if (cached) {
                    std::cerr << "CACHE_HIT order_id=" << order_id << std::endl;
                    auto r = HttpResponse::newHttpResponse();
                    r->setStatusCode(k200OK);
                    r->setContentTypeCode(CT_APPLICATION_JSON);
                    r->setBody(*cached);
                    cb(r);
                    return;
                }
            } catch (...) {}

            std::cerr << "CACHE_MISS order_id=" << order_id << std::endl;

            forward_get(order_id,
                [order_id, cb = std::move(cb)](std::string result) {
                    if (result.empty()) {
                        auto r = HttpResponse::newHttpResponse();
                        r->setStatusCode(k502BadGateway);
                        cb(r);
                        return;
                    }
                    try {
                        g_redis->setex("order:" + order_id, 60, result);
                    } catch (...) {}
                    auto r = HttpResponse::newHttpResponse();
                    r->setStatusCode(k200OK);
                    r->setContentTypeCode(CT_APPLICATION_JSON);
                    r->setBody(result);
                    cb(r);
                });
        },
        {Get});

    app().registerHandler("/events",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& cb) {
            std::lock_guard<std::mutex> lock(g_events_mu);
            Json::Value arr(Json::arrayValue);
            for (auto& e : g_events) arr.append(e);
            cb(HttpResponse::newHttpJsonResponse(arr));
        },
        {Get});

    app().run();
    return 0;
}
