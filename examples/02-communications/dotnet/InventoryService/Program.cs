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
    private static readonly Dictionary<string, int> Stock = new();
    private static readonly object Lock = new();
    private static readonly int InitialStock = int.Parse(
        Environment.GetEnvironmentVariable("INITIAL_STOCK") ?? "100");

    public override Task<ReserveReply> ReserveStock(ReserveRequest request, ServerCallContext context)
    {
        lock (Lock)
        {
            if (!Stock.ContainsKey(request.Sku))
                Stock[request.Sku] = InitialStock;

            if (Stock[request.Sku] >= request.Quantity)
            {
                Stock[request.Sku] -= request.Quantity;
                return Task.FromResult(new ReserveReply { Reserved = true, Remaining = Stock[request.Sku] });
            }
            return Task.FromResult(new ReserveReply { Reserved = false, Remaining = Stock[request.Sku] });
        }
    }
}
