namespace OrderService.Domain;

public class PlaceOrderUseCase(IOrderRepository repo, IEventPublisher events)
{
    public async Task<Order> ExecuteAsync(PlaceOrderCmd cmd)
    {
        var order = Order.Create(cmd);
        await repo.SaveAsync(order);
        await events.PublishAsync(new OrderPlaced(order.Id, order.Sku, order.Quantity));
        return order;
    }
}
