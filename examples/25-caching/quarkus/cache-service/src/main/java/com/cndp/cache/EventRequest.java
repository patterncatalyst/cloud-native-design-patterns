package com.cndp.cache;

import java.util.Map;

public record EventRequest(String id, String type, Map<String, Object> payload) {}
