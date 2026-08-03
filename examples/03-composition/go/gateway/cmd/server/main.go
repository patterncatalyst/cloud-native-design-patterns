package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"regexp"
	"strings"
	"syscall"
	"time"

	pb "github.com/patterncatalyst/cloud-native-design-patterns/examples/03-composition/go/gateway/pb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

var (
	orderAPIURL string
	invClient   pb.InventoryClient
	httpClient  = &http.Client{Timeout: 5 * time.Second}
	idRegex     = regexp.MustCompile(`id:\s*"([^"]+)"`)
)

func main() {
	orderAPIURL = os.Getenv("ORDER_API_URL")
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
	invClient = pb.NewInventoryClient(conn)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, 200, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /graphql", handleGraphQL)

	srv := &http.Server{Addr: ":8080", Handler: mux}
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGTERM, syscall.SIGINT)
		<-sigCh
		srv.Shutdown(context.Background())
	}()

	slog.Info("starting gateway on :8080")
	if err := srv.ListenAndServe(); err != http.ErrServerClosed {
		slog.Error("server error", "err", err)
	}
}

func handleGraphQL(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Query string `json:"query"`
	}
	json.NewDecoder(r.Body).Decode(&req)

	wantStock := strings.Contains(req.Query, "stock")

	if strings.Contains(req.Query, "order(") || strings.Contains(req.Query, "order (") {
		handleSingleOrder(w, r.Context(), req.Query, wantStock)
		return
	}

	if strings.Contains(req.Query, "orders") {
		handleOrdersList(w, r.Context(), wantStock)
		return
	}

	writeJSON(w, 200, map[string]any{"data": nil})
}

func handleOrdersList(w http.ResponseWriter, ctx context.Context, wantStock bool) {
	orders, err := fetchOrders(ctx)
	if err != nil {
		writeJSON(w, 200, graphqlError(err.Error()))
		return
	}

	if wantStock {
		enrichWithStock(ctx, orders)
	}

	writeJSON(w, 200, map[string]any{"data": map[string]any{"orders": orders}})
}

func handleSingleOrder(w http.ResponseWriter, ctx context.Context, query string, wantStock bool) {
	matches := idRegex.FindStringSubmatch(query)
	if len(matches) < 2 {
		writeJSON(w, 200, graphqlError("missing id argument"))
		return
	}
	id := matches[1]

	resp, err := httpClient.Get(fmt.Sprintf("%s/orders/%s", orderAPIURL, id))
	if err != nil || resp.StatusCode != 200 {
		writeJSON(w, 200, map[string]any{"data": map[string]any{"order": nil}})
		return
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)

	var order map[string]any
	json.Unmarshal(body, &order)

	if wantStock {
		enrichWithStock(ctx, []map[string]any{order})
	}

	writeJSON(w, 200, map[string]any{"data": map[string]any{"order": order}})
}

func fetchOrders(ctx context.Context) ([]map[string]any, error) {
	resp, err := httpClient.Get(orderAPIURL + "/orders")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)

	var orders []map[string]any
	json.Unmarshal(body, &orders)
	return orders, nil
}

func enrichWithStock(ctx context.Context, orders []map[string]any) {
	skuSet := map[string]bool{}
	for _, o := range orders {
		if sku, ok := o["sku"].(string); ok {
			skuSet[sku] = true
		}
	}

	skus := make([]string, 0, len(skuSet))
	for sku := range skuSet {
		skus = append(skus, sku)
	}

	grpcCtx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	reply, err := invClient.GetStockBatch(grpcCtx, &pb.GetStockBatchRequest{Skus: skus})
	if err != nil {
		slog.Warn("stock batch failed", "err", err)
		return
	}

	slog.Info(fmt.Sprintf("DataLoader batched %d skus in one gRPC call", len(skus)))

	stockMap := map[string]int32{}
	for _, item := range reply.Items {
		stockMap[item.Sku] = item.Available
	}

	for _, o := range orders {
		if sku, ok := o["sku"].(string); ok {
			o["stock"] = stockMap[sku]
		}
	}
}

func graphqlError(msg string) map[string]any {
	return map[string]any{"data": nil, "errors": []map[string]string{{"message": msg}}}
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
