package adapters

import (
	"context"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/patterncatalyst/cloud-native-design-patterns/examples/19-ddd-hexagonal/go/order-service/domain"
)

type PostgresRepo struct {
	pool *pgxpool.Pool
}

func NewPostgresRepo(pool *pgxpool.Pool) *PostgresRepo {
	return &PostgresRepo{pool: pool}
}

func (r *PostgresRepo) Save(ctx context.Context, order *domain.Order) error {
	_, err := r.pool.Exec(ctx,
		"INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4)",
		order.ID, order.SKU, order.Quantity, order.Status)
	return err
}

func (r *PostgresRepo) FindByID(ctx context.Context, id string) (*domain.Order, error) {
	var o domain.Order
	err := r.pool.QueryRow(ctx,
		"SELECT id, sku, quantity, status FROM orders WHERE id=$1", id).
		Scan(&o.ID, &o.SKU, &o.Quantity, &o.Status)
	if err != nil {
		return nil, err
	}
	return &o, nil
}

func (r *PostgresRepo) FindAll(ctx context.Context) ([]*domain.Order, error) {
	rows, err := r.pool.Query(ctx,
		"SELECT id, sku, quantity, status FROM orders ORDER BY created_at")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var orders []*domain.Order
	for rows.Next() {
		var o domain.Order
		rows.Scan(&o.ID, &o.SKU, &o.Quantity, &o.Status)
		orders = append(orders, &o)
	}
	return orders, nil
}
