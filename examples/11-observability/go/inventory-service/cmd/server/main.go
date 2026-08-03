package main

import (
	"context"
	"log/slog"
	"net"
	"os"
	"strconv"
	"sync"
	"time"

	pb "github.com/patterncatalyst/cloud-native-design-patterns/examples/11-observability/go/inventory-service/pb"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetrichttp"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/metric"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
	"google.golang.org/grpc"
)

var reservationCounter metric.Int64Counter

type server struct {
	pb.UnimplementedInventoryServiceServer
	mu    sync.Mutex
	stock map[string]int32
}

func (s *server) ReserveStock(ctx context.Context, req *pb.ReserveRequest) (*pb.ReserveResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	remaining, ok := s.stock[req.Sku]
	if !ok {
		remaining = s.stock["__default"]
		s.stock[req.Sku] = remaining
	}

	confirmed := req.Quantity <= remaining
	if confirmed {
		s.stock[req.Sku] = remaining - req.Quantity
		remaining = s.stock[req.Sku]
	}

	reservationCounter.Add(ctx, 1,
		metric.WithAttributes(
			attribute.String("sku", req.Sku),
			attribute.Bool("confirmed", confirmed),
		))

	slog.Info("reserve stock", "sku", req.Sku, "qty", req.Quantity, "confirmed", confirmed, "remaining", remaining)
	return &pb.ReserveResponse{Confirmed: confirmed, Remaining: remaining}, nil
}

func main() {
	ctx := context.Background()
	res := resource.NewWithAttributes(semconv.SchemaURL, semconv.ServiceName("inventory-service"))

	endpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	if endpoint == "" {
		endpoint = "http://lgtm:4318"
	}

	traceExp, _ := otlptracehttp.New(ctx, otlptracehttp.WithEndpoint(stripScheme(endpoint)), otlptracehttp.WithInsecure())
	tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(traceExp), sdktrace.WithResource(res))
	defer tp.Shutdown(ctx)
	otel.SetTracerProvider(tp)

	metricExp, _ := otlpmetrichttp.New(ctx, otlpmetrichttp.WithEndpoint(stripScheme(endpoint)), otlpmetrichttp.WithInsecure())
	mp := sdkmetric.NewMeterProvider(
		sdkmetric.WithReader(sdkmetric.NewPeriodicReader(metricExp, sdkmetric.WithInterval(5*time.Second))),
		sdkmetric.WithResource(res))
	defer mp.Shutdown(ctx)
	otel.SetMeterProvider(mp)

	meter := mp.Meter("inventory-service")
	reservationCounter, _ = meter.Int64Counter("stock_reservations_total")

	initial := int32(100)
	if v := os.Getenv("INITIAL_STOCK"); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			initial = int32(n)
		}
	}

	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		slog.Error("listen failed", "err", err)
		os.Exit(1)
	}

	s := grpc.NewServer(grpc.StatsHandler(otelgrpc.NewServerHandler()))
	pb.RegisterInventoryServiceServer(s, &server{
		stock: map[string]int32{"__default": initial},
	})

	slog.Info("starting inventory-service on :50051")
	if err := s.Serve(lis); err != nil {
		slog.Error("serve failed", "err", err)
	}
}

func stripScheme(url string) string {
	for _, p := range []string{"http://", "https://"} {
		if len(url) > len(p) && url[:len(p)] == p {
			return url[len(p):]
		}
	}
	return url
}
