package com.example.cache;

import java.util.Map;

public record EventResponse(String id, String type, Map<String, Object> payload, String source) {
}
