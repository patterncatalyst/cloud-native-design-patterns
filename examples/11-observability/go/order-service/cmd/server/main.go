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
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	pb "github.com/patterncatalyst/cloud-native-design-patterns/examples/11-observability/go/order-service/pb"
	"github.com/twmb/franz-go/pkg/kgo"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetrichttp"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/metric"
	"go.opentelemetry.io/otel/propagation"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

var (
	pool         *pgxpool.Pool
	producer     *kgo.Client
	invClient    pb.InventoryServiceClient
	tracer       trace.Tracer
	orderCounter metric.Int64Counter
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	res := resource.NewWithAttributes(semconv.SchemaURL, semconv.ServiceName("order-service"))
	endpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	if endpoint == "" {
		endpoint = "http://lgtm:4318"
	}
	host := stripScheme(endpoint)

	traceExp, _ := otlptracehttp.New(ctx, otlptracehttp.WithEndpoint(host), otlptracehttp.WithInsecure())
	tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(traceExp), sdktrace.WithResource(res))
	defer tp.Shutdown(ctx)
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.TraceContext{})

	metricExp, _ := otlpmetrichttp.New(ctx, otlpmetrichttp.WithEndpoint(host), otlpmetrichttp.WithInsecure())
	mp := sdkmetric.NewMeterProvider(
		sdkmetric.WithReader(sdkmetric.NewPeriodicReader(metricExp, sdkmetric.WithInterval(5*time.Second))),
		sdkmetric.WithResource(res))
	defer mp.Shutdown(ctx)
	otel.SetMeterProvider(mp)

	tracer = tp.Tracer("order-service")
	meter := mp.Meter("order-service")
	orderCounter, _ = meter.Int64Counter("orders_placed_total")

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
		slog.Error("kafka init failed", "err", err)
		os.Exit(1)
	}
	defer producer.Close()

	invAddr := os.Getenv("INVENTORY_ADDR")
	if invAddr == "" {
		invAddr = "inventory:50051"
	}
	conn, err := grpc.NewClient(invAddr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithStatsHandler(otelgrpc.NewClientHandler()))
	if err != nil {
		slog.Error("grpc connect failed", "err", err)
		os.Exit(1)
	}
	defer conn.Close()
	invClient = pb.NewInventoryServiceClient(conn)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /orders", handleCreateOrder)
	mux.HandleFunc("GET /orders", handleListOrders)

	handler := otelhttp.NewHandler(mux, "order-service")
	srv := &http.Server{Addr: ":8080", Handler: handler}
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGTERM, syscall.SIGINT)
		<-sigCh
		slog.Info("shutting down")
		srv.Shutdown(context.Background())
	}()

	slog.Info("starting order-service")
	if err := srv.ListenAndServe(); err != http.ErrServerClosed {
		slog.Error("server error", "err", err)
	}
}

func handleCreateOrder(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	var in struct {
		SKU      string `json:"sku"`
		Quantity int    `json:"quantity"`
	}
	json.NewDecoder(r.Body).Decode(&in)

	if in.SKU == "" || in.Quantity <= 0 {
		http.Error(w, "bad request", 400)
		return
	}

	ctx, span := tracer.Start(ctx, "reserve-stock")
	span.SetAttributes(attribute.String("sku", in.SKU), attribute.Int("quantity", in.Quantity))
	grpcCtx, grpcCancel := context.WithTimeout(ctx, 5*time.Second)
	defer grpcCancel()
	reply, err := invClient.ReserveStock(grpcCtx, &pb.ReserveRequest{
		Sku: in.SKU, Quantity: int32(in.Quantity),
	})
	span.End()

	status := "confirmed"
	if err != nil || !reply.GetConfirmed() {
		status = "rejected"
	}

	id := newUUID()
	pool.Exec(ctx,
		"INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4)",
		id, in.SKU, in.Quantity, status)

	event, _ := json.Marshal(map[string]any{
		"id": id, "sku": in.SKU, "quantity": in.Quantity, "status": status,
	})

	headers := make([]kgo.RecordHeader, 0)
	carrier := kafkaHeaderCarrier{headers: &headers}
	otel.GetTextMapPropagator().Inject(ctx, &carrier)

	rec := &kgo.Record{Topic: "order.placed", Key: []byte(id), Value: event, Headers: headers}
	for attempt := range 5 {
		results := producer.ProduceSync(ctx, rec)
		if err := results.FirstErr(); err != nil {
			slog.Warn("kafka produce retry", "attempt", attempt+1, "err", err)
			time.Sleep(time.Duration(attempt+1) * 500 * time.Millisecond)
			continue
		}
		break
	}

	tid := traceIDFromCtx(ctx)
	orderCounter.Add(ctx, 1, metric.WithAttributes(
		attribute.String("sku", in.SKU), attribute.String("status", status)))
	slog.Info("order placed", "id", id, "sku", in.SKU, "status", status, "trace_id", tid)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(201)
	json.NewEncoder(w).Encode(map[string]any{
		"id": id, "sku": in.SKU, "quantity": in.Quantity, "status": status,
	})
}

func handleListOrders(w http.ResponseWriter, r *http.Request) {
	rows, err := pool.Query(r.Context(),
		"SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT 50")
	if err != nil {
		http.Error(w, "internal error", 500)
		return
	}
	defer rows.Close()

	orders := make([]map[string]any, 0)
	for rows.Next() {
		var id, sku, status string
		var quantity int
		rows.Scan(&id, &sku, &quantity, &status)
		orders = append(orders, map[string]any{
			"id": id, "sku": sku, "quantity": quantity, "status": status,
		})
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(orders)
}

type kafkaHeaderCarrier struct {
	headers *[]kgo.RecordHeader
}

func (c *kafkaHeaderCarrier) Get(key string) string {
	for _, h := range *c.headers {
		if h.Key == key {
			return string(h.Value)
		}
	}
	return ""
}

func (c *kafkaHeaderCarrier) Set(key, val string) {
	*c.headers = append(*c.headers, kgo.RecordHeader{Key: key, Value: []byte(val)})
}

func (c *kafkaHeaderCarrier) Keys() []string {
	keys := make([]string, 0, len(*c.headers))
	for _, h := range *c.headers {
		keys = append(keys, h.Key)
	}
	return keys
}

func traceIDFromCtx(ctx context.Context) string {
	sc := trace.SpanFromContext(ctx).SpanContext()
	if sc.HasTraceID() {
		return sc.TraceID().String()
	}
	return ""
}

func stripScheme(url string) string {
	for _, p := range []string{"http://", "https://"} {
		if len(url) > len(p) && url[:len(p)] == p {
			return url[len(p):]
		}
	}
	return url
}

func newUUID() string {
	b := make([]byte, 16)
	rand.Read(b)
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}
