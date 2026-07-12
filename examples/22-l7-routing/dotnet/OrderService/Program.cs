using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");
var app = builder.Build();

var version = Environment.GetEnvironmentVariable("APP_VERSION") ?? "v1";

app.MapGet("/healthz", () => new { status = "ok", version });

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
