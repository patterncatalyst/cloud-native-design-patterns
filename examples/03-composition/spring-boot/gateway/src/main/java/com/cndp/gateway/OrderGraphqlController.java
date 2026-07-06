package com.cndp.gateway;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import com.cndp.proto.GetStockBatchRequest;
import com.cndp.proto.GetStockBatchReply;
import com.cndp.proto.GetStockReply;
import com.cndp.proto.InventoryGrpc;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.graphql.data.method.annotation.Argument;
import org.springframework.graphql.data.method.annotation.BatchMapping;
import org.springframework.graphql.data.method.annotation.QueryMapping;
import org.springframework.stereotype.Controller;
import org.springframework.web.client.RestClient;

@Controller
public class OrderGraphqlController {

    private static final Logger log = LoggerFactory.getLogger(OrderGraphqlController.class);

    private final RestClient orderApiClient;
    private final InventoryGrpc.InventoryBlockingStub inventoryStub;

    public OrderGraphqlController(RestClient orderApiClient,
                                  InventoryGrpc.InventoryBlockingStub inventoryStub) {
        this.orderApiClient = orderApiClient;
        this.inventoryStub = inventoryStub;
    }

    @QueryMapping
    public List<Order> orders(@Argument int limit) {
        List<Map<String, Object>> raw = orderApiClient.get()
                .uri("/orders?limit={limit}", limit)
                .retrieve()
                .body(new ParameterizedTypeReference<List<Map<String, Object>>>() {});
        if (raw == null) return List.of();
        return raw.stream()
                .map(this::toOrder)
                .toList();
    }

    @QueryMapping
    public Order order(@Argument String id) {
        try {
            Map<String, Object> raw = orderApiClient.get()
                    .uri("/orders/{id}", id)
                    .retrieve()
                    .body(new ParameterizedTypeReference<Map<String, Object>>() {});
            if (raw == null) return null;
            return toOrder(raw);
        } catch (org.springframework.web.client.HttpClientErrorException.NotFound e) {
            return null;
        }
    }

    @BatchMapping(typeName = "Order", field = "stock")
    public Map<Order, Integer> stock(List<Order> orders) {
        List<String> uniqueSkus = orders.stream()
                .map(Order::sku)
                .distinct()
                .toList();

        GetStockBatchReply reply = inventoryStub.getStockBatch(
                GetStockBatchRequest.newBuilder().addAllSkus(uniqueSkus).build());

        Map<String, Integer> stockMap = reply.getItemsList().stream()
                .collect(Collectors.toMap(GetStockReply::getSku, GetStockReply::getAvailable));

        log.info("DataLoader batched {} skus in one gRPC call", uniqueSkus.size());

        return orders.stream()
                .collect(Collectors.toMap(o -> o, o -> stockMap.getOrDefault(o.sku(), 0)));
    }

    private Order toOrder(Map<String, Object> m) {
        return new Order(
                (String) m.get("id"),
                (String) m.get("sku"),
                ((Number) m.get("quantity")).intValue(),
                (String) m.get("status"));
    }
}
