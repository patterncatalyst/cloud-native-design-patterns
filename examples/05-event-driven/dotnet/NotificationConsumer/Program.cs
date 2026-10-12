using Microsoft.EntityFrameworkCore;
using OpenTelemetry.Exporter;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = Host.CreateApplicationBuilder(args);

var dbUrl = builder.Configuration.GetValue("DATABASE_URL",
    "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass");
var otelEndpoint = builder.Configuration.GetValue("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318");

builder.Services.AddDbContext<NotificationsContext>(o => o.UseNpgsql(dbUrl));

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("notification-consumer"))
    .WithTracing(t => t
        .AddSource(NotificationWorker.SourceName)
        // 4318 is the OTLP/HTTP port: the exporter defaults to gRPC, and a code-set endpoint is used as given.
        .AddOtlpExporter(o =>
        {
            o.Endpoint = new Uri(otelEndpoint.TrimEnd('/') + "/v1/traces");
            o.Protocol = OtlpExportProtocol.HttpProtobuf;
        }));

builder.Services.AddHostedService<NotificationWorker>();

await builder.Build().RunAsync();
