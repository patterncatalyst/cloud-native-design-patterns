using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var connString = builder.Configuration.GetConnectionString("Default")
    ?? throw new InvalidOperationException("ConnectionStrings:Default is required");

builder.Services.AddDbContextFactory<SagaContext>(o => o.UseNpgsql(connString));
builder.Services.AddSingleton<SagaEngine>();
builder.Services.AddHostedService<SagaResumeService>();

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("saga-orchestrator"))
    .WithTracing(t => t
        .AddSource("saga")
        .AddAspNetCoreInstrumentation()
        .AddNpgsql()
        .AddOtlpExporter());

// The REST payloads use snake_case field names (order_id, step_index).
builder.Services.ConfigureHttpJsonOptions(opts =>
    opts.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower);

builder.Services.AddHealthChecks();

var app = builder.Build();

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

app.MapPost("/sagas", async (SagaRequest request, SagaEngine engine, IDbContextFactory<SagaContext> dbFactory) =>
{
    var context = new JsonObject
    {
        ["order_id"] = request.OrderId,
        ["sku"] = request.Sku,
        ["total"] = request.Total,
    };
    if (request.FailShipping) context["fail_shipping"] = true;

    var sagaId = Guid.NewGuid().ToString();
    await using (var db = await dbFactory.CreateDbContextAsync())
    {
        db.Sagas.Add(new Saga { Id = sagaId, Status = "RUNNING", StepIndex = 0, Context = context });
        await db.SaveChangesAsync();
    }

    await engine.AdvanceAsync(sagaId);

    await using var read = await dbFactory.CreateDbContextAsync();
    var saga = await read.Sagas.AsNoTracking().SingleAsync(s => s.Id == sagaId);
    return Results.Json(SagaDto.From(saga), statusCode: StatusCodes.Status201Created);
});

app.MapGet("/sagas/{sagaId}", async (string sagaId, IDbContextFactory<SagaContext> dbFactory) =>
{
    await using var db = await dbFactory.CreateDbContextAsync();
    var saga = await db.Sagas.AsNoTracking().FirstOrDefaultAsync(s => s.Id == sagaId);
    return saga is null ? Results.NotFound(new { error = "not found" }) : Results.Ok(SagaDto.From(saga));
});

app.MapGet("/sagas/{sagaId}/log", async (string sagaId, IDbContextFactory<SagaContext> dbFactory) =>
{
    await using var db = await dbFactory.CreateDbContextAsync();
    return await db.Log.AsNoTracking().Where(l => l.SagaId == sagaId).OrderBy(l => l.Id)
        .Select(l => SagaLogDto.From(l)).ToListAsync();
});

app.Run();
