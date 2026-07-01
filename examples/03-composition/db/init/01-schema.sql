CREATE TABLE IF NOT EXISTS orders (
    id       TEXT PRIMARY KEY,
    sku      TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    status   TEXT NOT NULL DEFAULT 'confirmed'
);

INSERT INTO orders (id, sku, quantity, status) VALUES
    ('ord-001', 'widget-a', 3, 'confirmed'),
    ('ord-002', 'widget-b', 1, 'confirmed'),
    ('ord-003', 'gadget-x', 5, 'confirmed'),
    ('ord-004', 'widget-a', 2, 'shipped'),
    ('ord-005', 'gadget-y', 10, 'confirmed');
