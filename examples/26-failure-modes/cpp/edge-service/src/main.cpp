// examples/26-failure-modes/cpp/edge-service: timeout, retry, circuit breaker, deadline propagation and bulkhead.
//
// API:
//   GET /healthz           → {"status":"ok"}
//   GET /with-timeout      → calls backend with a 2 s timeout
//   GET /with-retry        → retries up to 3 times with exponential backoff and jitter
//   GET /with-breaker      → calls backend through the circuit breaker
//   GET /breaker-state     → {"name","state"} plus counters
//   GET /with-deadline     → propagates the remaining budget to the backend
//   GET /with-bulkhead     → bounded concurrency (5), the overflow refused with 429
//   GET /bulkhead-state    → {"max_concurrent":5}
//
// No maintained C++ resilience library is on ConanCenter, so the breaker and the bulkhead are written here.
// Every handler is a coroutine on Drogon's async HttpClient: waiting on the backend or on a retry delay
// suspends the handler instead of blocking an event-loop thread.

#include <drogon/drogon.h>
#include <json/json.h>

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <random>
#include <semaphore>
#include <string>

using namespace drogon;
using namespace std::chrono_literals;

namespace {

std::string g_backend;

// ── Circuit breaker: 5 failures in a row open it, it stays open 10 s, then 2 successful trial calls close it.

class CircuitBreaker {
public:
    explicit CircuitBreaker(std::string name) : name_(std::move(name)) {}

    bool allow() {
        std::lock_guard lock(mtx_);
        if (state_ == "open" && Clock::now() - opened_at_ >= kResetTimeout) {
            state_ = "half-open";
            successes_ = 0;
        }
        return state_ != "open";
    }

    void record_success() {
        std::lock_guard lock(mtx_);
        failures_ = 0;
        if (state_ == "half-open" && ++successes_ >= kTrialSuccesses) state_ = "closed";
    }

    void record_failure() {
        std::lock_guard lock(mtx_);
        if (state_ == "half-open" || ++failures_ >= kThreshold) {
            state_ = "open";
            opened_at_ = Clock::now();
            failures_ = 0;
        }
    }

    std::string state() {
        std::lock_guard lock(mtx_);
        return state_;
    }

    Json::Value info() {
        std::lock_guard lock(mtx_);
        Json::Value v;
        v["name"] = name_;
        v["state"] = state_;
        v["consecutive_failures"] = failures_;
        return v;
    }

private:
    using Clock = std::chrono::steady_clock;
    static constexpr int kThreshold = 5;
    static constexpr int kTrialSuccesses = 2;
    static constexpr auto kResetTimeout = 10s;

    std::string name_;
    std::string state_ = "closed";
    int failures_ = 0;
    int successes_ = 0;
    Clock::time_point opened_at_{};
    std::mutex mtx_;
};

CircuitBreaker g_breaker("backend");

// ── Bulkhead: at most 5 calls in flight; try_acquire turns the sixth away at once.

constexpr int kBulkhead = 5;
std::counting_semaphore<kBulkhead> g_bulkhead(kBulkhead);

struct Permit {
    ~Permit() { g_bulkhead.release(); }
};

// ── Backend calls

struct Reply {
    int status = 0;  // 0: no answer (timeout or connection failure)
    Json::Value body;
};

Task<Reply> get_backend(double timeout_s, std::string deadline_ms = {}) {
    auto client = HttpClient::newHttpClient(g_backend);
    auto req = HttpRequest::newHttpRequest();
    req->setPath("/process");
    if (!deadline_ms.empty()) req->addHeader("X-Deadline-Ms", deadline_ms);
    try {
        auto resp = co_await client->sendRequestCoro(req, timeout_s);
        Reply reply{static_cast<int>(resp->getStatusCode())};
        if (auto json = resp->getJsonObject()) reply.body = *json;
        co_return reply;
    } catch (const HttpException&) {
        co_return Reply{};
    }
}

double seconds_since(std::chrono::steady_clock::time_point start) {
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
}

HttpResponsePtr json(const Json::Value& v, HttpStatusCode code = k200OK) {
    auto resp = HttpResponse::newHttpJsonResponse(v);
    resp->setStatusCode(code);
    return resp;
}

}  // namespace

