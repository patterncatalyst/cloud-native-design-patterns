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

	"github.com/cenkalti/backoff/v7"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/twmb/franz-go/pkg/kgo"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
	"go.opentelemetry.io/otel/trace"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	res := resource.NewWithAttributes(semconv.SchemaURL, semconv.ServiceName(serviceName()))
	endpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	if endpoint == "" {
		endpoint = "http://lgtm:4318"
	}
	traceExp, err := otlptracehttp.New(ctx, otlptracehttp.WithEndpoint(stripScheme(endpoint)), otlptracehttp.WithInsecure())
	if err != nil {
		slog.Error("otlp exporter init failed", "err", err)
		os.Exit(1)
	}
	tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(traceExp), sdktrace.WithResource(res))
	defer tp.Shutdown(context.Background())
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.TraceContext{})
	tracer := tp.Tracer("order-service")

	pool, err := pgxpool.New(ctx, os.Getenv("DATABASE_URL"))
	if err != nil {
		slog.Error("db connect failed", "err", err)
		os.Exit(1)
	}
	defer pool.Close()

	bootstrap := os.Getenv("KAFKA_BOOTSTRAP")
	if bootstrap == "" {
		bootstrap = "kafka:9094"
	}

	producer, err := kgo.NewClient(
		kgo.SeedBrokers(bootstrap),
		kgo.AllowAutoTopicCreation(),
	)
	if err != nil {
		slog.Error("kafka producer init failed", "err", err)
		os.Exit(1)
	}
	defer producer.Close()

	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	mux.HandleFunc("POST /orders", func(w http.ResponseWriter, r *http.Request) {
		var in struct {
			SKU      string `json:"sku"`
			Quantity int    `json:"quantity"`
		}
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
			http.Error(w, "bad request", 400)
			return
		}

		id := newUUID()
		_, err := pool.Exec(r.Context(),
			"INSERT INTO orders (id, sku, quantity) VALUES ($1, $2, $3)",
			id, in.SKU, in.Quantity)
		if err != nil {
			slog.Error("insert order failed", "err", err)
			http.Error(w, "internal error", 500)
			return
		}

		event, _ := json.Marshal(map[string]any{
			"id": id, "sku": in.SKU, "quantity": in.Quantity, "status": "pending",
		})
		produceCtx, span := tracer.Start(r.Context(), "order.placed publish", trace.WithSpanKind(trace.SpanKindProducer))
		span.SetAttributes(attribute.String("messaging.system", "kafka"), attribute.String("messaging.destination.name", "order.placed"))
		headers := make([]kgo.RecordHeader, 0, 1)
		otel.GetTextMapPropagator().Inject(produceCtx, &kafkaHeaderCarrier{headers: &headers})
		rec := &kgo.Record{Topic: "order.placed", Key: []byte(id), Value: event, Headers: headers}
		produceBackoff := backoff.NewExponentialBackOff()
		produceBackoff.InitialInterval = 500 * time.Millisecond
		produceBackoff.MaxInterval = 2 * time.Second
		if _, err := backoff.Retry(produceCtx, func() (struct{}, error) {
			return struct{}{}, producer.ProduceSync(produceCtx, rec).FirstErr()
		}, backoff.WithBackOff(produceBackoff), backoff.WithMaxTries(5),
			backoff.WithNotify(func(err error, next time.Duration) {
				slog.Warn("kafka produce retry", "err", err, "next_in", next)
			})); err != nil {
			span.RecordError(err)
			span.SetStatus(codes.Error, "produce failed")
			slog.Error("kafka produce failed", "err", err)
		}
		span.End()

		slog.Info("order placed", "id", id, "sku", in.SKU)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]any{
			"id": id, "sku": in.SKU, "quantity": in.Quantity, "status": "pending",
		})
	})

	mux.HandleFunc("GET /orders", func(w http.ResponseWriter, r *http.Request) {
		rows, err := pool.Query(r.Context(),
			"SELECT id, sku, quantity, status FROM orders ORDER BY created_at")
		if err != nil {
			http.Error(w, "internal error", 500)
			return
		}
		defer rows.Close()

		orders := make([]map[string]any, 0)
		for rows.Next() {
			var id, sku, status string
			var quantity int
			if err := rows.Scan(&id, &sku, &quantity, &status); err != nil {
				continue
			}
			orders = append(orders, map[string]any{
				"id": id, "sku": sku, "quantity": quantity, "status": status,
			})
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(orders)
	})

	srv := &http.Server{Addr: ":8080", Handler: otelhttp.NewHandler(mux, "order-service")}
	go func() {
		sigCtx, stopSignals := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
		defer stopSignals()
		<-sigCtx.Done()
		slog.Info("shutting down order-service")
		srv.Shutdown(context.Background())
	}()

	slog.Info("starting order-service")
	if err := srv.ListenAndServe(); err != http.ErrServerClosed {
		slog.Error("server error", "err", err)
	}
}

func newUUID() string {
	b := make([]byte, 16)
	rand.Read(b)
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
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

func serviceName() string {
	if n := os.Getenv("OTEL_SERVICE_NAME"); n != "" {
		return n
	}
	return "order-service"
}

func stripScheme(url string) string {
	for _, p := range []string{"http://", "https://"} {
		if len(url) > len(p) && url[:len(p)] == p {
			return url[len(p):]
		}
	}
	return url
}
