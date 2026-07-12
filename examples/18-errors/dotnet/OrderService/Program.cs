using System.Diagnostics;
using System.Text.Json;
using Grpc.Core;
using GrpcStatusCode = Grpc.Core.StatusCode;
using Grpc.Net.Client;
using Inventory.Grpc;
using Microsoft.AspNetCore.Mvc;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order-service"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter());

var app = builder.Build();

var inventoryAddr = Environment.GetEnvironmentVariable("INVENTORY_ADDR") ?? "http://inventory:50051";
var channel = GrpcChannel.ForAddress(inventoryAddr);
var inventoryClient = new InventoryService.InventoryServiceClient(channel);

string? GetTraceId()
{
    var activity = Activity.Current;
    return activity?.TraceId.ToString();
}

IResult ProblemResponse(int status, string code, string message, bool retryable = false,
    int? retryAfter = null, List<object>? details = null)
{
    var body = new Dictionary<string, object>
    {
        ["type"] = $"urn:error:{code.ToLower().Replace('_', '-')}",
        ["title"] = message,
        ["status"] = status,
        ["code"] = code,
        ["traceId"] = GetTraceId() ?? "",
        ["retryable"] = retryable
    };
    if (retryAfter.HasValue)
        body["retryAfter"] = retryAfter.Value;
    if (details != null)
        body["details"] = details;

    return new ProblemResult(body, status, retryAfter);
}

app.MapGet("/healthz", () => new { status = "ok" });

app.MapPost("/orders", async (HttpContext ctx) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var root = doc.RootElement;

    var errors = new List<object>();
    string? sku = null;
    int quantity = 0;

    if (!root.TryGetProperty("sku", out var skuProp) || skuProp.GetString() is null or "")
        errors.Add(new { field = "body.sku", message = "String should have at least 1 character" });
    else
        sku = skuProp.GetString()!;

    if (!root.TryGetProperty("quantity", out var qtyProp) || qtyProp.GetInt32() <= 0)
        errors.Add(new { field = "body.quantity", message = "Input should be greater than 0" });
    else
        quantity = qtyProp.GetInt32();

    if (errors.Count > 0)
        return ProblemResponse(422, "VALIDATION_ERROR", "request validation failed", details: errors);

    var orderId = Guid.NewGuid().ToString();

    try
    {
        var resp = await inventoryClient.ReserveStockAsync(new ReserveRequest
        {
            Sku = sku!,
            Quantity = quantity
        });

        if (!resp.Confirmed)
        {
            return ProblemResponse(409, "STOCK_UNAVAILABLE",
                $"insufficient stock for {sku}", retryable: false);
        }

        return Results.Json(new
        {
            id = orderId,
            sku,
            quantity,
            status = "confirmed",
            remaining_stock = resp.Remaining
        }, statusCode: 201);
    }
    catch (RpcException ex) when (ex.StatusCode == GrpcStatusCode.Unavailable)
    {
        return ProblemResponse(503, "INVENTORY_UNAVAILABLE",
            "inventory service is temporarily unavailable",
            retryable: true, retryAfter: 2);
    }
    catch (RpcException ex) when (ex.StatusCode == GrpcStatusCode.FailedPrecondition)
    {
        return ProblemResponse(409, "STOCK_UNAVAILABLE",
            ex.Status.Detail, retryable: false);
    }
    catch (RpcException ex)
    {
        app.Logger.LogError("gRPC error: StatusCode={Code} Detail={Detail}", ex.StatusCode, ex.Status.Detail);
        return ProblemResponse(502, "UPSTREAM_ERROR",
            "unexpected error from inventory service",
            retryable: true, retryAfter: 5);
    }
});

app.Run();

class ProblemResult(Dictionary<string, object> body, int statusCode, int? retryAfter) : IResult
{
    public async Task ExecuteAsync(HttpContext httpContext)
    {
        httpContext.Response.StatusCode = statusCode;
        httpContext.Response.ContentType = "application/problem+json";
        if (retryAfter.HasValue)
            httpContext.Response.Headers["Retry-After"] = retryAfter.Value.ToString();
        await httpContext.Response.WriteAsJsonAsync(body);
    }
}
