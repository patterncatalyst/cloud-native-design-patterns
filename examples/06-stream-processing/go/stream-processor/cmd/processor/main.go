// order.placed -> tumbling window per merchant -> revenue.by-merchant, built on goka.
//
// goka models a stream processor as a group of Kafka consumers with a partitioned,
// changelog-backed table. Two stages mirror the Kafka Streams topology:
//
//  1. "rekey":     order.placed -> parse -> stream-processor-by-merchant (keyed by merchant_id)
//  2. "aggregate": stream-processor-by-merchant -> windowed (count, total) in the group table
//     -> revenue.by-merchant (one record per update)
//
// The group name is the Kafka consumer group ("stream-processor"). The window state lives in
// memory and is mirrored to the table topic stream-processor-table, which goka replays on
// restart, so the container needs no volume. Every update to a (merchant, window) row is
// emitted downstream; consumers keep the latest record per (merchant_id, window_start).
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"math/big"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/IBM/sarama"
	"github.com/lovoo/goka"
	"github.com/lovoo/goka/codec"
	"github.com/lovoo/goka/storage"
)

const (
	group      = goka.Group("stream-processor")
	orders     = goka.Stream("order.placed")
	byMerchant = goka.Stream("stream-processor-by-merchant")
	revenue    = goka.Stream("revenue.by-merchant")

	defaultPartitions = 3
)

var windowSeconds int64 = 10

// rekeyed is the value of the repartition topic: the original record time plus the order total.
type rekeyed struct {
	TS    int64  `json:"ts"` // Kafka record timestamp, epoch millis
	Total string `json:"total"`
}

type acc struct {
	Count int    `json:"count"`
	Total string `json:"total"` // big.Rat text
}

// merchantState is the table value for one merchant: its open windows and its stream time.
type merchantState struct {
	StreamTime int64         `json:"stream_time"` // max record time seen, epoch millis
	Windows    map[int64]acc `json:"windows"`     // window start (epoch seconds) -> aggregate
}

type stateCodec struct{}

func (stateCodec) Encode(v any) ([]byte, error) { return json.Marshal(v) }
func (stateCodec) Decode(b []byte) (any, error) {
	s := &merchantState{}
	if err := json.Unmarshal(b, s); err != nil {
		return nil, err
	}
	return s, nil
}

type rekeyedCodec struct{}

func (rekeyedCodec) Encode(v any) ([]byte, error) { return json.Marshal(v) }
func (rekeyedCodec) Decode(b []byte) (any, error) {
	r := &rekeyed{}
	if err := json.Unmarshal(b, r); err != nil {
		return nil, err
	}
	return r, nil
}

// parse returns (merchant_id, total text) for a usable order event. merchant_id follows the
// Kafka Streams version (Jackson asText()): a string is used as is, a number or boolean is
// coerced to its JSON text, and a missing, null, empty or object/array value drops the record.
func parse(raw []byte) (merchant, total string, ok bool) {
	var event map[string]json.RawMessage
	if err := json.Unmarshal(raw, &event); err != nil || event == nil {
		return "", "", false
	}
	m, present := event["merchant_id"]
	if !present {
		return "", "", false
	}
	merchant, ok = scalarText(m)
	if !ok || merchant == "" || string(m) == "null" {
		return "", "", false
	}
	t, present := event["total"]
	if !present || string(t) == "null" {
		return merchant, "0", true
	}
	total, ok = scalarText(t)
	if !ok {
		// an object, array or boolean total is "not a number": keep it so the caller warns
		total = strings.TrimSpace(string(t))
	}
	return merchant, total, true
}

func scalarText(raw json.RawMessage) (string, bool) {
	s := strings.TrimSpace(string(raw))
	switch {
	case s == "":
		return "", false
	case s[0] == '"':
		var str string
		if err := json.Unmarshal(raw, &str); err != nil {
			return "", false
		}
		return str, true
	case s[0] == '{' || s[0] == '[':
		return "", false
	default: // number, true, false, null
		return s, true
	}
}

