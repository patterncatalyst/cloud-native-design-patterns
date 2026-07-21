// examples/26-failure-modes/cpp/backend-service — Simulated backend with
// controllable failure modes: healthy, slow, failing, flaky.
//
// API:
//   GET  /healthz → {"status":"ok"}
//   GET  /mode    → {"mode":"...", "call_count": N}
//   POST /mode    → {"mode":"healthy"|"slow"|"failing"|"flaky"} → resets call_count
//   GET  /process → behavior depends on mode + X-Deadline-Ms header

#include <drogon/drogon.h>
#include <json/json.h>
#include <atomic>
#include <chrono>
#include <mutex>
#include <random>
#include <string>
#include <thread>

using namespace drogon;

// Global state
std::string g_mode = "healthy";
std::atomic<int> g_call_count{0};
std::mutex g_mode_mutex;

// Random number generator for flaky mode
std::random_device rd;
std::mt19937 gen(rd());
std::uniform_int_distribution<> dist(0, 1);

int main() {
    // Suppress upload directory warning
    app().setUploadPath("/tmp");

    // Disable default logging to reduce noise
    app().setLogLevel(trantor::Logger::kWarn);

    // GET /healthz
    app().registerHandler(
        "/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value resp;
            resp["status"] = "ok";

            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            callback(http_resp);
        },
        {Get}
    );

    // GET /mode
    app().registerHandler(
        "/mode",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value resp;
            {
                std::lock_guard<std::mutex> lock(g_mode_mutex);
                resp["mode"] = g_mode;
            }
            resp["call_count"] = g_call_count.load();

            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            callback(http_resp);
        },
        {Get}
    );

    // POST /mode
    app().registerHandler(
        "/mode",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            auto json = req->getJsonObject();
            if (!json || !json->isMember("mode")) {
                auto http_resp = HttpResponse::newHttpResponse();
                http_resp->setStatusCode(k400BadRequest);
                http_resp->setBody(R"({"error":"missing mode field"})");
                callback(http_resp);
                return;
            }

            std::string new_mode = (*json)["mode"].asString();
            if (new_mode != "healthy" && new_mode != "slow" &&
                new_mode != "failing" && new_mode != "flaky") {
                auto http_resp = HttpResponse::newHttpResponse();
                http_resp->setStatusCode(k400BadRequest);
                http_resp->setBody(R"({"error":"invalid mode"})");
                callback(http_resp);
                return;
            }

            {
                std::lock_guard<std::mutex> lock(g_mode_mutex);
                g_mode = new_mode;
            }
            g_call_count.store(0);

            Json::Value resp;
            resp["mode"] = new_mode;
            resp["call_count"] = 0;

            auto http_resp = HttpResponse::newHttpJsonResponse(resp);
            callback(http_resp);
        },
        {Post}
    );

    // GET /process
    app().registerHandler(
        "/process",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            g_call_count.fetch_add(1);

            // Check deadline header
            auto deadline_header = req->getHeader("X-Deadline-Ms");
            if (!deadline_header.empty()) {
                try {
                    int deadline_ms = std::stoi(deadline_header);
                    if (deadline_ms < 100) {
                        Json::Value resp;
                        resp["status"] = "rejected";
                        resp["reason"] = "deadline_too_small";
                        resp["remaining_ms"] = deadline_ms;

                        auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                        http_resp->setStatusCode(k400BadRequest);
                        callback(http_resp);
                        return;
                    }
                } catch (...) {
                    // Ignore parse errors
                }
            }

            std::string current_mode;
            {
                std::lock_guard<std::mutex> lock(g_mode_mutex);
                current_mode = g_mode;
            }

            if (current_mode == "healthy") {
                Json::Value resp;
                resp["status"] = "ok";
                resp["mode"] = "healthy";

                auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                callback(http_resp);
            }
            else if (current_mode == "slow") {
                std::this_thread::sleep_for(std::chrono::seconds(5));

                Json::Value resp;
                resp["status"] = "ok";
                resp["mode"] = "slow";

                auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                callback(http_resp);
            }
            else if (current_mode == "failing") {
                Json::Value resp;
                resp["status"] = "error";
                resp["mode"] = "failing";

                auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                http_resp->setStatusCode(k500InternalServerError);
                callback(http_resp);
            }
            else if (current_mode == "flaky") {
                bool should_fail = dist(gen) == 0;  // 50/50 chance

                if (should_fail) {
                    Json::Value resp;
                    resp["status"] = "error";
                    resp["mode"] = "flaky";

                    auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                    http_resp->setStatusCode(k500InternalServerError);
                    callback(http_resp);
                } else {
                    Json::Value resp;
                    resp["status"] = "ok";
                    resp["mode"] = "flaky";

                    auto http_resp = HttpResponse::newHttpJsonResponse(resp);
                    callback(http_resp);
                }
            }
        },
        {Get}
    );

    // Start server
    app().addListener("0.0.0.0", 8081);

    LOG_INFO << "Backend service starting on port 8081";
    app().run();

    return 0;
}
