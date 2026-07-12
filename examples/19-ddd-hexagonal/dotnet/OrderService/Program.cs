using Npgsql;
using OrderService.Adapters;
using OrderService.Domain;

if (args.Length >= 3 && args[0] == "cli")
{
    var sku = args[1];
    var quantity = int.Parse(args[2]);
    var connStr = Environment.GetEnvironmentVariable("ConnectionStrings__Default")
        ?? "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass";

    var ds = new NpgsqlDataSourceBuilder(connStr).Build();
    using var loggerFactory = LoggerFactory.Create(b => b.AddConsole());
    var repo = new PostgresOrderRepository(ds);
    var events = new LogEventPublisher(loggerFactory.CreateLogger<LogEventPublisher>());
    var placeOrder = new PlaceOrderUseCase(repo, events);

    var order = await placeOrder.ExecuteAsync(new PlaceOrderCmd(sku, quantity));
    Console.WriteLine($"CLI_ORDER_CREATED id={order.Id} sku={order.Sku} qty={order.Quantity} status={order.Status}");
    return;
}

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var connString = builder.Configuration.GetConnectionString("Default")
    ?? throw new InvalidOperationException("ConnectionStrings:Default is required");

var dataSource = new NpgsqlDataSourceBuilder(connString).Build();
builder.Services.AddSingleton(dataSource);
builder.Services.AddSingleton<IOrderRepository, PostgresOrderRepository>();
builder.Services.AddSingleton<IEventPublisher, LogEventPublisher>();
builder.Services.AddSingleton<PlaceOrderUseCase>();

var app = builder.Build();

app.MapGet("/healthz", () => new { status = "ok" });

app.MapPost("/orders", async (HttpContext ctx, PlaceOrderUseCase placeOrder) =>
{
    using var doc = await System.Text.Json.JsonDocument.ParseAsync(ctx.Request.Body);
    var root = doc.RootElement;
    var sku = root.GetProperty("sku").GetString()!;
    var quantity = root.GetProperty("quantity").GetInt32();

    if (string.IsNullOrEmpty(sku) || quantity <= 0)
        return Results.Json(new { detail = "validation error" }, statusCode: 422);

    var order = await placeOrder.ExecuteAsync(new PlaceOrderCmd(sku, quantity));
    return Results.Json(new { id = order.Id, sku = order.Sku, quantity = order.Quantity, status = order.Status }, statusCode: 201);
});

app.MapGet("/orders/{orderId}", async (string orderId, IOrderRepository repo) =>
{
    var order = await repo.FindByIdAsync(orderId);
    if (order is null)
        return Results.NotFound(new { detail = "not found" });
    return Results.Ok(new { id = order.Id, sku = order.Sku, quantity = order.Quantity, status = order.Status });
});

app.MapGet("/orders", async (IOrderRepository repo) =>
{
    var orders = await repo.ListAllAsync();
    return orders.Select(o => new { id = o.Id, sku = o.Sku, quantity = o.Quantity, status = o.Status });
});

app.Run();
