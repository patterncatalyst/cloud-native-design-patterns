package com.example.cache;

import java.util.Map;

public record EventView(String id, String type, Map<String, Object> payload) {

    EventResponse from(String source) {
        return new EventResponse(id, type, payload, source);
    }
}
