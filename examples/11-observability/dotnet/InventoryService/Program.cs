using System.Diagnostics.Metrics;
using Grpc.Core;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Proto;

var builder = WebApplication.CreateBuilder(args);

builder.WebHost.ConfigureKestrel(k =>
    k.ListenAnyIP(50051, o => o.Protocols = HttpProtocols.Http2));
builder.Services.AddGrpc();

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("inventory-service"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter())
    .WithMetrics(m => m
        .AddMeter("inventory-service")
        .AddOtlpExporter());

var app = builder.Build();
app.MapGrpcService<InventoryImpl>();
app.Run();

public class InventoryImpl : InventoryService.InventoryServiceBase
{
    private static readonly Dictionary<string, int> Stock = new();
    private static readonly object Lock = new();
    private static readonly int InitialStock = int.Parse(
        Environment.GetEnvironmentVariable("INITIAL_STOCK") ?? "100");
    private static readonly Meter ServiceMeter = new("inventory-service");
    private static readonly Counter<long> StockReservations = ServiceMeter.CreateCounter<long>("stock.reservations");

    public override Task<ReserveResponse> ReserveStock(ReserveRequest request, ServerCallContext context)
    {
        lock (Lock)
        {
            if (!Stock.ContainsKey(request.Sku))
                Stock[request.Sku] = InitialStock;

            if (Stock[request.Sku] >= request.Quantity)
            {
                Stock[request.Sku] -= request.Quantity;
                StockReservations.Add(1,
                    new KeyValuePair<string, object?>("sku", request.Sku),
                    new KeyValuePair<string, object?>("confirmed", true));
                return Task.FromResult(new ReserveResponse { Confirmed = true, Remaining = Stock[request.Sku] });
            }

            StockReservations.Add(1,
                new KeyValuePair<string, object?>("sku", request.Sku),
                new KeyValuePair<string, object?>("confirmed", false));
            return Task.FromResult(new ReserveResponse { Confirmed = false, Remaining = Stock[request.Sku] });
        }
    }
}
