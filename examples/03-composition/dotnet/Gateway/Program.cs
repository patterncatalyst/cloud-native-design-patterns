using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using GreenDonut;
using Grpc.Net.Client;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Proto;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var orderApiUrl = builder.Configuration.GetValue("ORDER_API_URL", "http://order-api:8081");
var inventoryAddr = builder.Configuration.GetValue("INVENTORY_ADDR", "inventory:50051");

var channel = GrpcChannel.ForAddress($"http://{inventoryAddr}",
    new GrpcChannelOptions { HttpHandler = new SocketsHttpHandler { EnableMultipleHttp2Connections = true } });
builder.Services.AddSingleton(new Inventory.InventoryClient(channel));
builder.Services.AddHttpClient<OrderApiClient>(c => c.BaseAddress = new Uri(orderApiUrl));

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("gateway"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter(o => o.Endpoint = new Uri(
            builder.Configuration.GetValue("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318"))));

builder.Services
    .AddGraphQLServer()
    .AddQueryType<Query>()
    .AddTypeExtension<OrderStockExtension>();

builder.Services.AddHealthChecks();

var app = builder.Build();

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});
app.MapGraphQL("/graphql");

app.Run();

/// <summary>Typed client for the order API; the factory owns the handler lifetime.</summary>
public class OrderApiClient(HttpClient http)
{
    public async Task<List<OrderDto>> ListAsync(int limit, CancellationToken ct) =>
        await http.GetFromJsonAsync<List<OrderDto>>($"/orders?limit={limit}", ct) ?? [];

    public async Task<OrderDto?> FindAsync(string id, CancellationToken ct)
    {
        using var resp = await http.GetAsync($"/orders/{id}", ct);
        return resp.IsSuccessStatusCode ? await resp.Content.ReadFromJsonAsync<OrderDto>(ct) : null;
    }
}

public class OrderDto
{
    public string Id { get; set; } = "";
    public string Sku { get; set; } = "";
    public int Quantity { get; set; }
    public string Status { get; set; } = "";
}

public class Query
{
    public Task<List<OrderDto>> GetOrders(OrderApiClient api, CancellationToken ct, int limit = 50) =>
        api.ListAsync(limit, ct);

    public Task<OrderDto?> GetOrder(OrderApiClient api, string id, CancellationToken ct) =>
        api.FindAsync(id, ct);
}

[ExtendObjectType(typeof(OrderDto))]
public class OrderStockExtension
{
    public async Task<int?> GetStock([Parent] OrderDto order, StockBatchDataLoader loader)
        => await loader.LoadAsync(order.Sku);
}

public partial class StockBatchDataLoader : BatchDataLoader<string, int?>
{
    private readonly Inventory.InventoryClient _client;
    private readonly ILogger<StockBatchDataLoader> _logger;

    public StockBatchDataLoader(
        Inventory.InventoryClient client,
        IBatchScheduler batchScheduler,
        DataLoaderOptions options,
        ILogger<StockBatchDataLoader> logger)
        : base(batchScheduler, options)
    {
        _client = client;
        _logger = logger;
    }

    [LoggerMessage(Level = LogLevel.Information, Message = "DataLoader batched {Count} skus in one gRPC call")]
    private partial void LogBatched(int count);

    protected override async Task<IReadOnlyDictionary<string, int?>> LoadBatchAsync(
        IReadOnlyList<string> keys, CancellationToken ct)
    {
        var request = new GetStockBatchRequest();
        request.Skus.AddRange(keys);
        var reply = await _client.GetStockBatchAsync(request, cancellationToken: ct);
        LogBatched(keys.Count);
        return reply.Items.ToDictionary(i => i.Sku, i => (int?)i.Available);
    }
}
