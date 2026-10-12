package com.cndp.router;

import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.PUT;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.rest.client.inject.RestClient;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class RouterResource {

    @RestClient
    MonolithClient monolith;

    @RestClient
    NewServiceClient newService;

    ConcurrentHashMap<String, String> tenantRoutes = new ConcurrentHashMap<>();
    volatile String defaultRoute = "monolith";

    public RouterResource() {
        // Initialize default routing: acme -> new-service
        tenantRoutes.put("acme", "new-service");
    }

    @POST
    @Path("orders")
    public Response createOrder(Map<String, Object> body) {
        // Extract tenant from body
        String tenant = (String) body.get("tenant");
        if (tenant == null) {
            tenant = "";
        }

        // Forward POST to the upstream that owns this tenant
        String upstreamBody = routesToNewService(tenant)
                ? newService.createOrder(body)
                : monolith.createOrder(body);

        return Response.status(201).entity(upstreamBody).build();
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

    private boolean routesToNewService(String tenant) {
        return "new-service".equals(tenantRoutes.getOrDefault(tenant, defaultRoute));
    }
}
