#include <drogon/drogon.h>
#include <libpq-fe.h>
#include <json/json.h>
#include <random>
#include <sstream>
#include <iomanip>
#include <vector>
#include <functional>
#include <thread>
#include <string_view>

#include "saga_machine.hpp"

using namespace drogon;

static std::string g_connStr;

static std::string generateId(const std::string& prefix) {
    static thread_local std::mt19937 rng(std::random_device{}());
    std::uniform_int_distribution<uint32_t> dist;
    std::ostringstream ss;
    ss << prefix << std::hex << std::setfill('0')
       << std::setw(8) << dist(rng);
    return ss.str();
}

static std::string generateUuid() {
    static thread_local std::mt19937 rng(std::random_device{}());
    std::uniform_int_distribution<uint32_t> dist;
    auto h = [&](int w) {
        std::ostringstream s;
        s << std::hex << std::setfill('0') << std::setw(w) << (dist(rng) >> (32 - w*4));
        return s.str();
    };
    return h(8) + "-" + h(4) + "-4" + h(3) + "-" + h(4) + "-" + h(8) + h(4);
}

struct PgConn {
    PGconn* conn = nullptr;
    PgConn() { conn = PQconnectdb(g_connStr.c_str()); }
    ~PgConn() { if (conn) PQfinish(conn); }
    bool ok() const { return conn && PQstatus(conn) == CONNECTION_OK; }
    PgConn(const PgConn&) = delete;
    PgConn& operator=(const PgConn&) = delete;
};

struct PgResult {
    PGresult* res = nullptr;
    PgResult(PGresult* r) : res(r) {}
    ~PgResult() { if (res) PQclear(res); }
    bool ok() const { return res && (PQresultStatus(res) == PGRES_TUPLES_OK || PQresultStatus(res) == PGRES_COMMAND_OK); }
    int rows() const { return res ? PQntuples(res) : 0; }
    std::string get(int r, int c) const { return PQgetvalue(res, r, c); }
    PgResult(const PgResult&) = delete;
    PgResult& operator=(const PgResult&) = delete;
    PgResult(PgResult&& o) noexcept : res(o.res) { o.res = nullptr; }
};

static Json::Value parseJson(const std::string& s) {
    Json::Value root;
    Json::CharReaderBuilder builder;
    std::istringstream stream(s);
    Json::parseFromStream(builder, stream, &root, nullptr);
    return root;
}

static std::string toJsonString(const Json::Value& v) {
    Json::StreamWriterBuilder builder;
    builder["indentation"] = "";
    return Json::writeString(builder, v);
}

struct SagaStep {
    std::string name;
    std::string compensationName;
    std::function<Json::Value(const Json::Value&)> execute;
    std::function<Json::Value(const Json::Value&)> compensate;
};

static std::vector<SagaStep> g_steps = {
    {
        "charge_payment", "refund_payment",
        [](const Json::Value& ctx) {
            Json::Value r;
            r["payment_id"] = generateId("pay-");
            r["amount"] = ctx["total"].asDouble();
            return r;
        },
        [](const Json::Value&) {
            Json::Value r;
            r["refunded"] = true;
            return r;
        }
    },
    {
        "reserve_stock", "release_stock",
        [](const Json::Value& ctx) {
            Json::Value r;
            r["reservation_id"] = generateId("rsv-");
            r["sku"] = ctx["sku"].asString();
            return r;
        },
        [](const Json::Value&) {
            Json::Value r;
            r["released"] = true;
            return r;
        }
    },
    {
        "book_shipping", "cancel_shipping",
        [](const Json::Value& ctx) {
            if (ctx.isMember("fail_shipping") && ctx["fail_shipping"].asBool()) {
                throw std::runtime_error("shipping unavailable");
            }
            Json::Value r;
            r["shipment_id"] = generateId("shp-");
            return r;
        },
        [](const Json::Value&) {
            Json::Value r;
            r["cancelled"] = true;
            return r;
        }
    }
};

