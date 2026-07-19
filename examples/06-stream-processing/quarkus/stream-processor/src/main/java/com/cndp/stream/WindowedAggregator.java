package com.cndp.stream;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.quarkus.scheduler.Scheduled;
import jakarta.annotation.PreDestroy;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.eclipse.microprofile.reactive.messaging.Channel;
import org.eclipse.microprofile.reactive.messaging.Emitter;
import org.eclipse.microprofile.reactive.messaging.Incoming;
import org.jboss.logging.Logger;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@ApplicationScoped
public class WindowedAggregator {

    private static final Logger log = Logger.getLogger(WindowedAggregator.class);

    @Inject
    ObjectMapper objectMapper;

    @Inject
    @Channel("revenue-out")
    Emitter<String> revenueEmitter;

    @ConfigProperty(name = "window.seconds", defaultValue = "10")
    int windowSeconds;

    private final ConcurrentHashMap<Long, ConcurrentHashMap<String, MerchantAccumulator>> windows =
            new ConcurrentHashMap<>();

    @Incoming("order-placed")
    public void onOrderPlaced(String message) {
        try {
            JsonNode event = objectMapper.readTree(message);
            long now = System.currentTimeMillis() / 1000;
            long windowStart = floorToWindow(now);

            String merchantId = event.get("merchant_id").asText();
            BigDecimal total = event.has("total") && !event.get("total").isNull()
                    ? new BigDecimal(event.get("total").asText())
                    : BigDecimal.ZERO;

            windows.computeIfAbsent(windowStart, k -> new ConcurrentHashMap<>())
                    .computeIfAbsent(merchantId, k -> new MerchantAccumulator())
                    .add(total);

            log.debugf("aggregated order merchant=%s total=%s window=%d", merchantId, total, windowStart);
        } catch (Exception e) {
            log.errorf("Failed to process order event: %s", e.getMessage());
        }
    }

    @Scheduled(every = "1s")
    void flushExpiredWindows() {
        long currentWindow = floorToWindow(System.currentTimeMillis() / 1000);
        for (Map.Entry<Long, ConcurrentHashMap<String, MerchantAccumulator>> entry :
                windows.entrySet()) {
            long windowStart = entry.getKey();
            if (windowStart < currentWindow) {
                emitWindow(windowStart, entry.getValue());
                windows.remove(windowStart);
            }
        }
    }

    @PreDestroy
    void flushRemainingWindows() {
        log.info("flushing remaining windows on shutdown");
        for (Map.Entry<Long, ConcurrentHashMap<String, MerchantAccumulator>> entry :
                windows.entrySet()) {
            emitWindow(entry.getKey(), entry.getValue());
        }
        windows.clear();
    }

    private void emitWindow(long windowStart, ConcurrentHashMap<String, MerchantAccumulator> merchants) {
        long windowEnd = windowStart + windowSeconds;
        for (Map.Entry<String, MerchantAccumulator> me : merchants.entrySet()) {
            String merchantId = me.getKey();
            MerchantAccumulator acc = me.getValue();
            try {
                String json = objectMapper.writeValueAsString(Map.of(
                    "window_start", windowStart,
                    "window_end", windowEnd,
                    "merchant_id", merchantId,
                    "order_count", acc.count(),
                    "revenue", acc.total().setScale(2, RoundingMode.HALF_UP)
                ));
                revenueEmitter.send(json);
                log.infof("emitted revenue window=%d merchant=%s count=%d revenue=%s",
                        windowStart, merchantId, acc.count(), acc.total());
            } catch (Exception e) {
                log.errorf("Failed to emit revenue: %s", e.getMessage());
            }
        }
    }

    private long floorToWindow(long epochSeconds) {
        return (epochSeconds / windowSeconds) * windowSeconds;
    }

    private static class MerchantAccumulator {
        private int count;
        private BigDecimal total = BigDecimal.ZERO;

        synchronized void add(BigDecimal amount) {
            count++;
            total = total.add(amount);
        }

        synchronized int count() {
            return count;
        }

        synchronized BigDecimal total() {
            return total;
        }
    }
}
