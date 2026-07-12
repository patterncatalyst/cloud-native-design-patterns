using OpenFeature;
using OpenFeature.Contrib.Providers.Flagd;
using OpenFeature.Model;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");
var app = builder.Build();
var logger = app.Logger;

var flagdHost = Environment.GetEnvironmentVariable("FLAGD_HOST") ?? "flagd";
var flagdPort = int.Parse(Environment.GetEnvironmentVariable("FLAGD_PORT") ?? "8013");

try
{
    var provider = new FlagdProvider(new Uri($"http://{flagdHost}:{flagdPort}"));
    await Api.Instance.SetProviderAsync(provider);
    logger.LogInformation("OpenFeature provider set: flagd at {Host}:{Port}", flagdHost, flagdPort);
}
catch (Exception ex)
{
    logger.LogError(ex, "Failed to connect to flagd — will use defaults");
}

async Task<bool> GetFlag(string name, bool defaultValue, EvaluationContext evalCtx)
{
    try
    {
        var client = Api.Instance.GetClient();
        var flagTask = client.GetBooleanValueAsync(name, defaultValue, evalCtx);
        var completed = await Task.WhenAny(flagTask, Task.Delay(2000));
        return completed == flagTask ? flagTask.Result : defaultValue;
    }
    catch
    {
        return defaultValue;
    }
}

EvaluationContext MakeCtx(HttpContext ctx)
{
    var user = ctx.Request.Headers["X-User"].FirstOrDefault() ?? "anonymous";
    var plan = ctx.Request.Headers["X-Plan"].FirstOrDefault() ?? "free";
    var region = ctx.Request.Headers["X-Region"].FirstOrDefault() ?? "us";
    return EvaluationContext.Builder()
        .SetTargetingKey(user)
        .Set("plan", plan)
        .Set("region", region)
        .Build();
}

app.MapGet("/healthz", () => new { status = "ok" });

// 1. Release flag — new-checkout
app.MapPost("/checkout", async (HttpContext ctx) =>
{
    var user = ctx.Request.Headers["X-User"].FirstOrDefault() ?? "anonymous";
    var plan = ctx.Request.Headers["X-Plan"].FirstOrDefault() ?? "free";
    var evalCtx = MakeCtx(ctx);
    var useNew = await GetFlag("new-checkout", false, evalCtx);
    return Results.Json(new { path = useNew ? "new" : "legacy", user, plan });
});

// 2. Kill switch — recommendations-enabled
app.MapGet("/recommendations", async (HttpContext ctx) =>
{
    var evalCtx = MakeCtx(ctx);
    var enabled = await GetFlag("recommendations-enabled", true, evalCtx);
    if (!enabled)
        return Results.Json(new { recommendations = Array.Empty<string>(), reason = "killed" });
    return Results.Json(new
    {
        recommendations = new[] { "product-a", "product-b", "product-c" },
        reason = "live"
    });
});

// 3. Simple flag — dark-mode
app.MapGet("/ui-config", async (HttpContext ctx) =>
{
    var user = ctx.Request.Headers["X-User"].FirstOrDefault() ?? "anonymous";
    var evalCtx = MakeCtx(ctx);
    var dark = await GetFlag("dark-mode", false, evalCtx);
    return Results.Json(new { dark_mode = dark, user });
});

// 4. Debug endpoint — all flags
app.MapGet("/flags", async (HttpContext ctx) =>
{
    var user = ctx.Request.Headers["X-User"].FirstOrDefault() ?? "anonymous";
    var plan = ctx.Request.Headers["X-Plan"].FirstOrDefault() ?? "free";
    var evalCtx = MakeCtx(ctx);

    var newCheckout = await GetFlag("new-checkout", false, evalCtx);
    var darkMode = await GetFlag("dark-mode", false, evalCtx);
    var recsEnabled = await GetFlag("recommendations-enabled", true, evalCtx);

    return Results.Json(new Dictionary<string, object>
    {
        ["new-checkout"] = newCheckout,
        ["dark-mode"] = darkMode,
        ["recommendations-enabled"] = recsEnabled,
        ["user"] = user,
        ["plan"] = plan
    });
});

app.Run();
