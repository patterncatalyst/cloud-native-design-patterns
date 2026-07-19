package com.cndp.gateway;

import com.cndp.proto.GetStockBatchReply;
import com.cndp.proto.GetStockBatchRequest;
import com.cndp.proto.GetStockReply;
import com.cndp.proto.Inventory;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.quarkus.grpc.GrpcClient;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.eclipse.microprofile.graphql.GraphQLApi;
import org.eclipse.microprofile.graphql.Query;
import org.eclipse.microprofile.graphql.Source;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Logger;
import java.util.stream.Collectors;

@GraphQLApi
public class OrderGraphql {

    private static final Logger log = Logger.getLogger(OrderGraphql.class.getName());

    @ConfigProperty(name = "order-api.url", defaultValue = "http://order-api:8081")
    String orderApiUrl;

    @Inject
    @GrpcClient("inventory")
    Inventory inventoryClient;

    private final HttpClient httpClient = HttpClient.newHttpClient();
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Query("orders")
    public List<Order> getOrders(Integer limit) throws Exception {
        int maxResults = limit != null ? limit : 10;
        String url = orderApiUrl + "/orders?limit=" + maxResults;

        log.info("Fetching orders from: " + url);

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .GET()
            .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() != 200) {
            throw new RuntimeException("Failed to fetch orders: " + response.statusCode());
        }

        Order[] orders = objectMapper.readValue(response.body(), Order[].class);
        return List.of(orders);
    }

    @Query("order")
    public Order getOrder(String id) throws Exception {
        String url = orderApiUrl + "/orders/" + id;

        log.info("Fetching order from: " + url);

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .GET()
            .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() == 404) {
            return null;
        }

        if (response.statusCode() != 200) {
            throw new RuntimeException("Failed to fetch order: " + response.statusCode());
        }

        return objectMapper.readValue(response.body(), Order.class);
    }

    public List<Integer> stock(@Source List<Order> orders) {
        // Extract unique SKUs from the batch of orders
        List<String> skus = orders.stream()
            .map(Order::getSku)
            .collect(Collectors.toList());

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
            result.add(stockMap.getOrDefault(order.getSku(), 0));
        }

        return result;
    }
}
