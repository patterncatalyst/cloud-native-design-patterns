package com.cndp.saga.model;

import java.util.Map;

public record SagaLogEntry(String step, String action, Map<String, Object> result) {}
