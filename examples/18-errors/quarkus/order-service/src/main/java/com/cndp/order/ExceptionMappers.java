package com.cndp.order;

import com.fasterxml.jackson.core.JsonProcessingException;
import io.opentelemetry.api.trace.Span;
import io.quarkus.logging.Log;
import jakarta.ws.rs.core.Response;
import org.jboss.resteasy.reactive.server.ServerExceptionMapper;

import java.util.UUID;

public class ExceptionMappers {

    @ServerExceptionMapper
    public Response handleJsonProcessing(JsonProcessingException e) {
        ErrorResponse body = new ErrorResponse("VALIDATION_ERROR", "request validation failed",
                getTraceId(), "request body is missing or malformed", false, null);
        return Response.status(422)
                .type("application/problem+json")
                .entity(body)
                .build();
    }

    @ServerExceptionMapper
    public Response handleGenericException(Exception e) {
        Log.error("unhandled exception", e);
        ErrorResponse body = new ErrorResponse("INTERNAL_ERROR", "an unexpected error occurred",
                getTraceId(), null, false, null);
        return Response.status(500)
                .type("application/problem+json")
                .entity(body)
                .build();
    }

    private String getTraceId() {
        Span span = Span.current();
        if (span != null && span.getSpanContext().isValid()) {
            return span.getSpanContext().getTraceId();
        }
        return UUID.randomUUID().toString().replace("-", "");
    }
}
