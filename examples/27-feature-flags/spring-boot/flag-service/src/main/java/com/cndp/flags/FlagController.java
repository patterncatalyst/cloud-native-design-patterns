package com.cndp.flags;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

import dev.openfeature.sdk.Client;
import dev.openfeature.sdk.MutableContext;
import dev.openfeature.sdk.OpenFeatureAPI;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class FlagController {

    private static final Logger log = LoggerFactory.getLogger(FlagController.class);

    private MutableContext buildContext(String user, String plan, String region) {
        MutableContext ctx = new MutableContext(user);
        ctx.add("plan", plan);
        ctx.add("region", region);
        return ctx;
    }

    private boolean evalFlag(String flag, boolean defaultValue, MutableContext ctx) {
        try {
            Client client = OpenFeatureAPI.getInstance().getClient();
            return CompletableFuture.supplyAsync(() ->
                    client.getBooleanValue(flag, defaultValue, ctx))
                .get(2, TimeUnit.SECONDS);
        } catch (Exception e) {
            log.warn("Flag evaluation failed for '{}', returning default {}: {}",
                     flag, defaultValue, e.getMessage());
            return defaultValue;
        }
    }

    // -----------------------------------------------------------------------
    // 1. Release flag -- new-checkout (default off, enterprise always on, 25%)
    // -----------------------------------------------------------------------
    @PostMapping("/checkout")
    public Map<String, Object> checkout(
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String user,
            @RequestHeader(value = "X-Plan", defaultValue = "free") String plan,
            @RequestHeader(value = "X-Region", defaultValue = "us") String region) {

        MutableContext ctx = buildContext(user, plan, region);
        boolean useNew = evalFlag("new-checkout", false, ctx);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("path", useNew ? "new" : "legacy");
        result.put("user", user);
        result.put("plan", plan);
        return result;
    }

    // -----------------------------------------------------------------------
    // 2. Kill switch -- recommendations-enabled (default on)
    // -----------------------------------------------------------------------
    @GetMapping("/recommendations")
    public Map<String, Object> recommendations(
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String user) {

        MutableContext ctx = buildContext(user, "free", "us");
        boolean enabled = evalFlag("recommendations-enabled", true, ctx);

        Map<String, Object> result = new LinkedHashMap<>();
        if (enabled) {
            result.put("recommendations", List.of("product-a", "product-b", "product-c"));
            result.put("reason", "live");
        } else {
            result.put("recommendations", List.of());
            result.put("reason", "killed");
        }
        return result;
    }

    // -----------------------------------------------------------------------
    // 3. Simple on/off flag -- dark-mode (default off)
    // -----------------------------------------------------------------------
    @GetMapping("/ui-config")
    public Map<String, Object> uiConfig(
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String user) {

        MutableContext ctx = buildContext(user, "free", "us");
        boolean dark = evalFlag("dark-mode", false, ctx);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("dark_mode", dark);
        result.put("user", user);
        return result;
    }

    // -----------------------------------------------------------------------
    // 4. Debug endpoint -- evaluate all flags
    // -----------------------------------------------------------------------
    @GetMapping("/flags")
    public Map<String, Object> allFlags(
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String user,
            @RequestHeader(value = "X-Plan", defaultValue = "free") String plan) {

        MutableContext ctx = buildContext(user, plan, "us");

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("new-checkout", evalFlag("new-checkout", false, ctx));
        result.put("dark-mode", evalFlag("dark-mode", false, ctx));
        result.put("recommendations-enabled", evalFlag("recommendations-enabled", true, ctx));
        result.put("user", user);
        result.put("plan", plan);
        return result;
    }

    // -----------------------------------------------------------------------
    // Health
    // -----------------------------------------------------------------------
    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }
}
