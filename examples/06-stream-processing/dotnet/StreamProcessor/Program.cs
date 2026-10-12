using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("stream-processor"))
    .WithTracing(t => t.AddOtlpExporter(o => o.Endpoint = new Uri(
        builder.Configuration.GetValue("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318"))));

builder.Services.AddHostedService<RevenueStream>();

await builder.Build().RunAsync();
