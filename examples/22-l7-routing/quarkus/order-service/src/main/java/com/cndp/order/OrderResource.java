package com.cndp.order;

import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.List;
import java.util.Collections;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class OrderResource {

    @ConfigProperty(name = "app.version", defaultValue = "v1")
    String version;

    @GET
    @Path("healthz")
    public Map<String, String> healthz() {
        Map<String, String> response = new LinkedHashMap<>();
        response.put("status", "ok");
        response.put("version", version);
        return response;
    }

    @POST
    @Path("orders")
    public Response createOrder(Map<String, Object> body) {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("id", "1");
        response.put("sku", body.get("sku"));
        response.put("quantity", body.get("quantity"));
        response.put("version", version);
        return Response.status(Response.Status.CREATED).entity(response).build();
    }

    @GET
    @Path("orders")
    public Map<String, Object> getOrders() {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("orders", Collections.emptyList());
        response.put("version", version);
        return response;
    }
}
