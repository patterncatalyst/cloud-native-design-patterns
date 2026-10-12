#include <drogon/drogon.h>
#include <sw/redis++/redis++.h>
#include <librdkafka/rdkafkacpp.h>
#include <cstdio>
#include <functional>
#include <mutex>
#include <vector>
#include <atomic>
#include <chrono>
#include <memory>
#include <sstream>
#include <thread>

using namespace drogon;

static std::string g_legacy_url;
static std::unique_ptr<sw::redis::Redis> g_redis;
static std::unique_ptr<RdKafka::Producer> g_producer;
static std::atomic<bool> g_producer_running{false};
static std::thread g_poller;

// Carried as the message opaque. `done` is the request's continuation: the legacy response
// is returned only after the delivery report, as the other languages' decorators do.
struct Pending {
    std::string order_id;
    std::function<void()> done;
};

// The delivery report confirms the broker's ack; only then is the EVENT line logged.
// message.timeout.ms guarantees a report (success, timeout or purge) for every message.
class DeliveryLog : public RdKafka::DeliveryReportCb {
public:
    void dr_cb(RdKafka::Message& message) override {
        std::unique_ptr<Pending> pending(static_cast<Pending*>(message.msg_opaque()));
        if (message.err() != RdKafka::ERR_NO_ERROR) {
            LOG_ERROR << "kafka send failed: " << message.errstr();
        } else if (pending) {
            LOG_INFO << "EVENT order.placed order_id=" << pending->order_id;
        }
        if (pending && pending->done) pending->done();
    }
};
static DeliveryLog g_dr_cb;
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

// Queues the event; `done` runs once the broker acked it, or the delivery failed or timed out.
// If nothing could be queued, `done` runs immediately.
static void publish_event(const std::string& order_id, const std::string& order_json,
                          std::function<void()> done) {
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
        auto* opaque = new Pending{order_id, done};  // owned by the delivery report callback
        RdKafka::ErrorCode err = g_producer->produce(
            "order.placed", RdKafka::Topic::PARTITION_UA, RdKafka::Producer::RK_MSG_COPY,
            msg.data(), msg.size(), nullptr, 0, 0, opaque);
        if (err == RdKafka::ERR_NO_ERROR) return;
        delete opaque;
        LOG_ERROR << "kafka send failed: " << RdKafka::err2str(err);
    } catch (const std::exception& e) {
        LOG_ERROR << "kafka send failed: " << e.what();
    }
    if (done) done();
}

int main() {
    // docker logs reads a pipe: line-buffer stdout so LOG_* lines show up as they are written.
    std::setvbuf(stdout, nullptr, _IOLBF, 0);
    auto env_legacy = std::getenv("LEGACY_URL");
    g_legacy_url = env_legacy ? env_legacy : "http://legacy:8080";

    auto env_redis = std::getenv("REDIS_URL");
    std::string redis_url = env_redis ? env_redis : "redis://redis:6379";
    g_redis = std::make_unique<sw::redis::Redis>(redis_url);

    auto env_kafka = std::getenv("KAFKA_BOOTSTRAP");
    std::string kafka_bs = env_kafka ? env_kafka : "kafka:9094";
    std::string errstr;
    std::unique_ptr<RdKafka::Conf> conf(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));
    if (conf->set("bootstrap.servers", kafka_bs, errstr) != RdKafka::Conf::CONF_OK ||
        conf->set("client.id", "decorator", errstr) != RdKafka::Conf::CONF_OK ||
        conf->set("acks", "all", errstr) != RdKafka::Conf::CONF_OK ||
        conf->set("message.timeout.ms", "10000", errstr) != RdKafka::Conf::CONF_OK ||
        conf->set("dr_cb", &g_dr_cb, errstr) != RdKafka::Conf::CONF_OK) {
        LOG_ERROR << "kafka config: " << errstr;
        return 1;
    }
    g_producer.reset(RdKafka::Producer::create(conf.get(), errstr));
    if (!g_producer) {
        LOG_ERROR << "kafka producer: " << errstr;
        return 1;
    }
    g_producer_running = true;
    g_poller = std::thread([] {
        while (g_producer_running) g_producer->poll(100);
    });

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
                        // The legacy order already exists, so its response goes back either
                        // way, but only after the event's delivery report.
                        publish_event(oid, resp_body, [cb, resp] { cb(resp); });
                        return;
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
                    LOG_INFO << "CACHE_HIT order_id=" << order_id;
                    auto r = HttpResponse::newHttpResponse();
                    r->setStatusCode(k200OK);
                    r->setContentTypeCode(CT_APPLICATION_JSON);
                    r->setBody(*cached);
                    cb(r);
                    return;
                }
            } catch (...) {}

            LOG_INFO << "CACHE_MISS order_id=" << order_id;

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

    if (g_producer->flush(10000) != RdKafka::ERR_NO_ERROR) {
        // Still queued after the grace period: purge so every report fires and frees its opaque.
        g_producer->purge(RdKafka::Producer::PURGE_QUEUE | RdKafka::Producer::PURGE_INFLIGHT);
        g_producer->flush(2000);
    }
    g_producer_running = false;
    g_poller.join();
    g_producer.reset();
    return 0;
}
