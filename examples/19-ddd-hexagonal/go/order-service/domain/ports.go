package domain

import "context"

type OrderRepository interface {
	Save(ctx context.Context, order *Order) error
	FindByID(ctx context.Context, id string) (*Order, error)
	FindAll(ctx context.Context) ([]*Order, error)
}

type EventPublisher interface {
	Publish(event OrderPlaced)
}
