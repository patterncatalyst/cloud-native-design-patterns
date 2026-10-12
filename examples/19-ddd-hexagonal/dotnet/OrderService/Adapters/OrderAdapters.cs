using Microsoft.EntityFrameworkCore;
using OrderService.Domain;

namespace OrderService.Adapters;

public static class OrderAdapters
{
    /// <summary>Wires the use case to its driven adapters; the REST host and the CLI host share it.</summary>
    public static IServiceCollection AddOrderAdapters(this IServiceCollection services, IConfiguration configuration)
    {
        var connString = configuration.GetConnectionString("Default")
            ?? throw new InvalidOperationException("ConnectionStrings:Default is required");

        services.AddDbContext<OrdersContext>(o => o.UseNpgsql(connString));
        services.AddScoped<IOrderRepository, EfOrderRepository>();
        services.AddSingleton<IEventPublisher, LogEventPublisher>();
        services.AddScoped<PlaceOrderUseCase>();
        return services;
    }
}

/// <summary>The REST representation of an order.</summary>
public record OrderView(string Id, string Sku, int Quantity, string Status)
{
    public static OrderView From(Order o) => new(o.Id, o.Sku, o.Quantity, o.Status);
}
