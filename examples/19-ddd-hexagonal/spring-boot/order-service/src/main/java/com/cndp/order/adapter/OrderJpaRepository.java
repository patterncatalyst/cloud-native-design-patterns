package com.cndp.order.adapter;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

interface OrderJpaRepository extends JpaRepository<OrderJpaEntity, String> {

    List<OrderJpaEntity> findAllByOrderByCreatedAtAsc();
}
