package main

import (
	"context"
	"log/slog"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	pb "github.com/patterncatalyst/cloud-native-design-patterns/examples/03-composition/go/inventory-service/pb"
	"google.golang.org/grpc"
)

type server struct {
	pb.UnimplementedInventoryServer
	stock map[string]int32
}

func (s *server) GetStock(_ context.Context, req *pb.GetStockRequest) (*pb.GetStockReply, error) {
	avail := s.stock[req.Sku]
	return &pb.GetStockReply{Sku: req.Sku, Available: avail}, nil
}

func (s *server) GetStockBatch(_ context.Context, req *pb.GetStockBatchRequest) (*pb.GetStockBatchReply, error) {
	items := make([]*pb.GetStockReply, 0, len(req.Skus))
	for _, sku := range req.Skus {
		items = append(items, &pb.GetStockReply{Sku: sku, Available: s.stock[sku]})
	}
	return &pb.GetStockBatchReply{Items: items}, nil
}

func main() {
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		slog.Error("listen failed", "err", err)
		os.Exit(1)
	}

	s := grpc.NewServer()
	pb.RegisterInventoryServer(s, &server{
		stock: map[string]int32{
			"widget-a": 42,
			"widget-b": 18,
			"gadget-x": 7,
			"gadget-y": 55,
		},
	})

	slog.Info("starting inventory gRPC server on :50051")
	sigCtx, stopSignals := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stopSignals()
	serveErr := make(chan error, 1)
	go func() { serveErr <- s.Serve(lis) }()
	select {
	case err := <-serveErr:
		slog.Error("serve failed", "err", err)
	case <-sigCtx.Done():
		slog.Info("shutting down")
		done := make(chan struct{})
		go func() {
			s.GracefulStop()
			close(done)
		}()
		select {
		case <-done:
		case <-time.After(10 * time.Second):
			s.Stop()
		}
	}
}
