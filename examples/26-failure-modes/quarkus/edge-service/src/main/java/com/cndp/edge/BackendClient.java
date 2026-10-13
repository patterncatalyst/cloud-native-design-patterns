package com.cndp.edge;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;
import org.jboss.resteasy.reactive.RestHeader;

/**
 * Typed client for the backend. Base URL and timeouts come from quarkus.rest-client.backend.*;
 * a 4xx or 5xx answer is thrown as a WebApplicationException, which the fault-tolerance guards count as a failure.
 */
@RegisterRestClient(configKey = "backend")
@Path("/process")
public interface BackendClient {

    @GET
    Response process();

    @GET
    Response process(@RestHeader("X-Deadline-Ms") String deadlineMs);
}
