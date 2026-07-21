// examples/26-failure-modes/cpp/edge-service — Demonstrates timeout, retry,
// circuit breaker, deadline propagation, and bulkhead patterns.
//
// API:
//   GET /healthz           → {"status":"ok"}
//   GET /with-timeout      → calls backend with 2s timeout
//   GET /with-retry        → retries up to 3 times with exponential backoff
//   GET /breaker-state     → circuit breaker state
//   GET /with-breaker      → calls backend through circuit breaker
//   GET /with-deadline     → propagates deadline to backend
//   GET /with-bulkhead     → bounded concurrency (max 5)
//   GET /bulkhead-state    → bulkhead state

#include <drogon/drogon.h>
#include <json/json.h>
#include <curl/curl.h>
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <map>
#include <mutex>
#include <random>
#include <semaphore>
#include <string>
#include <thread>

using namespace drogon;

// ════════════════════════════════════════════════════════════════════════
// HTTP client (libcurl wrapper)
// ════════════════════════════════════════════════════════════════════════

struct CurlResponse {
    int status_code = 0;
    std::string body;
    double elapsed_s = 0.0;
};

size_t write_callback(void* ptr, size_t size, size_t nmemb, std::string* data) {
    data->append(static_cast<char*>(ptr), size * nmemb);
    return size * nmemb;
}

CurlResponse http_get(const std::string& url, double timeout_s = 2.0,
                      const std::map<std::string, std::string>& headers = {}) {
    CurlResponse resp;
    CURL* curl = curl_easy_init();
    if (!curl) {
        return resp;
    }

    auto start = std::chrono::steady_clock::now();

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &resp.body);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT_MS, static_cast<long>(timeout_s * 1000));
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT_MS, 500L);

    struct curl_slist* header_list = nullptr;
    for (const auto& [k, v] : headers) {
        header_list = curl_slist_append(header_list, (k + ": " + v).c_str());
    }
    if (header_list) {
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, header_list);
    }

    CURLcode res = curl_easy_perform(curl);

    auto end = std::chrono::steady_clock::now();
    resp.elapsed_s = std::chrono::duration<double>(end - start).count();

    if (res == CURLE_OK) {
        long code;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &code);
        resp.status_code = static_cast<int>(code);
    } else if (res == CURLE_OPERATION_TIMEDOUT) {
        resp.status_code = 0;  // timeout marker
    }

    if (header_list) {
        curl_slist_free_all(header_list);
    }
    curl_easy_cleanup(curl);
    return resp;
}

// ════════════════════════════════════════════════════════════════════════
// Circuit breaker
// ════════════════════════════════════════════════════════════════════════

class CircuitBreaker {
public:
    CircuitBreaker(const std::string& name, int threshold = 5, double reset_timeout = 10.0)
        : name_(name), threshold_(threshold), reset_timeout_(reset_timeout) {}

    bool allow() {
        std::lock_guard<std::mutex> lock(mtx_);
        total_calls_++;

        if (state_ == "open") {
            double elapsed = now() - opened_at_;
            if (elapsed >= reset_timeout_) {
                state_ = "half-open";
                success_count_ = 0;
                return true;
            }
            total_rejected_++;
            return false;
        }
        return true;
    }

    void record_success() {
        std::lock_guard<std::mutex> lock(mtx_);
        if (state_ == "half-open") {
            success_count_++;
            if (success_count_ >= 2) {  // 2 successful trials to close
                state_ = "closed";
                failure_count_ = 0;
                success_count_ = 0;
            }
        } else if (state_ == "closed") {
            failure_count_ = 0;  // reset on success
        }
    }

    void record_failure() {
        std::lock_guard<std::mutex> lock(mtx_);
        if (state_ == "half-open") {
            state_ = "open";
            opened_at_ = now();
            failure_count_ = 0;
            success_count_ = 0;
        } else if (state_ == "closed") {
            failure_count_++;
            if (failure_count_ >= threshold_) {
                state_ = "open";
                opened_at_ = now();
                failure_count_ = 0;
            }
        }
    }

