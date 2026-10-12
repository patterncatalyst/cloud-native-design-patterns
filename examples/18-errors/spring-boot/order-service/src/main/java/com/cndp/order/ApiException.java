package com.cndp.order;

import org.springframework.http.HttpStatus;

/** A failure the API reports as an RFC 9457 problem with a stable {@code code}. */
public class ApiException extends RuntimeException {

    private final HttpStatus status;
    private final String code;
    private final String title;
    private final boolean retryable;
    private final Integer retryAfter;

    public ApiException(HttpStatus status, String code, String title, String detail,
                        boolean retryable, Integer retryAfter) {
        super(detail);
        this.status = status;
        this.code = code;
        this.title = title;
        this.retryable = retryable;
        this.retryAfter = retryAfter;
    }

    public HttpStatus status() {
        return status;
    }

    public String code() {
        return code;
    }

    public String title() {
        return title;
    }

    public boolean retryable() {
        return retryable;
    }

    public Integer retryAfter() {
        return retryAfter;
    }
}
