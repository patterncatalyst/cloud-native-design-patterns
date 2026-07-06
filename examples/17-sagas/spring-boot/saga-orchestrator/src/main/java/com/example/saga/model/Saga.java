package com.example.saga.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

public record Saga(
    String id,
    String status,
    @JsonProperty("step_index") int stepIndex,
    Map<String, Object> context
) {}
