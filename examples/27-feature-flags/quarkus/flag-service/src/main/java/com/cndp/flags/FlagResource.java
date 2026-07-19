package com.cndp.flags;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

import dev.openfeature.sdk.Client;
import dev.openfeature.sdk.MutableContext;
import dev.openfeature.sdk.OpenFeatureAPI;
import io.quarkus.logging.Log;
import jakarta.ws.rs.DefaultValue;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.HeaderParam;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
public class FlagResource {

    private MutableContext buildContext(String user, String plan) {
        MutableContext ctx = new MutableContext(user);
        ctx.add("plan", plan);
        return ctx;
    }

    private boolean evalFlag(String flag, boolean defaultValue, MutableContext ctx) {
        try {
            Client client = OpenFeatureAPI.getInstance().getClient();
            return CompletableFuture.supplyAsync(() ->
                    client.getBooleanValue(flag, defaultValue, ctx))
                .get(2, TimeUnit.SECONDS);
        } catch (Exception e) {
            Log.warnf("Flag evaluation failed for '%s', returning default %s: %s",
                      flag, defaultValue, e.getMessage());
            return defaultValue;
        }
    }

    @GET
    @Path("healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @POST
    @Path("checkout")
    public Map<String, Object> checkout(
            @HeaderParam("X-User") @DefaultValue("anonymous") String user,
            @HeaderParam("X-Plan") @DefaultValue("free") String plan) {

        MutableContext ctx = buildContext(user, plan);
        boolean useNew = evalFlag("new-checkout", false, ctx);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("path", useNew ? "new" : "legacy");
        result.put("user", user);
        result.put("plan", plan);
        return result;
    }

    @GET
    @Path("recommendations")
    public Map<String, Object> recommendations(
            @HeaderParam("X-User") @DefaultValue("anonymous") String user) {

        MutableContext ctx = buildContext(user, "free");
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

    @GET
    @Path("ui-config")
    public Map<String, Object> uiConfig(
            @HeaderParam("X-User") @DefaultValue("anonymous") String user) {

        MutableContext ctx = buildContext(user, "free");
        boolean dark = evalFlag("dark-mode", false, ctx);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("dark_mode", dark);
        result.put("user", user);
        return result;
    }

    @GET
    @Path("flags")
    public Map<String, Object> allFlags(
            @HeaderParam("X-User") @DefaultValue("anonymous") String user,
            @HeaderParam("X-Plan") @DefaultValue("free") String plan) {

        MutableContext ctx = buildContext(user, plan);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("new-checkout", evalFlag("new-checkout", false, ctx));
        result.put("dark-mode", evalFlag("dark-mode", false, ctx));
        result.put("recommendations-enabled", evalFlag("recommendations-enabled", true, ctx));
        result.put("user", user);
        result.put("plan", plan);
        return result;
    }
}
