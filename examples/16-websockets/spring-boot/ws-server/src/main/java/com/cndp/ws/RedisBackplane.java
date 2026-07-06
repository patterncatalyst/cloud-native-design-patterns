package com.cndp.ws;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.connection.Message;
import org.springframework.data.redis.connection.MessageListener;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.listener.ChannelTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.stereotype.Component;

import jakarta.annotation.PostConstruct;
import java.util.Map;

/**
 * Redis pub/sub backplane for cross-pod WebSocket message delivery.
 * <p>
 * Subscribes to the "ws:broadcast" channel. When a message arrives from
 * another pod, delivers it to local clients matching the target (or all
 * clients if no target is specified).
 */
@Component
public class RedisBackplane implements MessageListener {

    private static final Logger log = LoggerFactory.getLogger(RedisBackplane.class);
    private static final ObjectMapper mapper = new ObjectMapper();
    private static final String CHANNEL = "ws:broadcast";

    @Value("${POD_NAME:ws-pod-unknown}")
    private String podName;

    private final StringRedisTemplate redisTemplate;
    private final RedisMessageListenerContainer listenerContainer;
    private final ClientRegistry registry;

    public RedisBackplane(StringRedisTemplate redisTemplate,
                          RedisMessageListenerContainer listenerContainer,
                          ClientRegistry registry) {
        this.redisTemplate = redisTemplate;
        this.listenerContainer = listenerContainer;
        this.registry = registry;
    }

    @PostConstruct
    public void subscribe() {
        listenerContainer.addMessageListener(this, new ChannelTopic(CHANNEL));
        log.info("Subscribed to Redis channel '{}' on pod {}", CHANNEL, podName);
    }

    /**
     * Publish a message to the Redis backplane.
     *
     * @param target  target client ID, or null for broadcast
     * @param message the message payload
     */
    public void publish(String target, String message) {
        try {
            Map<String, Object> payload = new java.util.LinkedHashMap<>();
            payload.put("pod", podName);
            payload.put("target", target);
            payload.put("data", message);
            String json = mapper.writeValueAsString(payload);
            redisTemplate.convertAndSend(CHANNEL, json);
        } catch (Exception e) {
            log.error("Failed to publish to Redis: {}", e.getMessage());
        }
    }

    @Override
    public void onMessage(Message message, byte[] pattern) {
        try {
            JsonNode node = mapper.readTree(message.getBody());
            String senderPod = node.has("pod") ? node.get("pod").asText() : "";
            String target = node.has("target") && !node.get("target").isNull()
                    ? node.get("target").asText() : null;
            String data = node.has("data") ? node.get("data").asText() : "";

            // Skip messages from this pod (already delivered locally)
            if (podName.equals(senderPod)) {
                return;
            }

            if (target != null) {
                registry.sendToClient(target, data);
            } else {
                registry.broadcast(data);
            }
        } catch (Exception e) {
            log.error("Failed to process backplane message: {}", e.getMessage());
        }
    }
}
