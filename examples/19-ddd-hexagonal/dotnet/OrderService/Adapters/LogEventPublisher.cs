using OrderService.Domain;

namespace OrderService.Adapters;

public class LogEventPublisher : IEventPublisher
{
    private readonly ILogger<LogEventPublisher> _logger;

    public LogEventPublisher(ILogger<LogEventPublisher> logger) => _logger = logger;

    public Task PublishAsync(OrderPlaced evt)
    {
        _logger.LogInformation("EVENT OrderPlaced order_id={OrderId} sku={Sku} qty={Quantity}",
            evt.OrderId, evt.Sku, evt.Quantity);
        return Task.CompletedTask;
    }
}
