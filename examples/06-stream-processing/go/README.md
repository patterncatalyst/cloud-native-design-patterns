# Example 06 - Go stream processor

The Go variant uses [goka](https://github.com/lovoo/goka) on sarama. `order-service` writes
`order.placed`; `stream-processor` re-keys each order by merchant, sums revenue per merchant in
tumbling windows (`WINDOW_SECONDS`, 10 s in the compose file) and emits every update to
`revenue.by-merchant`.

## Stream time is tracked per merchant

Window state lives in goka's per-key table, so the stream clock is kept per merchant, not per
partition or per processor. A window for one merchant closes only when that merchant sees a
later record. A merchant that goes quiet keeps its last window open, and a record that arrives
for an already-closed window of that merchant is dropped as late (no grace period, like Kafka
Streams `TimeWindows.ofSizeWithNoGrace`).

The reason is the programming model: a goka processor callback runs per key against that key's
value and has no shared clock or punctuation timer across keys. A global clock would need extra
state in a separate group table plus a cross-partition fan-in. Per-merchant time keeps the
processor stateless across keys, and it does not change what the example shows: each update is
emitted when it happens, so `revenue.by-merchant` shows a merchant's totals without waiting for
its window to close.

## Kafka protocol version

`cfg.Version` is `sarama.V4_3_1_0`, the newest version in sarama v1.61. sarama lowers every
request to the versions the broker advertises, so the same image runs against Kafka 3.8 and 4.3
(both were tested on a private network).
