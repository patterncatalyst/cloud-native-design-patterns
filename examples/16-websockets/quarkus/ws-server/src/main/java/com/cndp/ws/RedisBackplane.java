package com.cndp.ws;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.quarkus.redis.datasource.RedisDataSource;
import io.quarkus.redis.datasource.pubsub.PubSubCommands;
import io.quarkus.runtime.StartupEvent;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.event.Observes;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.jboss.logging.Logger;

import java.util.LinkedHashMap;
import java.util.Map;

@ApplicationScoped
public class RedisBackplane {
    private static final Logger LOG = Logger.getLogger(RedisBackplane.class);
    private static final String CHANNEL = "ws:broadcast";

    @ConfigProperty(name = "pod.name", defaultValue = "ws-pod-unknown")
    String podName;

    @Inject
    RedisDataSource redisDataSource;

    @Inject
    ObjectMapper mapper;

    @Inject
    ClientRegistry registry;

    void onStart(@Observes StartupEvent ev) {
        PubSubCommands<String> pubsub = redisDataSource.pubsub(String.class);
        pubsub.subscribe(CHANNEL, this::handleBackplaneMessage);
        LOG.infof("Subscribed to %s on pod %s", CHANNEL, podName);
    }

    public void publish(String target, String message) {
        try {
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("pod", podName);
            payload.put("target", target);
            payload.put("data", message);
            String json = mapper.writeValueAsString(payload);
            redisDataSource.pubsub(String.class).publish(CHANNEL, json);
        } catch (Exception e) {
            LOG.error("Publish failed", e);
        }
    }

    private void handleBackplaneMessage(String json) {
        try {
            JsonNode node = mapper.readTree(json);
            String senderPod = node.has("pod") ? node.get("pod").asText() : "";
            String target = node.has("target") && !node.get("target").isNull()
                    ? node.get("target").asText() : null;
            String data = node.has("data") ? node.get("data").asText() : "";

            if (podName.equals(senderPod)) {
                return;
            }

            if (target != null) {
                registry.sendToClient(target, data);
            } else {
                registry.broadcast(data);
            }
        } catch (Exception e) {
            LOG.error("Failed to handle backplane message", e);
        }
    }
}
