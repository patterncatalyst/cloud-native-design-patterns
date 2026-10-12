package com.example.saga.repository;

import java.util.List;

import com.example.saga.entity.SagaLogEntity;

import org.springframework.data.jpa.repository.JpaRepository;

public interface SagaLogRepository extends JpaRepository<SagaLogEntity, Long> {

    List<SagaLogEntity> findBySagaIdOrderByIdAsc(String sagaId);
}
