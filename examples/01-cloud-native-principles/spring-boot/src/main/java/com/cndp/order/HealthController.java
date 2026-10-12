package com.cndp.order;

import java.util.Map;

import javax.sql.DataSource;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {

    private final DataSource dataSource;

    @Value("${service.version}")
    private String serviceVersion;

    public HealthController(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @GetMapping("/readyz")
    public ResponseEntity<Map<String, Object>> readyz() {
        try (var conn = dataSource.getConnection()) {
            conn.createStatement().executeQuery("SELECT 1").close();
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                    .body(Map.of("status", "down", "checks", Map.of("database", "unreachable")));
        }
        return ResponseEntity.ok(Map.of("status", "ready", "checks", Map.of("database", "ok")));
    }

    @GetMapping("/")
    public Map<String, String> root() {
        return Map.of(
                "service", "order-service",
                "version", serviceVersion,
                "config_source", "environment"
        );
    }
}
