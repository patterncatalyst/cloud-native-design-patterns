package com.example.order;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {

    @Value("${app.version}")
    private String version;

    @GetMapping("/healthz")
    public Map<String, Object> healthz() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", "ok");
        result.put("version", version);
        return result;
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
