package main

import (
	"context"
	"log/slog"
	"net"
	"os"
	"strconv"
	"sync"

	pb "github.com/patterncatalyst/cloud-native-design-patterns/examples/02-communications/go/inventory-service/pb"
	"google.golang.org/grpc"
)

type server struct {
	pb.UnimplementedInventoryServer
	mu    sync.Mutex
	stock map[string]int32
}

func (s *server) ReserveStock(_ context.Context, req *pb.ReserveRequest) (*pb.ReserveReply, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	remaining, ok := s.stock[req.Sku]
	if !ok {
		remaining = s.stock["__default"]
		s.stock[req.Sku] = remaining
	}

	if req.Quantity <= remaining {
		s.stock[req.Sku] = remaining - req.Quantity
		slog.Info("stock reserved", "sku", req.Sku, "qty", req.Quantity, "remaining", s.stock[req.Sku])
		return &pb.ReserveReply{Reserved: true, Remaining: s.stock[req.Sku]}, nil
	}

	slog.Info("insufficient stock", "sku", req.Sku, "requested", req.Quantity, "available", remaining)
	return &pb.ReserveReply{Reserved: false, Remaining: remaining}, nil
}

func main() {
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

	s := grpc.NewServer()
	pb.RegisterInventoryServer(s, &server{
		stock: map[string]int32{"__default": initial},
	})

	slog.Info("starting inventory gRPC server on :50051", "initial_stock", initial)
	if err := s.Serve(lis); err != nil {
		slog.Error("serve failed", "err", err)
	}
}
