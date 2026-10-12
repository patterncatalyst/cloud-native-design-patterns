using OrderService.Domain;

namespace OrderService.Adapters;

public class LogEventPublisher(ILogger<LogEventPublisher> logger) : IEventPublisher
{
    public Task PublishAsync(OrderPlaced evt)
    {
        logger.LogInformation("EVENT OrderPlaced order_id={OrderId} sku={Sku} qty={Quantity}",
            evt.OrderId, evt.Sku, evt.Quantity);
        return Task.CompletedTask;
    }
}
