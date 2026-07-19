package com.cndp.order;

import java.sql.DriverManager;
import java.util.Map;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

import org.eclipse.microprofile.config.inject.ConfigProperty;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
public class HealthResource {

    @ConfigProperty(name = "quarkus.datasource.jdbc.url")
    String jdbcUrl;

    @ConfigProperty(name = "quarkus.datasource.username")
    String dbUser;

    @ConfigProperty(name = "quarkus.datasource.password")
    String dbPass;

    @ConfigProperty(name = "service.version", defaultValue = "0.0.0")
    String serviceVersion;

    @GET
    public Map<String, String> root() {
        return Map.of(
                "service", "order-service",
                "version", serviceVersion,
                "config_source", "environment"
        );
    }

    @GET
    @Path("healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @GET
    @Path("readyz")
    public Map<String, Object> readyz() {
        for (int attempt = 0; attempt < 2; attempt++) {
            try (var conn = DriverManager.getConnection(jdbcUrl, dbUser, dbPass);
                 var stmt = conn.createStatement();
                 var rs = stmt.executeQuery("SELECT 1")) {
                return Map.of("status", "ready", "checks", Map.of("database", "ok"));
            } catch (Exception e) {
                if (attempt == 0) {
                    try { Thread.sleep(1000); } catch (InterruptedException ie) { break; }
                }
            }
        }
        return Map.of("status", "down", "checks", Map.of("database", "unreachable"));
    }
}
