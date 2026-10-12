package com.cndp.ws;

/** Redis pub/sub payload on ws:broadcast; a null target means every client. */
public record BackplaneMessage(String pod, String target, String data) {}
