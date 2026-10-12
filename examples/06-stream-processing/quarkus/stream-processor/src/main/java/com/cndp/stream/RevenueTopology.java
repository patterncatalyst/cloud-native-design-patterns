package com.cndp.stream;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Duration;

import io.quarkus.kafka.client.serialization.ObjectMapperSerde;
import io.quarkus.logging.Log;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KeyValue;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.Topology;
import org.apache.kafka.streams.kstream.Consumed;
import org.apache.kafka.streams.kstream.Grouped;
import org.apache.kafka.streams.kstream.Materialized;
import org.apache.kafka.streams.kstream.Produced;
import org.apache.kafka.streams.kstream.TimeWindows;
import org.eclipse.microprofile.config.inject.ConfigProperty;

/**
 * order.placed -> tumbling window per merchant -> revenue.by-merchant.
 *
 * The windowed aggregate is a KTable; every update to a (merchant, window) row is
 * emitted downstream, so a window yields a running total that settles when the
 * window closes. Consumers keep the latest record per (merchant_id, window_start).
 * Records that fail to deserialize are logged and skipped by the configured
 * LogAndContinueExceptionHandler.
 */
@ApplicationScoped
public class RevenueTopology {

    static final String ORDERS = "order.placed";
    static final String REVENUE = "revenue.by-merchant";

    @ConfigProperty(name = "window.seconds", defaultValue = "10")
    int windowSeconds;

    public record Acc(int count, BigDecimal total) {
        Acc add(BigDecimal amount) {
            return new Acc(count + 1, total.add(amount == null ? BigDecimal.ZERO : amount));
        }
    }

    @Produces
    public Topology topology() {
        StreamsBuilder builder = new StreamsBuilder();
        var orderSerde = new ObjectMapperSerde<>(OrderEvent.class);
        var accSerde = new ObjectMapperSerde<>(Acc.class);
        var revenueSerde = new ObjectMapperSerde<>(RevenueWindow.class);

        builder.stream(ORDERS, Consumed.with(Serdes.String(), orderSerde))
                .filter((key, order) -> order != null && order.merchantId() != null)
                .groupBy((key, order) -> order.merchantId(), Grouped.with(Serdes.String(), orderSerde))
                .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofSeconds(windowSeconds)))
                .aggregate(
                        () -> new Acc(0, BigDecimal.ZERO),
                        (merchant, order, acc) -> acc.add(order.total()),
                        Materialized.with(Serdes.String(), accSerde))
                .toStream()
                .map((window, acc) -> {
                    String merchant = window.key();
                    long start = window.window().start() / 1000;
                    BigDecimal revenue = acc.total().setScale(2, RoundingMode.HALF_UP);
                    Log.infof("emitted revenue window=%d merchant=%s count=%d revenue=%s",
                            start, merchant, acc.count(), revenue);
                    return KeyValue.pair(merchant,
                            new RevenueWindow(start, start + windowSeconds, merchant, acc.count(), revenue));
                })
                .to(REVENUE, Produced.with(Serdes.String(), revenueSerde));

        return builder.build();
    }
}
