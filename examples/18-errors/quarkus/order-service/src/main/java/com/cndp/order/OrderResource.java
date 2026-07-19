package com.cndp.order;

import com.cndp.proto.ReserveReply;
import io.grpc.StatusRuntimeException;
import io.opentelemetry.api.trace.Span;
import io.quarkus.logging.Log;
import io.smallrye.common.annotation.Blocking;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

@Path("/")
public class OrderResource {

    @Inject
    InventoryClient inventoryClient;

    @GET
    @Path("/healthz")
    @Produces(MediaType.APPLICATION_JSON)
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @POST
    @Path("/orders")
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    @Blocking
    public Response placeOrder(OrderRequest body) {
        if (body == null || body.sku() == null || body.sku().isBlank()) {
            return problemResponse(422, "VALIDATION_ERROR", "request validation failed",
                    "sku must not be empty", false, null);
        }
        if (body.quantity() <= 0) {
            return problemResponse(422, "VALIDATION_ERROR", "request validation failed",
                    "quantity must be greater than 0", false, null);
        }

        try {
            ReserveReply reply = inventoryClient.reserveStock(body.sku(), body.quantity());

            if (!reply.getReserved()) {
                return problemResponse(409, "STOCK_UNAVAILABLE",
                        "insufficient stock for " + body.sku(),
                        "insufficient stock for " + body.sku(), false, null);
            }

            Map<String, Object> result = new LinkedHashMap<>();
            result.put("id", UUID.randomUUID().toString());
            result.put("sku", body.sku());
            result.put("quantity", body.quantity());
            result.put("status", "confirmed");
            result.put("remaining_stock", reply.getRemaining());

            return Response.status(201).entity(result).build();

        } catch (StatusRuntimeException e) {
            return handleGrpcError(e, body.sku());
        }
    }

    private Response handleGrpcError(StatusRuntimeException e, String sku) {
        return switch (e.getStatus().getCode()) {
            case RESOURCE_EXHAUSTED -> {
                String detail = e.getStatus().getDescription();
                if (detail == null) {
                    detail = "insufficient stock for " + sku;
                }
                yield problemResponse(409, "STOCK_UNAVAILABLE",
                        "insufficient stock for " + sku, detail, false, null);
            }
            case DEADLINE_EXCEEDED, UNAVAILABLE -> problemResponse(503, "INVENTORY_UNAVAILABLE",
                    "inventory service is temporarily unavailable",
                    "gRPC " + e.getStatus().getCode().name().toLowerCase(), true, 5);
            default -> {
                Log.errorf(e, "unexpected gRPC error from inventory: status=%s desc=%s",
                        e.getStatus().getCode(), e.getStatus().getDescription());
                yield problemResponse(500, "INTERNAL_ERROR",
                        "unexpected error from inventory service",
                        e.getStatus().getDescription(), false, null);
            }
        };
    }

    private Response problemResponse(int status, String code, String message,
                                     String detail, boolean retryable, Integer retryAfter) {
        String traceId = getTraceId();
        ErrorResponse body = new ErrorResponse(code, message, traceId, detail, retryable, retryAfter);

        Response.ResponseBuilder builder = Response.status(status)
                .type("application/problem+json")
                .entity(body);

        if (retryAfter != null) {
            builder.header("Retry-After", retryAfter.toString());
        }

        return builder.build();
    }

    private String getTraceId() {
        Span span = Span.current();
        if (span != null && span.getSpanContext().isValid()) {
            return span.getSpanContext().getTraceId();
        }
        return UUID.randomUUID().toString().replace("-", "");
    }
}
