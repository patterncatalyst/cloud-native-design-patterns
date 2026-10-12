package com.cndp.gateway;

import java.util.List;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;
import org.jboss.resteasy.reactive.RestPath;
import org.jboss.resteasy.reactive.RestQuery;

/** Typed client for order-api; the base URL comes from quarkus.rest-client.order-api.url. */
@RegisterRestClient(configKey = "order-api")
@Path("/orders")
public interface OrderApiClient {

    @GET
    List<Order> orders(@RestQuery int limit);

    @GET
    @Path("/{id}")
    Order order(@RestPath String id);
}
