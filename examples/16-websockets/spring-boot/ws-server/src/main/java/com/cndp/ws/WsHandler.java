package com.cndp.ws;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import org.springframework.web.util.UriTemplate;

import java.net.URI;
import java.util.Map;

/**
 * Raw WebSocket handler (not STOMP).
 * <p>
 * Endpoint: /ws/{clientId}
 * <p>
 * On message: if {"type":"ping"}, responds with {"type":"pong","pod":"<POD_NAME>"}.
 */
@Component
public class WsHandler extends TextWebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(WsHandler.class);
    private static final ObjectMapper mapper = new ObjectMapper();
    private static final UriTemplate URI_TEMPLATE = new UriTemplate("/ws/{clientId}");

    @Value("${POD_NAME:ws-pod-unknown}")
    private String podName;

    private final ClientRegistry registry;

    public WsHandler(ClientRegistry registry) {
        this.registry = registry;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        String clientId = extractClientId(session);
        if (clientId == null) {
            session.close(CloseStatus.BAD_DATA);
            return;
        }

        ClientSession cs = new ClientSession(clientId, session);
        registry.register(clientId, cs);

        // Handle resume: replay missed messages if resume_seq query param is present
        URI uri = session.getUri();
        if (uri != null && uri.getQuery() != null) {
            String query = uri.getQuery();
            for (String param : query.split("&")) {
                String[] kv = param.split("=", 2);
                if ("resume_seq".equals(kv[0]) && kv.length == 2) {
                    long resumeSeq = Long.parseLong(kv[1]);
                    var missed = cs.getMissedMessages(resumeSeq);
                    for (MessageFrame frame : missed) {
                        String json = mapper.writeValueAsString(frame);
                        session.sendMessage(new TextMessage(json));
                    }
                    log.info("Replayed {} missed messages for client={} from seq={}",
                            missed.size(), clientId, resumeSeq);
                    break;
                }
            }
        }

        log.info("Client connected: {} on pod {}", clientId, podName);
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        try {
            JsonNode node = mapper.readTree(payload);
            String type = node.has("type") ? node.get("type").asText() : "";

            if ("ping".equals(type)) {
                String pong = mapper.writeValueAsString(
                        Map.of("type", "pong", "pod", podName));
                session.sendMessage(new TextMessage(pong));
            }
        } catch (Exception e) {
            log.warn("Failed to parse message from {}: {}", extractClientId(session), e.getMessage());
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        String clientId = extractClientId(session);
        if (clientId != null) {
            registry.unregister(clientId);
            log.info("Client disconnected: {} on pod {}", clientId, podName);
        }
    }

    private String extractClientId(WebSocketSession session) {
        URI uri = session.getUri();
        if (uri == null) {
            return null;
        }
        Map<String, String> vars = URI_TEMPLATE.match(uri.getPath());
        return vars != null ? vars.get("clientId") : null;
    }
}
