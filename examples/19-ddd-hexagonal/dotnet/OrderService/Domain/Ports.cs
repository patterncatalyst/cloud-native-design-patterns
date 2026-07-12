namespace OrderService.Domain;

public interface IOrderRepository
{
    Task SaveAsync(Order order);
    Task<Order?> FindByIdAsync(string orderId);
    Task<IReadOnlyList<Order>> ListAllAsync();
}

public interface IEventPublisher
{
    Task PublishAsync(OrderPlaced evt);
}
