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

    // Wrong algorithm: same claims signed HS512 with the right secret.
    auto hs512 = jwt::create()
                     .set_issuer(kIssuer)
                     .set_expires_at(std::chrono::system_clock::now() + std::chrono::minutes(5))
                     .set_payload_claim("res", jwt::claim(std::string("r")))
                     .set_payload_claim("op", jwt::claim(std::string("GET")))
                     .sign(jwt::algorithm::hs512{secret});
    auto exp = jwt::decode(hs512).get_expires_at().time_since_epoch();
    check(!verify(secret, "r", "GET",
                  std::chrono::duration_cast<std::chrono::seconds>(exp).count(), hs512),
          "HS512 token rejected");

    // alg=none: unsigned token with valid-looking claims.
    auto none = jwt::create()
                    .set_issuer(kIssuer)
                    .set_expires_at(std::chrono::system_clock::now() + std::chrono::minutes(5))
                    .set_payload_claim("res", jwt::claim(std::string("r")))
                    .set_payload_claim("op", jwt::claim(std::string("GET")))
                    .sign(jwt::algorithm::none{});
    check(!verify(secret, "r", "GET",
                  std::chrono::duration_cast<std::chrono::seconds>(exp).count(), none),
          "alg=none token rejected");

    // Expired: minted with a negative ttl.
    auto old = mint(secret, "r", "GET", std::chrono::seconds(-60));
    check(!verify(secret, "r", "GET", old.expires, old.token), "expired token");

    return failures == 0 ? 0 : 1;
}
