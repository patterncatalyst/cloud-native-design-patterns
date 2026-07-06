package com.cndp.order;

import com.fasterxml.jackson.annotation.JsonInclude;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class ErrorResponse {
    private String code;
    private String message;
    private String traceId;
    private String detail;
    private Boolean retryable;
    private Integer retryAfter;

    public ErrorResponse() {}

    public ErrorResponse(String code, String message, String traceId) {
        this.code = code;
        this.message = message;
        this.traceId = traceId;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getTraceId() {
        return traceId;
    }

    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public String getDetail() {
        return detail;
    }

    public void setDetail(String detail) {
        this.detail = detail;
    }

    public Boolean getRetryable() {
        return retryable;
    }

    public void setRetryable(Boolean retryable) {
        this.retryable = retryable;
    }

    public Integer getRetryAfter() {
        return retryAfter;
    }

    public void setRetryAfter(Integer retryAfter) {
        this.retryAfter = retryAfter;
    }
}
