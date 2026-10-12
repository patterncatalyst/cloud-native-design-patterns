package com.cndp.orderapi;

import java.util.List;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderRepository extends JpaRepository<Order, String> {

    List<Order> findAllByOrderByIdAsc(Pageable page);
}
