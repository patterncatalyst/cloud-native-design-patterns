CREATE TABLE orders (
    id   TEXT PRIMARY KEY,
    sku  TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    status   TEXT NOT NULL DEFAULT 'placed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
