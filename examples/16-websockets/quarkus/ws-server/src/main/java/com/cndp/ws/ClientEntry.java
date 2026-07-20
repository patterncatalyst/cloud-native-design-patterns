package com.cndp.ws;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

public class ClientEntry {
    static final int BUFFER_SIZE = 100;

    private final String clientId;
    private final AtomicLong seq = new AtomicLong(0);
    private final List<MessageFrame> buffer = Collections.synchronizedList(new ArrayList<>());

    public ClientEntry(String clientId) {
        this.clientId = clientId;
    }

    public String getClientId() {
        return clientId;
    }

    public long nextSeq() {
        return seq.incrementAndGet();
    }

    public void addToBuffer(MessageFrame frame) {
        buffer.add(frame);
        while (buffer.size() > BUFFER_SIZE) {
            buffer.remove(0);
        }
    }
}
