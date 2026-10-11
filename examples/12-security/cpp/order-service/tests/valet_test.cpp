// Unit tests for the valet key (JWT) helpers: no framework, plain checks and an exit code.
#include <cstdio>
#include <string>

#include "valet.hpp"

namespace {
int failures = 0;
void check(bool ok, const char* what) {
    std::printf("%s %s\n", ok ? "ok  " : "FAIL", what);
    if (!ok) ++failures;
}
}  // namespace

int main() {
    using namespace cndp::valet;
    const std::string secret = "test-secret";

    auto m = mint(secret, "exports/report.csv", "GET");
    check(verify(secret, "exports/report.csv", "GET", m.expires, m.token), "round trip");
    check(!verify(secret, "exports/report.csv", "DELETE", m.expires, m.token), "operation mismatch");
    check(!verify(secret, "other", "GET", m.expires, m.token), "resource mismatch");
    check(!verify(secret, "exports/report.csv", "GET", 9999999999, m.token), "expiry mismatch");
    check(!verify(secret, "exports/report.csv", "GET", m.expires, "tampered"), "garbage token");
    check(!verify("other-secret", "exports/report.csv", "GET", m.expires, m.token), "wrong key");

    // Wrong algorithm. Every token below carries identical claims (issuer, res, op, iat and the
    // same exp), so the algorithm is the only thing that differs. The HS256 control proves the
    // claims themselves are acceptable; HS512 and alg=none must then be rejected for the
    // algorithm alone.
    const auto now = std::chrono::system_clock::now();
    const auto exp_tp = std::chrono::time_point_cast<std::chrono::seconds>(now + std::chrono::minutes(5));
    const std::int64_t exp_s = exp_tp.time_since_epoch().count();
    auto with_claims = [&](auto&& alg) {
        return jwt::create()
            .set_type("JWT")
            .set_issuer(kIssuer)
            .set_issued_at(now)
            .set_expires_at(exp_tp)
            .set_payload_claim("res", jwt::claim(std::string("r")))
            .set_payload_claim("op", jwt::claim(std::string("GET")))
            .sign(alg);
    };
    check(verify(secret, "r", "GET", exp_s, with_claims(jwt::algorithm::hs256{secret})),
          "control: same claims signed HS256 verify");
    check(!verify(secret, "r", "GET", exp_s, with_claims(jwt::algorithm::hs512{secret})),
          "HS512 token rejected");
    check(!verify(secret, "r", "GET", exp_s, with_claims(jwt::algorithm::none{})),
          "alg=none token rejected");

    // Expired: minted with a negative ttl.
    auto old = mint(secret, "r", "GET", std::chrono::seconds(-60));
    check(!verify(secret, "r", "GET", old.expires, old.token), "expired token");

    return failures == 0 ? 0 : 1;
}
