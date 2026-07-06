package com.example.order;

import java.math.BigDecimal;

public record Order(
    String id,
    String merchantId,
    String sku,
    int quantity,
    BigDecimal total,
    String status
) {}
