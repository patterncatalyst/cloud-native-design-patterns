// Unit tests for the sandboxed Lua routing engine: routing, bad scripts, sandbox escapes,
// execution limits and concurrent use.
#include <atomic>
#include <chrono>
#include <cstdio>
#include <string>
#include <thread>
#include <vector>

#include "routing_engine.hpp"

using cndp::routing::Decision;
using cndp::routing::Limits;
using cndp::routing::RoutingEngine;
using cndp::routing::Rules;

namespace {
int failures = 0;
void check(bool ok, const char* what) {
    std::printf("%s %s\n", ok ? "ok  " : "FAIL", what);
    if (!ok) ++failures;
}

const char* kDefault = R"(
function route(order, rules)
  if order.amount >= rules.vip_threshold then return rules.priority_topic, true end
  return rules.default_topic, false
end)";

template <class F>
bool throws(F&& f) {
    try { f(); } catch (const std::exception&) { return true; }
    return false;
}

// A script whose route() tries to run `body`; it must fail (error), never succeed.
bool escape_blocked(const std::string& body) {
    RoutingEngine e("function route(o, r) " + body + " return 'x', false end");
    return throws([&] { e.route("s", 1, 1, Rules{}); });
}
}  // namespace

int main() {
    Rules rules;
    {
        RoutingEngine e(kDefault);
        auto d = e.route("diamond", 1, 2500, rules);
        check(d.topic == "orders.priority" && d.vip, "VIP order goes to the priority topic");
        d = e.route("widget", 3, 50, rules);
        check(d.topic == "orders.default" && !d.vip, "ordinary order goes to the default topic");
        rules.vip_threshold = 500;
        d = e.route("gadget", 1, 750, rules);
        check(d.topic == "orders.priority", "lowered threshold is applied");
    }
    check(throws([] { RoutingEngine("function route(("); }), "syntax error rejected at startup");
    check(throws([] { RoutingEngine("x = 1"); }), "script without route() rejected");
    {
        RoutingEngine e("function route(o, r) return 1, true end");
        check(throws([&] { e.route("x", 1, 1, Rules{}); }), "non-string topic rejected");
    }

    // Sandbox: nothing that reaches the host is reachable.
    check(escape_blocked("os.execute('true')"), "os.execute blocked");
    check(escape_blocked("io.open('/etc/passwd')"), "io.open blocked");
    check(escape_blocked("load('return 1')()"), "load blocked");
    check(escape_blocked("require('os')"), "require blocked");
    check(escape_blocked("dofile('/etc/passwd')"), "dofile blocked");
    check(escape_blocked("loadfile('/etc/passwd')"), "loadfile blocked");
    check(escape_blocked("debug.getinfo(1)"), "debug blocked");
    check(escape_blocked("package.loadlib('x','y')"), "package blocked");
    check(escape_blocked("string.dump(function() end)"), "string.dump blocked");
    check(escape_blocked("print('x')"), "print blocked");

    check(escape_blocked("pcall(error, 'x')"), "pcall removed");
    check(escape_blocked("xpcall(error, print, 'x')"), "xpcall removed");
    check(escape_blocked("collectgarbage()"), "collectgarbage blocked");
    check(escape_blocked("setmetatable('', {})"), "setmetatable on a string rejected");
    check(escape_blocked("local d = ('x'):dump()"), "string.dump via method blocked");
    check(escape_blocked("string.gsub('a', 'a', 'b')"), "string.gsub removed");
    check(escape_blocked("string.match('a', 'a')"), "string.match removed");
    check(escape_blocked("string.gmatch('a', 'a')()"), "string.gmatch removed");
    check(escape_blocked("string.find('a', 'a')"), "string.find with patterns rejected");
    {
        RoutingEngine e("function route(o, r) local i = string.find(o.sku, '-', 1, true) "
                        "return i and 'dash' or 'plain', false end");
        check(e.route("a-b", 1, 1, Rules{}).topic == "dash", "string.find plain=true works");
    }

    // Limits.
    {
        // pcall used to swallow the hook's error and loop forever.
        Limits lim;
        lim.instructions = 1'000'000;
        lim.wall = std::chrono::milliseconds(50);
        RoutingEngine e("function route(o, r) while true do pcall(function() while true do end end) end end", lim);
        auto t0 = std::chrono::steady_clock::now();
        bool failed = throws([&] { e.route("x", 1, 1, Rules{}); });
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
        check(failed && ms < 2000, "pcall loop attack fails quickly");
    }
    {
        // Backtracking pattern on a long subject: unavailable, so it fails at once.
        Limits lim;
        lim.wall = std::chrono::milliseconds(50);
        RoutingEngine e("function route(o, r) local s = string.rep('a', 5000) "
                        "return tostring(s:find('a*a*a*a*a*a*b')), false end", lim);
        auto t0 = std::chrono::steady_clock::now();
        bool failed = throws([&] { e.route("x", 1, 1, Rules{}); });
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
        check(failed && ms < 2000, "backtracking pattern attack fails quickly");
    }
    {
        RoutingEngine e(kDefault);
        check(throws([&] { e.route(std::string(10'000, 'x'), 1, 1, Rules{}); }), "oversized sku rejected");
    }
    {
        Limits lim;
        lim.wall = std::chrono::milliseconds(10'000);
        lim.instructions = 200'000;
        RoutingEngine e("function route(o, r) local n = 0 while true do n = n + 1 end end", lim);
        check(throws([&] { e.route("x", 1, 1, Rules{}); }), "instruction limit trips");
    }
    {
        Limits lim;
        lim.instructions = ~std::uint64_t{0} >> 1;
        lim.wall = std::chrono::milliseconds(50);
        RoutingEngine e("function route(o, r) while true do end end", lim);
        auto t0 = std::chrono::steady_clock::now();
        bool tripped = throws([&] { e.route("x", 1, 1, Rules{}); });
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
        check(tripped && ms < 2000, "wall-clock limit trips quickly");
    }
    {
        RoutingEngine e("function route(o, r) local s = string.rep('x', 1 << 28) return s, false end");
        check(throws([&] { e.route("x", 1, 1, Rules{}); }), "memory cap trips");
    }

    // State safety: globals set by one call are not visible to the next.
    {
        RoutingEngine e("count = (count or 0) + 1 function route(o, r) count = count + 1 "
                        "return tostring(count), false end");
        auto a = e.route("x", 1, 1, Rules{});
        auto b = e.route("x", 1, 1, Rules{});
        check(a.topic == "2" && b.topic == "2", "no state leaks between calls");
    }

    // Concurrency: many threads route at once and every answer is right.
    {
        RoutingEngine e(kDefault);
        std::atomic<int> bad{0};
        std::vector<std::thread> ts;
        for (int t = 0; t < 16; ++t) {
            ts.emplace_back([&, t] {
                for (int i = 0; i < 200; ++i) {
                    double amount = (t * 200 + i) % 2 ? 2000 : 10;
                    auto d = e.route("s", 1, amount, Rules{});
                    if (d.vip != (amount >= 1000)) ++bad;
                }
            });
        }
        for (auto& th : ts) th.join();
        check(bad == 0, "concurrent routing is correct");
    }
    return failures == 0 ? 0 : 1;
}
