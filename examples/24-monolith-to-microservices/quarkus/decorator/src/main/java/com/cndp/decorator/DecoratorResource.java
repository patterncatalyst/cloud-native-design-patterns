package com.cndp.decorator;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.quarkus.redis.datasource.RedisDataSource;
import io.quarkus.redis.datasource.value.ValueCommands;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.eclipse.microprofile.reactive.messaging.Channel;
import org.eclipse.microprofile.reactive.messaging.Emitter;
import org.jboss.logging.Logger;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.CompletionException;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class DecoratorResource {

    private static final Logger LOG = Logger.getLogger(DecoratorResource.class);
    private static final String TOPIC = "order.placed";

    @ConfigProperty(name = "legacy.url", defaultValue = "http://legacy:8080")
    String legacyUrl;

    @Inject
    ObjectMapper objectMapper;

    @Inject
    RedisDataSource redisDataSource;

    @Channel("order-events-out")
    Emitter<String> kafkaEmitter;

    List<Map<String, Object>> publishedEvents = Collections.synchronizedList(new ArrayList<>());
    HttpClient httpClient = HttpClient.newHttpClient();

    @GET
    @Path("healthz")
    public Response healthz() {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("status", "ok");
        return Response.ok(response).build();
    }

    @POST
    @Path("orders")
    public Response createOrder(Map<String, Object> body) throws Exception {
        // 1. Forward POST to legacy/orders
        String requestBody = objectMapper.writeValueAsString(body);
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(legacyUrl + "/orders"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        // 2. Parse response to get order id
        @SuppressWarnings("unchecked")
        Map<String, Object> legacyResponse = objectMapper.readValue(response.body(), Map.class);
        String orderId = (String) legacyResponse.get("id");

        // 3. Build event
        Map<String, Object> event = new LinkedHashMap<>();
        event.put("event", TOPIC);
        event.put("order_id", orderId);
        event.putAll(body);

        // 4. Add to publishedEvents list
        publishedEvents.add(event);

        // 5. Publish to Kafka
        String eventJson = objectMapper.writeValueAsString(event);
        kafkaEmitter.send(eventJson);

        // 6. Log
        LOG.infof("EVENT %s -> Kafka order_id=%s", TOPIC, orderId);

        // 7. Return 201 + legacy response
        return Response.status(201).entity(response.body()).build();
    }

    @GET
    @Path("orders/{orderId}")
    public Response getOrder(@PathParam("orderId") String orderId) throws Exception {
        String cacheKey = "order:" + orderId;
        ValueCommands<String, String> commands = redisDataSource.value(String.class);

        // 1. Check Redis
        String cached = commands.get(cacheKey);
        if (cached != null) {
            // 2. Cache hit
            LOG.infof("CACHE_HIT order_id=%s", orderId);
            return Response.ok(cached).build();
        }

        // 3. Cache miss
        LOG.infof("CACHE_MISS order_id=%s", orderId);

        // GET from legacy
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(legacyUrl + "/orders/" + orderId))
                .GET()
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        // 4. Store in Redis with 60s TTL
        commands.setex(cacheKey, 60, response.body());

        // 5. Return response
        return Response.ok(response.body()).build();
    }

    @GET
    @Path("events")
    public Response getEvents() {
        return Response.ok(publishedEvents).build();
    }
}
