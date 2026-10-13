package com.cndp.order;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Inbound order payload. processing_ms (optional, default 10, at most 3000) simulates slow work, so the per-tenant
 * bulkhead can be seen filling up.
 */
public record OrderRequest(String sku, int quantity, String tenant,
                           @JsonProperty("processing_ms") Integer processingMs) {

    int processingTimeMs() {
        return Math.clamp(processingMs == null ? 10 : processingMs, 0, 3000);
    }
}