    Json::Value info() {
        std::lock_guard<std::mutex> lock(mtx_);
        Json::Value resp;
        resp["name"] = name_;
        resp["state"] = state_;
        resp["failure_count"] = failure_count_;
        resp["success_count"] = success_count_;
        resp["threshold"] = threshold_;
        resp["reset_timeout_s"] = reset_timeout_;
        resp["total_calls"] = total_calls_;
        resp["total_rejected"] = total_rejected_;
        if (state_ == "open") {
            resp["open_elapsed_s"] = now() - opened_at_;
        }
        return resp;
    }

private:
    std::string name_;
    std::string state_ = "closed";
    int failure_count_ = 0;
    int success_count_ = 0;
    int threshold_;
    double reset_timeout_;
    double opened_at_ = 0.0;
    int total_calls_ = 0;
    int total_rejected_ = 0;
    std::mutex mtx_;

    double now() const {
        return std::chrono::duration<double>(
            std::chrono::steady_clock::now().time_since_epoch()
        ).count();
    }
};

// ════════════════════════════════════════════════════════════════════════
// Bulkhead
// ════════════════════════════════════════════════════════════════════════

class Bulkhead {
public:
    Bulkhead(int max_concurrent) : sem_(max_concurrent), max_(max_concurrent) {}

    bool try_acquire() {
        if (sem_.try_acquire()) {
            active_.fetch_add(1);
            return true;
        }
        rejected_.fetch_add(1);
        return false;
    }

    void release() {
        active_.fetch_sub(1);
        sem_.release();
    }

    Json::Value state() {
        Json::Value resp;
        resp["max_concurrent"] = max_;
        resp["active"] = active_.load();
        resp["rejected"] = rejected_.load();
        return resp;
    }

private:
    std::counting_semaphore<5> sem_;
    int max_;
    std::atomic<int> active_{0};
    std::atomic<int> rejected_{0};
};

// ════════════════════════════════════════════════════════════════════════
// Retry with exponential backoff
// ════════════════════════════════════════════════════════════════════════

std::random_device rd_retry;
std::mt19937 gen_retry(rd_retry());

double jitter(double base) {
    std::uniform_real_distribution<> dist(0.0, base * 0.1);
    return dist(gen_retry);
}

CurlResponse retry_with_backoff(const std::string& url, int max_attempts = 3) {
    double wait = 0.1;  // initial wait 100ms
    const double max_wait = 2.0;

    for (int attempt = 1; attempt <= max_attempts; ++attempt) {
        auto resp = http_get(url, 2.0);
        if (resp.status_code == 200) {
            return resp;  // success
        }

        if (attempt < max_attempts) {
            double sleep_time = wait + jitter(wait);
            std::this_thread::sleep_for(
                std::chrono::duration<double>(sleep_time)
            );
            wait = std::min(wait * 2.0, max_wait);
        } else {
            return resp;  // last attempt failed
        }
    }

    CurlResponse fail;
    return fail;
}

// ════════════════════════════════════════════════════════════════════════
// Global instances
// ════════════════════════════════════════════════════════════════════════

CircuitBreaker g_breaker("backend", 5, 10.0);
Bulkhead g_bulkhead(5);

