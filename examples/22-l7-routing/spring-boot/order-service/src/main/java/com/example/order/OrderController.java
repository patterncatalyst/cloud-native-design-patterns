package com.example.order;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {

    private final String version;

    public OrderController(AppProperties app) {
        this.version = app.version();
    }

    @PostMapping("/orders")
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> createOrder(@RequestBody Map<String, Object> body) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", "1");
        result.put("sku", body.get("sku"));
        result.put("quantity", body.get("quantity"));
        result.put("version", version);
        return result;
    }

    @GetMapping("/orders")
    public Map<String, Object> listOrders() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("orders", Collections.emptyList());
        result.put("version", version);
        return result;
    }
}
