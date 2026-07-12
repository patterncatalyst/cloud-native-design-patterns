using Grpc.Core;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Proto;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.ConfigureKestrel(k =>
    k.ListenAnyIP(50051, o => o.Protocols = HttpProtocols.Http2));
builder.Services.AddGrpc();
var app = builder.Build();

app.MapGrpcService<InventoryImpl>();
app.Run();

public class InventoryImpl : Inventory.InventoryBase
{
    private static readonly Dictionary<string, int> Stock = new()
    {
        ["widget-a"] = 42, ["widget-b"] = 17,
        ["gadget-x"] = 100, ["gadget-y"] = 0
    };
    private static readonly object Lock = new();

    public override Task<GetStockReply> GetStock(GetStockRequest request, ServerCallContext context)
    {
        lock (Lock)
        {
            var available = Stock.GetValueOrDefault(request.Sku, 0);
            return Task.FromResult(new GetStockReply { Sku = request.Sku, Available = available });
        }
    }

    public override Task<GetStockBatchReply> GetStockBatch(GetStockBatchRequest request, ServerCallContext context)
    {
        var reply = new GetStockBatchReply();
        lock (Lock)
        {
            foreach (var sku in request.Skus)
                reply.Items.Add(new GetStockReply { Sku = sku, Available = Stock.GetValueOrDefault(sku, 0) });
        }
        return Task.FromResult(reply);
    }
}
