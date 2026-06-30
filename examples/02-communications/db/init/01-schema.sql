CREATE TABLE IF NOT EXISTS orders (
    id       TEXT PRIMARY KEY,
    sku      TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    status   TEXT NOT NULL DEFAULT 'pending'
);
