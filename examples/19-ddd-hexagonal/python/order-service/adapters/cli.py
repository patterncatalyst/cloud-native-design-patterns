"""Second driving adapter: a CLI that calls the same PlaceOrder use case.
Proves the domain is adapter-agnostic — no domain files change.
Run as `cli-place-order <sku> <quantity>` (wrapper for `python -m adapters.cli`)."""
import asyncio
import sys

import asyncpg
from pydantic_settings import BaseSettings

from adapters.log_publisher import LogEventPublisher
from adapters.postgres_repo import PostgresOrderRepository
from domain.models import PlaceOrderCmd
from domain.service import PlaceOrder


class Settings(BaseSettings):
    database_url: str = "postgres://appuser:apppass@postgres:5432/appdb"


settings = Settings()


async def main():
    if len(sys.argv) < 3:
        print("Usage: cli-place-order <sku> <quantity>", file=sys.stderr)
        sys.exit(1)

    sku = sys.argv[1]
    quantity = int(sys.argv[2])

    dsn = settings.database_url
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
