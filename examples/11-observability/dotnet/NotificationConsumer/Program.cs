using Microsoft.EntityFrameworkCore;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = Host.CreateApplicationBuilder(args);

var dbUrl = builder.Configuration.GetValue("DATABASE_URL",
    "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass");

builder.Services.AddDbContext<NotificationsContext>(o => o.UseNpgsql(dbUrl));

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("notification-consumer"))
    .WithTracing(t => t
        .AddSource(NotificationWorker.SourceName)
        .AddOtlpExporter());

builder.Services.AddHostedService<NotificationWorker>();

await builder.Build().RunAsync();
