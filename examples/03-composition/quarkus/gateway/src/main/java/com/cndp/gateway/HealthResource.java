package com.cndp.gateway;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;

import java.util.Map;

@Path("/healthz")
public class HealthResource {

    @GET
    public Map<String, String> health() {
        return Map.of("status", "ok");
    }
}
