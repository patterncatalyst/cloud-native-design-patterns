#include <drogon/drogon.h>
#include <libpq-fe.h>
#include <json/json.h>
#include <random>
#include <sstream>
#include <iomanip>
#include <vector>
#include <functional>
#include <thread>

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
        [](const Json::Value& ctx) {
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
        [](const Json::Value& ctx) {
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
        [](const Json::Value& ctx) {
            Json::Value r;
            r["cancelled"] = true;
            return r;
        }
    }
};

static std::string escapeStr(const std::string& s) {
    std::string out;
    for (char c : s) {
        if (c == '\'') out += "''";
        else out += c;
    }
    return out;
}

static void logStep(PGconn* conn, const std::string& sagaId,
                    const std::string& step, const std::string& action,
                    const Json::Value& result) {
    std::string sql = "INSERT INTO saga_log (saga_id, step, action, result) VALUES ('"
        + escapeStr(sagaId) + "', '" + escapeStr(step) + "', '"
        + escapeStr(action) + "', '" + escapeStr(toJsonString(result)) + "')";
    PgResult r(PQexec(conn, sql.c_str()));
}

static void advance(const std::string& sagaId);
static void compensate(const std::string& sagaId);

static void advance(const std::string& sagaId) {
    PgConn db;
    if (!db.ok()) return;

    PQexec(db.conn, "BEGIN");

    std::string sql = "SELECT status, step_index, context FROM sagas WHERE id = '"
        + escapeStr(sagaId) + "' FOR UPDATE";
    PgResult row(PQexec(db.conn, sql.c_str()));
    if (!row.ok() || row.rows() == 0) { PQexec(db.conn, "ROLLBACK"); return; }

    std::string status = row.get(0, 0);
    int stepIdx = std::stoi(row.get(0, 1));
    Json::Value context = parseJson(row.get(0, 2));

    if (status != "RUNNING") { PQexec(db.conn, "ROLLBACK"); return; }

    int numSteps = static_cast<int>(g_steps.size());
    if (stepIdx >= numSteps) {
        std::string upd = "UPDATE sagas SET status = 'COMPLETED', updated_at = now() WHERE id = '"
            + escapeStr(sagaId) + "'";
        PQexec(db.conn, upd.c_str());
        PQexec(db.conn, "COMMIT");
        return;
    }

    auto& step = g_steps[stepIdx];
    try {
        Json::Value result = step.execute(context);
        context[step.name] = result;
        logStep(db.conn, sagaId, step.name, "execute", result);

        std::string upd = "UPDATE sagas SET step_index = " + std::to_string(stepIdx + 1)
            + ", context = '" + escapeStr(toJsonString(context))
            + "', updated_at = now() WHERE id = '" + escapeStr(sagaId) + "'";
        PQexec(db.conn, upd.c_str());
        PQexec(db.conn, "COMMIT");

        advance(sagaId);

    } catch (const std::exception& e) {
        Json::Value failResult;
        failResult["error"] = e.what();
        logStep(db.conn, sagaId, step.name, "failed", failResult);

        std::string upd = "UPDATE sagas SET status = 'COMPENSATING', updated_at = now() WHERE id = '"
            + escapeStr(sagaId) + "'";
        PQexec(db.conn, upd.c_str());
        PQexec(db.conn, "COMMIT");

        compensate(sagaId);
    }
}

static void compensate(const std::string& sagaId) {
    PgConn db;
    if (!db.ok()) return;

    PQexec(db.conn, "BEGIN");

    std::string sql = "SELECT status, step_index, context FROM sagas WHERE id = '"
        + escapeStr(sagaId) + "' FOR UPDATE";
    PgResult row(PQexec(db.conn, sql.c_str()));
    if (!row.ok() || row.rows() == 0) { PQexec(db.conn, "ROLLBACK"); return; }

    int stepIdx = std::stoi(row.get(0, 1));
    Json::Value context = parseJson(row.get(0, 2));

    // Compensate completed steps in reverse (step_index is next-to-run, so completed = 0..stepIdx-1)
    for (int i = stepIdx - 1; i >= 0; --i) {
        auto& step = g_steps[i];
        Json::Value result = step.compensate(context);
        logStep(db.conn, sagaId, step.compensationName, "compensate", result);
    }

    std::string upd = "UPDATE sagas SET status = 'COMPENSATED', updated_at = now() WHERE id = '"
        + escapeStr(sagaId) + "'";
    PQexec(db.conn, upd.c_str());
    PQexec(db.conn, "COMMIT");
}

static Json::Value getSaga(const std::string& sagaId) {
    PgConn db;
    if (!db.ok()) return Json::Value::null;

    std::string sql = "SELECT id, status, step_index, context FROM sagas WHERE id = '"
        + escapeStr(sagaId) + "'";
    PgResult row(PQexec(db.conn, sql.c_str()));
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

    std::string sql = "SELECT step, action, result FROM saga_log WHERE saga_id = '"
        + escapeStr(sagaId) + "' ORDER BY id";
    PgResult rows(PQexec(db.conn, sql.c_str()));
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

    PgResult rows(PQexec(db.conn, "SELECT id FROM sagas WHERE status = 'RUNNING'"));
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

            std::string sql = "INSERT INTO sagas (id, status, step_index, context) VALUES ('"
                + escapeStr(sagaId) + "', 'RUNNING', 0, '" + escapeStr(toJsonString(context)) + "')";
            PgResult r(PQexec(db.conn, sql.c_str()));

            advance(sagaId);

            Json::Value saga = getSaga(sagaId);
            auto resp = HttpResponse::newHttpJsonResponse(saga);
            resp->setStatusCode(k201Created);
            callback(resp);
        },
        {Post});

    app().registerHandler("/sagas/{saga_id}",
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback,
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
        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback,
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
