using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var monolithUrl = builder.Configuration.GetValue("MONOLITH_URL", "http://monolith:8080");
var newServiceUrl = builder.Configuration.GetValue("NEW_SERVICE_URL", "http://new-service:8080");

builder.Services.AddHttpClient<UpstreamClient>();
builder.Services.AddHealthChecks();

var app = builder.Build();

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

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

app.MapPost("/orders", async (HttpContext ctx, UpstreamClient upstreams) =>
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

    var reply = await upstreams.PostOrderAsync(ResolveUpstream(tenant), body);
    ctx.Response.StatusCode = reply.StatusCode;
    ctx.Response.ContentType = "application/json";
    await ctx.Response.WriteAsync(reply.Body);
});

app.MapGet("/orders/{orderId}", async (string orderId, HttpContext ctx, UpstreamClient upstreams, string tenant = "") =>
{
    var reply = await upstreams.GetOrderAsync(ResolveUpstream(tenant), orderId);
    ctx.Response.StatusCode = reply.StatusCode;
    ctx.Response.ContentType = "application/json";
    await ctx.Response.WriteAsync(reply.Body);
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

public record UpstreamReply(int StatusCode, string Body);

/// <summary>Typed client for the monolith and the extracted service; the factory manages the handlers.</summary>
public class UpstreamClient(HttpClient http)
{
    public Task<UpstreamReply> PostOrderAsync(string upstream, string json) =>
        SendAsync(http.PostAsync($"{upstream}/orders", new StringContent(json, System.Text.Encoding.UTF8, "application/json")));

    public Task<UpstreamReply> GetOrderAsync(string upstream, string orderId) =>
        SendAsync(http.GetAsync($"{upstream}/orders/{orderId}"));

    private static async Task<UpstreamReply> SendAsync(Task<HttpResponseMessage> request)
    {
        using var resp = await request;
        return new UpstreamReply((int)resp.StatusCode, await resp.Content.ReadAsStringAsync());
    }
}
