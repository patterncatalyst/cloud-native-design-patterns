package com.cndp.ws;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.quarkus.websockets.next.OpenConnections;
import io.quarkus.websockets.next.WebSocketConnection;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.jboss.logging.Logger;

import java.util.concurrent.ConcurrentHashMap;

@ApplicationScoped
public class ClientRegistry {
    private static final Logger LOG = Logger.getLogger(ClientRegistry.class);

    private final ConcurrentHashMap<String, ClientEntry> clients = new ConcurrentHashMap<>();

    @Inject
    OpenConnections openConnections;

    @Inject
    ObjectMapper mapper;

    public void register(String clientId) {
        clients.put(clientId, new ClientEntry(clientId));
    }

    public void unregister(String clientId) {
        clients.remove(clientId);
    }

    public void sendToClient(String clientId, String data) {
        ClientEntry entry = clients.get(clientId);
        if (entry == null) return;

        long s = entry.nextSeq();
        MessageFrame frame = new MessageFrame(s, data);
        entry.addToBuffer(frame);

        WebSocketConnection conn = findConnection(clientId);
        if (conn != null) {
            sendFrame(conn, clientId, frame);
        }
    }

    public void broadcast(String data) {
        for (var e : clients.entrySet()) {
            String clientId = e.getKey();
            ClientEntry entry = e.getValue();

            long s = entry.nextSeq();
            MessageFrame frame = new MessageFrame(s, data);
            entry.addToBuffer(frame);

            WebSocketConnection conn = findConnection(clientId);
            if (conn != null) {
                sendFrame(conn, clientId, frame);
            }
        }
    }

    private WebSocketConnection findConnection(String clientId) {
        for (WebSocketConnection conn : openConnections) {
            if (clientId.equals(conn.pathParam("clientId"))) {
                return conn;
            }
        }
        return null;
    }

    private void sendFrame(WebSocketConnection conn, String clientId, MessageFrame frame) {
        try {
            String json = mapper.writeValueAsString(frame);
            conn.sendText(json).subscribe().with(
                    v -> {},
                    err -> LOG.errorf(err, "Failed to send to %s", clientId)
            );
        } catch (Exception e) {
            LOG.errorf(e, "Failed to serialize frame for %s", clientId);
        }
    }
}