// decimal parses a plain decimal number. Anything else (NaN, Infinity, booleans, huge
// exponents) is rejected so one bad record cannot stall the stream.
func decimal(s string) (*big.Rat, bool) {
	s = strings.TrimSpace(s)
	if s == "" || len(s) > 64 || strings.ContainsAny(s, "/xXpP_") {
		return nil, false
	}
	if i := strings.IndexAny(s, "eE"); i >= 0 {
		exp, err := strconv.Atoi(s[i+1:])
		if err != nil || exp > 30 || exp < -30 {
			return nil, false
		}
	}
	r, ok := new(big.Rat).SetString(s)
	return r, ok
}

// money renders r with two decimals, rounding half away from zero (HALF_UP).
func money(r *big.Rat) string {
	scaled := new(big.Rat).Mul(r, big.NewRat(100, 1))
	neg := scaled.Sign() < 0
	scaled.Abs(scaled)
	num, den := scaled.Num(), scaled.Denom()
	// floor((2*num + den) / (2*den))
	q := new(big.Int).Mul(num, big.NewInt(2))
	q.Add(q, den)
	q.Quo(q, new(big.Int).Mul(den, big.NewInt(2)))
	hundred := big.NewInt(100)
	whole, frac := new(big.Int).QuoRem(q, hundred, new(big.Int))
	sign := ""
	if neg && q.Sign() != 0 {
		sign = "-"
	}
	return fmt.Sprintf("%s%s.%02d", sign, whole.String(), frac.Int64())
}

func rekey(ctx goka.Context, msg any) {
	merchant, total, ok := parse(msg.([]byte))
	if !ok {
		slog.Warn("skipping unreadable order record")
		return
	}
	if _, ok := decimal(total); !ok {
		// A total that is not a number skips the record instead of killing the processor.
		slog.Warn(fmt.Sprintf("skipping order with invalid total merchant=%s total=%s", merchant, total))
		return
	}
	ctx.Emit(byMerchant, merchant, &rekeyed{TS: ctx.Timestamp().UnixMilli(), Total: total})
}

func aggregate(ctx goka.Context, msg any) {
	in := msg.(*rekeyed)
	merchant := ctx.Key()
	amount, ok := decimal(in.Total)
	if !ok {
		return
	}

	state := &merchantState{Windows: map[int64]acc{}}
	if v := ctx.Value(); v != nil {
		state = v.(*merchantState)
		if state.Windows == nil {
			state.Windows = map[int64]acc{}
		}
	}

	// Tumbling window containing the record time. No grace: a record whose window already
	// ended relative to stream time is late and dropped, like TimeWindows.ofSizeWithNoGrace.
	start := (in.TS / 1000 / windowSeconds) * windowSeconds
	if in.TS > state.StreamTime {
		state.StreamTime = in.TS
	}
	if (start+windowSeconds)*1000 <= state.StreamTime {
		slog.Debug("dropping late record", "merchant", merchant, "window", start)
		ctx.SetValue(state)
		return
	}
	for ws := range state.Windows {
		if (ws+windowSeconds)*1000 <= state.StreamTime {
			delete(state.Windows, ws) // window closed: state no longer needed
		}
	}

	cur := acc{Total: "0"}
	if a, ok := state.Windows[start]; ok {
		cur = a
	}
	// The stored total is our own RatString output (for example "2001/200"), which the strict
	// input parser rejects, so read it back with big.Rat directly.
	sum, ok := new(big.Rat).SetString(cur.Total)
	if !ok {
		sum = new(big.Rat)
	}
	sum.Add(sum, amount)
	cur = acc{Count: cur.Count + 1, Total: sum.RatString()}
	state.Windows[start] = cur
	ctx.SetValue(state)

	shown := money(sum)
	slog.Info(fmt.Sprintf("emitted revenue window=%d merchant=%s count=%d revenue=%s", start, merchant, cur.Count, shown))
	merchantJSON, _ := json.Marshal(merchant)
	// revenue is spliced in as a JSON number with exactly two decimals
	body := fmt.Sprintf(`{"window_start":%d,"window_end":%d,"merchant_id":%s,"order_count":%d,"revenue":%s}`,
		start, start+windowSeconds, merchantJSON, cur.Count, shown)
	ctx.Emit(revenue, merchant, []byte(body))
}

