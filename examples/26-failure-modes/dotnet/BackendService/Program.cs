using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8081");
var app = builder.Build();

var mode = "healthy";
var callCount = 0;
var random = new Random();

app.MapPost("/mode", async (HttpContext ctx) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var newMode = doc.RootElement.GetProperty("mode").GetString()!;
    if (newMode is not ("healthy" or "slow" or "failing" or "flaky"))
        return Results.BadRequest(new { error = "mode must be healthy|slow|failing|flaky" });
    mode = newMode;
    callCount = 0;
    return Results.Ok(new { mode });
});

app.MapGet("/mode", () => new { mode, call_count = callCount });

app.MapGet("/process", async (HttpContext ctx) =>
{
    Interlocked.Increment(ref callCount);

    var deadlineHeader = ctx.Request.Headers["X-Deadline-Ms"].FirstOrDefault();
    if (deadlineHeader is not null && int.TryParse(deadlineHeader, out var remaining) && remaining < 100)
        return Results.Ok(new { status = "rejected", reason = "deadline_too_small", remaining_ms = remaining });

    if (mode == "slow")
    {
        await Task.Delay(5000);
        return Results.Ok(new { status = "ok", mode, delay = 5 });
    }
    if (mode == "failing")
        return Results.Json(new { detail = "backend error" }, statusCode: 500);
    if (mode == "flaky")
    {
        if (random.NextDouble() < 0.5)
            return Results.Json(new { detail = "backend error (flaky)" }, statusCode: 500);
        return Results.Ok(new { status = "ok", mode });
    }
    return Results.Ok(new { status = "ok", mode });
});

app.MapGet("/healthz", () => new { status = "ok" });

app.Run();
