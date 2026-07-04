CREATE TABLE orders (
    id         SERIAL PRIMARY KEY,
    sku        TEXT NOT NULL,
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    status     TEXT NOT NULL DEFAULT 'placed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
