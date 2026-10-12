package com.cndp.order;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;

public record OrderRequest(
        @NotBlank(message = "sku must not be empty") String sku,
        @Positive(message = "quantity must be greater than 0") int quantity) {
}
