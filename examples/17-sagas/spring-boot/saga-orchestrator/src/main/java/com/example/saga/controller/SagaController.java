package com.example.saga.controller;

import java.util.List;
import java.util.Map;

import com.example.saga.model.Saga;
import com.example.saga.model.SagaLogEntry;
import com.example.saga.model.SagaRequest;
import com.example.saga.service.SagaService;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class SagaController {

    private final SagaService sagaService;

    public SagaController(SagaService sagaService) {
        this.sagaService = sagaService;
    }

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @PostMapping("/sagas")
    public ResponseEntity<Saga> createSaga(@RequestBody SagaRequest request) {
        Saga saga = sagaService.createAndRun(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(saga);
    }

    @GetMapping("/sagas/{id}")
    public ResponseEntity<?> getSaga(@PathVariable String id) {
        Saga saga = sagaService.getSaga(id);
        if (saga == null) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(Map.of("error", "not found"));
        }
        return ResponseEntity.ok(saga);
    }

    @GetMapping("/sagas/{id}/log")
    public ResponseEntity<?> getSagaLog(@PathVariable String id) {
        Saga saga = sagaService.getSaga(id);
        if (saga == null) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(Map.of("error", "not found"));
        }
        List<SagaLogEntry> entries = sagaService.getSagaLog(id);
        return ResponseEntity.ok(entries);
    }
}
