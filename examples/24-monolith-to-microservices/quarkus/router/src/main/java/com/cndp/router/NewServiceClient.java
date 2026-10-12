package com.cndp.router;

import java.util.Map;

import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;

/** Typed client for the "new-service" upstream (quarkus.rest-client.new-service.url); the body comes back as sent. */
@RegisterRestClient(configKey = "new-service")
@Path("/orders")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public interface NewServiceClient {

    @POST
    String createOrder(Map<String, Object> body);
}
