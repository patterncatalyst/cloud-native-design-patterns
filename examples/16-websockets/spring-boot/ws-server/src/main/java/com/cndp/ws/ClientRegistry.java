package com.cndp.ws;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.TextMessage;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Thread-safe registry of connected WebSocket clients on this pod.
 * Handles sending sequenced message frames.
 */
@Component
public class ClientRegistry {

    private static final Logger log = LoggerFactory.getLogger(ClientRegistry.class);
    private static final ObjectMapper mapper = new ObjectMapper();

    private final Map<String, ClientSession> clients = new ConcurrentHashMap<>();

    public void register(String clientId, ClientSession session) {
        clients.put(clientId, session);
        log.info("Client registered: {}", clientId);
    }

    public void unregister(String clientId) {
        clients.remove(clientId);
        log.info("Client unregistered: {}", clientId);
    }

    public ClientSession get(String clientId) {
        return clients.get(clientId);
    }

    public boolean hasClient(String clientId) {
        return clients.containsKey(clientId);
    }

    /**
     * Send a sequenced message frame to a specific client.
     */
    public void sendToClient(String clientId, String data) {
        ClientSession cs = clients.get(clientId);
        if (cs == null) {
            return;
        }
        long seq = cs.nextSeq();
        MessageFrame frame = new MessageFrame(seq, data);
        cs.addToBuffer(frame);
        sendFrame(cs, frame);
    }

    /**
     * Broadcast a sequenced message frame to all connected clients.
     */
    public void broadcast(String data) {
        for (Map.Entry<String, ClientSession> entry : clients.entrySet()) {
            ClientSession cs = entry.getValue();
            long seq = cs.nextSeq();
            MessageFrame frame = new MessageFrame(seq, data);
            cs.addToBuffer(frame);
            sendFrame(cs, frame);
        }
    }

    private void sendFrame(ClientSession cs, MessageFrame frame) {
        try {
            String json = mapper.writeValueAsString(frame);
            cs.getSession().sendMessage(new TextMessage(json));
        } catch (IOException e) {
            log.warn("Failed to send frame to {}: {}", cs.getClientId(), e.getMessage());
        }
    }
}
