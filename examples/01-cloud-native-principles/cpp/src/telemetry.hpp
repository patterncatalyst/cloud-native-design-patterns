// telemetry.hpp — OpenTelemetry C++ tracing for the Drogon service.
//
// Traces go over OTLP/HTTP to the endpoint in OTEL_EXPORTER_OTLP_ENDPOINT
// (http://lgtm:4318 in compose; the exporter appends /v1/traces). The resource
// (service.name, service.version, deployment.environment) comes from
// OTEL_SERVICE_NAME and OTEL_RESOURCE_ATTRIBUTES. Each request gets a server
// span that continues an incoming W3C traceparent; handlers log the trace_id
// so a log line can be joined to its trace in Grafana.

#pragma once

#include <memory>
#include <string>
#include <utility>

#include <drogon/HttpRequest.h>
#include <drogon/HttpResponse.h>

#include "opentelemetry/context/propagation/global_propagator.h"
#include "opentelemetry/context/propagation/text_map_propagator.h"
#include "opentelemetry/exporters/otlp/otlp_http_exporter_factory.h"
#include "opentelemetry/exporters/otlp/otlp_http_exporter_options.h"
#include "opentelemetry/sdk/resource/resource.h"
#include "opentelemetry/sdk/resource/resource_detector.h"
#include "opentelemetry/sdk/trace/batch_span_processor_factory.h"
#include "opentelemetry/sdk/trace/batch_span_processor_options.h"
#include "opentelemetry/sdk/trace/tracer_provider.h"
#include "opentelemetry/sdk/trace/tracer_provider_factory.h"
#include "opentelemetry/trace/propagation/http_trace_context.h"
#include "opentelemetry/trace/provider.h"
#include "opentelemetry/trace/span.h"

namespace cndp::telemetry {

namespace otel = opentelemetry;

// Reads the incoming headers for the propagator; Drogon lower-cases header names.
class RequestCarrier : public otel::context::propagation::TextMapCarrier {
public:
    explicit RequestCarrier(const drogon::HttpRequestPtr& req) : req_(req) {}
    otel::nostd::string_view Get(otel::nostd::string_view key) const noexcept override {
        const std::string& v = req_->getHeader(std::string(key));
        return {v.data(), v.size()};
    }
    void Set(otel::nostd::string_view, otel::nostd::string_view) noexcept override {}

private:
    drogon::HttpRequestPtr req_;
};

inline void init(const std::string& default_service_name) {
    otel::exporter::otlp::OtlpHttpExporterOptions opts;  // URL and headers from OTEL_EXPORTER_OTLP_*
    auto exporter = otel::exporter::otlp::OtlpHttpExporterFactory::Create(opts);
    otel::sdk::trace::BatchSpanProcessorOptions bopts;
    auto processor = otel::sdk::trace::BatchSpanProcessorFactory::Create(std::move(exporter), bopts);

    auto resource = otel::sdk::resource::Resource::Create(
        {{"service.name", default_service_name}});
    resource = resource.Merge(otel::sdk::resource::OTELResourceDetector().Detect());

    std::shared_ptr<otel::trace::TracerProvider> provider =
        otel::sdk::trace::TracerProviderFactory::Create(std::move(processor), resource);
    otel::trace::Provider::SetTracerProvider(provider);
    otel::context::propagation::GlobalTextMapPropagator::SetGlobalPropagator(
        otel::nostd::shared_ptr<otel::context::propagation::TextMapPropagator>(
            new otel::trace::propagation::HttpTraceContext()));
}

// Flushes the batch processor; call once after the event loop stops.
inline void shutdown() {
    auto provider = otel::trace::Provider::GetTracerProvider();
    if (auto* sdk = dynamic_cast<otel::sdk::trace::TracerProvider*>(provider.get())) {
        sdk->ForceFlush();
        sdk->Shutdown();
    }
    otel::trace::Provider::SetTracerProvider(
        otel::nostd::shared_ptr<otel::trace::TracerProvider>(new otel::trace::NoopTracerProvider()));
}

using SpanPtr = otel::nostd::shared_ptr<otel::trace::Span>;

inline constexpr const char* kSpanAttr = "otel.span";

// Pre-routing advice: start a server span, continuing an incoming traceparent.
inline void start_server_span(const drogon::HttpRequestPtr& req) {
    auto tracer = otel::trace::Provider::GetTracerProvider()->GetTracer("order-service");
    RequestCarrier carrier(req);
    auto propagator = otel::context::propagation::GlobalTextMapPropagator::GetGlobalPropagator();
    auto current = otel::context::RuntimeContext::GetCurrent();
    auto parent_ctx = propagator->Extract(carrier, current);

    otel::trace::StartSpanOptions so;
    so.kind = otel::trace::SpanKind::kServer;
    so.parent = otel::trace::GetSpan(parent_ctx)->GetContext();
    std::string method = req->getMethodString();
    auto span = tracer->StartSpan(method + " " + req->path(),
                                  {{"http.request.method", method},
                                   {"url.path", req->path()}},
                                  so);
    req->attributes()->insert(kSpanAttr, SpanPtr(span));
}

// Pre-sending advice: record the status and end the span.
inline void end_server_span(const drogon::HttpRequestPtr& req, const drogon::HttpResponsePtr& resp) {
    if (!req->attributes()->find(kSpanAttr)) return;
    auto span = req->attributes()->get<SpanPtr>(kSpanAttr);
    int status = static_cast<int>(resp->statusCode());
    span->SetAttribute("http.response.status_code", status);
    if (status >= 500) span->SetStatus(otel::trace::StatusCode::kError);
    span->End();
    req->attributes()->erase(kSpanAttr);
}

// Hex trace id of the request's span, or "" outside a request.
inline std::string trace_id(const drogon::HttpRequestPtr& req) {
    if (!req->attributes()->find(kSpanAttr)) return {};
    auto span = req->attributes()->get<SpanPtr>(kSpanAttr);
    char buf[32];
    span->GetContext().trace_id().ToLowerBase16(buf);
    return std::string(buf, 32);
}

}  // namespace cndp::telemetry
