package main

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"sync"
)

type rules struct {
	mu             sync.RWMutex
	VIPThreshold   float64 `json:"vip_threshold"`
	PriorityTopic  string  `json:"priority_topic"`
	DefaultTopic   string  `json:"default_topic"`
}

var routingRules = &rules{
	VIPThreshold:  1000,
	PriorityTopic: "orders.priority",
	DefaultTopic:  "orders.default",
}

func main() {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	mux.HandleFunc("POST /orders", func(w http.ResponseWriter, r *http.Request) {
		var in struct {
			SKU      string  `json:"sku"`
			Quantity int     `json:"quantity"`
			Amount   float64 `json:"amount"`
		}
		json.NewDecoder(r.Body).Decode(&in)

		routingRules.mu.RLock()
		threshold := routingRules.VIPThreshold
		priorityTopic := routingRules.PriorityTopic
		defaultTopic := routingRules.DefaultTopic
		routingRules.mu.RUnlock()

		var topic string
		var vip bool
		if in.Amount >= threshold {
			topic = priorityTopic
			vip = true
			slog.Info("ROUTED", "sku", in.SKU, "amount", in.Amount, "topic", topic, "vip", true)
		} else {
			topic = defaultTopic
			vip = false
			slog.Info("ROUTED", "sku", in.SKU, "amount", in.Amount, "topic", topic)
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]any{
			"routed_to": topic,
			"vip":       vip,
			"amount":    in.Amount,
		})
	})

	mux.HandleFunc("GET /rules", func(w http.ResponseWriter, _ *http.Request) {
		routingRules.mu.RLock()
		defer routingRules.mu.RUnlock()
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"vip_threshold":  routingRules.VIPThreshold,
			"priority_topic": routingRules.PriorityTopic,
			"default_topic":  routingRules.DefaultTopic,
		})
	})

	mux.HandleFunc("PUT /rules", func(w http.ResponseWriter, r *http.Request) {
		var update map[string]any
		json.NewDecoder(r.Body).Decode(&update)

		routingRules.mu.Lock()
		if v, ok := update["vip_threshold"]; ok {
			if f, ok := v.(float64); ok {
				routingRules.VIPThreshold = f
			}
		}
		if v, ok := update["priority_topic"]; ok {
			if s, ok := v.(string); ok {
				routingRules.PriorityTopic = s
			}
		}
		if v, ok := update["default_topic"]; ok {
			if s, ok := v.(string); ok {
				routingRules.DefaultTopic = s
			}
		}
		routingRules.mu.Unlock()

		slog.Info("RULES_UPDATED", "vip_threshold", routingRules.VIPThreshold)

		routingRules.mu.RLock()
		defer routingRules.mu.RUnlock()
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"vip_threshold":  routingRules.VIPThreshold,
			"priority_topic": routingRules.PriorityTopic,
			"default_topic":  routingRules.DefaultTopic,
		})
	})

	slog.Info("starting router-service")
	http.ListenAndServe(":8080", mux)
}
