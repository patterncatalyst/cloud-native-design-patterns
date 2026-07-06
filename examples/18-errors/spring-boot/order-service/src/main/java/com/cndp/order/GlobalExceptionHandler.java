package com.cndp.order;

import io.opentelemetry.api.trace.Span;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.UUID;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);
    private static final MediaType PROBLEM_JSON = MediaType.parseMediaType("application/problem+json");

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorResponse> handleBadRequest(HttpMessageNotReadableException ex) {
        ErrorResponse body = new ErrorResponse("VALIDATION_ERROR", "request validation failed", getTraceId());
        body.setDetail("request body is missing or malformed");
        body.setRetryable(false);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(PROBLEM_JSON);

        return new ResponseEntity<>(body, headers, HttpStatus.UNPROCESSABLE_ENTITY);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleUnexpected(Exception ex) {
        log.error("unhandled exception", ex);

        ErrorResponse body = new ErrorResponse("INTERNAL_ERROR", "an unexpected error occurred", getTraceId());
        body.setRetryable(false);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(PROBLEM_JSON);

        return new ResponseEntity<>(body, headers, HttpStatus.INTERNAL_SERVER_ERROR);
    }

    private String getTraceId() {
        Span span = Span.current();
        if (span != null && span.getSpanContext().isValid()) {
            return span.getSpanContext().getTraceId();
        }
        return UUID.randomUUID().toString().replace("-", "");
    }
}
