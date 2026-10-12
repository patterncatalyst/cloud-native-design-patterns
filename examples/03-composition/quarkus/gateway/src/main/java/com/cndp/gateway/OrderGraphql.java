package com.cndp.gateway;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Logger;

import com.cndp.proto.GetStockBatchReply;
import com.cndp.proto.GetStockBatchRequest;
import com.cndp.proto.GetStockReply;
import com.cndp.proto.Inventory;
import io.quarkus.grpc.GrpcClient;
import jakarta.inject.Inject;
import jakarta.ws.rs.WebApplicationException;
import org.eclipse.microprofile.graphql.GraphQLApi;
import org.eclipse.microprofile.graphql.Query;
import org.eclipse.microprofile.graphql.Source;
import org.eclipse.microprofile.rest.client.inject.RestClient;

@GraphQLApi
public class OrderGraphql {

    private static final Logger log = Logger.getLogger(OrderGraphql.class.getName());

    @Inject
    @RestClient
    OrderApiClient orderApi;

    @Inject
    @GrpcClient("inventory")
    Inventory inventoryClient;

    @Query("orders")
    public List<Order> getOrders(Integer limit) {
        int maxResults = limit != null ? limit : 10;
        log.info("Fetching orders, limit=" + maxResults);
        return orderApi.orders(maxResults);
    }

    @Query("order")
    public Order getOrder(String id) {
        log.info("Fetching order: " + id);
        try {
            return orderApi.order(id);
        } catch (WebApplicationException e) {
            if (e.getResponse().getStatus() == 404) {
                return null;
            }
            throw e;
        }
    }

    public List<Integer> stock(@Source List<Order> orders) {
        // Extract unique SKUs from the batch of orders
        List<String> skus = orders.stream().map(Order::sku).toList();

        log.info("DataLoader batched " + skus.size() + " skus in one gRPC call");

        // Call inventory service with batch request
        GetStockBatchRequest request = GetStockBatchRequest.newBuilder()
            .addAllSkus(skus)
            .build();

        GetStockBatchReply reply = inventoryClient.getStockBatch(request).await().indefinitely();

        // Build a map of sku -> available
        Map<String, Integer> stockMap = new HashMap<>();
        for (GetStockReply item : reply.getItemsList()) {
            stockMap.put(item.getSku(), item.getAvailable());
        }

        // Return stock values in the same order as the input orders
        List<Integer> result = new ArrayList<>();
        for (Order order : orders) {
            result.add(stockMap.getOrDefault(order.sku(), 0));
        }

        return result;
    }
}
