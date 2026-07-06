package com.example.orderservice;

public class OrderEvent {

    private String id;
    private String sku;
    private int quantity;
    private String status;

    public OrderEvent() {
    }

    public OrderEvent(String id, String sku, int quantity, String status) {
        this.id = id;
        this.sku = sku;
        this.quantity = quantity;
        this.status = status;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getSku() {
        return sku;
    }

    public void setSku(String sku) {
        this.sku = sku;
    }

    public int getQuantity() {
        return quantity;
    }

    public void setQuantity(int quantity) {
        this.quantity = quantity;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
