// routing_engine.hpp — the Lua routing policy, run with sol2 in a sandbox.
//
//  * Libraries: base, table, string and math only. dofile, loadfile, load, loadstring,
//    require, print, collectgarbage and string.dump are removed; io, os, debug and package
//    are never opened.
//  * State safety: a lua_State is not thread-safe and scripts may keep globals, so every
//    call builds a fresh state, loads the script into it and throws it away. Nothing is
//    shared between concurrent requests or leaks from one request to the next.
//  * Limits per call: an instruction budget and a wall-clock deadline (both checked by a
//    count hook every 1000 VM instructions) and a memory cap in the allocator. A runaway
//    script ends in an error; the request fails with 500 and the service keeps serving.

#pragma once

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <stdexcept>
#include <string>
#include <utility>

#define SOL_ALL_SAFETIES_ON 1
#include <sol/sol.hpp>

namespace cndp::routing {

struct Rules {
    double vip_threshold = 1000;
    std::string priority_topic = "orders.priority";
    std::string default_topic = "orders.default";
};

struct Decision {
    std::string topic;
    bool vip = false;
};

struct Limits {
    std::chrono::milliseconds wall{100};
    std::uint64_t instructions = 5'000'000;
    std::size_t memory_bytes = 8u * 1024 * 1024;
};

class RoutingEngine {
public:
    // Loads the script once in a throwaway sandbox so a syntax error, a runtime error at
    // load time or a missing route() function stops the service at startup.
    explicit RoutingEngine(std::string script, Limits limits = {})
        : script_(std::move(script)), limits_(limits) {
        Sandbox box(limits_);
        box.load(script_);
        if (!box.has_route()) throw std::runtime_error("rules script must define route(order, rules)");
    }

    Decision route(const std::string& sku, int quantity, double amount, const Rules& rules) const {
        Sandbox box(limits_);
        box.load(script_);
        return box.call_route(sku, quantity, amount, rules);
    }

private:
    struct Mem {
        std::size_t used = 0;
        std::size_t limit = 0;
    };

    struct Budget {
        std::uint64_t remaining = 0;
        std::chrono::steady_clock::time_point deadline;
    };

    static void* alloc(void* ud, void* ptr, std::size_t osize, std::size_t nsize) {
        auto* m = static_cast<Mem*>(ud);
        const std::size_t old = ptr ? osize : 0;  // osize is a type tag when ptr is null
        if (nsize == 0) {
            std::free(ptr);
            m->used -= old;
            return nullptr;
        }
        if (nsize > old && m->used - old + nsize > m->limit) return nullptr;  // over the cap
        void* p = std::realloc(ptr, nsize);
        if (p) m->used = m->used - old + nsize;
        return p;
    }

    static constexpr int kHookEvery = 1000;

    static void hook(lua_State* L, lua_Debug*) {
        auto* b = *static_cast<Budget**>(lua_getextraspace(L));
        if (b->remaining <= kHookEvery) luaL_error(L, "instruction limit exceeded");
        b->remaining -= kHookEvery;
        if (std::chrono::steady_clock::now() > b->deadline) luaL_error(L, "time limit exceeded");
    }

    class Sandbox {
    public:
        explicit Sandbox(const Limits& lim) {
            mem_.limit = lim.memory_bytes;
            budget_.remaining = lim.instructions;
            budget_.deadline = std::chrono::steady_clock::now() + lim.wall;
            L_ = lua_newstate(&RoutingEngine::alloc, &mem_);
            if (!L_) throw std::runtime_error("cannot create Lua state");
            *static_cast<Budget**>(lua_getextraspace(L_)) = &budget_;
            lua_sethook(L_, &RoutingEngine::hook, LUA_MASKCOUNT, kHookEvery);
            sol::state_view lua(L_);
            lua.open_libraries(sol::lib::base, sol::lib::table, sol::lib::string, sol::lib::math);
            for (const char* name : {"dofile", "loadfile", "load", "loadstring", "require", "print",
                                     "collectgarbage"}) {
                lua[name] = sol::lua_nil;
            }
            lua["string"]["dump"] = sol::lua_nil;
        }
        ~Sandbox() { lua_close(L_); }
        Sandbox(const Sandbox&) = delete;
        Sandbox& operator=(const Sandbox&) = delete;

        void load(const std::string& script) {
            sol::state_view lua(L_);
            auto r = lua.safe_script(script, sol::script_pass_on_error, "routing.lua");
            if (!r.valid()) {
                sol::error e = r;
                throw std::runtime_error(std::string("rules script failed to load: ") + e.what());
            }
        }

        bool has_route() {
            sol::state_view lua(L_);
            return lua["route"].get_type() == sol::type::function;
        }

        Decision call_route(const std::string& sku, int quantity, double amount, const Rules& rules) {
            sol::state_view lua(L_);
            sol::protected_function fn = lua["route"];
            if (!fn.valid()) throw std::runtime_error("rules script must define route(order, rules)");
            sol::table order = lua.create_table();
            order["sku"] = sku;
            order["quantity"] = quantity;
            order["amount"] = amount;
            sol::table cfg = lua.create_table();
            cfg["vip_threshold"] = rules.vip_threshold;
            cfg["priority_topic"] = rules.priority_topic;
            cfg["default_topic"] = rules.default_topic;

            sol::protected_function_result res = fn(order, cfg);
            if (!res.valid()) {
                sol::error e = res;
                throw std::runtime_error(std::string("rule evaluation failed: ") + e.what());
            }
            if (res.get_type(0) != sol::type::string)
                throw std::runtime_error("route() must return a topic string");
            return {res.get<std::string>(0), res.get<bool>(1)};
        }

    private:
        Mem mem_;
        Budget budget_;
        lua_State* L_ = nullptr;
    };

    std::string script_;
    Limits limits_;
};

}  // namespace cndp::routing
