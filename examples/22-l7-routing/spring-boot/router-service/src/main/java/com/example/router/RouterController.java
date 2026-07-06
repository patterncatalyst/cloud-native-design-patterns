package com.example.router;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class RouterController {

    private static final Logger logger = LoggerFactory.getLogger(RouterController.class);

    private final Map<String, Object> rules = new ConcurrentHashMap<>();

    public RouterController() {
        rules.put("vip_threshold", 1000);
        rules.put("priority_topic", "orders.priority");
        rules.put("default_topic", "orders.default");
    }

    @PostMapping("/orders")
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> routeOrder(@RequestBody Map<String, Object> body) {
        double amount = ((Number) body.get("amount")).doubleValue();
        int threshold = ((Number) rules.get("vip_threshold")).intValue();

        Map<String, Object> result = new LinkedHashMap<>();

        if (amount >= threshold) {
            String topic = (String) rules.get("priority_topic");
            logger.info("ROUTED sku={} amount={} -> {} (VIP)", body.get("sku"), amount, topic);
            result.put("routed_to", topic);
            result.put("vip", true);
            result.put("amount", amount);
        } else {
            String topic = (String) rules.get("default_topic");
            logger.info("ROUTED sku={} amount={} -> {}", body.get("sku"), amount, topic);
            result.put("routed_to", topic);
            result.put("vip", false);
            result.put("amount", amount);
        }

        return result;
    }

    @GetMapping("/rules")
    public Map<String, Object> getRules() {
        return new LinkedHashMap<>(rules);
    }

    @PutMapping("/rules")
    public Map<String, Object> updateRules(@RequestBody Map<String, Object> newRules) {
        rules.putAll(newRules);
        logger.info("RULES_UPDATED {}", rules);
        return new LinkedHashMap<>(rules);
    }

    @GetMapping("/healthz")
    public Map<String, Object> healthz() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", "ok");
        return result;
    }
}
