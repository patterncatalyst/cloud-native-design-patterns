import logging

from domain.models import OrderPlaced

logger = logging.getLogger("events")


class LogEventPublisher:
    async def publish(self, event: OrderPlaced) -> None:
        logger.info(
            "EVENT OrderPlaced order_id=%s sku=%s qty=%d",
            event.order_id,
            event.sku,
            event.quantity,
        )
