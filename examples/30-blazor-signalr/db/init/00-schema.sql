CREATE TABLE IF NOT EXISTS orders (
    id         TEXT PRIMARY KEY,
    sku        TEXT NOT NULL,
    quantity   INT  NOT NULL,
    status     TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
