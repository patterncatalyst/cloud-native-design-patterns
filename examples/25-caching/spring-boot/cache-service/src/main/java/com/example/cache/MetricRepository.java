package com.example.cache;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;

public interface MetricRepository extends JpaRepository<Metric, String> {

    /** Insert or overwrite in one statement: the write-back flusher can replay a flush safely. */
    @Modifying
    @Transactional
    @Query(value = "INSERT INTO metrics (id, payload) VALUES (:id, CAST(:payload AS jsonb)) "
            + "ON CONFLICT (id) DO UPDATE SET payload = CAST(:payload AS jsonb), ts = NOW()",
            nativeQuery = true)
    void upsert(@Param("id") String id, @Param("payload") String payload);
}
