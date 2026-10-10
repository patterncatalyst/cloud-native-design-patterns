package main

import (
	"context"
	_ "embed"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	lua "github.com/yuin/gopher-lua"
)

//go:embed routing.lua
var defaultScript string

// rules are the tunable inputs of the routing policy. The policy itself is the Lua script.
type rules struct {
	mu            sync.RWMutex
	VIPThreshold  float64
	PriorityTopic string
	DefaultTopic  string
}

func (r *rules) snapshot() map[string]any {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return map[string]any{
		"vip_threshold":  r.VIPThreshold,
		"priority_topic": r.PriorityTopic,
		"default_topic":  r.DefaultTopic,
	}
}

var routingRules = &rules{
	VIPThreshold:  1000,
	PriorityTopic: "orders.priority",
	DefaultTopic:  "orders.default",
}

// engine runs the Lua policy. A lua.LState is not safe for concurrent use, so each request
// borrows one from a pool; the script is compiled once and loaded into every new state.
type engine struct {
	proto *lua.FunctionProto
	pool  sync.Pool
}

func newEngine(script string) (*engine, error) {
	// Compile once up front so a syntax error stops the service at startup.
	proto, err := compile(script)
	if err != nil {
		return nil, err
	}
	e := &engine{proto: proto}
	e.pool.New = func() any {
		L := lua.NewState(lua.Options{SkipOpenLibs: true})
		// A rules script gets arithmetic, tables and strings, and nothing that touches the
		// host: no io, os, debug, package or dofile.
		for _, lib := range []struct {
			name string
			fn   lua.LGFunction
		}{
			{lua.BaseLibName, lua.OpenBase},
			{lua.TabLibName, lua.OpenTable},
			{lua.StringLibName, lua.OpenString},
			{lua.MathLibName, lua.OpenMath},
		} {
			L.Push(L.NewFunction(lib.fn))
			L.Push(lua.LString(lib.name))
			L.Call(1, 0)
		}
		for _, unsafe := range []string{"dofile", "loadfile", "load", "loadstring", "require"} {
			L.SetGlobal(unsafe, lua.LNil)
		}
		fn := L.NewFunctionFromProto(e.proto)
		L.Push(fn)
		if err := L.PCall(0, lua.MultRet, nil); err != nil {
			slog.Error("rules script failed to load", "err", err)
		}
		return L
	}
	return e, nil
}

func compile(script string) (*lua.FunctionProto, error) {
	L := lua.NewState(lua.Options{SkipOpenLibs: true})
	defer L.Close()
	fn, err := L.LoadString(script)
	if err != nil {
		return nil, err
	}
	return fn.Proto, nil
}

// scriptTimeout bounds one rule evaluation.
const scriptTimeout = 100 * time.Millisecond

// route calls route(order, rules) in Lua and returns the topic and the VIP flag.
func (e *engine) route(ctx context.Context, sku string, quantity int, amount float64, r map[string]any) (string, bool, error) {
	// A runaway script is cancelled when the budget runs out, so it cannot hang the request.
	ctx, cancel := context.WithTimeout(ctx, scriptTimeout)
	defer cancel()
	L := e.pool.Get().(*lua.LState)
	L.SetContext(ctx)
	failed := true
	defer func() {
		if failed {
			L.Close() // a state that was interrupted mid-call is not reused
			return
		}
		L.SetContext(context.Background())
		e.pool.Put(L)
	}()

	order := L.NewTable()
	order.RawSetString("sku", lua.LString(sku))
	order.RawSetString("quantity", lua.LNumber(quantity))
	order.RawSetString("amount", lua.LNumber(amount))
	cfg := L.NewTable()
	cfg.RawSetString("vip_threshold", lua.LNumber(r["vip_threshold"].(float64)))
	cfg.RawSetString("priority_topic", lua.LString(r["priority_topic"].(string)))
	cfg.RawSetString("default_topic", lua.LString(r["default_topic"].(string)))

	if err := L.CallByParam(lua.P{Fn: L.GetGlobal("route"), NRet: 2, Protect: true}, order, cfg); err != nil {
		return "", false, err
	}
	vip := lua.LVAsBool(L.Get(-1))
	topic, ok := L.Get(-2).(lua.LString)
	L.Pop(2)
	failed = false
	if !ok {
		return "", false, errors.New("route() must return a topic string")
	}
	return string(topic), vip, nil
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
	defer stop()

	script := defaultScript
	if path := os.Getenv("ROUTING_RULES_FILE"); path != "" {
		b, err := os.ReadFile(path)
		if err != nil {
			slog.Error("cannot read rules file", "path", path, "err", err)
			os.Exit(1)
		}
		script = string(b)
	}
	eng, err := newEngine(script)
	if err != nil {
		slog.Error("invalid rules script", "err", err)
		os.Exit(1)
	}

	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})

	mux.HandleFunc("POST /orders", func(w http.ResponseWriter, r *http.Request) {
		var in struct {
			SKU      string  `json:"sku"`
			Quantity int     `json:"quantity"`
			Amount   float64 `json:"amount"`
		}
		json.NewDecoder(r.Body).Decode(&in)

		topic, vip, err := eng.route(r.Context(), in.SKU, in.Quantity, in.Amount, routingRules.snapshot())
		if err != nil {
			slog.Error("rule evaluation failed", "err", err)
			writeJSON(w, http.StatusInternalServerError, map[string]string{"detail": "rule evaluation failed"})
			return
		}
		if vip {
			slog.Info("ROUTED", "sku", in.SKU, "amount", in.Amount, "topic", topic, "vip", true)
		} else {
			slog.Info("ROUTED", "sku", in.SKU, "amount", in.Amount, "topic", topic)
		}
		writeJSON(w, http.StatusCreated, map[string]any{"routed_to": topic, "vip": vip, "amount": in.Amount})
	})

	mux.HandleFunc("GET /rules", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, routingRules.snapshot())
	})

	mux.HandleFunc("PUT /rules", func(w http.ResponseWriter, r *http.Request) {
		var update map[string]any
		json.NewDecoder(r.Body).Decode(&update)

		routingRules.mu.Lock()
		if f, ok := update["vip_threshold"].(float64); ok {
			routingRules.VIPThreshold = f
		}
		if s, ok := update["priority_topic"].(string); ok {
			routingRules.PriorityTopic = s
		}
		if s, ok := update["default_topic"].(string); ok {
			routingRules.DefaultTopic = s
		}
		threshold := routingRules.VIPThreshold
		routingRules.mu.Unlock()

		slog.Info("RULES_UPDATED", "vip_threshold", threshold)
		writeJSON(w, http.StatusOK, routingRules.snapshot())
	})

	srv := &http.Server{Addr: ":8080", Handler: mux}
	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		srv.Shutdown(shutdownCtx)
	}()

	slog.Info(fmt.Sprintf("starting router-service (rules engine: %s)", lua.PackageName+" "+lua.LuaVersion))
	if err := srv.ListenAndServe(); err != http.ErrServerClosed {
		slog.Error("server error", "err", err)
		os.Exit(1)
	}
}
