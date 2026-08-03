package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

const cacheTTL = 60 * time.Second

var (
	pool *pgxpool.Pool
	rdb  *redis.Client
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	var err error
	pool, err = pgxpool.New(ctx, os.Getenv("DATABASE_URL"))
	if err != nil {
		slog.Error("db connect failed", "err", err)
		os.Exit(1)
	}
	defer pool.Close()

	opt, err := redis.ParseURL(os.Getenv("REDIS_URL"))
	if err != nil {
		slog.Error("redis URL parse failed", "err", err)
		os.Exit(1)
	}
	rdb = redis.NewClient(opt)
	defer rdb.Close()

	go flusher(ctx)
	go refresher(ctx)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", handleHealthz)
	mux.HandleFunc("GET /cache-aside/products/{id}", handleCacheAsideGet)
	mux.HandleFunc("PUT /cache-aside/products/{id}", handleCacheAsidePut)
	mux.HandleFunc("GET /read-through/products/{id}", handleReadThroughGet)
	mux.HandleFunc("GET /write-through/products/{id}", handleWriteThroughGet)
	mux.HandleFunc("PUT /write-through/products/{id}", handleWriteThroughPut)
	mux.HandleFunc("POST /write-around/events", handleWriteAroundPost)
	mux.HandleFunc("GET /write-around/events/{id}", handleWriteAroundGet)
	mux.HandleFunc("PUT /write-back/metrics/{id}", handleWriteBackPut)
	mux.HandleFunc("GET /write-back/metrics/{id}", handleWriteBackGet)
	mux.HandleFunc("GET /write-back/flush-status", handleFlushStatus)
	mux.HandleFunc("GET /refresh-ahead/products/{id}", handleRefreshAheadGet)
	mux.HandleFunc("GET /cache-keys", handleCacheKeys)

	srv := &http.Server{Addr: ":8080", Handler: mux}
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGTERM, syscall.SIGINT)
		<-sigCh
		slog.Info("shutting down")
		cancel()
		srv.Shutdown(context.Background())
	}()

	slog.Info("starting cache-service")
	if err := srv.ListenAndServe(); err != http.ErrServerClosed {
		slog.Error("server error", "err", err)
	}
}

func safeGet(ctx context.Context, key string) (string, bool) {
	val, err := rdb.Get(ctx, key).Result()
	if err == redis.Nil {
		return "", false
	}
	if err != nil {
		return "", false
	}
	return val, true
}

func safeSet(ctx context.Context, key, val string, ttl time.Duration) {
	rdb.Set(ctx, key, val, ttl)
}

func safeDel(ctx context.Context, key string) {
	rdb.Del(ctx, key)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func loadProduct(ctx context.Context, id string) map[string]any {
	var name string
	var priceCents int
	err := pool.QueryRow(ctx,
		"SELECT name, price_cents FROM products WHERE id=$1", id).Scan(&name, &priceCents)
	if err != nil {
		return nil
	}
	return map[string]any{"id": id, "name": name, "price_cents": priceCents}
}

func handleHealthz(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, 200, map[string]string{"status": "ok"})
}

func handleCacheAsideGet(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	key := "ca:product:" + id

	if val, ok := safeGet(r.Context(), key); ok {
		var p map[string]any
		json.Unmarshal([]byte(val), &p)
		p["source"] = "cache"
		writeJSON(w, 200, p)
		return
	}

	p := loadProduct(r.Context(), id)
	if p == nil {
		http.Error(w, "not found", 404)
		return
	}
	data, _ := json.Marshal(p)
	safeSet(r.Context(), key, string(data), cacheTTL)
	p["source"] = "db"
	writeJSON(w, 200, p)
}

func handleCacheAsidePut(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	var in struct {
		Name       string `json:"name"`
		PriceCents int    `json:"price_cents"`
	}
	json.NewDecoder(r.Body).Decode(&in)

	pool.Exec(r.Context(),
		"UPDATE products SET name=$1, price_cents=$2 WHERE id=$3",
		in.Name, in.PriceCents, id)
	safeDel(r.Context(), "ca:product:"+id)
	writeJSON(w, 200, map[string]any{"id": id, "name": in.Name, "price_cents": in.PriceCents})
}

func handleReadThroughGet(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	key := "rt:product:" + id

	if val, ok := safeGet(r.Context(), key); ok {
		var p map[string]any
		json.Unmarshal([]byte(val), &p)
		p["source"] = "cache"
		writeJSON(w, 200, p)
		return
	}

	p := loadProduct(r.Context(), id)
	if p == nil {
		http.Error(w, "not found", 404)
		return
	}
	data, _ := json.Marshal(p)
	safeSet(r.Context(), key, string(data), cacheTTL)
	p["source"] = "db"
	writeJSON(w, 200, p)
}

func handleWriteThroughPut(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	var in struct {
		Name       string `json:"name"`
		PriceCents int    `json:"price_cents"`
	}
	json.NewDecoder(r.Body).Decode(&in)

	pool.Exec(r.Context(),
		"UPDATE products SET name=$1, price_cents=$2 WHERE id=$3",
		in.Name, in.PriceCents, id)

	p := map[string]any{"id": id, "name": in.Name, "price_cents": in.PriceCents}
	data, _ := json.Marshal(p)
	safeSet(r.Context(), "wt:product:"+id, string(data), cacheTTL)
	writeJSON(w, 200, p)
}

