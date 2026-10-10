package main

import (
	"context"
	"sync"
	"testing"
	"time"
)

func TestRoute(t *testing.T) {
	e, err := newEngine(defaultScript)
	if err != nil {
		t.Fatal(err)
	}
	cfg := routingRules.snapshot()
	topic, vip, err := e.route(context.Background(), "diamond", 1, 2500, cfg)
	if err != nil || topic != "orders.priority" || !vip {
		t.Fatalf("vip: %s %v %v", topic, vip, err)
	}
	topic, vip, err = e.route(context.Background(), "widget", 3, 50, cfg)
	if err != nil || topic != "orders.default" || vip {
		t.Fatalf("default: %s %v %v", topic, vip, err)
	}
	cfg["vip_threshold"] = 500.0
	if topic, _, _ = e.route(context.Background(), "gadget", 1, 750, cfg); topic != "orders.priority" {
		t.Fatalf("lowered threshold not applied: %s", topic)
	}
}

func TestBadScripts(t *testing.T) {
	if _, err := newEngine("function route(("); err == nil {
		t.Fatal("syntax error accepted")
	}
	e, _ := newEngine("function route(o, r) return 1, true end")
	if _, _, err := e.route(context.Background(), "x", 1, 1, routingRules.snapshot()); err == nil {
		t.Fatal("non-string topic accepted")
	}
}

func TestConcurrent(t *testing.T) {
	e, _ := newEngine(defaultScript)
	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			if _, _, err := e.route(context.Background(), "s", 1, float64(i*100), routingRules.snapshot()); err != nil {
				t.Error(err)
			}
		}(i)
	}
	wg.Wait()
}

func TestRunawayScriptTimesOut(t *testing.T) {
	e, err := newEngine("function route(o, r) while true do end end")
	if err != nil {
		t.Fatal(err)
	}
	start := time.Now()
	if _, _, err := e.route(context.Background(), "x", 1, 1, routingRules.snapshot()); err == nil {
		t.Fatal("runaway script returned without error")
	}
	if d := time.Since(start); d > 2*time.Second {
		t.Fatalf("timeout not enforced: %v", d)
	}
}
