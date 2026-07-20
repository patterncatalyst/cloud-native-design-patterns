package com.cndp.ws;

import io.quarkus.logging.Log;
import jakarta.inject.Inject;
import jakarta.ws.rs.DefaultValue;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.QueryParam;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.util.Map;

import static jakarta.ws.rs.core.MediaType.APPLICATION_JSON;

@Path("/")
@Produces(APPLICATION_JSON)
public class ApiResource {

    @ConfigProperty(name = "pod.name", defaultValue = "ws-pod-unknown")
    String podName;

    @Inject
    ClientRegistry registry;

    @Inject
    RedisBackplane backplane;

    @GET
    @Path("healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok", "pod", podName);
    }

    @POST
    @Path("send")
    public Map<String, Object> send(
            @QueryParam("target") String target,
            @QueryParam("message") @DefaultValue("hello") String message) {

        Log.infof("Sending message on pod %s: target=%s, message=%s", podName, target, message);

        // Publish to Redis backplane for cross-pod delivery
        backplane.publish(target, message);

        // Also deliver locally if the target is on THIS pod
        if (target != null) {
            registry.sendToClient(target, message);
        } else {
            registry.broadcast(message);
        }

        return Map.of("sent", true, "pod", podName);
    }
}
