package com.cndp.order;

import com.fasterxml.jackson.annotation.JsonInclude;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record ErrorResponse(
        String code,
        String message,
        String traceId,
        String detail,
        boolean retryable,
        Integer retryAfter) {
}
