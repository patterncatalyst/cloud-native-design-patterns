using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");
var app = builder.Build();

var monolithUrl = Environment.GetEnvironmentVariable("MONOLITH_URL") ?? "http://monolith:8080";
var newServiceUrl = Environment.GetEnvironmentVariable("NEW_SERVICE_URL") ?? "http://new-service:8080";
var httpClient = new HttpClient();

var routes = new Dictionary<string, object>
{
    ["tenant_routes"] = new Dictionary<string, string> { ["acme"] = "new-service" },
    ["default"] = "monolith"
};

string ResolveUpstream(string tenant)
{
    if (routes["tenant_routes"] is Dictionary<string, string> tenantRoutes
        && tenantRoutes.TryGetValue(tenant, out var target) && target == "new-service")
        return newServiceUrl;
    return monolithUrl;
}

app.MapGet("/healthz", () => new { status = "ok" });

app.MapPost("/orders", async (HttpContext ctx) =>
{
    var body = await new StreamReader(ctx.Request.Body).ReadToEndAsync();
    var tenant = "";
    try
    {
        using var doc = JsonDocument.Parse(body);
        if (doc.RootElement.TryGetProperty("tenant", out var t))
            tenant = t.GetString() ?? "";
    }
    catch { }

    var upstream = ResolveUpstream(tenant);
    var resp = await httpClient.PostAsync($"{upstream}/orders",
        new StringContent(body, System.Text.Encoding.UTF8, "application/json"));
    var content = await resp.Content.ReadAsStringAsync();
    ctx.Response.StatusCode = (int)resp.StatusCode;
    ctx.Response.ContentType = "application/json";
    await ctx.Response.WriteAsync(content);
});

app.MapGet("/orders/{orderId}", async (string orderId, HttpContext ctx, string tenant = "") =>
{
    var upstream = ResolveUpstream(tenant);
    var resp = await httpClient.GetAsync($"{upstream}/orders/{orderId}");
    var content = await resp.Content.ReadAsStringAsync();
    ctx.Response.StatusCode = (int)resp.StatusCode;
    ctx.Response.ContentType = "application/json";
    await ctx.Response.WriteAsync(content);
});

app.MapGet("/rules", () => routes);

app.MapPut("/rules", async (HttpContext ctx) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    foreach (var prop in doc.RootElement.EnumerateObject())
    {
        if (prop.Name == "tenant_routes" && prop.Value.ValueKind == JsonValueKind.Object)
        {
            var tr = new Dictionary<string, string>();
            foreach (var inner in prop.Value.EnumerateObject())
                tr[inner.Name] = inner.Value.GetString()!;
            routes["tenant_routes"] = tr;
        }
        else if (prop.Name == "default")
        {
            routes["default"] = prop.Value.GetString()!;
        }
    }
    return Results.Json(routes);
});

app.Run();
