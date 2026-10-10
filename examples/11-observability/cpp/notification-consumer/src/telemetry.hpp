// telemetry.hpp — OpenTelemetry C++ traces over OTLP/HTTP.
//
// The exporters read OTEL_EXPORTER_OTLP_ENDPOINT (http://lgtm:4318 in compose; they append
// /v1/traces). The resource takes service.name from OTEL_SERVICE_NAME and
// OTEL_RESOURCE_ATTRIBUTES, with the name passed to init() as the default.

#pragma once

#include <chrono>
#include <cstdio>
#include <memory>
#include <string>
#include <utility>

#include "opentelemetry/exporters/otlp/otlp_http_exporter_factory.h"
#include "opentelemetry/exporters/otlp/otlp_http_exporter_options.h"
#include "opentelemetry/sdk/resource/resource.h"
#include "opentelemetry/sdk/resource/resource_detector.h"
#include "opentelemetry/sdk/trace/batch_span_processor_factory.h"
#include "opentelemetry/sdk/trace/batch_span_processor_options.h"
#include "opentelemetry/sdk/trace/tracer_provider.h"
#include "opentelemetry/sdk/trace/tracer_provider_factory.h"
#include "opentelemetry/trace/provider.h"
#include "opentelemetry/trace/span.h"

namespace cndp::telemetry {

namespace otel = opentelemetry;

inline void init(const std::string& default_service_name) {
    auto resource = otel::sdk::resource::Resource::Create({{"service.name", default_service_name}});
    resource = resource.Merge(otel::sdk::resource::OTELResourceDetector().Detect());

    // Traces: batch processor -> OTLP/HTTP.
    otel::exporter::otlp::OtlpHttpExporterOptions topts;
    auto texporter = otel::exporter::otlp::OtlpHttpExporterFactory::Create(topts);
    auto processor = otel::sdk::trace::BatchSpanProcessorFactory::Create(
        std::move(texporter), otel::sdk::trace::BatchSpanProcessorOptions{});
    std::shared_ptr<otel::trace::TracerProvider> tp =
        otel::sdk::trace::TracerProviderFactory::Create(std::move(processor), resource);
    otel::trace::Provider::SetTracerProvider(tp);
}

inline void shutdown() {
    if (auto* tp = dynamic_cast<otel::sdk::trace::TracerProvider*>(
            otel::trace::Provider::GetTracerProvider().get())) {
        tp->ForceFlush();
        tp->Shutdown();
    }
}

using SpanPtr = otel::nostd::shared_ptr<otel::trace::Span>;

inline otel::nostd::shared_ptr<otel::trace::Tracer> tracer(const std::string& name) {
    return otel::trace::Provider::GetTracerProvider()->GetTracer(name);
}

inline std::string trace_id_of(const SpanPtr& span) {
    char buf[32];
    span->GetContext().trace_id().ToLowerBase16(buf);
    return std::string(buf, 32);
}

// W3C traceparent header value for a span (sampled).
inline std::string traceparent_of(const SpanPtr& span) {
    char tid[32], sid[16];
    span->GetContext().trace_id().ToLowerBase16(tid);
    span->GetContext().span_id().ToLowerBase16(sid);
    return "00-" + std::string(tid, 32) + "-" + std::string(sid, 16) + "-01";
}

}  // namespace cndp::telemetry
