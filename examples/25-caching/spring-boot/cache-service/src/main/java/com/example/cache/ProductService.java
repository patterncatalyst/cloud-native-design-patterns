package com.example.cache;

import java.util.Optional;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ProductService {

    private final ProductRepository products;

    public ProductService(ProductRepository products) {
        this.products = products;
    }

    @Transactional(readOnly = true)
    public Optional<ProductView> find(String pid) {
        return products.findById(pid).map(Product::toView);
    }

    /** Updates the row; an unknown id is a no-op, as the plain UPDATE it replaces was. */
    @Transactional
    public Optional<ProductView> update(String pid, ProductUpdate update) {
        return products.findById(pid).map(p -> {
            p.update(update.name(), update.priceCents());
            return p.toView();
        });
    }
}
