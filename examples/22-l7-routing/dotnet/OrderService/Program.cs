using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var version = builder.Configuration.GetValue("APP_VERSION", "v1");
builder.Services.AddHealthChecks();

var app = builder.Build();

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok", version }),
});

app.MapPost("/orders", async (HttpContext ctx) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var root = doc.RootElement;
    var sku = root.GetProperty("sku").GetString()!;
    var quantity = root.GetProperty("quantity").GetInt32();
    return Results.Json(new { id = "1", sku, quantity, version }, statusCode: 201);
});

app.MapGet("/orders", () => new { orders = Array.Empty<object>(), version });

app.Run();
