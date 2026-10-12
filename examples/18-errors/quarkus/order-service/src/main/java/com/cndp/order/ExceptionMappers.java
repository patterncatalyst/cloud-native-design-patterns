package com.cndp.order;

import java.util.UUID;

import com.fasterxml.jackson.core.JsonProcessingException;
import io.opentelemetry.api.trace.Span;
import io.quarkus.logging.Log;
import jakarta.ws.rs.core.Response;
import org.jboss.resteasy.reactive.server.ServerExceptionMapper;

/** One place that renders every error as application/problem+json with the same fields. */
public class ExceptionMappers {

    @ServerExceptionMapper
    public Response handleProblem(ProblemException e) {
        ErrorResponse body = new ErrorResponse(e.code(), e.getMessage(), traceId(), e.detail(),
                e.retryable(), e.retryAfter());
        Response.ResponseBuilder builder = problem(e.status(), body);
        if (e.retryAfter() != null) {
            builder.header("Retry-After", e.retryAfter().toString());
        }
        return builder.build();
    }

    @ServerExceptionMapper
    public Response handleJsonProcessing(JsonProcessingException e) {
        ErrorResponse body = new ErrorResponse("VALIDATION_ERROR", "request validation failed",
                traceId(), "request body is missing or malformed", false, null);
        return problem(422, body).build();
    }

    @ServerExceptionMapper
    public Response handleGenericException(Exception e) {
        Log.error("unhandled exception", e);
        ErrorResponse body = new ErrorResponse("INTERNAL_ERROR", "an unexpected error occurred",
                traceId(), null, false, null);
        return problem(500, body).build();
    }

    private static Response.ResponseBuilder problem(int status, ErrorResponse body) {
        return Response.status(status).type("application/problem+json").entity(body);
    }

    private static String traceId() {
        Span span = Span.current();
        if (span != null && span.getSpanContext().isValid()) {
            return span.getSpanContext().getTraceId();
        }
        return UUID.randomUUID().toString().replace("-", "");
    }
}
