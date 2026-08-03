package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/twmb/franz-go/pkg/kgo"
)

var (
	legacyURL string
	rdb       *redis.Client
	producer  *kgo.Client
	client    = &http.Client{Timeout: 5 * time.Second}
	events    []map[string]any
	eventsMu  sync.Mutex
)

func main() {
	legacyURL = os.Getenv("LEGACY_URL")
	if legacyURL == "" {
		legacyURL = "http://legacy:8080"
	}

	opt, _ := redis.ParseURL(os.Getenv("REDIS_URL"))
	rdb = redis.NewClient(opt)

	bootstrap := os.Getenv("KAFKA_BOOTSTRAP")
	if bootstrap == "" {
		bootstrap = "kafka:9094"
	}
	var err error
	producer, err = kgo.NewClient(kgo.SeedBrokers(bootstrap), kgo.AllowAutoTopicCreation())
	if err != nil {
		slog.Error("kafka init failed", "err", err)
		os.Exit(1)
	}
	defer producer.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /orders", handleCreateOrder)
	mux.HandleFunc("GET /orders/{id}", handleGetOrder)
	mux.HandleFunc("GET /events", handleEvents)

	slog.Info("starting decorator on :8080")
	http.ListenAndServe(":8080", mux)
}

func handleCreateOrder(w http.ResponseWriter, r *http.Request) {
	body, _ := io.ReadAll(r.Body)
	resp, err := client.Post(legacyURL+"/orders", "application/json", bytes.NewReader(body))
	if err != nil {
		http.Error(w, "legacy error", 502)
		return
	}
	defer resp.Body.Close()
	respBody, _ := io.ReadAll(resp.Body)

	var order map[string]any
	json.Unmarshal(respBody, &order)

	orderID, _ := order["id"].(string)
	event := map[string]any{
		"event_type": "order.placed",
		"order_id":   orderID,
		"timestamp":  time.Now().UTC().Format(time.RFC3339),
	}
	eventData, _ := json.Marshal(event)

	rec := &kgo.Record{Topic: "order.placed", Key: []byte(orderID), Value: eventData}
	for attempt := range 5 {
		results := producer.ProduceSync(r.Context(), rec)
		if err := results.FirstErr(); err != nil {
			slog.Warn("kafka produce retry", "attempt", attempt+1, "err", err)
			time.Sleep(time.Duration(attempt+1) * 500 * time.Millisecond)
			continue
		}
		break
	}
	slog.Info("EVENT order.placed", "order_id", orderID)

	eventsMu.Lock()
	events = append(events, event)
	eventsMu.Unlock()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	w.Write(respBody)
}

func handleGetOrder(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	key := "order:" + id

	val, err := rdb.Get(r.Context(), key).Result()
	if err == nil {
		slog.Info("CACHE_HIT", "id", id)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, val)
		return
	}

	slog.Info("CACHE_MISS", "id", id)
	resp, err := client.Get(legacyURL + "/orders/" + id)
	if err != nil {
		http.Error(w, "legacy error", 502)
		return
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)

	rdb.Set(r.Context(), key, string(body), 60*time.Second)

	w.Header().Set("Content-Type", "application/json")
	w.Write(body)
}

func handleEvents(w http.ResponseWriter, _ *http.Request) {
	eventsMu.Lock()
	defer eventsMu.Unlock()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(events)
}
