package com.cndp.ws;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.quarkus.websockets.next.OnClose;
import io.quarkus.websockets.next.OnOpen;
import io.quarkus.websockets.next.OnTextMessage;
import io.quarkus.websockets.next.WebSocket;
import io.quarkus.websockets.next.WebSocketConnection;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.jboss.logging.Logger;

import java.util.Map;

@WebSocket(path = "/ws/{clientId}")
public class WsEndpoint {
    private static final Logger LOG = Logger.getLogger(WsEndpoint.class);

    @Inject
    ClientRegistry registry;

    @Inject
    ObjectMapper mapper;

    @Inject
    WebSocketConnection connection;

    @ConfigProperty(name = "pod.name", defaultValue = "ws-pod-unknown")
    String podName;

    @OnOpen
    void onOpen() {
        String clientId = connection.pathParam("clientId");
        registry.register(clientId);
        LOG.infof("Client connected: %s on pod %s", clientId, podName);
    }

    @OnTextMessage
    void onMessage(String message) {
        try {
            JsonNode node = mapper.readTree(message);
            String type = node.has("type") ? node.get("type").asText() : "";

            if ("ping".equals(type)) {
                String pong = mapper.writeValueAsString(Map.of("type", "pong", "pod", podName));
                connection.sendTextAndAwait(pong);
            }
        } catch (Exception e) {
            LOG.warnf("Failed to parse message: %s", e.getMessage());
        }
    }

    @OnClose
    void onClose() {
        String clientId = connection.pathParam("clientId");
        registry.unregister(clientId);
        LOG.infof("Client disconnected: %s on pod %s", clientId, podName);
    }
}
