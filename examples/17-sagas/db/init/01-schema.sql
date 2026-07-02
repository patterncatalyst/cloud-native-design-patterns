CREATE TABLE IF NOT EXISTS sagas (
    id          TEXT PRIMARY KEY,
    status      TEXT NOT NULL DEFAULT 'RUNNING',
    step_index  INTEGER NOT NULL DEFAULT 0,
    context     JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS saga_log (
    id          BIGSERIAL PRIMARY KEY,
    saga_id     TEXT NOT NULL REFERENCES sagas(id),
    step        TEXT NOT NULL,
    action      TEXT NOT NULL,
    result      JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
