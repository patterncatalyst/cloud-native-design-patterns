package com.cndp.router;

import java.util.Map;

import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;

/** Typed client for the "monolith" upstream (quarkus.rest-client.monolith.url); the body comes back as sent. */
@RegisterRestClient(configKey = "monolith")
@Path("/orders")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public interface MonolithClient {

    @POST
    String createOrder(Map<String, Object> body);
}
