package adapters

import (
	"log/slog"

	"github.com/patterncatalyst/cloud-native-design-patterns/examples/19-ddd-hexagonal/go/order-service/domain"
)

type LogPublisher struct{}

func (p *LogPublisher) Publish(event domain.OrderPlaced) {
	slog.Info("EVENT OrderPlaced", "order_id", event.OrderID, "sku", event.SKU, "quantity", event.Quantity)
}
