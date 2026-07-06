package com.cndp.ws;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class ApiController {

    @Value("${POD_NAME:ws-pod-unknown}")
    private String podName;

    private final ClientRegistry registry;
    private final RedisBackplane backplane;

    public ApiController(ClientRegistry registry, RedisBackplane backplane) {
        this.registry = registry;
        this.backplane = backplane;
    }

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok", "pod", podName);
    }

    /**
     * Send a message to a specific client (targeted) or all clients (broadcast).
     * <p>
     * The message is published to Redis for cross-pod delivery, and also
     * delivered locally if the target client is connected to this pod.
     *
     * @param target  optional client ID; if omitted, broadcasts to all
     * @param message the message payload
     */
    @PostMapping("/send")
    public Map<String, Object> send(
            @RequestParam(required = false) String target,
            @RequestParam(defaultValue = "hello") String message) {

        // Publish to Redis backplane for cross-pod delivery
        backplane.publish(target, message);

        // Also deliver locally if the target is on this pod
        if (target != null) {
            registry.sendToClient(target, message);
        } else {
            registry.broadcast(message);
        }

        return Map.of("sent", true, "pod", podName);
    }
}