func handleWriteThroughGet(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	key := "wt:product:" + id

	if val, ok := safeGet(r.Context(), key); ok {
		var p map[string]any
		json.Unmarshal([]byte(val), &p)
		p["source"] = "cache"
		writeJSON(w, 200, p)
		return
	}

	p := loadProduct(r.Context(), id)
	if p == nil {
		http.Error(w, "not found", 404)
		return
	}
	data, _ := json.Marshal(p)
	safeSet(r.Context(), key, string(data), cacheTTL)
	p["source"] = "db"
	writeJSON(w, 200, p)
}

func handleWriteAroundPost(w http.ResponseWriter, r *http.Request) {
	var in struct {
		ID      string          `json:"id"`
		Type    string          `json:"type"`
		Payload json.RawMessage `json:"payload"`
	}
	json.NewDecoder(r.Body).Decode(&in)

	pool.Exec(r.Context(),
		"INSERT INTO events (id, type, payload) VALUES ($1, $2, $3)",
		in.ID, in.Type, in.Payload)
	writeJSON(w, 200, map[string]any{"id": in.ID, "type": in.Type, "payload": in.Payload})
}

func handleWriteAroundGet(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	key := "wa:event:" + id

	if val, ok := safeGet(r.Context(), key); ok {
		var e map[string]any
		json.Unmarshal([]byte(val), &e)
		e["source"] = "cache"
		writeJSON(w, 200, e)
		return
	}

	var etype string
	var payload json.RawMessage
	err := pool.QueryRow(r.Context(),
		"SELECT type, payload FROM events WHERE id=$1", id).Scan(&etype, &payload)
	if err != nil {
		http.Error(w, "not found", 404)
		return
	}
	e := map[string]any{"id": id, "type": etype, "payload": json.RawMessage(payload)}
	data, _ := json.Marshal(e)
	safeSet(r.Context(), key, string(data), cacheTTL)
	e["source"] = "db"
	writeJSON(w, 200, e)
}

func handleWriteBackPut(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	var raw json.RawMessage
	json.NewDecoder(r.Body).Decode(&raw)

	var parsed map[string]any
	json.Unmarshal(raw, &parsed)
	parsed["id"] = id

	key := "metric:" + id
	data, _ := json.Marshal(parsed)
	safeSet(r.Context(), key, string(data), 0)
	rdb.SAdd(r.Context(), "metric:dirty", key)

	writeJSON(w, 200, parsed)
}

func handleWriteBackGet(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	key := "metric:" + id

	if val, ok := safeGet(r.Context(), key); ok {
		var m map[string]any
		json.Unmarshal([]byte(val), &m)
		m["source"] = "cache"
		writeJSON(w, 200, m)
		return
	}

	var payload json.RawMessage
	err := pool.QueryRow(r.Context(),
		"SELECT payload FROM metrics WHERE id=$1", id).Scan(&payload)
	if err != nil {
		http.Error(w, "not found", 404)
		return
	}
	var m map[string]any
	json.Unmarshal(payload, &m)
	m["id"] = id
	m["source"] = "db"
	writeJSON(w, 200, m)
}

func handleFlushStatus(w http.ResponseWriter, r *http.Request) {
	var count int
	pool.QueryRow(r.Context(), "SELECT count(*) FROM metrics").Scan(&count)
	writeJSON(w, 200, map[string]any{"persisted_rows": count})
}

func handleRefreshAheadGet(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	key := "ra:product:" + id

	if val, ok := safeGet(r.Context(), key); ok {
		var p map[string]any
		json.Unmarshal([]byte(val), &p)
		p["source"] = "cache"
		writeJSON(w, 200, p)
		return
	}

	p := loadProduct(r.Context(), id)
	if p == nil {
		http.Error(w, "not found", 404)
		return
	}
	data, _ := json.Marshal(p)
	safeSet(r.Context(), key, string(data), cacheTTL)
	rdb.ZAdd(r.Context(), "product:hot", redis.Z{
		Score: float64(time.Now().Unix()), Member: id,
	})
	p["source"] = "db"
	writeJSON(w, 200, p)
}

func handleCacheKeys(w http.ResponseWriter, r *http.Request) {
	keys := make([]string, 0)
	iter := rdb.Scan(r.Context(), 0, "*", 0).Iterator()
	for iter.Next(r.Context()) {
		keys = append(keys, iter.Val())
	}
	writeJSON(w, 200, map[string]any{"keys": keys})
}

func flusher(ctx context.Context) {
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			members, err := rdb.SPopN(ctx, "metric:dirty", 100).Result()
			if err != nil || len(members) == 0 {
				continue
			}
			for _, key := range members {
				val, err := rdb.Get(ctx, key).Result()
				if err != nil {
					continue
				}
				var m map[string]any
				json.Unmarshal([]byte(val), &m)
				id, _ := m["id"].(string)
				payload, _ := json.Marshal(m)
				pool.Exec(ctx,
					"INSERT INTO metrics (id, payload) VALUES ($1, $2) ON CONFLICT (id) DO UPDATE SET payload=$2, ts=NOW()",
					id, payload)
				slog.Info("flushed metric", "id", id)
			}
		}
	}
}

func refresher(ctx context.Context) {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			members, err := rdb.ZRange(ctx, "product:hot", 0, -1).Result()
			if err != nil || len(members) == 0 {
				continue
			}
			for _, id := range members {
				key := "ra:product:" + id
				ttl, err := rdb.TTL(ctx, key).Result()
				if err != nil {
					continue
				}
				if ttl > 0 && ttl < 10*time.Second {
					p := loadProduct(ctx, id)
					if p != nil {
						data, _ := json.Marshal(p)
						safeSet(ctx, key, string(data), cacheTTL)
						slog.Info("refreshed product", "id", id)
					}
				}
			}
		}
	}
}
