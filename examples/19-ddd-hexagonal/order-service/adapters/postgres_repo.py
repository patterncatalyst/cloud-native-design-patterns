from typing import Optional

import asyncpg

from domain.models import Order


class PostgresOrderRepository:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def save(self, order: Order) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO orders (id, sku, quantity, status, created_at)"
                " VALUES ($1, $2, $3, $4, $5)",
                order.id,
                order.sku,
                order.quantity,
                order.status,
                order.created_at,
            )

    async def find_by_id(self, order_id: str) -> Optional[Order]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, sku, quantity, status, created_at FROM orders WHERE id = $1",
                order_id,
            )
            if row is None:
                return None
            return Order(
                id=row["id"],
                sku=row["sku"],
                quantity=row["quantity"],
                status=row["status"],
                created_at=row["created_at"],
            )

    async def list_all(self) -> list[Order]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, sku, quantity, status, created_at"
                " FROM orders ORDER BY created_at"
            )
            return [
                Order(
                    id=r["id"],
                    sku=r["sku"],
                    quantity=r["quantity"],
                    status=r["status"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
