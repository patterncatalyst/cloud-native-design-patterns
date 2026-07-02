CREATE TABLE IF NOT EXISTS orders (
    id         TEXT PRIMARY KEY,
    sku        TEXT NOT NULL,
    quantity   INTEGER NOT NULL,
    status     TEXT NOT NULL DEFAULT 'confirmed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