int main() {
    // Suppress upload directory warning
    app().setUploadPath("/tmp");

    // Disable default logging to reduce noise
    app().setLogLevel(trantor::Logger::kWarn);

    // Get backend URL from environment
    const char* backend_url_env = std::getenv("BACKEND_URL");
    std::string backend_base = backend_url_env ? backend_url_env : "http://localhost:8081";

    // GET /healthz
    app().registerHandler(
        "/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value resp;
            resp["status"] = "ok";

            auto http_resp = drogon::HttpResponse::newHttpJsonResponse(resp);
            callback(http_resp);
        },
        {Get}
    );

    // GET /with-timeout — calls backend with 2s timeout
    app().registerHandler(
        "/with-timeout",
        [backend_base](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            std::string url = backend_base + "/process";
            auto resp = http_get(url, 2.0);

            Json::Value result;
            if (resp.status_code == 200) {
                result["status"] = 200;
                result["elapsed_s"] = resp.elapsed_s;
                Json::CharReaderBuilder reader;
                Json::Value body;
                std::string errs;
                std::istringstream iss(resp.body);
                if (Json::parseFromStream(reader, iss, &body, &errs)) {
                    result["body"] = body;
                }
            } else if (resp.status_code == 0) {
                result["error"] = "timeout";
                result["elapsed_s"] = resp.elapsed_s;
                result["pattern"] = "timeout";
            } else {
                result["error"] = "http_error";
                result["status"] = resp.status_code;
                result["elapsed_s"] = resp.elapsed_s;
            }

            auto http_resp = drogon::HttpResponse::newHttpJsonResponse(result);
            callback(http_resp);
        },
        {Get}
    );

    // GET /with-retry — retries up to 3 times with exponential backoff
    app().registerHandler(
        "/with-retry",
        [backend_base](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            std::string url = backend_base + "/process";

            int max_attempts = 3;
            double wait = 0.1;
            const double max_wait = 2.0;

            for (int attempt = 1; attempt <= max_attempts; ++attempt) {
                auto resp = http_get(url, 2.0);

                if (resp.status_code == 200) {
                    Json::Value result;
                    result["status"] = 200;
                    result["attempts"] = attempt;
                    result["elapsed_s"] = resp.elapsed_s;
                    Json::CharReaderBuilder reader;
                    Json::Value body;
                    std::string errs;
                    std::istringstream iss(resp.body);
                    if (Json::parseFromStream(reader, iss, &body, &errs)) {
                        result["body"] = body;
                    }

                    auto http_resp = drogon::HttpResponse::newHttpJsonResponse(result);
                    callback(http_resp);
                    return;
                }

                if (attempt < max_attempts) {
                    double sleep_time = wait + jitter(wait);
                    std::this_thread::sleep_for(
                        std::chrono::duration<double>(sleep_time)
                    );
                    wait = std::min(wait * 2.0, max_wait);
                } else {
                    // Last attempt failed
                    Json::Value result;
                    result["error"] = resp.status_code == 0 ? "timeout" : "http_error";
                    result["attempts"] = attempt;
                    result["elapsed_s"] = resp.elapsed_s;
                    result["pattern"] = "retry-exhausted";

                    auto http_resp = drogon::HttpResponse::newHttpJsonResponse(result);
                    callback(http_resp);
                }
            }
        },
        {Get}
    );

    // GET /breaker-state
    app().registerHandler(
        "/breaker-state",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            auto info = g_breaker.info();
            auto http_resp = drogon::HttpResponse::newHttpJsonResponse(info);
            callback(http_resp);
        },
        {Get}
    );

    // GET /with-breaker
    app().registerHandler(
        "/with-breaker",
        [backend_base](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            if (!g_breaker.allow()) {
                Json::Value result;
                result["source"] = "fallback";
                result["reason"] = "circuit_open";
                result["breaker"] = "open";

                auto http_resp = drogon::HttpResponse::newHttpJsonResponse(result);
                callback(http_resp);
                return;
            }

            std::string url = backend_base + "/process";
            auto resp = http_get(url, 2.0);

            if (resp.status_code == 200) {
                g_breaker.record_success();

                Json::Value result;
                result["source"] = "live";
                result["breaker"] = g_breaker.info()["state"];
                Json::CharReaderBuilder reader;
                Json::Value body;
                std::string errs;
                std::istringstream iss(resp.body);
                if (Json::parseFromStream(reader, iss, &body, &errs)) {
                    result["body"] = body;
                }

                auto http_resp = drogon::HttpResponse::newHttpJsonResponse(result);
                callback(http_resp);
            } else {
                g_breaker.record_failure();

                Json::Value result;
                result["source"] = "fallback";
                result["reason"] = "backend_error";
                result["breaker"] = g_breaker.info()["state"];

                auto http_resp = drogon::HttpResponse::newHttpJsonResponse(result);
                callback(http_resp);
            }
        },
        {Get}
    );

    // GET /with-deadline
    app().registerHandler(
        "/with-deadline",
        [backend_base](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            auto budget_ms_str = req->getParameter("budget_ms");
            if (budget_ms_str.empty()) {
                auto http_resp = drogon::HttpResponse::newHttpResponse();
                http_resp->setStatusCode(k400BadRequest);
                http_resp->setBody(R"({"error":"missing budget_ms parameter"})");
                callback(http_resp);
                return;
            }

            int budget_ms = std::stoi(budget_ms_str);
            int edge_overhead = 50;
            int remaining = budget_ms - edge_overhead;

            if (remaining < 50) {
                Json::Value result;
                result["error"] = "deadline_exceeded";
                result["reason"] = "insufficient budget at edge";
                result["budget_ms"] = budget_ms;
                result["remaining_ms"] = remaining;

                auto http_resp = drogon::HttpResponse::newHttpJsonResponse(result);
                callback(http_resp);
                return;
            }

            std::map<std::string, std::string> headers;
            headers["X-Deadline-Ms"] = std::to_string(remaining);

            std::string url = backend_base + "/process";
            double timeout_s = remaining / 1000.0;
            auto resp = http_get(url, timeout_s, headers);

            Json::CharReaderBuilder reader;
            Json::Value body;
            std::string errs;
            std::istringstream iss(resp.body);
            Json::parseFromStream(reader, iss, &body, &errs);

            if (resp.status_code == 200) {
                Json::Value result;
                result["status"] = 200;
                result["budget_ms"] = budget_ms;
                result["remaining_ms"] = remaining;
                result["elapsed_s"] = resp.elapsed_s;
                if (!body.isNull()) result["body"] = body;

                auto http_resp = drogon::HttpResponse::newHttpJsonResponse(result);
                callback(http_resp);
            } else if (resp.status_code > 0 && !body.isNull()) {
                auto http_resp = drogon::HttpResponse::newHttpJsonResponse(body);
                callback(http_resp);
            } else {
                Json::Value result;
                result["error"] = "deadline_exceeded";
                result["reason"] = "timed out waiting for backend";
                result["budget_ms"] = budget_ms;
                result["elapsed_s"] = resp.elapsed_s;

                auto http_resp = drogon::HttpResponse::newHttpJsonResponse(result);
                callback(http_resp);
            }
        },
        {Get}
    );

    // GET /bulkhead-state
    app().registerHandler(
        "/bulkhead-state",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            auto state = g_bulkhead.state();
            auto http_resp = drogon::HttpResponse::newHttpJsonResponse(state);
            callback(http_resp);
        },
        {Get}
    );

    // GET /with-bulkhead
    app().registerHandler(
        "/with-bulkhead",
        [backend_base](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            if (!g_bulkhead.try_acquire()) {
                Json::Value result;
                result["error"] = "bulkhead_full";
                result["pattern"] = "bulkhead";

                auto http_resp = drogon::HttpResponse::newHttpJsonResponse(result);
                http_resp->setStatusCode(k503ServiceUnavailable);
                callback(http_resp);
                return;
            }

            std::string url = backend_base + "/process";
            auto resp = http_get(url, 2.0);

            g_bulkhead.release();

            Json::Value result;
            if (resp.status_code == 200) {
                result["status"] = 200;
                result["elapsed_s"] = resp.elapsed_s;
                Json::CharReaderBuilder reader;
                Json::Value body;
                std::string errs;
                std::istringstream iss(resp.body);
                if (Json::parseFromStream(reader, iss, &body, &errs)) {
                    result["body"] = body;
                }
            } else {
                result["error"] = resp.status_code == 0 ? "timeout" : "http_error";
                result["status"] = resp.status_code;
                result["elapsed_s"] = resp.elapsed_s;
            }

            auto http_resp = drogon::HttpResponse::newHttpJsonResponse(result);
            callback(http_resp);
        },
        {Get}
    );

    // Start server
    app().addListener("0.0.0.0", 8080);

    LOG_INFO << "Edge service starting on port 8080";
    LOG_INFO << "Backend URL: " << backend_base;
    app().run();

    return 0;
}
