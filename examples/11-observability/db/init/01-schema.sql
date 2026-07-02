CREATE TABLE IF NOT EXISTS orders (
    id         TEXT PRIMARY KEY,
    sku        TEXT NOT NULL,
    quantity   INTEGER NOT NULL,
    status     TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notifications (
    id         BIGSERIAL PRIMARY KEY,
    order_id   TEXT NOT NULL,
    channel    TEXT NOT NULL DEFAULT 'email',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (order_id)
);
