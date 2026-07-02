CREATE TABLE products (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price_cents INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE events (
    id      TEXT PRIMARY KEY,
    type    TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    ts      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE metrics (
    id      TEXT PRIMARY KEY,
    payload JSONB NOT NULL DEFAULT '{}',
    ts      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO products (id, name, price_cents) VALUES
    ('p1', 'Widget',  999),
    ('p2', 'Gadget', 1499),
    ('p3', 'Gizmo',  2499);
