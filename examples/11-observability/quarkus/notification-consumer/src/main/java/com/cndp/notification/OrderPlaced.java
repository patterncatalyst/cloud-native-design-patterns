package com.cndp.notification;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/** order.placed payload; other producers may add fields, so unknown ones are ignored. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record OrderPlaced(String id, String sku, int quantity, String status) {}
