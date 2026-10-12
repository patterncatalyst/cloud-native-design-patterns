package com.cndp.order;

import java.util.UUID;
import java.util.stream.Collectors;

import io.grpc.StatusRuntimeException;
import io.opentelemetry.api.trace.Span;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

/**
 * Maps every failure to an RFC 9457 {@link ProblemDetail}. The extension members
 * {@code code}, {@code traceId}, {@code retryable} and {@code retryAfter} are properties of the
 * problem, serialized at the top level of the JSON body.
 */
@RestControllerAdvice
public class ApiErrors extends ResponseEntityExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(ApiErrors.class);

    @ExceptionHandler(ApiException.class)
    ResponseEntity<Object> handleApi(ApiException ex) {
        return problem(ex.status(), ex.code(), ex.title(), ex.getMessage(), ex.retryable(), ex.retryAfter());
    }

    @ExceptionHandler(StatusRuntimeException.class)
    ResponseEntity<Object> handleGrpc(StatusRuntimeException ex) {
        return switch (ex.getStatus().getCode()) {
            case RESOURCE_EXHAUSTED -> problem(HttpStatus.CONFLICT, "STOCK_UNAVAILABLE",
                    "insufficient stock", ex.getStatus().getDescription(), false, null);
            case DEADLINE_EXCEEDED, UNAVAILABLE -> problem(HttpStatus.SERVICE_UNAVAILABLE, "INVENTORY_UNAVAILABLE",
                    "inventory service is temporarily unavailable",
                    "gRPC " + ex.getStatus().getCode().name().toLowerCase(), true, 2);
            default -> {
                log.error("unexpected gRPC error from inventory: status={} desc={}",
                        ex.getStatus().getCode(), ex.getStatus().getDescription(), ex);
                yield problem(HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR",
                        "unexpected error from inventory service", ex.getStatus().getDescription(), false, null);
            }
        };
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<Object> handleUnexpected(Exception ex) {
        log.error("unhandled exception", ex);
        return problem(HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR",
                "an unexpected error occurred", null, false, null);
    }

    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(MethodArgumentNotValidException ex,
            HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        String detail = ex.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining("; "));
        return problem(HttpStatus.UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "request validation failed",
                detail, false, null);
    }

    @Override
    protected ResponseEntity<Object> handleHttpMessageNotReadable(HttpMessageNotReadableException ex,
            HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        return problem(HttpStatus.UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "request validation failed",
                "request body is missing or malformed", false, null);
    }

    private ResponseEntity<Object> problem(HttpStatus status, String code, String title, String detail,
                                           boolean retryable, Integer retryAfter) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(status, detail);
        problem.setTitle(title);
        problem.setProperty("code", code);
        problem.setProperty("traceId", traceId());
        problem.setProperty("retryable", retryable);
        var response = ResponseEntity.status(status);
        if (retryAfter != null) {
            problem.setProperty("retryAfter", retryAfter);
            response.header(HttpHeaders.RETRY_AFTER, retryAfter.toString());
        }
        return response.body(problem);
    }

    private static String traceId() {
        Span span = Span.current();
        return span.getSpanContext().isValid()
                ? span.getSpanContext().getTraceId()
                : UUID.randomUUID().toString().replace("-", "");
    }
}
