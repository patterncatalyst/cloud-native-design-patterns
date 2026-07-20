package com.cndp.saga;

import com.cndp.saga.model.Saga;
import com.cndp.saga.model.SagaLogEntry;
import com.cndp.saga.model.SagaRequest;
import com.cndp.saga.service.SagaService;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.jboss.logging.Logger;

import java.util.List;
import java.util.Map;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class SagaResource {
    private static final Logger LOG = Logger.getLogger(SagaResource.class);

    @Inject
    SagaService sagaService;

    @GET
    @Path("healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @POST
    @Path("sagas")
    public Response createSaga(SagaRequest request) {
        try {
            Saga saga = sagaService.createAndRun(request);
            return Response.status(Response.Status.CREATED).entity(saga).build();
        } catch (Exception e) {
            LOG.error("Failed to create saga", e);
            return Response.status(Response.Status.INTERNAL_SERVER_ERROR)
                .entity(Map.of("error", e.getMessage()))
                .build();
        }
    }

    @GET
    @Path("sagas/{id}")
    public Response getSaga(@PathParam("id") String id) {
        try {
            Saga saga = sagaService.getSaga(id);
            if (saga == null) {
                return Response.status(Response.Status.NOT_FOUND)
                    .entity(Map.of("error", "not found"))
                    .build();
            }
            return Response.ok(saga).build();
        } catch (Exception e) {
            LOG.error("Failed to get saga", e);
            return Response.status(Response.Status.INTERNAL_SERVER_ERROR)
                .entity(Map.of("error", e.getMessage()))
                .build();
        }
    }

    @GET
    @Path("sagas/{id}/log")
    public Response getSagaLog(@PathParam("id") String id) {
        try {
            Saga saga = sagaService.getSaga(id);
            if (saga == null) {
                return Response.status(Response.Status.NOT_FOUND)
                    .entity(Map.of("error", "not found"))
                    .build();
            }
            List<SagaLogEntry> log = sagaService.getSagaLog(id);
            return Response.ok(log).build();
        } catch (Exception e) {
            LOG.error("Failed to get saga log", e);
            return Response.status(Response.Status.INTERNAL_SERVER_ERROR)
                .entity(Map.of("error", e.getMessage()))
                .build();
        }
    }
}
