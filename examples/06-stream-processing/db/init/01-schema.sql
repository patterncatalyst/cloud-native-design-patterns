CREATE TABLE IF NOT EXISTS orders (
    id          TEXT PRIMARY KEY,
    merchant_id TEXT NOT NULL,
    sku         TEXT NOT NULL,
    quantity    INTEGER NOT NULL,
    total       NUMERIC(12,2) NOT NULL,
    status      TEXT NOT NULL DEFAULT 'confirmed',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
