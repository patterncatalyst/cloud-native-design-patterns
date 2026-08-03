package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/twmb/franz-go/pkg/kgo"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
)

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
	defer cancel()

	res := resource.NewWithAttributes(semconv.SchemaURL, semconv.ServiceName("notification-consumer"))
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
	tracer := tp.Tracer("notification-consumer")

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
	client, err := kgo.NewClient(
		kgo.SeedBrokers(bootstrap),
		kgo.ConsumerGroup("notification-group"),
		kgo.ConsumeTopics("order.placed"),
		kgo.DisableAutoCommit(),
		kgo.ConsumeResetOffset(kgo.NewOffset().AtStart()),
		kgo.AllowAutoTopicCreation(),
	)
	if err != nil {
		slog.Error("kafka consumer init failed", "err", err)
		os.Exit(1)
	}
	defer client.Close()

	slog.Info("notification-consumer started")

	for {
		fetches := client.PollFetches(ctx)
		if ctx.Err() != nil {
			break
		}

		fetches.EachRecord(func(rec *kgo.Record) {
			carrier := kafkaHeaderCarrier{headers: rec.Headers}
			parentCtx := otel.GetTextMapPropagator().Extract(ctx, &carrier)
			_, span := tracer.Start(parentCtx, "process_notification")
			defer span.End()

			var event struct {
				ID string `json:"id"`
			}
			if err := json.Unmarshal(rec.Value, &event); err != nil {
				slog.Error("bad event payload", "err", err)
				return
			}

			_, err := pool.Exec(ctx,
				"INSERT INTO notifications (order_id, channel) VALUES ($1, 'email') ON CONFLICT (order_id) DO NOTHING",
				event.ID)
			if err != nil {
				slog.Error("insert notification failed", "err", err, "order_id", event.ID)
				return
			}
			slog.Info("notification sent", "order_id", event.ID)
		})

		if err := client.CommitUncommittedOffsets(ctx); err != nil && ctx.Err() == nil {
			slog.Error("commit failed", "err", err)
		}
	}
}

type kafkaHeaderCarrier struct {
	headers []kgo.RecordHeader
}

func (c *kafkaHeaderCarrier) Get(key string) string {
	for _, h := range c.headers {
		if h.Key == key {
			return string(h.Value)
		}
	}
	return ""
}

func (c *kafkaHeaderCarrier) Set(key, val string) {
	c.headers = append(c.headers, kgo.RecordHeader{Key: key, Value: []byte(val)})
}

func (c *kafkaHeaderCarrier) Keys() []string {
	keys := make([]string, 0, len(c.headers))
	for _, h := range c.headers {
		keys = append(keys, h.Key)
	}
	return keys
}

func stripScheme(url string) string {
	for _, p := range []string{"http://", "https://"} {
		if len(url) > len(p) && url[:len(p)] == p {
			return url[len(p):]
		}
	}
	return url
}
