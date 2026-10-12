package com.cndp.edge;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;
import org.jboss.resteasy.reactive.RestHeader;

/**
 * Typed client for the backend. Base URL and timeouts come from quarkus.rest-client.backend.*;
 * the Response return type lets the caller see 4xx/5xx bodies, which the failure patterns report.
 */
@RegisterRestClient(configKey = "backend")
@Path("/call")
public interface BackendClient {

    @GET
    Response call();

    @GET
    Response call(@RestHeader("X-Deadline-Remaining") String deadlineRemaining);
}
