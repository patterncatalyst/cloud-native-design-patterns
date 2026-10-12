package com.example.stream;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Duration;

import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KeyValue;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.kstream.Consumed;
import org.apache.kafka.streams.kstream.Grouped;
import org.apache.kafka.streams.kstream.KStream;
import org.apache.kafka.streams.kstream.Materialized;
import org.apache.kafka.streams.kstream.Produced;
import org.apache.kafka.streams.kstream.TimeWindows;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.annotation.EnableKafkaStreams;
import org.springframework.kafka.config.TopicBuilder;
import org.springframework.kafka.core.KafkaAdmin.NewTopics;
import org.springframework.kafka.support.serializer.JacksonJsonSerde;

/**
 * order.placed -> tumbling window per merchant -> revenue.by-merchant.
 *
 * The windowed aggregate is a KTable; every update to a (merchant, window) row is
 * emitted downstream, so a window yields a running total that settles when the
 * window closes. Consumers keep the latest record per (merchant_id, window_start).
 */
@Configuration
@EnableKafkaStreams
public class RevenueTopology {

    private static final Logger log = LoggerFactory.getLogger(RevenueTopology.class);

    static final String ORDERS = "order.placed";
    static final String REVENUE = "revenue.by-merchant";

    private final int windowSeconds;

    public RevenueTopology(@Value("${window.seconds:10}") int windowSeconds) {
        this.windowSeconds = windowSeconds;
        log.info("stream-processor started (window={}s)", windowSeconds);
    }

    public record Acc(int count, BigDecimal total) {
        Acc add(BigDecimal amount) {
            return new Acc(count + 1, total.add(amount));
        }
    }

    /**
     * Kafka Streams stops when a source topic is missing. The topic is created by the
     * broker (auto-create) when order-service first produces, which may be after this
     * service starts, so the admin client creates it up front. The sink topic is left
     * to the broker: it does not exist until Streams writes to it.
     */
    @Bean
    public NewTopics sourceTopics() {
        return new NewTopics(TopicBuilder.name(ORDERS).build());
    }

    @Bean
    public KStream<String, MerchantRevenue> revenueStream(StreamsBuilder builder) {
        var orderSerde = new JacksonJsonSerde<>(OrderPlaced.class).ignoreTypeHeaders().noTypeInfo();
        var accSerde = new JacksonJsonSerde<>(Acc.class).noTypeInfo();
        var revenueSerde = new JacksonJsonSerde<>(MerchantRevenue.class).noTypeInfo();

        var revenue = builder.stream(ORDERS, Consumed.with(Serdes.String(), orderSerde))
                .filter((key, order) -> order != null && order.merchantId() != null)
                .selectKey((key, order) -> order.merchantId())
                .groupByKey(Grouped.with(Serdes.String(), orderSerde))
                .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofSeconds(windowSeconds)))
                .aggregate(
                        () -> new Acc(0, BigDecimal.ZERO),
                        (merchant, order, acc) -> acc.add(order.total() == null ? BigDecimal.ZERO : order.total()),
                        Materialized.with(Serdes.String(), accSerde))
                .toStream()
                .map((window, acc) -> {
                    String merchant = window.key();
                    long start = window.window().start() / 1000;
                    BigDecimal revenueTotal = acc.total().setScale(2, RoundingMode.HALF_UP);
                    log.info("emitted revenue window={} merchant={} count={} revenue={}",
                            start, merchant, acc.count(), revenueTotal);
                    return KeyValue.pair(merchant,
                            new MerchantRevenue(start, start + windowSeconds, merchant, acc.count(), revenueTotal));
                });
        revenue.to(REVENUE, Produced.with(Serdes.String(), revenueSerde));
        return revenue;
    }
}
