package com.cndp.order;

/** A failure with a stable error code; ExceptionMappers turns it into the problem+json body. */
public class ProblemException extends RuntimeException {

    private final int status;
    private final String code;
    private final String detail;
    private final boolean retryable;
    private final Integer retryAfter;

    public ProblemException(int status, String code, String message, String detail,
                            boolean retryable, Integer retryAfter) {
        super(message);
        this.status = status;
        this.code = code;
        this.detail = detail;
        this.retryable = retryable;
        this.retryAfter = retryAfter;
    }

    public static ProblemException validation(String detail) {
        return new ProblemException(422, "VALIDATION_ERROR", "request validation failed", detail, false, null);
    }

    public int status() { return status; }
    public String code() { return code; }
    public String detail() { return detail; }
    public boolean retryable() { return retryable; }
    public Integer retryAfter() { return retryAfter; }
}
