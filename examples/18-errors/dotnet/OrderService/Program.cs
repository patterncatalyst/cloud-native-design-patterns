using System.Diagnostics;
using Grpc.Core;
using GrpcStatusCode = Grpc.Core.StatusCode;
using Inventory.Grpc;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order-service"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter());

// Problem bodies carry the bare W3C trace id (32 hex digits), not the framework's traceparent-style default.
builder.Services.AddProblemDetails(o => o.CustomizeProblemDetails = c =>
    c.ProblemDetails.Extensions["traceId"] = Activity.Current?.TraceId.ToString() ?? "");
builder.Services.AddHealthChecks();

var inventoryAddr = builder.Configuration.GetValue("INVENTORY_ADDR", "http://inventory:50051");
// gRPC client factory: the channel is managed like any typed HttpClient.
builder.Services.AddGrpcClient<InventoryService.InventoryServiceClient>(o => o.Address = new Uri(inventoryAddr));

var app = builder.Build();

app.UseExceptionHandler();
app.UseStatusCodePages();

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

app.MapPost("/orders", async (OrderRequest request, InventoryService.InventoryServiceClient inventory,
    HttpContext http, ILogger<Program> logger) =>
{
    var errors = new List<object>();
    if (string.IsNullOrEmpty(request.Sku))
        errors.Add(new { field = "body.sku", message = "String should have at least 1 character" });
    if (request.Quantity is not > 0)
        errors.Add(new { field = "body.quantity", message = "Input should be greater than 0" });

    if (errors.Count > 0)
        return ProblemFor(http, 422, "VALIDATION_ERROR", "request validation failed", details: errors);

    try
    {
        var resp = await inventory.ReserveStockAsync(new ReserveRequest
        {
            Sku = request.Sku!,
            Quantity = request.Quantity!.Value
        });

        if (!resp.Confirmed)
            return ProblemFor(http, 409, "STOCK_UNAVAILABLE", $"insufficient stock for {request.Sku}");

        return TypedResults.Json(new
        {
            id = Guid.NewGuid().ToString(),
            sku = request.Sku,
            quantity = request.Quantity,
            status = "confirmed",
            remaining_stock = resp.Remaining
        }, statusCode: StatusCodes.Status201Created);
    }
    catch (RpcException ex) when (ex.StatusCode == GrpcStatusCode.Unavailable)
    {
        return ProblemFor(http, 503, "INVENTORY_UNAVAILABLE",
            "inventory service is temporarily unavailable", retryable: true, retryAfter: 2);
    }
    catch (RpcException ex) when (ex.StatusCode == GrpcStatusCode.FailedPrecondition)
    {
        return ProblemFor(http, 409, "STOCK_UNAVAILABLE", ex.Status.Detail);
    }
    catch (RpcException ex)
    {
        logger.LogError("gRPC error: StatusCode={Code} Detail={Detail}", ex.StatusCode, ex.Status.Detail);
        return ProblemFor(http, 502, "UPSTREAM_ERROR",
            "unexpected error from inventory service", retryable: true, retryAfter: 5);
    }
});

app.Run();

/// <summary>RFC 9457 problem with the collection's extension members: code, retryable, retryAfter, details (traceId is added by CustomizeProblemDetails).</summary>
static IResult ProblemFor(HttpContext http, int status, string code, string message,
    bool retryable = false, int? retryAfter = null, List<object>? details = null)
{
    var extensions = new Dictionary<string, object?>
    {
        ["code"] = code,
        ["retryable"] = retryable,
    };
    if (retryAfter is { } seconds)
    {
        extensions["retryAfter"] = seconds;
        http.Response.Headers.RetryAfter = seconds.ToString();
    }
    if (details is not null)
        extensions["details"] = details;

    return TypedResults.Problem(
        title: message,
        statusCode: status,
        type: $"urn:error:{code.ToLower().Replace('_', '-')}",
        extensions: extensions);
}

public record OrderRequest(string? Sku, int? Quantity);
