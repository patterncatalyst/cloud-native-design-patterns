package domain

import (
	"context"
	"crypto/rand"
	"fmt"
)

type PlaceOrder struct {
	repo OrderRepository
	pub  EventPublisher
}

func NewPlaceOrder(repo OrderRepository, pub EventPublisher) *PlaceOrder {
	return &PlaceOrder{repo: repo, pub: pub}
}

func (s *PlaceOrder) Execute(ctx context.Context, cmd PlaceOrderCmd) (*Order, error) {
	if cmd.SKU == "" || cmd.Quantity <= 0 {
		return nil, fmt.Errorf("invalid order: sku and quantity > 0 required")
	}

	order := &Order{
		ID:       newUUID(),
		SKU:      cmd.SKU,
		Quantity: cmd.Quantity,
		Status:   "placed",
	}

	if err := s.repo.Save(ctx, order); err != nil {
		return nil, err
	}

	s.pub.Publish(OrderPlaced{OrderID: order.ID, SKU: order.SKU, Quantity: order.Quantity})
	return order, nil
}

func newUUID() string {
	b := make([]byte, 16)
	rand.Read(b)
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}
