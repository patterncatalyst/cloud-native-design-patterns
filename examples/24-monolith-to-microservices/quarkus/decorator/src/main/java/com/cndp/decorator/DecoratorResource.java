package com.cndp.decorator;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import io.quarkus.redis.datasource.RedisDataSource;
import io.quarkus.redis.datasource.value.ValueCommands;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.reactive.messaging.Channel;
import org.eclipse.microprofile.reactive.messaging.Emitter;
import org.eclipse.microprofile.rest.client.inject.RestClient;
import org.jboss.logging.Logger;
import org.jboss.resteasy.reactive.RestPath;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class DecoratorResource {

    private static final Logger LOG = Logger.getLogger(DecoratorResource.class);
    private static final String TOPIC = "order.placed";

    @RestClient
    LegacyClient legacy;

    @Inject
    RedisDataSource redisDataSource;

    @Channel("order-events-out")
    Emitter<Map<String, Object>> kafkaEmitter;

    List<Map<String, Object>> publishedEvents = Collections.synchronizedList(new ArrayList<>());

    @POST
    @Path("orders")
    public Response createOrder(Map<String, Object> body) {
        // 1. Forward POST to legacy/orders
        Map<String, Object> legacyResponse = legacy.createOrder(body);
        String orderId = (String) legacyResponse.get("id");

        // 2. Build event: Jackson writes the map in insertion order (event, order_id, then the request fields)
        Map<String, Object> event = new LinkedHashMap<>();
        event.put("event", TOPIC);
        event.put("order_id", orderId);
        event.putAll(body);

        // 3. Remember it and publish to Kafka
        publishedEvents.add(event);
        kafkaEmitter.send(event);

        LOG.infof("EVENT %s -> Kafka order_id=%s", TOPIC, orderId);

        // 4. Return 201 + legacy response
        return Response.status(201).entity(legacyResponse).build();
    }

    @GET
    @Path("orders/{orderId}")
    public Response getOrder(@RestPath String orderId) {
        String cacheKey = "order:" + orderId;
        ValueCommands<String, String> commands = redisDataSource.value(String.class);

        // 1. Check Redis
        String cached = commands.get(cacheKey);
        if (cached != null) {
            LOG.infof("CACHE_HIT order_id=%s", orderId);
            return Response.ok(cached).build();
        }

        // 2. Cache miss: GET from legacy and store with a 60s TTL
        LOG.infof("CACHE_MISS order_id=%s", orderId);
        String body = legacy.getOrder(orderId);
        commands.setex(cacheKey, 60, body);

        return Response.ok(body).build();
    }

    @GET
    @Path("events")
    public List<Map<String, Object>> getEvents() {
        return publishedEvents;
    }
}
