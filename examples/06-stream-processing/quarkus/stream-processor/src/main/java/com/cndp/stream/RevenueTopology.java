package com.cndp.stream;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.quarkus.kafka.client.serialization.ObjectMapperSerde;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import jakarta.inject.Inject;
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
import org.jboss.logging.Logger;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * order.placed -> tumbling window per merchant -> revenue.by-merchant.
 *
 * The windowed aggregate is a KTable; every update to a (merchant, window) row is
 * emitted downstream, so a window yields a running total that settles when the
 * window closes. Consumers keep the latest record per (merchant_id, window_start).
 */
@ApplicationScoped
public class RevenueTopology {

    private static final Logger LOG = Logger.getLogger(RevenueTopology.class);

    static final String ORDERS = "order.placed";
    static final String REVENUE = "revenue.by-merchant";

    @Inject
    ObjectMapper mapper;

    @ConfigProperty(name = "window.seconds", defaultValue = "10")
    int windowSeconds;

    public record Acc(int count, BigDecimal total) {
        Acc add(BigDecimal amount) {
            return new Acc(count + 1, total.add(amount));
        }
    }

    @Produces
    public Topology topology() {
        StreamsBuilder builder = new StreamsBuilder();
        ObjectMapperSerde<Acc> accSerde = new ObjectMapperSerde<>(Acc.class);

        builder.stream(ORDERS, Consumed.with(Serdes.String(), Serdes.String()))
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
                    Map<String, Object> out = new LinkedHashMap<>();
                    out.put("window_start", start);
                    out.put("window_end", start + windowSeconds);
                    out.put("merchant_id", merchant);
                    out.put("order_count", acc.count());
                    out.put("revenue", acc.total().setScale(2, RoundingMode.HALF_UP));
                    LOG.infof("emitted revenue window=%d merchant=%s count=%d revenue=%s",
                            start, merchant, acc.count(), acc.total().setScale(2, RoundingMode.HALF_UP));
                    return KeyValue.pair(merchant, write(out));
                })
                .to(REVENUE, Produced.with(Serdes.String(), Serdes.String()));

        return builder.build();
    }

    /** A total that is not a number skips the record instead of killing the stream thread. */
    private Acc add(String merchant, Acc acc, String amount) {
        try {
            return acc.add(new BigDecimal(amount));
        } catch (NumberFormatException e) {
            LOG.warnf("skipping order with invalid total merchant=%s total=%s", merchant, amount);
            return acc;
        }
    }

    /** Re-keys an order event by merchant; the value is the order total. */
    private KeyValue<String, String> parse(String json) {
        try {
            JsonNode event = mapper.readTree(json);
            JsonNode total = event.get("total");
            String amount = total == null || total.isNull() ? "0" : total.asText();
            return KeyValue.pair(event.get("merchant_id").asText(), amount);
        } catch (Exception e) {
            return KeyValue.pair(null, null);
        }
    }

    private String write(Map<String, Object> out) {
        try {
            return mapper.writeValueAsString(out);
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }
}
