package com.cndp.router;

import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import org.jboss.logging.Logger;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class RouterResource {

    private static final Logger LOG = Logger.getLogger(RouterResource.class);

    private final ConcurrentHashMap<String, Object> rules = new ConcurrentHashMap<>();

    public RouterResource() {
        rules.put("vip_threshold", 1000);
        rules.put("priority_topic", "orders.priority");
        rules.put("default_topic", "orders.default");
    }

    @POST
    @Path("orders")
    public Map<String, Object> routeOrder(Map<String, Object> body) {
        double amount = ((Number) body.get("amount")).doubleValue();
        int threshold = (Integer) rules.get("vip_threshold");

        String routedTo;
        boolean isVip;

        if (amount >= threshold) {
            routedTo = (String) rules.get("priority_topic");
            isVip = true;
        } else {
            routedTo = (String) rules.get("default_topic");
            isVip = false;
        }

        String sku = body.get("sku") != null ? body.get("sku").toString() : "unknown";
        LOG.infof("ROUTED sku=%s amount=%.2f -> %s", sku, amount, routedTo);

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("routed_to", routedTo);
        response.put("vip", isVip);
        response.put("amount", amount);
        return response;
    }

    @GET
    @Path("rules")
    public Map<String, Object> getRules() {
        return new LinkedHashMap<>(rules);
    }

    @PUT
    @Path("rules")
    public Map<String, Object> updateRules(Map<String, Object> newRules) {
        rules.putAll(newRules);
        LOG.info("RULES_UPDATED");
        return new LinkedHashMap<>(rules);
    }

    @GET
    @Path("healthz")
    public Map<String, String> healthz() {
        Map<String, String> response = new LinkedHashMap<>();
        response.put("status", "ok");
        return response;
    }
}
