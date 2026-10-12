package com.cndp.order;

import java.util.List;

import io.quarkus.panache.common.Sort;
import jakarta.transaction.Transactional;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

@Path("/outbox")
@Produces(MediaType.APPLICATION_JSON)
public class OutboxResource {

    @GET
    @Transactional
    public List<OutboxView> listOutbox() {
        return OutboxEvent.<OutboxEvent>listAll(Sort.descending("createdAt"))
                .stream().map(OutboxEvent::toView).toList();
    }
}
