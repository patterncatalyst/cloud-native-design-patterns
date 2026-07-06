package com.cndp.ws;

import org.springframework.web.socket.WebSocketSession;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Tracks a connected WebSocket client: its session, sequence counter,
 * and a ring-buffer of the last {@value BUFFER_SIZE} messages for resume.
 */
public class ClientSession {

    static final int BUFFER_SIZE = 100;

    private final String clientId;
    private final WebSocketSession session;
    private final AtomicLong seq = new AtomicLong(0);
    private final List<MessageFrame> buffer = new ArrayList<>();

    public ClientSession(String clientId, WebSocketSession session) {
        this.clientId = clientId;
        this.session = session;
    }

    public String getClientId() {
        return clientId;
    }

    public WebSocketSession getSession() {
        return session;
    }

    public long nextSeq() {
        return seq.incrementAndGet();
    }

    public synchronized void addToBuffer(MessageFrame frame) {
        buffer.add(frame);
        if (buffer.size() > BUFFER_SIZE) {
            buffer.remove(0);
        }
    }

    public synchronized List<MessageFrame> getMissedMessages(long afterSeq) {
        List<MessageFrame> missed = new ArrayList<>();
        for (MessageFrame f : buffer) {
            if (f.seq() > afterSeq) {
                missed.add(f);
            }
        }
        return missed;
    }
}
