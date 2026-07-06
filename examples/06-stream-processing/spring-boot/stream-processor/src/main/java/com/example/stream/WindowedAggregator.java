package com.example.stream;

import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class WindowedAggregator {

    private static final Logger log = LoggerFactory.getLogger(WindowedAggregator.class);

    private final KafkaTemplate<String, RevenueResult> kafkaTemplate;
    private final int windowSeconds;

    // windowStart -> merchantId -> accumulator
    private final ConcurrentHashMap<Long, ConcurrentHashMap<String, MerchantAccumulator>> windows =
            new ConcurrentHashMap<>();

    public WindowedAggregator(
            KafkaTemplate<String, RevenueResult> kafkaTemplate,
            @Value("${window.seconds:10}") int windowSeconds) {
        this.kafkaTemplate = kafkaTemplate;
        this.windowSeconds = windowSeconds;
        log.info("stream-processor started (window={}s)", windowSeconds);
    }

    @KafkaListener(topics = "order.placed", groupId = "stream-processor")
    public void onOrderPlaced(OrderEvent order) {
        long now = System.currentTimeMillis() / 1000;
        long windowStart = floorToWindow(now);

        String merchantId = order.merchantId();
        BigDecimal total = order.total() != null ? order.total() : BigDecimal.ZERO;

        windows.computeIfAbsent(windowStart, k -> new ConcurrentHashMap<>())
                .computeIfAbsent(merchantId, k -> new MerchantAccumulator())
                .add(total);

        log.debug("aggregated order merchant={} total={} window={}", merchantId, total, windowStart);
    }

    @Scheduled(fixedRate = 1000)
    public void flushExpiredWindows() {
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
    public void flushRemainingWindows() {
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
            RevenueResult result = new RevenueResult(
                    windowStart, windowEnd, merchantId,
                    acc.count(), acc.total().setScale(2, RoundingMode.HALF_UP)
            );
            kafkaTemplate.send("revenue.by-merchant", merchantId, result);
            log.info("emitted revenue window={} merchant={} count={} revenue={}",
                    windowStart, merchantId, acc.count(), acc.total());
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