int main() {
    // docker logs reads a pipe: line-buffer stdout so LOG_* lines show up as they are written.
    std::setvbuf(stdout, nullptr, _IOLBF, 0);
    app().setUploadPath("/tmp");
    app().setLogLevel(trantor::Logger::kWarn);

    const char* env = std::getenv("BACKEND_URL");
    g_backend = env ? env : "http://localhost:8081";

    app().registerHandler("/healthz", [](HttpRequestPtr) -> Task<HttpResponsePtr> {
        Json::Value v;
        v["status"] = "ok";
        co_return json(v);
    }, {Get});

    // 1. Timeout: the call gives up after 2 s.
    app().registerHandler("/with-timeout", [](HttpRequestPtr) -> Task<HttpResponsePtr> {
        auto start = std::chrono::steady_clock::now();
        auto reply = co_await get_backend(2.0);
        Json::Value v;
        if (reply.status == 0) {
            v["error"] = "timeout";
            v["pattern"] = "timeout";
        } else {
            v["status"] = reply.status;
            v["body"] = reply.body;
        }
        v["elapsed_s"] = seconds_since(start);
        co_return json(v);
    }, {Get});

    // 2. Retry: 3 attempts, waits from 100 ms doubling to 2 s with up to 50% jitter; a 5xx or no answer is retried.
    app().registerHandler("/with-retry", [](HttpRequestPtr) -> Task<HttpResponsePtr> {
        thread_local std::mt19937 rng{std::random_device{}()};
        auto start = std::chrono::steady_clock::now();
        auto wait = 0.1;
        Reply reply;
        int attempt = 1;
        for (;; ++attempt) {
            reply = co_await get_backend(2.0);
            if ((reply.status != 0 && reply.status < 500) || attempt == 3) break;
            co_await sleepCoro(trantor::EventLoop::getEventLoopOfCurrentThread(),
                               wait + std::uniform_real_distribution<>(0.0, wait * 0.5)(rng));
            wait = std::min(wait * 2, 2.0);
        }
        Json::Value v;
        v["attempts"] = attempt;
        v["elapsed_s"] = seconds_since(start);
        if (reply.status != 0 && reply.status < 500) {
            v["status"] = reply.status;
            v["body"] = reply.body;
        } else {
            v["error"] = reply.status == 0 ? "timeout" : "HTTP " + std::to_string(reply.status);
            v["pattern"] = "retry-exhausted";
        }
        co_return json(v);
    }, {Get});

    // 3. Circuit breaker with a fallback.
    app().registerHandler("/with-breaker", [](HttpRequestPtr) -> Task<HttpResponsePtr> {
        Json::Value v;
        if (!g_breaker.allow()) {
            v["source"] = "fallback";
            v["reason"] = "circuit_open";
        } else {
            auto reply = co_await get_backend(2.0);
            if (reply.status != 0 && reply.status < 500) {
                g_breaker.record_success();
                v["source"] = "live";
                v["body"] = reply.body;
            } else {
                g_breaker.record_failure();
                v["source"] = "fallback";
                v["reason"] = reply.status == 0 ? "upstream_unreachable" : "upstream_" + std::to_string(reply.status);
            }
        }
        v["breaker"] = g_breaker.state();
        co_return json(v);
    }, {Get});

    app().registerHandler("/breaker-state", [](HttpRequestPtr) -> Task<HttpResponsePtr> {
        co_return json(g_breaker.info());
    }, {Get});

    // 4. Deadline propagation: the backend gets what is left of the caller's budget.
    app().registerHandler("/with-deadline", [](HttpRequestPtr req) -> Task<HttpResponsePtr> {
        auto start = std::chrono::steady_clock::now();
        auto param = req->getParameter("budget_ms");
        int budget_ms = param.empty() ? 1000 : std::stoi(param);
        int remaining = budget_ms - 50;  // edge overhead
        Json::Value v;
        v["budget_ms"] = budget_ms;
        if (remaining < 50) {
            v["error"] = "deadline_exceeded";
            v["reason"] = "insufficient budget at edge";
            v["remaining_ms"] = remaining;
            co_return json(v);
        }
        auto reply = co_await get_backend(remaining / 1000.0, std::to_string(remaining));
        if (reply.status == 0) {
            v["error"] = "deadline_exceeded";
            v["reason"] = "timed out waiting for backend";
        } else {
            v["status"] = reply.status;
            v["remaining_ms"] = remaining;
            v["body"] = reply.body;
        }
        v["elapsed_s"] = seconds_since(start);
        co_return json(v);
    }, {Get});

    // 5. Bulkhead: at most 5 calls in flight, the overflow refused with 429.
    app().registerHandler("/with-bulkhead", [](HttpRequestPtr) -> Task<HttpResponsePtr> {
        Json::Value v;
        if (!g_bulkhead.try_acquire()) {
            v["error"] = "bulkhead_full";
            v["pattern"] = "bulkhead";
            co_return json(v, k429TooManyRequests);
        }
        Permit permit;
        auto reply = co_await get_backend(2.0);
        if (reply.status == 0) {
            v["error"] = "timeout";
        } else {
            v["status"] = reply.status;
            v["body"] = reply.body;
        }
        co_return json(v);
    }, {Get});

    app().registerHandler("/bulkhead-state", [](HttpRequestPtr) -> Task<HttpResponsePtr> {
        Json::Value v;
        v["max_concurrent"] = kBulkhead;
        co_return json(v);
    }, {Get});

    app().addListener("0.0.0.0", 8080);
    LOG_INFO << "Edge service starting on port 8080, backend " << g_backend;
    app().run();
    return 0;
}
