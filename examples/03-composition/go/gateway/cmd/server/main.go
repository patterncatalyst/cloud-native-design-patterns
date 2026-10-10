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

	"github.com/99designs/gqlgen/graphql/handler"
	"github.com/99designs/gqlgen/graphql/handler/extension"
	"github.com/99designs/gqlgen/graphql/handler/transport"
	"github.com/patterncatalyst/cloud-native-design-patterns/examples/03-composition/go/gateway/graph"
	pb "github.com/patterncatalyst/cloud-native-design-patterns/examples/03-composition/go/gateway/pb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

func main() {
	orderAPIURL := os.Getenv("ORDER_API_URL")
	if orderAPIURL == "" {
		orderAPIURL = "http://order-api:8081"
	}

	invAddr := os.Getenv("INVENTORY_ADDR")
	if invAddr == "" {
		invAddr = "inventory:50051"
	}
	conn, err := grpc.NewClient(invAddr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		slog.Error("grpc connect failed", "err", err)
		os.Exit(1)
	}
	defer conn.Close()
	invClient := pb.NewInventoryClient(conn)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, 200, map[string]string{"status": "ok"})
	})
	// gqlgen serves graph/schema.graphqls; the resolver composes order-api (REST) and inventory (gRPC).
	gql := handler.New(graph.NewExecutableSchema(graph.Config{Resolvers: &graph.Resolver{
		OrderAPIURL: orderAPIURL,
		Inventory:   invClient,
		HTTP:        &http.Client{Timeout: 5 * time.Second},
	}}))
	gql.AddTransport(transport.POST{})
	gql.Use(extension.Introspection{})
	mux.Handle("POST /graphql", gql)

	srv := &http.Server{Addr: ":8080", Handler: mux}
	go func() {
		sigCtx, stopSignals := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
		defer stopSignals()
		<-sigCtx.Done()
		srv.Shutdown(context.Background())
	}()

	slog.Info("starting gateway on :8080")
	if err := srv.ListenAndServe(); err != http.ErrServerClosed {
		slog.Error("server error", "err", err)
	}
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
