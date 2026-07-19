package com.cndp.order;

public class Order {
    public String id;
    public String sku;
    public int quantity;
    public String status;

    public Order() {
    }

    public Order(String id, String sku, int quantity, String status) {
        this.id = id;
        this.sku = sku;
        this.quantity = quantity;
        this.status = status;
    }
}
