package com.example.decorator;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;

@RestController
public class DecoratorController {

    private static final Logger logger = LoggerFactory.getLogger(DecoratorController.class);
    private static final String TOPIC = "order.placed";
    private static final long CACHE_TTL_SECONDS = 60;

    @Value("${LEGACY_URL:http://legacy:8080}")
    private String legacyUrl;

    private final RestClient restClient;
    private final StringRedisTemplate redisTemplate;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;
    private final List<Map<String, Object>> publishedEvents = Collections.synchronizedList(new ArrayList<>());

    public DecoratorController(RestClient restClient,
                               StringRedisTemplate redisTemplate,
                               KafkaTemplate<String, String> kafkaTemplate,
                               ObjectMapper objectMapper) {
        this.restClient = restClient;
        this.redisTemplate = redisTemplate;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @SuppressWarnings("unchecked")
    @PostMapping("/orders")
    public ResponseEntity<String> createOrder(@RequestBody String body) {
        // Forward to legacy
        String response = restClient.post()
                .uri(legacyUrl + "/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .body(body)
                .retrieve()
                .body(String.class);

        // Parse response to extract order_id
        String orderId = null;
        try {
            Map<String, Object> data = objectMapper.readValue(response, Map.class);
            orderId = String.valueOf(data.get("id"));
        } catch (JsonProcessingException e) {
            logger.warn("Failed to parse legacy response: {}", e.getMessage());
        }

        // Build event
        Map<String, Object> event = new LinkedHashMap<>();
        event.put("event", TOPIC);
        event.put("order_id", orderId);
        try {
            Map<String, Object> bodyMap = objectMapper.readValue(body, Map.class);
            event.putAll(bodyMap);
        } catch (JsonProcessingException e) {
            // ignore
        }
        publishedEvents.add(event);

        // Publish to Kafka
        try {
            String eventJson = objectMapper.writeValueAsString(event);
            kafkaTemplate.send(TOPIC, eventJson);
            logger.info("EVENT order.placed -> Kafka order_id={}", orderId);
        } catch (Exception e) {
            logger.warn("Kafka publish failed: {}", e.getMessage());
        }

        return ResponseEntity.status(HttpStatus.CREATED)
                .contentType(MediaType.APPLICATION_JSON)
                .body(response);
    }

    @GetMapping("/orders/{orderId}")
    public ResponseEntity<String> getOrder(@PathVariable String orderId) {
        String cacheKey = "order:" + orderId;

        // Check cache
        try {
            String cached = redisTemplate.opsForValue().get(cacheKey);
            if (cached != null) {
                logger.info("CACHE_HIT order_id={}", orderId);
                return ResponseEntity.ok()
                        .contentType(MediaType.APPLICATION_JSON)
                        .body(cached);
            }
        } catch (Exception e) {
            logger.warn("Redis get failed: {}", e.getMessage());
        }

        // Cache miss — fetch from legacy
        logger.info("CACHE_MISS order_id={}", orderId);
        String response = restClient.get()
                .uri(legacyUrl + "/orders/" + orderId)
                .retrieve()
                .body(String.class);

        // Store in cache
        try {
            redisTemplate.opsForValue().set(cacheKey, response, Duration.ofSeconds(CACHE_TTL_SECONDS));
        } catch (Exception e) {
            logger.warn("Redis set failed: {}", e.getMessage());
        }

        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_JSON)
                .body(response);
    }

    @GetMapping("/events")
    public List<Map<String, Object>> listEvents() {
        return publishedEvents;
    }
}