// Parameterised statements only: ids and JSON go in as $n values, never as SQL text.
static PgResult query(PGconn* conn, const char* sql, const std::vector<std::string>& args = {}) {
    std::vector<const char*> values;
    for (const auto& a : args) values.push_back(a.c_str());
    return PgResult(PQexecParams(conn, sql, static_cast<int>(values.size()), nullptr,
                                 values.data(), nullptr, nullptr, 0));
}

static void logStep(PGconn* conn, const std::string& sagaId,
                    const std::string& step, const std::string& action,
                    const Json::Value& result) {
    query(conn, "INSERT INTO saga_log (saga_id, step, action, result) VALUES ($1, $2, $3, $4::jsonb)",
          {sagaId, step, action, toJsonString(result)});
}

static void setState(PGconn* conn, const std::string& sagaId, std::string_view status,
                     int stepIndex, const Json::Value* context) {
    if (context) {
        query(conn, "UPDATE sagas SET status = $1, step_index = $2, context = $3::jsonb, "
                    "updated_at = now() WHERE id = $4",
              {std::string(status), std::to_string(stepIndex), toJsonString(*context), sagaId});
    } else {
        query(conn, "UPDATE sagas SET status = $1, step_index = $2, updated_at = now() WHERE id = $3",
              {std::string(status), std::to_string(stepIndex), sagaId});
    }
}

// Runs one saga to a terminal status. Every step is its own transaction, so a crash leaves the
// saga RUNNING at the last committed step_index and resumeRunningSagas() picks it up.
// The state machine (saga_machine.hpp) decides the next status; this function does the I/O.
static void advance(const std::string& sagaId) {
    PgConn db;
    if (!db.ok()) return;
    const int numSteps = static_cast<int>(g_steps.size());

    for (;;) {
        PQexec(db.conn, "BEGIN");
        auto row = query(db.conn,
            "SELECT status, step_index, context FROM sagas WHERE id = $1 FOR UPDATE", {sagaId});
        if (!row.ok() || row.rows() == 0) { PQexec(db.conn, "ROLLBACK"); return; }

        cndp::saga::Progress progress{std::stoi(row.get(0, 1)), numSteps};
        cndp::saga::Machine sm{progress};
        cndp::saga::restore(sm, row.get(0, 0));
        Json::Value context = parseJson(row.get(0, 2));
        const std::string status(cndp::saga::status_of(sm));

        if (status == "COMPENSATING") {
            // Undo completed steps in reverse order, then record COMPENSATED.
            for (int i : cndp::saga::compensation_order(progress.step_index)) {
                auto& step = g_steps[i];
                logStep(db.conn, sagaId, step.compensationName, "compensate", step.compensate(context));
            }
            sm.process_event(cndp::saga::Compensated{});
            setState(db.conn, sagaId, cndp::saga::status_of(sm), progress.step_index, nullptr);
            PQexec(db.conn, "COMMIT");
            return;
        }
        if (status != "RUNNING") { PQexec(db.conn, "ROLLBACK"); return; }

        if (progress.step_index >= numSteps) {
            sm.process_event(cndp::saga::AllStepsDone{});
            setState(db.conn, sagaId, cndp::saga::status_of(sm), progress.step_index, nullptr);
            PQexec(db.conn, "COMMIT");
            return;
        }

        auto& step = g_steps[progress.step_index];
        try {
            Json::Value result = step.execute(context);
            context[step.name] = result;
            logStep(db.conn, sagaId, step.name, "execute", result);
            sm.process_event(cndp::saga::StepSucceeded{});
            setState(db.conn, sagaId, cndp::saga::status_of(sm), progress.step_index, &context);
            PQexec(db.conn, "COMMIT");
        } catch (const std::exception& e) {
            Json::Value failResult;
            failResult["error"] = e.what();
            logStep(db.conn, sagaId, step.name, "failed", failResult);
            sm.process_event(cndp::saga::StepFailed{});
            setState(db.conn, sagaId, cndp::saga::status_of(sm), progress.step_index, nullptr);
            PQexec(db.conn, "COMMIT");
        }
    }
}

