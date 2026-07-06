package com.example.router;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;

@RestController
public class RouterController {

    @Value("${MONOLITH_URL:http://monolith:8080}")
    private String monolithUrl;

    @Value("${NEW_SERVICE_URL:http://new-service:8080}")
    private String newServiceUrl;

    private final RestClient restClient;
    private final ObjectMapper objectMapper;

    private final Map<String, String> tenantRoutes = new ConcurrentHashMap<>();
    private volatile String defaultRoute = "monolith";

    public RouterController(RestClient restClient, ObjectMapper objectMapper) {
        this.restClient = restClient;
        this.objectMapper = objectMapper;
        tenantRoutes.put("acme", "new-service");
    }

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @PostMapping("/orders")
    public ResponseEntity<String> routePost(@RequestBody String body) {
        String tenant = extractTenant(body);
        String upstream = resolveUpstream(tenant);

        String response = restClient.post()
                .uri(upstream + "/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .body(body)
                .retrieve()
                .body(String.class);

        return ResponseEntity.status(201)
                .contentType(MediaType.APPLICATION_JSON)
                .body(response);
    }

    @GetMapping("/orders/{orderId}")
    public ResponseEntity<String> routeGet(@PathVariable String orderId,
                                           @RequestParam(defaultValue = "") String tenant) {
        String upstream = resolveUpstream(tenant);

        String response = restClient.get()
                .uri(upstream + "/orders/" + orderId)
                .retrieve()
                .body(String.class);

        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_JSON)
                .body(response);
    }

    @GetMapping("/rules")
    public Map<String, Object> getRules() {
        Map<String, Object> rules = new LinkedHashMap<>();
        rules.put("tenant_routes", new LinkedHashMap<>(tenantRoutes));
        rules.put("default", defaultRoute);
        return rules;
    }

    @SuppressWarnings("unchecked")
    @PutMapping("/rules")
    public Map<String, Object> updateRules(@RequestBody Map<String, Object> newRules) {
        if (newRules.containsKey("tenant_routes")) {
            tenantRoutes.clear();
            Map<String, String> routes = (Map<String, String>) newRules.get("tenant_routes");
            tenantRoutes.putAll(routes);
        }
        if (newRules.containsKey("default")) {
            defaultRoute = (String) newRules.get("default");
        }
        return getRules();
    }

    private String resolveUpstream(String tenant) {
        String target = tenantRoutes.getOrDefault(tenant, defaultRoute);
        if ("new-service".equals(target)) {
            return newServiceUrl;
        }
        return monolithUrl;
    }

    private String extractTenant(String body) {
        try {
            Map<?, ?> parsed = objectMapper.readValue(body, Map.class);
            Object tenant = parsed.get("tenant");
            return tenant != null ? tenant.toString() : "";
        } catch (Exception e) {
            return "";
        }
    }
}
