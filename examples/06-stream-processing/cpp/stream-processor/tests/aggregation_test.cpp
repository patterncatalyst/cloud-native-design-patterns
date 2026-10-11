// Unit tests for the pure stream-processing logic: window math, money rounding, event parsing
// and the per-merchant tumbling windows. Run by ctest in the image build.

#include <cstdio>
#include <cstdlib>
#include <string>

#include "aggregation.hpp"

namespace {
int failures = 0;

void check(bool ok, const char* what, int line) {
    if (!ok) {
        std::fprintf(stderr, "FAIL line %d: %s\n", line, what);
        ++failures;
    }
}
#define CHECK(c) check((c), #c, __LINE__)

std::string m(const std::string& s) {
    auto d = cndp::parse_decimal(s);
    return d ? cndp::money(*d) : "invalid";
}
}  // namespace

int main() {
    using namespace cndp;

    // window math: epoch millis -> start of the tumbling window in epoch seconds
    CHECK(window_start(0, 10) == 0);
    CHECK(window_start(9'999, 10) == 0);
    CHECK(window_start(10'000, 10) == 10);
    CHECK(window_start(1'700'000'123'456, 10) == 1'700'000'120);

    // money: two decimals, HALF_UP (away from zero), no binary floating point
    CHECK(m("10") == "10.00");
    CHECK(m("10.0") == "10.00");
    CHECK(m("2.675") == "2.68");      // a double would print 2.67
    CHECK(m("2.674") == "2.67");
    CHECK(m("0.005") == "0.01");
    CHECK(m("0.004") == "0.00");
    CHECK(m("-2.675") == "-2.68");
    CHECK(m("-0.004") == "0.00");
    CHECK(m("1e2") == "100.00");
    CHECK(m("1.5E-1") == "0.15");
    CHECK(m("123456789012345678.995") == "123456789012345679.00");

    // rejected as totals
    for (const char* bad : {"", "NaN", "Infinity", "true", "0x10", "1e99", "1/2", "--1", "1.2.3", "abc", "1e"})
        CHECK(!parse_decimal(bad));

    // exact sums: 0.1 + 0.2 is exactly 0.3
    {
        auto s = add(*parse_decimal("0.1"), *parse_decimal("0.2"));
        CHECK(s && money(*s) == "0.30");
        auto t = add(*s, *parse_decimal("2.675"));
        CHECK(t && money(*t) == "2.98");
    }

    // 128-bit limits: scaling is checked before it can overflow
    {
        const std::string big35(35, '9');  // 35 nines, scale 0
        auto a = parse_decimal(big35);
        auto frac = parse_decimal("0." + std::string(36, '1'));  // scale 36
        CHECK(a && frac);
        CHECK(!add(*a, *frac));  // aligning 10^35 to scale 36 would overflow 128 bits
        CHECK(!add(*a, *a));     // 2*10^35 is 2*10^37 in cents: over the limit
        auto ok = add(*parse_decimal("1"), *parse_decimal("2"));
        CHECK(ok && money(*ok) == "3.00");
        MerchantWindows w(10);
        CHECK(w.apply(1000000000000, *a).has_value());  // just under the limit: accepted
        CHECK(!w.apply(1000000000000, *a).has_value() && w.overflowed());  // the second one would overflow: skipped, total kept
        auto after = w.apply(1000000000000, *parse_decimal("0.01"));  // still fits: the window keeps working
        CHECK(after && after->count == 2);
    }

    // event parsing, same rules as the Go and Kafka Streams versions
    {
        auto e = parse_order_event(R"({"merchant_id":"merchant-a","total":10.0})");
        CHECK(e && e->merchant == "merchant-a" && e->total_text == "10.0");
        e = parse_order_event(R"({"merchant_id":7,"total":"12.50"})");
        CHECK(e && e->merchant == "7" && e->total_text == "12.50");
        e = parse_order_event(R"({"merchant_id":"m"})");
        CHECK(e && e->total_text == "0");
        e = parse_order_event(R"({"merchant_id":"m","total":null})");
        CHECK(e && e->total_text == "0");
        e = parse_order_event(R"({"merchant_id":"m","total":"abc"})");
        CHECK(e && !parse_decimal(e->total_text));
        e = parse_order_event(R"({"merchant_id":"m","total":{"x":1}})");
        CHECK(e && !parse_decimal(e->total_text));
        CHECK(!parse_order_event(R"({"total":5})"));
        CHECK(!parse_order_event(R"({"merchant_id":null,"total":5})"));
        CHECK(!parse_order_event(R"({"merchant_id":"","total":5})"));
        CHECK(!parse_order_event(R"({"merchant_id":{"a":1},"total":5})"));
        CHECK(!parse_order_event("not json"));
        CHECK(!parse_order_event("[1,2]"));
        // a nested merchant_id/total does not count
        e = parse_order_event(R"({"x":{"merchant_id":"no","total":1},"merchant_id":"yes","total":2})");
        CHECK(e && e->merchant == "yes" && e->total_text == "2");
    }

    // tumbling windows, no grace
    {
        MerchantWindows w(10);
        auto one = *parse_decimal("10.00");
        auto u1 = w.apply(1'000'000'000'000, one);              // window 1'000'000'000
        CHECK(u1 && u1->start == 1'000'000'000 && u1->end == 1'000'000'010 && u1->count == 1);
        auto u2 = w.apply(1'000'000'005'000, *parse_decimal("2.675"));
        CHECK(u2 && u2->count == 2 && money(u2->total) == "12.68");
        auto u3 = w.apply(1'000'000'012'000, one);              // next window; first one closes
        CHECK(u3 && u3->start == 1'000'000'010 && u3->count == 1);
        CHECK(w.open_windows() == 1);
        CHECK(!w.apply(1'000'000'003'000, one));                 // late: dropped, no grace
        auto u4 = w.apply(1'000'000'019'999, one);
        CHECK(u4 && u4->count == 2 && money(u4->total) == "20.00");
        // output body: exactly two decimals, merchant escaped
        CHECK(revenue_json("m\"x", *u4) ==
              R"({"window_start":1000000010,"window_end":1000000020,"merchant_id":"m\"x","order_count":2,"revenue":20.00})");
    }

    if (failures) {
        std::fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    std::puts("aggregation_test: all checks passed");
    return 0;
}
