from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass(frozen=True)
class PlaceOrderCmd:
    sku: str
    quantity: int


@dataclass
class Order:
    id: str
    sku: str
    quantity: int
    status: str
    created_at: datetime

    @classmethod
    def create(cls, cmd: PlaceOrderCmd) -> "Order":
        if cmd.quantity <= 0:
            raise ValueError("quantity must be positive")
        if not cmd.sku:
            raise ValueError("sku is required")
        return cls(
            id=str(uuid.uuid4()),
            sku=cmd.sku,
            quantity=cmd.quantity,
            status="placed",
            created_at=datetime.now(timezone.utc),
        )


@dataclass(frozen=True)
class OrderPlaced:
    order_id: str
    sku: str
    quantity: int
