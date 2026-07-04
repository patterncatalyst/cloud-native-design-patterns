"""Second driving adapter: a CLI that calls the same PlaceOrder use case.
Proves the domain is adapter-agnostic — no domain files change."""
import asyncio
import os
import sys

import asyncpg

from adapters.log_publisher import LogEventPublisher
from adapters.postgres_repo import PostgresOrderRepository
from domain.models import PlaceOrderCmd
from domain.service import PlaceOrder


async def main():
    if len(sys.argv) < 3:
        print("Usage: python cli_place_order.py <sku> <quantity>", file=sys.stderr)
        sys.exit(1)

    sku = sys.argv[1]
    quantity = int(sys.argv[2])

    dsn = os.environ.get("DATABASE_URL", "postgres://appuser:apppass@localhost:5432/appdb")
    pool = await asyncpg.create_pool(dsn)

    repo = PostgresOrderRepository(pool)
    publisher = LogEventPublisher()
    place_order = PlaceOrder(repo=repo, events=publisher)

    order = await place_order(PlaceOrderCmd(sku=sku, quantity=quantity))
    print(
        f"CLI_ORDER_CREATED id={order.id} sku={order.sku}"
        f" qty={order.quantity} status={order.status}"
    )

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
