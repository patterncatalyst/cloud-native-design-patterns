package com.cndp.order;

import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeFormatterBuilder;
import java.time.temporal.ChronoField;

/** Renders a timestamptz the way PostgreSQL prints it ("2026-10-12 10:00:00.123456+00"), as the API always has. */
final class PgTimestamps {

    private static final DateTimeFormatter PG = new DateTimeFormatterBuilder()
            .appendPattern("yyyy-MM-dd HH:mm:ss")
            .appendFraction(ChronoField.MICRO_OF_SECOND, 0, 6, true)
            .appendOffset("+HH:mm", "+00")
            .toFormatter();

    private PgTimestamps() {}

    static String format(Instant instant) {
        return instant == null ? null : PG.format(instant.atZone(ZoneId.systemDefault()));
    }
}
