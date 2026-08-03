package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"os"
	"os/signal"
	"strconv"
	"sync"
	"syscall"
	"time"

	"github.com/twmb/franz-go/pkg/kgo"
)

type windowKey struct {
	Start      time.Time
	MerchantID string
}

type windowAgg struct {
	Count   int     `json:"order_count"`
	Revenue float64 `json:"revenue"`
}

var (
	windowSec int
	mu        sync.Mutex
	windows   = map[windowKey]*windowAgg{}
)

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
	defer cancel()

	windowSec = 10
	if v := os.Getenv("WINDOW_SECONDS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			windowSec = n
		}
	}

	bootstrap := os.Getenv("KAFKA_BOOTSTRAP")
	if bootstrap == "" {
		bootstrap = "kafka:9094"
	}

	consumer, err := kgo.NewClient(
		kgo.SeedBrokers(bootstrap),
		kgo.ConsumerGroup("stream-processor"),
		kgo.ConsumeTopics("order.placed"),
		kgo.DisableAutoCommit(),
		kgo.ConsumeResetOffset(kgo.NewOffset().AtStart()),
		kgo.AllowAutoTopicCreation(),
		kgo.OnPartitionsAssigned(func(ctx context.Context, cl *kgo.Client, assigned map[string][]int32) {
			offsets := make(map[string]map[int32]kgo.EpochOffset)
			for topic, parts := range assigned {
				m := make(map[int32]kgo.EpochOffset)
				for _, p := range parts {
					m[p] = kgo.EpochOffset{Offset: 0}
				}
				offsets[topic] = m
			}
			cl.CommitOffsets(ctx, offsets, nil)
			slog.Info("committed initial offsets for all assigned partitions")
		}),
	)
	if err != nil {
		slog.Error("consumer init failed", "err", err)
		os.Exit(1)
	}
	defer consumer.Close()

	producer, err := kgo.NewClient(
		kgo.SeedBrokers(bootstrap),
		kgo.AllowAutoTopicCreation(),
	)
	if err != nil {
		slog.Error("producer init failed", "err", err)
		os.Exit(1)
	}
	defer producer.Close()

	go windowFlusher(ctx, producer)

	slog.Info("stream-processor started", "window_seconds", windowSec)

	for {
		fetches := consumer.PollFetches(ctx)
		if ctx.Err() != nil {
			break
		}

		fetches.EachRecord(func(rec *kgo.Record) {
			var event struct {
				MerchantID string  `json:"merchant_id"`
				Total      float64 `json:"total"`
			}
			if err := json.Unmarshal(rec.Value, &event); err != nil {
				return
			}

			now := time.Now().UTC()
			wStart := now.Truncate(time.Duration(windowSec) * time.Second)

			mu.Lock()
			key := windowKey{Start: wStart, MerchantID: event.MerchantID}
			agg, ok := windows[key]
			if !ok {
				agg = &windowAgg{}
				windows[key] = agg
			}
			agg.Count++
			agg.Revenue += event.Total
			mu.Unlock()
		})

		if err := consumer.CommitUncommittedOffsets(ctx); err != nil && ctx.Err() == nil {
			slog.Error("commit failed", "err", err)
		}
	}

	flushAllWindows(context.Background(), producer)
	slog.Info("stream-processor stopped")
}

func windowFlusher(ctx context.Context, producer *kgo.Client) {
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			flushExpiredWindows(ctx, producer)
		}
	}
}

func flushExpiredWindows(ctx context.Context, producer *kgo.Client) {
	now := time.Now().UTC()
	cutoff := now.Add(-time.Duration(windowSec) * time.Second)

	mu.Lock()
	var expired []windowKey
	for k := range windows {
		if k.Start.Before(cutoff) {
			expired = append(expired, k)
		}
	}

	toFlush := make(map[windowKey]*windowAgg, len(expired))
	for _, k := range expired {
		toFlush[k] = windows[k]
		delete(windows, k)
	}
	mu.Unlock()

	for k, agg := range toFlush {
		out, _ := json.Marshal(map[string]any{
			"window_start": k.Start.Format(time.RFC3339),
			"window_end":   k.Start.Add(time.Duration(windowSec) * time.Second).Format(time.RFC3339),
			"merchant_id":  k.MerchantID,
			"order_count":  agg.Count,
			"revenue":      agg.Revenue,
		})
		producer.ProduceSync(ctx, &kgo.Record{
			Topic: "revenue.by-merchant",
			Key:   []byte(k.MerchantID),
			Value: out,
		})
		slog.Info("window flushed", "merchant_id", k.MerchantID, "count", agg.Count, "revenue", agg.Revenue)
	}
}

func flushAllWindows(ctx context.Context, producer *kgo.Client) {
	mu.Lock()
	all := make(map[windowKey]*windowAgg, len(windows))
	for k, v := range windows {
		all[k] = v
	}
	windows = map[windowKey]*windowAgg{}
	mu.Unlock()

	for k, agg := range all {
		out, _ := json.Marshal(map[string]any{
			"window_start": k.Start.Format(time.RFC3339),
			"window_end":   k.Start.Add(time.Duration(windowSec) * time.Second).Format(time.RFC3339),
			"merchant_id":  k.MerchantID,
			"order_count":  agg.Count,
			"revenue":      agg.Revenue,
		})
		producer.ProduceSync(ctx, &kgo.Record{
			Topic: "revenue.by-merchant",
			Key:   []byte(k.MerchantID),
			Value: out,
		})
	}
}
