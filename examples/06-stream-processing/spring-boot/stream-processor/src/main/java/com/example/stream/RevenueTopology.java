package com.example.stream;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;

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
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

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

    private static final JsonMapper MAPPER = JsonMapper.builder().build();

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
    public KStream<String, String> revenueStream(StreamsBuilder builder) {
        JacksonJsonSerde<Acc> accSerde = new JacksonJsonSerde<>(Acc.class).noTypeInfo();

        var revenue = builder.stream(ORDERS, Consumed.with(Serdes.String(), Serdes.String()))
                .map((key, json) -> parse(json))
                .filter((merchant, amount) -> merchant != null)
                .groupByKey(Grouped.with(Serdes.String(), Serdes.String()))
                .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofSeconds(windowSeconds)))
                .aggregate(
                        () -> new Acc(0, BigDecimal.ZERO),
                        (merchant, amount, acc) -> add(merchant, acc, amount),
                        Materialized.with(Serdes.String(), accSerde))
                .toStream()
                .map((window, acc) -> {
                    String merchant = window.key();
                    long start = window.window().start() / 1000;
                    BigDecimal revenueTotal = acc.total().setScale(2, RoundingMode.HALF_UP);
                    Map<String, Object> out = new LinkedHashMap<>();
                    out.put("window_start", start);
                    out.put("window_end", start + windowSeconds);
                    out.put("merchant_id", merchant);
                    out.put("order_count", acc.count());
                    out.put("revenue", revenueTotal);
                    log.info("emitted revenue window={} merchant={} count={} revenue={}",
                            start, merchant, acc.count(), revenueTotal);
                    return KeyValue.pair(merchant, MAPPER.writeValueAsString(out));
                });
        revenue.to(REVENUE, Produced.with(Serdes.String(), Serdes.String()));
        return revenue;
    }

    /** A total that is not a number skips the record instead of killing the stream thread. */
    private Acc add(String merchant, Acc acc, String amount) {
        try {
            return acc.add(new BigDecimal(amount));
        } catch (NumberFormatException e) {
            log.warn("skipping order with invalid total merchant={} total={}", merchant, amount);
            return acc;
        }
    }

    /** Re-keys an order event by merchant; the value is the order total. */
    private KeyValue<String, String> parse(String json) {
        try {
            JsonNode event = MAPPER.readTree(json);
            JsonNode total = event.get("total");
            String amount = total == null || total.isNull() ? "0" : total.asString();
            return KeyValue.pair(event.get("merchant_id").asString(), amount);
        } catch (Exception e) {
            return KeyValue.pair(null, null);
        }
    }
}
