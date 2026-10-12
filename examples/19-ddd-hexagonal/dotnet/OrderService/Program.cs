using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using OrderService.Adapters;
using OrderService.Domain;

// CLI driving adapter: a plain host, so no Kestrel and no port is bound. It reuses the EF Core
// repository and the use case through the same registrations as the web host.
if (args is ["place-order", ..])
{
    var cli = Host.CreateApplicationBuilder();
    cli.Services.AddOrderAdapters(cli.Configuration);
    using var host = cli.Build();
    await using var scope = host.Services.CreateAsyncScope();
    return await CliPlaceOrder.RunAsync(args[1..], scope.ServiceProvider.GetRequiredService<PlaceOrderUseCase>());
}

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

builder.Services.AddOrderAdapters(builder.Configuration);
builder.Services.AddHealthChecks();

var app = builder.Build();

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

app.MapPost("/orders", async (PlaceOrderCmd cmd, PlaceOrderUseCase placeOrder) =>
{
    if (string.IsNullOrEmpty(cmd.Sku) || cmd.Quantity <= 0)
        return Results.Json(new { detail = "validation error" }, statusCode: StatusCodes.Status422UnprocessableEntity);

    var order = await placeOrder.ExecuteAsync(cmd);
    return Results.Json(OrderView.From(order), statusCode: StatusCodes.Status201Created);
});

app.MapGet("/orders/{orderId}", async (string orderId, IOrderRepository repo) =>
    await repo.FindByIdAsync(orderId) is { } order
        ? Results.Ok(OrderView.From(order))
        : Results.NotFound(new { detail = "not found" }));

app.MapGet("/orders", async (IOrderRepository repo) =>
    (await repo.ListAllAsync()).Select(OrderView.From));

app.Run();
return 0;