func saramaConfig() *sarama.Config {
	cfg := goka.DefaultConfig()
	// Protocol version of the sarama client: the newest constant sarama v1.61 defines
	// (MaxVersion). sarama caps each request at the versions the broker advertises in
	// ApiVersions (restrictApiVersion), so this also works with older brokers; the image was
	// run against Kafka 3.8 and 4.3.
	cfg.Version = sarama.V4_3_1_0
	// read order.placed from the beginning on the first run of the group
	cfg.Consumer.Offsets.Initial = sarama.OffsetOldest
	cfg.Consumer.Group.Session.Timeout = 10 * time.Second
	cfg.Consumer.Group.Heartbeat.Interval = 3 * time.Second
	return cfg
}

// ensureTopics creates the source, the repartition topic and the sink up front and returns
// the partition count that the co-partitioned topics share.
func ensureTopics(brokers []string, cfg *sarama.Config) (int, error) {
	tmc := goka.NewTopicManagerConfig()
	tmc.Table.Replication = 1
	tmc.Stream.Replication = 1
	tm, err := goka.NewTopicManager(brokers, cfg, tmc)
	if err != nil {
		return 0, err
	}
	defer tm.Close()

	if err := tm.EnsureTopicExists(string(orders), defaultPartitions, 1, nil); err != nil {
		return 0, err
	}
	parts, err := tm.Partitions(string(orders))
	if err != nil {
		return 0, err
	}
	n := len(parts)
	if err := tm.EnsureTopicExists(string(revenue), n, 1, nil); err != nil {
		return 0, err
	}
	if err := tm.EnsureStreamExists(string(byMerchant), n); err != nil {
		return 0, err
	}
	return n, nil
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
	defer stop()

	if v := os.Getenv("WINDOW_SECONDS"); v != "" {
		if n, err := strconv.ParseInt(v, 10, 64); err == nil && n > 0 {
			windowSeconds = n
		}
	}
	bootstrap := os.Getenv("KAFKA_BOOTSTRAP")
	if bootstrap == "" {
		bootstrap = "kafka:9094"
	}
	brokers := strings.Split(bootstrap, ",")

	cfg := saramaConfig()
	goka.ReplaceGlobalConfig(cfg)

	var partitions int
	for attempt := 1; ; attempt++ {
		var err error
		if partitions, err = ensureTopics(brokers, cfg); err == nil {
			break
		} else if attempt >= 30 || ctx.Err() != nil {
			slog.Error("could not prepare topics", "err", err)
			os.Exit(1)
		} else {
			slog.Warn(fmt.Sprintf("Kafka not ready, retry %d/30: %v", attempt, err))
			select {
			case <-ctx.Done():
			case <-time.After(2 * time.Second):
			}
		}
	}

	tmc := goka.NewTopicManagerConfig()
	tmc.Table.Replication = 1
	tmc.Stream.Replication = 1

	graph := goka.DefineGroup(group,
		goka.Input(orders, new(codec.Bytes), rekey),
		goka.Output(byMerchant, rekeyedCodec{}),
		goka.Input(byMerchant, rekeyedCodec{}, aggregate),
		goka.Output(revenue, new(codec.Bytes)),
		goka.Persist(stateCodec{}),
	)
	proc, err := goka.NewProcessor(brokers, graph,
		goka.WithTopicManagerBuilder(goka.TopicManagerBuilderWithConfig(cfg, tmc)),
		goka.WithStorageBuilder(storage.MemoryBuilder()),
	)
	if err != nil {
		slog.Error("processor init failed", "err", err)
		os.Exit(1)
	}

	slog.Info("stream-processor started", "window_seconds", windowSeconds, "partitions", partitions)
	if err := proc.Run(ctx); err != nil {
		slog.Error("processor stopped with error", "err", err)
		os.Exit(1)
	}
	slog.Info("stream-processor stopped")
}
