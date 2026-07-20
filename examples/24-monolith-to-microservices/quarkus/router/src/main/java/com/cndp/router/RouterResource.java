package com.cndp.router;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class RouterResource {

    @ConfigProperty(name = "monolith.url", defaultValue = "http://monolith:8080")
    String monolithUrl;

    @ConfigProperty(name = "new-service.url", defaultValue = "http://new-service:8080")
    String newServiceUrl;

    @Inject
    ObjectMapper objectMapper;

    ConcurrentHashMap<String, String> tenantRoutes = new ConcurrentHashMap<>();
    volatile String defaultRoute = "monolith";

    HttpClient httpClient = HttpClient.newHttpClient();

    public RouterResource() {
        // Initialize default routing: acme -> new-service
        tenantRoutes.put("acme", "new-service");
    }

    @GET
    @Path("healthz")
    public Response healthz() {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("status", "ok");
        return Response.ok(response).build();
    }

    @POST
    @Path("orders")
    public Response createOrder(Map<String, Object> body) throws Exception {
        // Extract tenant from body
        String tenant = (String) body.get("tenant");
        if (tenant == null) {
            tenant = "";
        }

        // Resolve upstream URL
        String upstreamUrl = resolveUpstream(tenant);

        // Forward POST to upstream
        String requestBody = objectMapper.writeValueAsString(body);
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(upstreamUrl + "/orders"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        return Response.status(201).entity(response.body()).build();
    }

    @GET
    @Path("rules")
    public Response getRules() {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("tenant_routes", new LinkedHashMap<>(tenantRoutes));
        response.put("default", defaultRoute);
        return Response.ok(response).build();
    }

    @PUT
    @Path("rules")
    public Response updateRules(Map<String, Object> body) {
        @SuppressWarnings("unchecked")
        Map<String, String> newTenantRoutes = (Map<String, String>) body.get("tenant_routes");
        String newDefault = (String) body.get("default");

        if (newTenantRoutes != null) {
            // CRITICAL: clear existing routes before adding new ones
            tenantRoutes.clear();
            tenantRoutes.putAll(newTenantRoutes);
        }

        if (newDefault != null) {
            defaultRoute = newDefault;
        }

        return Response.ok().build();
    }

    private String resolveUpstream(String tenant) {
        // Look up tenant in tenantRoutes
        String route = tenantRoutes.getOrDefault(tenant, defaultRoute);

        // Map route to URL
        if ("new-service".equals(route)) {
            return newServiceUrl;
        } else {
            return monolithUrl;
        }
    }
}
