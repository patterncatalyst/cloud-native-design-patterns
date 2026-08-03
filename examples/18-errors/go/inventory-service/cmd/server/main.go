package main

import (
	"context"
	"fmt"
	"log/slog"
	"net"
	"os"
	"strconv"
	"sync"

	pb "github.com/patterncatalyst/cloud-native-design-patterns/examples/18-errors/go/inventory-service/pb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type inventoryServer struct {
	pb.UnimplementedInventoryServiceServer
	mu           sync.Mutex
	stock        map[string]int
	initialStock int
}

func (s *inventoryServer) ReserveStock(_ context.Context, req *pb.ReserveRequest) (*pb.ReserveResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, ok := s.stock[req.Sku]; !ok {
		s.stock[req.Sku] = s.initialStock
	}

	if s.stock[req.Sku] < int(req.Quantity) {
		slog.Warn("insufficient stock", "sku", req.Sku, "have", s.stock[req.Sku], "need", req.Quantity)
		return nil, status.Errorf(codes.FailedPrecondition,
			"insufficient stock for %s: have %d, need %d", req.Sku, s.stock[req.Sku], req.Quantity)
	}

	s.stock[req.Sku] -= int(req.Quantity)
	slog.Info("reserved", "sku", req.Sku, "qty", req.Quantity, "remaining", s.stock[req.Sku])
	return &pb.ReserveResponse{Confirmed: true, Remaining: int32(s.stock[req.Sku])}, nil
}

func main() {
	initialStock := 10
	if v := os.Getenv("INITIAL_STOCK"); v != "" {
		initialStock, _ = strconv.Atoi(v)
	}

	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		slog.Error("listen failed", "err", err)
		os.Exit(1)
	}

	srv := grpc.NewServer()
	pb.RegisterInventoryServiceServer(srv, &inventoryServer{
		stock:        make(map[string]int),
		initialStock: initialStock,
	})

	slog.Info(fmt.Sprintf("inventory-service started on :50051 (stock=%d)", initialStock))
	if err := srv.Serve(lis); err != nil {
		slog.Error("serve failed", "err", err)
		os.Exit(1)
	}
}
