using System.Text.Json;
using GreenDonut;
using Grpc.Net.Client;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Proto;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var orderApiUrl = Environment.GetEnvironmentVariable("ORDER_API_URL") ?? "http://order-api:8081";
var inventoryAddr = Environment.GetEnvironmentVariable("INVENTORY_ADDR") ?? "inventory:50051";

var channel = GrpcChannel.ForAddress($"http://{inventoryAddr}",
    new GrpcChannelOptions { HttpHandler = new SocketsHttpHandler { EnableMultipleHttp2Connections = true } });
builder.Services.AddSingleton(new Inventory.InventoryClient(channel));
builder.Services.AddSingleton(new OrderApiClient(orderApiUrl));

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("gateway"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter(o => o.Endpoint = new Uri(
            Environment.GetEnvironmentVariable("OTEL_EXPORTER_OTLP_ENDPOINT") ?? "http://lgtm:4318")));

builder.Services
    .AddGraphQLServer()
    .AddQueryType<Query>()
    .AddTypeExtension<OrderStockExtension>();

var app = builder.Build();

app.MapGet("/healthz", () => new { status = "ok" });
app.MapGraphQL("/graphql");

app.Run();

public class OrderApiClient
{
    public HttpClient Http { get; }
    public OrderApiClient(string baseUrl) => Http = new HttpClient { BaseAddress = new Uri(baseUrl) };
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
    public async Task<List<OrderDto>> GetOrders(OrderApiClient api, int limit = 50)
    {
        var resp = await api.Http.GetAsync($"/orders?limit={limit}");
        var json = await resp.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<List<OrderDto>>(json,
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true }) ?? new();
    }

    public async Task<OrderDto?> GetOrder(OrderApiClient api, string id)
    {
        var resp = await api.Http.GetAsync($"/orders/{id}");
        if (!resp.IsSuccessStatusCode) return null;
        var json = await resp.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<OrderDto>(json,
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
    }
}

[ExtendObjectType(typeof(OrderDto))]
public class OrderStockExtension
{
    public async Task<int?> GetStock([Parent] OrderDto order, StockBatchDataLoader loader)
        => await loader.LoadAsync(order.Sku);
}

public class StockBatchDataLoader : BatchDataLoader<string, int?>
{
    private readonly Inventory.InventoryClient _client;

    public StockBatchDataLoader(
        Inventory.InventoryClient client,
        IBatchScheduler batchScheduler,
        DataLoaderOptions? options = null)
        : base(batchScheduler, options) => _client = client;

    protected override async Task<IReadOnlyDictionary<string, int?>> LoadBatchAsync(
        IReadOnlyList<string> keys, CancellationToken ct)
    {
        var request = new GetStockBatchRequest();
        request.Skus.AddRange(keys);
        var reply = await _client.GetStockBatchAsync(request, cancellationToken: ct);
        Console.WriteLine($"DataLoader batched {keys.Count} skus in one gRPC call");
        return reply.Items.ToDictionary(i => i.Sku, i => (int?)i.Available);
    }
}
