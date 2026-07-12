using Grpc.Core;
using Inventory.Grpc;
using Microsoft.AspNetCore.Server.Kestrel.Core;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.ConfigureKestrel(k =>
    k.ListenAnyIP(50051, o => o.Protocols = HttpProtocols.Http2));
builder.Services.AddGrpc();
builder.Services.AddSingleton<StockStore>();
var app = builder.Build();
app.MapGrpcService<InventoryServiceImpl>();
app.Run();

public class StockStore
{
    private readonly int _initial;
    private readonly Dictionary<string, int> _stock = new();

    public StockStore()
    {
        _initial = int.Parse(Environment.GetEnvironmentVariable("INITIAL_STOCK") ?? "10");
    }

    public (bool confirmed, int remaining) Reserve(string sku, int quantity)
    {
        lock (_stock)
        {
            if (!_stock.ContainsKey(sku))
                _stock[sku] = _initial;

            if (_stock[sku] < quantity)
                return (false, _stock[sku]);

            _stock[sku] -= quantity;
            return (true, _stock[sku]);
        }
    }
}

public class InventoryServiceImpl : InventoryService.InventoryServiceBase
{
    private readonly StockStore _store;
    private readonly ILogger<InventoryServiceImpl> _logger;

    public InventoryServiceImpl(StockStore store, ILogger<InventoryServiceImpl> logger)
    {
        _store = store;
        _logger = logger;
    }

    public override Task<ReserveResponse> ReserveStock(ReserveRequest request, ServerCallContext context)
    {
        var (confirmed, remaining) = _store.Reserve(request.Sku, request.Quantity);

        if (!confirmed)
        {
            throw new RpcException(new Status(
                StatusCode.FailedPrecondition,
                $"insufficient stock for {request.Sku}: have {remaining}, need {request.Quantity}"));
        }

        _logger.LogInformation("reserved sku={Sku} qty={Qty} remaining={Remaining}",
            request.Sku, request.Quantity, remaining);
        return Task.FromResult(new ReserveResponse { Confirmed = true, Remaining = remaining });
    }
}
