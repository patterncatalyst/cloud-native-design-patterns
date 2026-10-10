package main

import (
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/99designs/gqlgen/graphql/handler"
	"github.com/99designs/gqlgen/graphql/handler/extension"
	"github.com/99designs/gqlgen/graphql/handler/transport"
	"github.com/cenkalti/backoff/v7"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/patterncatalyst/cloud-native-design-patterns/examples/02-communications/go/order-service/graph"
	pb "github.com/patterncatalyst/cloud-native-design-patterns/examples/02-communications/go/order-service/pb"
	"github.com/twmb/franz-go/pkg/kgo"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

var (
	pool      *pgxpool.Pool
	producer  *kgo.Client
	invConn   *grpc.ClientConn
	invClient pb.InventoryClient
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

	bootstrap := os.Getenv("KAFKA_BOOTSTRAP")
	if bootstrap == "" {
		bootstrap = "kafka:9094"
	}
	producer, err = kgo.NewClient(kgo.SeedBrokers(bootstrap), kgo.AllowAutoTopicCreation())
	if err != nil {
		slog.Error("kafka producer failed", "err", err)
		os.Exit(1)
	}
	defer producer.Close()

	invAddr := os.Getenv("INVENTORY_ADDR")
	if invAddr == "" {
		invAddr = "inventory:50051"
	}
	invConn, err = grpc.NewClient(invAddr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		slog.Error("grpc connect failed", "err", err)
		os.Exit(1)
	}
	defer invConn.Close()
	invClient = pb.NewInventoryClient(invConn)

	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, 200, map[string]string{"status": "ok"})
	})

	mux.HandleFunc("POST /orders", handleCreateOrder)
	mux.HandleFunc("GET /orders", handleListOrders)
	// gqlgen serves graph/schema.graphqls; the resolver reads the same orders table.
	gql := handler.New(graph.NewExecutableSchema(graph.Config{Resolvers: &graph.Resolver{Pool: pool}}))
	gql.AddTransport(transport.POST{})
	gql.Use(extension.Introspection{})
	mux.Handle("POST /graphql", gql)

	srv := &http.Server{Addr: ":8080", Handler: mux}
	go func() {
		sigCtx, stopSignals := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
		defer stopSignals()
		<-sigCtx.Done()
		slog.Info("shutting down")
		srv.Shutdown(context.Background())
	}()

	slog.Info("starting order-service")
	if err := srv.ListenAndServe(); err != http.ErrServerClosed {
		slog.Error("server error", "err", err)
	}
}

func handleCreateOrder(w http.ResponseWriter, r *http.Request) {
	var in struct {
		SKU      string `json:"sku"`
		Quantity int    `json:"quantity"`
	}
	json.NewDecoder(r.Body).Decode(&in)

	if in.SKU == "" || in.Quantity <= 0 {
		writeJSON(w, 422, map[string]string{"error": "sku required, quantity must be > 0"})
		return
	}

	grpcCtx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	reply, err := invClient.ReserveStock(grpcCtx, &pb.ReserveRequest{
		Sku: in.SKU, Quantity: int32(in.Quantity),
	})

	status := "confirmed"
	if err != nil || !reply.GetReserved() {
		status = "rejected"
	}

	id := newUUID()
	pool.Exec(r.Context(),
		"INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4)",
		id, in.SKU, in.Quantity, status)

	event, _ := json.Marshal(map[string]any{
		"id": id, "sku": in.SKU, "quantity": in.Quantity, "status": status,
	})
	rec := &kgo.Record{Topic: "order.placed", Key: []byte(id), Value: event}
	produceBackoff := backoff.NewExponentialBackOff()
	produceBackoff.InitialInterval = 500 * time.Millisecond
	produceBackoff.MaxInterval = 2 * time.Second
	if _, err := backoff.Retry(r.Context(), func() (struct{}, error) {
		return struct{}{}, producer.ProduceSync(r.Context(), rec).FirstErr()
	}, backoff.WithBackOff(produceBackoff), backoff.WithMaxTries(5),
		backoff.WithNotify(func(err error, next time.Duration) {
			slog.Warn("kafka produce retry", "err", err, "next_in", next)
		})); err != nil {
		slog.Error("kafka produce failed", "err", err)
	}

	slog.Info("order created", "id", id, "sku", in.SKU, "status", status)
	writeJSON(w, 201, map[string]any{
		"id": id, "sku": in.SKU, "quantity": in.Quantity, "status": status,
	})
}

func handleListOrders(w http.ResponseWriter, r *http.Request) {
	limit := 20
	if v := r.URL.Query().Get("limit"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 && n <= 100 {
			limit = n
		}
	}
	after := r.URL.Query().Get("after")

	var query string
	var args []any
	if after != "" {
		query = "SELECT id, sku, quantity, status FROM orders WHERE id > $1 ORDER BY id LIMIT $2"
		args = []any{after, limit + 1}
	} else {
		query = "SELECT id, sku, quantity, status FROM orders ORDER BY id LIMIT $1"
		args = []any{limit + 1}
	}

	rows, err := pool.Query(r.Context(), query, args...)
	if err != nil {
		writeJSON(w, 500, map[string]string{"error": "internal"})
		return
	}
	defer rows.Close()

	items := make([]map[string]any, 0)
	for rows.Next() {
		var id, sku, status string
		var quantity int
		rows.Scan(&id, &sku, &quantity, &status)
		items = append(items, map[string]any{
			"id": id, "sku": sku, "quantity": quantity, "status": status,
		})
	}

	var nextCursor *string
	if len(items) > limit {
		cursor := items[limit-1]["id"].(string)
		nextCursor = &cursor
		items = items[:limit]
	}

	result := map[string]any{"items": items}
	if nextCursor != nil {
		result["next_cursor"] = *nextCursor
	}
	writeJSON(w, 200, result)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func newUUID() string {
	b := make([]byte, 16)
	rand.Read(b)
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}
