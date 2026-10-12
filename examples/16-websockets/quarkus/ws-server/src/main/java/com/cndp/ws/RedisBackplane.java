package com.cndp.ws;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.quarkus.redis.datasource.RedisDataSource;
import io.quarkus.redis.datasource.pubsub.PubSubCommands;
import io.quarkus.runtime.StartupEvent;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.event.Observes;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.jboss.logging.Logger;

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
            String json = mapper.writeValueAsString(new BackplaneMessage(podName, target, message));
            redisDataSource.pubsub(String.class).publish(CHANNEL, json);
        } catch (Exception e) {
            LOG.error("Publish failed", e);
        }
    }

    private void handleBackplaneMessage(String json) {
        try {
            BackplaneMessage message = mapper.readValue(json, BackplaneMessage.class);
            String senderPod = message.pod() != null ? message.pod() : "";
            String target = message.target();
            String data = message.data() != null ? message.data() : "";

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
