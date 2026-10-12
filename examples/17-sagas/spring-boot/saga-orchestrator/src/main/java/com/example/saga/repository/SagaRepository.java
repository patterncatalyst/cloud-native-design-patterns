package com.example.saga.repository;

import java.util.List;
import java.util.Optional;

import com.example.saga.entity.SagaEntity;

import jakarta.persistence.LockModeType;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface SagaRepository extends JpaRepository<SagaEntity, String> {

    /** SELECT ... FOR UPDATE: one worker advances a saga at a time. */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select s from SagaEntity s where s.id = :id")
    Optional<SagaEntity> lockById(@Param("id") String id);

    List<SagaEntity> findByStatus(String status);
}
