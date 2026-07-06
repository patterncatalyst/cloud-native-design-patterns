package com.cndp.ws;

/**
 * A sequenced message frame sent to a WebSocket client.
 */
public record MessageFrame(long seq, String data) {
}
