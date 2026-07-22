#include <drogon/drogon.h>
#include <drogon/WebSocketController.h>
#include <sw/redis++/redis++.h>
#include <mutex>
#include <unordered_map>
#include <deque>
#include <thread>
#include <atomic>
#include <csignal>
#include <iostream>

using namespace drogon;

static std::string g_pod_name;
static std::string g_redis_url;
static std::unique_ptr<sw::redis::Redis> g_redis;
static std::atomic<bool> g_shutdown{false};

void signal_handler(int) { g_shutdown = true; }

struct ClientState {
    WebSocketConnectionPtr conn;
    int64_t seq = 0;
    std::deque<Json::Value> buffer;
    static constexpr size_t MAX_BUFFER = 100;
};

static std::mutex g_clients_mu;
static std::unordered_map<std::string, ClientState> g_clients;

static void send_frame(const std::string& client_id, const std::string& data) {
    std::lock_guard<std::mutex> lock(g_clients_mu);
    auto it = g_clients.find(client_id);
    if (it == g_clients.end()) return;

    auto& cs = it->second;
    cs.seq++;
    Json::Value frame;
    frame["seq"] = static_cast<Json::Int64>(cs.seq);
    frame["data"] = data;

    cs.buffer.push_back(frame);
    if (cs.buffer.size() > ClientState::MAX_BUFFER)
        cs.buffer.pop_front();

    Json::FastWriter writer;
    writer.omitEndingLineFeed();
    cs.conn->send(writer.write(frame));
}

static void broadcast_local(const std::string& data) {
    std::lock_guard<std::mutex> lock(g_clients_mu);
    for (auto& [cid, cs] : g_clients) {
        cs.seq++;
        Json::Value frame;
        frame["seq"] = static_cast<Json::Int64>(cs.seq);
        frame["data"] = data;

        cs.buffer.push_back(frame);
        if (cs.buffer.size() > ClientState::MAX_BUFFER)
            cs.buffer.pop_front();

        Json::FastWriter writer;
        writer.omitEndingLineFeed();
        cs.conn->send(writer.write(frame));
    }
}

