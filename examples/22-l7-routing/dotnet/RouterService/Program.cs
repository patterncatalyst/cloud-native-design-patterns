using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");
var app = builder.Build();
var logger = app.Logger;

var rules = new Dictionary<string, object>
{
    ["vip_threshold"] = 1000,
    ["priority_topic"] = "orders.priority",
    ["default_topic"] = "orders.default"
};

app.MapGet("/healthz", () => new { status = "ok" });

app.MapPost("/orders", async (HttpContext ctx) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var root = doc.RootElement;
    var sku = root.GetProperty("sku").GetString()!;
    var quantity = root.GetProperty("quantity").GetInt32();
    var amount = root.GetProperty("amount").GetDouble();

    var threshold = Convert.ToDouble(rules["vip_threshold"]);
    if (amount >= threshold)
    {
        var topic = (string)rules["priority_topic"];
        logger.LogInformation("ROUTED sku={Sku} amount={Amount:F2} -> {Topic} (VIP)", sku, amount, topic);
        return Results.Json(new { routed_to = topic, vip = true, amount }, statusCode: 201);
    }
    else
    {
        var topic = (string)rules["default_topic"];
        logger.LogInformation("ROUTED sku={Sku} amount={Amount:F2} -> {Topic}", sku, amount, topic);
        return Results.Json(new { routed_to = topic, vip = false, amount }, statusCode: 201);
    }
});

app.MapGet("/rules", () => rules);

app.MapPut("/rules", async (HttpContext ctx) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    foreach (var prop in doc.RootElement.EnumerateObject())
    {
        rules[prop.Name] = prop.Value.ValueKind switch
        {
            JsonValueKind.Number => prop.Value.GetDouble() == Math.Floor(prop.Value.GetDouble())
                ? (object)(int)prop.Value.GetDouble()
                : prop.Value.GetDouble(),
            JsonValueKind.String => prop.Value.GetString()!,
            _ => prop.Value.ToString()
        };
    }
    logger.LogInformation("RULES_UPDATED {Rules}", JsonSerializer.Serialize(rules));
    return Results.Json(rules);
});

app.Run();