static Json::Value getSaga(const std::string& sagaId) {
    PgConn db;
    if (!db.ok()) return Json::Value::null;

    auto row = query(db.conn, "SELECT id, status, step_index, context FROM sagas WHERE id = $1", {sagaId});
    if (!row.ok() || row.rows() == 0) return Json::Value::null;

    Json::Value saga;
    saga["id"] = row.get(0, 0);
    saga["status"] = row.get(0, 1);
    saga["step_index"] = std::stoi(row.get(0, 2));
    saga["context"] = parseJson(row.get(0, 3));
    return saga;
}

static Json::Value getSagaLog(const std::string& sagaId) {
    PgConn db;
    if (!db.ok()) return Json::Value(Json::arrayValue);

    auto rows = query(db.conn, "SELECT step, action, result FROM saga_log WHERE saga_id = $1 ORDER BY id", {sagaId});
    if (!rows.ok()) return Json::Value(Json::arrayValue);

    Json::Value log(Json::arrayValue);
    for (int i = 0; i < rows.rows(); ++i) {
        Json::Value entry;
        entry["step"] = rows.get(i, 0);
        entry["action"] = rows.get(i, 1);
        entry["result"] = parseJson(rows.get(i, 2));
        log.append(entry);
    }
    return log;
}

static void resumeRunningSagas() {
    PgConn db;
    if (!db.ok()) {
        LOG_ERROR << "Cannot connect to DB for saga resume";
        return;
    }

    auto rows = query(db.conn, "SELECT id FROM sagas WHERE status IN ('RUNNING', 'COMPENSATING')");
    if (!rows.ok()) return;

    for (int i = 0; i < rows.rows(); ++i) {
        std::string id = rows.get(i, 0);
        LOG_INFO << "Resuming saga: " << id;
        advance(id);
    }
}

int main() {
    const char* dbUrl = std::getenv("DATABASE_URL");
    g_connStr = dbUrl ? dbUrl : "postgres://appuser:apppass@localhost:5432/appdb";

    app().setLogLevel(trantor::Logger::kInfo);
    app().setUploadPath("/tmp");

    app().registerHandler("/healthz",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value resp;
            resp["status"] = "ok";
            callback(HttpResponse::newHttpJsonResponse(resp));
        },
        {Get});

    app().registerHandler("/sagas",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {
            auto body = req->getJsonObject();
            if (!body) {
                auto resp = HttpResponse::newHttpJsonResponse(Json::Value("invalid json"));
                resp->setStatusCode(k400BadRequest);
                callback(resp);
                return;
            }

            std::string sagaId = generateUuid();
            Json::Value context = *body;

            PgConn db;
            if (!db.ok()) {
                auto resp = HttpResponse::newHttpJsonResponse(Json::Value("db error"));
                resp->setStatusCode(k500InternalServerError);
                callback(resp);
                return;
            }

            query(db.conn, "INSERT INTO sagas (id, status, step_index, context) VALUES ($1, 'RUNNING', 0, $2::jsonb)",
                  {sagaId, toJsonString(context)});

            advance(sagaId);

            Json::Value saga = getSaga(sagaId);
            auto resp = HttpResponse::newHttpJsonResponse(saga);
            resp->setStatusCode(k201Created);
            callback(resp);
        },
        {Post});

    app().registerHandler("/sagas/{saga_id}",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback,
           const std::string& sagaId) {
            Json::Value saga = getSaga(sagaId);
            if (saga.isNull()) {
                auto resp = HttpResponse::newHttpJsonResponse(Json::Value("not found"));
                resp->setStatusCode(k404NotFound);
                callback(resp);
                return;
            }
            callback(HttpResponse::newHttpJsonResponse(saga));
        },
        {Get});

    app().registerHandler("/sagas/{saga_id}/log",
        [](const HttpRequestPtr&, std::function<void(const HttpResponsePtr&)>&& callback,
           const std::string& sagaId) {
            callback(HttpResponse::newHttpJsonResponse(getSagaLog(sagaId)));
        },
        {Get});

    // Resume any incomplete sagas after startup
    app().getLoop()->runAfter(2.0, []() {
        std::thread([]() { resumeRunningSagas(); }).detach();
    });

    LOG_INFO << "Saga orchestrator starting on 0.0.0.0:8080";
    app().addListener("0.0.0.0", 8080).run();
}