static void redis_subscriber_loop() {
    try {
        auto sub = sw::redis::Subscriber(g_redis->subscriber());
        sub.subscribe("ws:broadcast");
        sub.on_message([](const std::string&, const std::string& msg) {
            Json::CharReaderBuilder builder;
            Json::Value payload;
            std::istringstream stream(msg);
            if (!Json::parseFromStream(builder, stream, &payload, nullptr)) return;

            std::string sender_pod = payload.get("pod", "").asString();
            if (sender_pod == g_pod_name) return;

            std::string target = payload.get("target", "").asString();
            std::string data = payload.get("data", "").asString();

            if (!target.empty()) {
                send_frame(target, data);
            } else {
                broadcast_local(data);
            }
        });

        while (!g_shutdown) {
            try {
                sub.consume();
            } catch (const sw::redis::TimeoutError&) {
                continue;
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Redis subscriber error: " << e.what() << std::endl;
    }
}

class WsCtrl : public WebSocketController<WsCtrl> {
public:
    void handleNewMessage(const WebSocketConnectionPtr& conn,
                          std::string&& message,
                          const WebSocketMessageType& type) override {
        if (type != WebSocketMessageType::Text) return;

        Json::CharReaderBuilder builder;
        Json::Value msg;
        std::istringstream stream(message);
        if (!Json::parseFromStream(builder, stream, &msg, nullptr)) return;

        if (msg.get("type", "").asString() == "ping") {
            Json::Value pong;
            pong["type"] = "pong";
            pong["pod"] = g_pod_name;
            Json::FastWriter writer;
            writer.omitEndingLineFeed();
            conn->send(writer.write(pong));
        }
    }

    void handleNewConnection(const HttpRequestPtr& req,
                             const WebSocketConnectionPtr& conn) override {
        std::string client_id = req->getHeader("X-Client-Id");
        if (client_id.empty()) client_id = "unknown";

        conn->setContext(std::make_shared<std::string>(client_id));

        {
            std::lock_guard<std::mutex> lock(g_clients_mu);
            g_clients[client_id] = {conn, 0, {}};
        }

        std::cerr << "client connected id=" << client_id << " pod=" << g_pod_name << std::endl;
    }

    void handleConnectionClosed(const WebSocketConnectionPtr& conn) override {
        auto ctx = conn->getContext<std::string>();
        if (!ctx) return;

        std::lock_guard<std::mutex> lock(g_clients_mu);
        g_clients.erase(*ctx);
        std::cerr << "client disconnected id=" << *ctx << " pod=" << g_pod_name << std::endl;
    }

    WS_PATH_LIST_BEGIN
    WS_PATH_ADD("/ws", Get);
    WS_PATH_LIST_END
};

int main() {
    std::signal(SIGTERM, signal_handler);
    std::signal(SIGINT, signal_handler);

    const char* env;

    env = std::getenv("POD_NAME");
    g_pod_name = env ? env : "ws-pod-unknown";

    env = std::getenv("REDIS_URL");
    g_redis_url = env ? env : "redis://redis:6379";

    sw::redis::ConnectionOptions opts;
    auto sep = g_redis_url.find("://");
    std::string host_port = (sep != std::string::npos) ? g_redis_url.substr(sep + 3) : g_redis_url;
    auto colon = host_port.find(':');
    opts.host = (colon != std::string::npos) ? host_port.substr(0, colon) : host_port;
    opts.port = (colon != std::string::npos) ? std::stoi(host_port.substr(colon + 1)) : 6379;
    opts.socket_timeout = std::chrono::milliseconds(1000);

    g_redis = std::make_unique<sw::redis::Redis>(opts);

    std::thread subscriber(redis_subscriber_loop);

    app().setLogLevel(trantor::Logger::kInfo);
    app().addListener("0.0.0.0", 8080);
    app().setUploadPath("/tmp");

    app().registerPreRoutingAdvice(
        [](const HttpRequestPtr& req,
           std::function<void(const HttpResponsePtr&)>&& callback,
           std::function<void()>&& pass) {
            auto path = req->path();
            if (path.size() > 4 && path.substr(0, 4) == "/ws/") {
                req->addHeader("X-Client-Id", path.substr(4));
                req->setPath("/ws");
            }
            pass();
        });

    app().registerHandler("/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value r;
            r["status"] = "ok";
            r["pod"] = g_pod_name;
            callback(HttpResponse::newHttpJsonResponse(r));
        },
        {Get});

    app().registerHandler("/info",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value r;
            r["pod"] = g_pod_name;
            Json::Value clients(Json::arrayValue);
            {
                std::lock_guard<std::mutex> lock(g_clients_mu);
                for (auto& [cid, _] : g_clients)
                    clients.append(cid);
            }
            r["clients"] = clients;
            callback(HttpResponse::newHttpJsonResponse(r));
        },
        {Get});

    app().registerHandler("/send",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            std::string target = req->getParameter("target");
            std::string message = req->getParameter("message");
            if (message.empty()) message = "hello";

            Json::Value payload;
            payload["pod"] = g_pod_name;
            payload["data"] = message;
            if (!target.empty()) payload["target"] = target;

            Json::FastWriter writer;
            writer.omitEndingLineFeed();
            std::string pub_msg = writer.write(payload);

            try {
                g_redis->publish("ws:broadcast", pub_msg);
            } catch (const std::exception& e) {
                std::cerr << "Redis publish error: " << e.what() << std::endl;
            }

            if (!target.empty()) {
                send_frame(target, message);
            } else {
                broadcast_local(message);
            }

            Json::Value r;
            r["sent"] = true;
            r["pod"] = g_pod_name;
            callback(HttpResponse::newHttpJsonResponse(r));
        },
        {Post});

    std::cerr << "ws-server started pod=" << g_pod_name << std::endl;
    app().run();

    g_shutdown = true;
    subscriber.join();
    return 0;
}
