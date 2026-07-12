namespace OrderService.Domain;

public class PlaceOrderUseCase
{
    private readonly IOrderRepository _repo;
    private readonly IEventPublisher _events;

    public PlaceOrderUseCase(IOrderRepository repo, IEventPublisher events)
    {
        _repo = repo;
        _events = events;
    }

    public async Task<Order> ExecuteAsync(PlaceOrderCmd cmd)
    {
        var order = Order.Create(cmd);
        await _repo.SaveAsync(order);
        await _events.PublishAsync(new OrderPlaced(order.Id, order.Sku, order.Quantity));
        return order;
    }
}
