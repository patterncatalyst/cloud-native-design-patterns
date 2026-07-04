from .models import Order, OrderPlaced, PlaceOrderCmd
from .ports import EventPublisher, OrderRepository


class PlaceOrder:
    def __init__(self, repo: OrderRepository, events: EventPublisher):
        self.repo = repo
        self.events = events

    async def __call__(self, cmd: PlaceOrderCmd) -> Order:
        order = Order.create(cmd)
        await self.repo.save(order)
        await self.events.publish(
            OrderPlaced(order_id=order.id, sku=order.sku, quantity=order.quantity)
        )
        return order
