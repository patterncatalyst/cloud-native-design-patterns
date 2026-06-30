CREATE TABLE IF NOT EXISTS orders (
    id    SERIAL PRIMARY KEY,
    customer TEXT NOT NULL,
    total    NUMERIC(10, 2) NOT NULL
);
