package com.cndp.decorator;

import java.util.Map;

import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;
import org.jboss.resteasy.reactive.RestPath;

/** The legacy order API, untouched; the base URL is quarkus.rest-client.legacy.url. */
@RegisterRestClient(configKey = "legacy")
@Path("/orders")
@Produces(MediaType.APPLICATION_JSON)
public interface LegacyClient {

    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    Map<String, Object> createOrder(Map<String, Object> body);

    /** Raw body, so the cache stores exactly what legacy sent. */
    @GET
    @Path("/{orderId}")
    String getOrder(@RestPath String orderId);
}
