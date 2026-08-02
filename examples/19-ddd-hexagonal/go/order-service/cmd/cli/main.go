package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"strconv"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/patterncatalyst/cloud-native-design-patterns/examples/19-ddd-hexagonal/go/order-service/adapters"
	"github.com/patterncatalyst/cloud-native-design-patterns/examples/19-ddd-hexagonal/go/order-service/domain"
)

func main() {
	if len(os.Args) < 3 {
		fmt.Fprintf(os.Stderr, "Usage: cli-place-order <sku> <quantity>\n")
		os.Exit(1)
	}

	sku := os.Args[1]
	qty, err := strconv.Atoi(os.Args[2])
	if err != nil {
		fmt.Fprintf(os.Stderr, "invalid quantity: %s\n", os.Args[2])
		os.Exit(1)
	}

	ctx := context.Background()
	pool, err := pgxpool.New(ctx, os.Getenv("DATABASE_URL"))
	if err != nil {
		slog.Error("db connect failed", "err", err)
		os.Exit(1)
	}
	defer pool.Close()

	repo := adapters.NewPostgresRepo(pool)
	pub := &adapters.LogPublisher{}
	placeOrder := domain.NewPlaceOrder(repo, pub)

	order, err := placeOrder.Execute(ctx, domain.PlaceOrderCmd{SKU: sku, Quantity: qty})
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("CLI_ORDER_CREATED id=%s sku=%s qty=%d\n", order.ID, order.SKU, order.Quantity)
}
