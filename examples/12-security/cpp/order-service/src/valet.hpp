// valet.hpp — valet keys as HS256 JWTs (jwt-cpp).
//
// A valet key is a signed, time-bound token scoped to one resource and one operation:
//   claims  res, op, iss="order-service", iat, exp (epoch seconds)
// Verification pins the algorithm to HS256, so a token signed with another algorithm
// (including "none") is rejected before any claim is looked at.

#pragma once

#include <chrono>
#include <cstdint>
#include <string>

#include <jwt-cpp/traits/nlohmann-json/defaults.h>

namespace cndp::valet {

struct Minted {
    std::string token;
    std::int64_t expires;  // epoch seconds, the exp claim
};

inline constexpr const char* kIssuer = "order-service";

inline Minted mint(const std::string& secret, const std::string& resource,
                   const std::string& operation,
                   std::chrono::seconds ttl = std::chrono::minutes(5)) {
    const auto now = std::chrono::system_clock::now();
    const auto exp = std::chrono::time_point_cast<std::chrono::seconds>(now + ttl);
    auto token = jwt::create()
                     .set_type("JWT")
                     .set_issuer(kIssuer)
                     .set_issued_at(now)
                     .set_expires_at(exp)
                     .set_payload_claim("res", jwt::claim(resource))
                     .set_payload_claim("op", jwt::claim(operation))
                     .sign(jwt::algorithm::hs256{secret});
    return {std::move(token), exp.time_since_epoch().count()};
}

// True only for an unexpired HS256 token minted for exactly this resource, operation and expiry.
inline bool verify(const std::string& secret, const std::string& resource,
                   const std::string& operation, std::int64_t expires,
                   const std::string& token) noexcept {
    try {
        const auto decoded = jwt::decode(token);
        // Pin the algorithm: the verifier below is HS256-only, and this rejects the
        // header up front so that "none" or RS256 tokens never reach it.
        if (decoded.get_algorithm() != "HS256") return false;
        auto verifier = jwt::verify()
                            .allow_algorithm(jwt::algorithm::hs256{secret})
                            .with_issuer(kIssuer)
                            .with_claim("res", jwt::claim(resource))
                            .with_claim("op", jwt::claim(operation));
        verifier.verify(decoded);  // signature + exp (leeway 0) + claims; throws on failure
        if (!decoded.has_expires_at()) return false;
        const auto exp = std::chrono::time_point_cast<std::chrono::seconds>(decoded.get_expires_at());
        return exp.time_since_epoch().count() == expires;
    } catch (...) {
        return false;
    }
}

}  // namespace cndp::valet
