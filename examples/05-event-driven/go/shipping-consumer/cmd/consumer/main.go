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
)

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
	defer cancel()

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
		kgo.ConsumerGroup("shipping-group"),
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

	slog.Info("shipping-consumer started")

	for {
		fetches := client.PollFetches(ctx)
		if ctx.Err() != nil {
			break
		}

		fetches.EachRecord(func(rec *kgo.Record) {
			var event struct {
				ID string `json:"id"`
			}
			if err := json.Unmarshal(rec.Value, &event); err != nil {
				slog.Error("bad event payload", "err", err)
				return
			}

			_, err := pool.Exec(ctx,
				"INSERT INTO shipments (order_id, status) VALUES ($1, 'scheduled') ON CONFLICT (order_id) DO NOTHING",
				event.ID)
			if err != nil {
				slog.Error("insert shipment failed", "err", err, "order_id", event.ID)
				return
			}
			slog.Info("shipment scheduled", "order_id", event.ID)
		})

		if err := client.CommitUncommittedOffsets(ctx); err != nil && ctx.Err() == nil {
			slog.Error("commit failed", "err", err)
		}
	}

	slog.Info("shipping-consumer stopped")
}
