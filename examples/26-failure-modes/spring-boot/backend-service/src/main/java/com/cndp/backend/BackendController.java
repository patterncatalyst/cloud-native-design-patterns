package com.cndp.backend;

import java.util.Map;
import java.util.Random;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class BackendController {

    private static final Logger log = LoggerFactory.getLogger(BackendController.class);
    private static final Random random = new Random();

    private final AtomicReference<String> mode = new AtomicReference<>("healthy");
    private final AtomicInteger callCount = new AtomicInteger(0);

    @PostMapping("/mode")
    public ResponseEntity<Map<String, Object>> setMode(@RequestBody Map<String, String> body) {
        String newMode = body.get("mode");
        if (newMode == null || !newMode.matches("healthy|slow|failing|flaky")) {
            return ResponseEntity.badRequest()
                    .body(Map.of("error", "mode must be healthy|slow|failing|flaky"));
        }
        mode.set(newMode);
        callCount.set(0);
        log.info("Mode set to: {}", newMode);
        return ResponseEntity.ok(Map.of("mode", newMode));
    }

    @GetMapping("/mode")
    public Map<String, Object> getMode() {
        return Map.of("mode", mode.get(), "call_count", callCount.get());
    }

    @GetMapping("/process")
    public ResponseEntity<Map<String, Object>> process(
            @RequestHeader(value = "X-Deadline-Ms", required = false) String deadlineMs) {

        callCount.incrementAndGet();
        String currentMode = mode.get();

        if (deadlineMs != null) {
            int remaining = Integer.parseInt(deadlineMs);
            if (remaining < 100) {
                log.info("Deadline too small ({}ms), refusing", remaining);
                return ResponseEntity.ok(Map.of(
                        "status", "rejected",
                        "reason", "deadline_too_small",
                        "remaining_ms", remaining));
            }
        }

        switch (currentMode) {
            case "slow":
                try {
                    Thread.sleep(5000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                return ResponseEntity.ok(Map.of(
                        "status", "ok",
                        "mode", "slow",
                        "delay", 5));

            case "failing":
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                        .body(Map.of("detail", "backend error"));

            case "flaky":
                if (random.nextDouble() < 0.5) {
                    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                            .body(Map.of("detail", "backend error (flaky)"));
                }
                return ResponseEntity.ok(Map.of("status", "ok", "mode", "flaky"));

            default: // healthy
                return ResponseEntity.ok(Map.of("status", "ok", "mode", "healthy"));
        }
    }

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }
}
