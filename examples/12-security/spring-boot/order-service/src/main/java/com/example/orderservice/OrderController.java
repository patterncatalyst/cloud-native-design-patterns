package com.example.orderservice;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

@RestController
public class OrderController {

    private final BulkheadService bulkhead;
    private final ValetKeyService valetKeyService;

    private final ConcurrentHashMap<String, Map<String, Object>> orders = new ConcurrentHashMap<>();
    private final AtomicInteger counter = new AtomicInteger(0);

    public OrderController(BulkheadService bulkhead, ValetKeyService valetKeyService) {
        this.bulkhead = bulkhead;
        this.valetKeyService = valetKeyService;
    }

    // -----------------------------------------------------------------
    // Health check — open path (filter skips it)
    // -----------------------------------------------------------------
    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    // -----------------------------------------------------------------
    // Create order — requires identity, uses per-tenant bulkhead
    // -----------------------------------------------------------------
    @PostMapping("/orders")
    public ResponseEntity<Map<String, Object>> createOrder(
            @RequestBody OrderRequest body,
            HttpServletRequest request) {

        String identity = (String) request.getAttribute(SidecarTrustFilter.ATTR_IDENTITY);
        String subject = (String) request.getAttribute(SidecarTrustFilter.ATTR_SUBJECT);

        Semaphore sem = bulkhead.forTenant(body.tenant());
        try {
            if (!sem.tryAcquire(5, TimeUnit.SECONDS)) {
                return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS)
                        .body(Map.of("detail", "tenant bulkhead full"));
            }
            try {
                // Simulate a short processing delay
                Thread.sleep(10);

                String id = String.valueOf(counter.incrementAndGet());
                Map<String, Object> order = new LinkedHashMap<>();
                order.put("id", id);
                order.put("sku", body.sku());
                order.put("quantity", body.quantity());
                order.put("tenant", body.tenant());
                order.put("identity", identity);
                order.put("subject", subject);

                orders.put(id, order);
                return ResponseEntity.status(HttpStatus.CREATED).body(order);
            } finally {
                sem.release();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                    .body(Map.of("detail", "interrupted"));
        }
    }

    // -----------------------------------------------------------------
    // Get order by ID
    // -----------------------------------------------------------------
    @GetMapping("/orders/{orderId}")
    public ResponseEntity<Map<String, Object>> getOrder(@PathVariable String orderId) {
        Map<String, Object> order = orders.get(orderId);
        if (order == null) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(Map.of("detail", "not found"));
        }
        return ResponseEntity.ok(order);
    }

    // -----------------------------------------------------------------
    // Valet key — mint
    // -----------------------------------------------------------------
    @PostMapping("/valet-key")
    public Map<String, Object> mintValetKey(
            @RequestParam String resource,
            @RequestParam(defaultValue = "GET") String operation) {
        return valetKeyService.mint(resource, operation);
    }

    // -----------------------------------------------------------------
    // Valet key — verify
    // -----------------------------------------------------------------
    @GetMapping("/verify-valet")
    public ResponseEntity<?> verifyValetKey(
            @RequestParam String resource,
            @RequestParam String operation,
            @RequestParam long expires,
            @RequestParam String token) {
        if (valetKeyService.verify(resource, operation, expires, token)) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("valid", true);
            result.put("resource", resource);
            result.put("operation", operation);
            return ResponseEntity.ok(result);
        }
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
                .body(Map.of("detail", "invalid or expired valet key"));
    }

    // -----------------------------------------------------------------
    // Bulkhead state
    // -----------------------------------------------------------------
    @GetMapping("/bulkhead-state")
    public Map<String, Map<String, Integer>> bulkheadState() {
        return bulkhead.state();
    }
}
