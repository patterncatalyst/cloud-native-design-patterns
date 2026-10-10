package graph

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"slices"
	"time"

	"github.com/99designs/gqlgen/graphql"
	"github.com/patterncatalyst/cloud-native-design-patterns/examples/03-composition/go/gateway/graph/model"

	pb "github.com/patterncatalyst/cloud-native-design-patterns/examples/03-composition/go/gateway/pb"
)

// Resolver holds the two backends the gateway composes: the order REST API and the
// inventory gRPC service. It is created once and shared by every request.
type Resolver struct {
	OrderAPIURL string
	Inventory   pb.InventoryClient
	HTTP        *http.Client
}

// getJSON fetches url and decodes the body into out. A non-200 status is an error.
func (r *Resolver) getJSON(ctx context.Context, url string, out any) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return err
	}
	resp, err := r.HTTP.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		io.Copy(io.Discard, resp.Body)
		return fmt.Errorf("order-api %s: status %d", url, resp.StatusCode)
	}
	return json.NewDecoder(resp.Body).Decode(out)
}

// stockFor makes one GetStockBatch call for every distinct SKU. This is the DataLoader
// idea without a loader library: the parent resolver sees the whole selection set, so it
// asks the inventory service once for all orders instead of once per order.
func (r *Resolver) stockFor(ctx context.Context, skus []string) (map[string]int32, error) {
	set := map[string]struct{}{}
	uniq := make([]string, 0, len(skus))
	for _, s := range skus {
		if _, ok := set[s]; !ok {
			set[s] = struct{}{}
			uniq = append(uniq, s)
		}
	}
	callCtx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	reply, err := r.Inventory.GetStockBatch(callCtx, &pb.GetStockBatchRequest{Skus: uniq})
	if err != nil {
		return nil, err
	}
	slog.Info(fmt.Sprintf("DataLoader batched %d skus in one gRPC call", len(uniq)))
	out := make(map[string]int32, len(reply.Items))
	for _, item := range reply.Items {
		out[item.Sku] = item.Available
	}
	return out, nil
}

// attachStock fills Order.stock, but only when the query selects it: a query without
// "stock" never touches the inventory service.
func (r *Resolver) attachStock(ctx context.Context, orders []*model.Order) {
	if len(orders) == 0 || !slices.Contains(graphql.CollectAllFields(ctx), "stock") {
		return
	}
	skus := make([]string, len(orders))
	for i, o := range orders {
		skus[i] = o.Sku
	}
	stock, err := r.stockFor(ctx, skus)
	if err != nil {
		slog.Warn("stock batch failed", "err", err)
		return // stock stays null
	}
	for _, o := range orders {
		s := int(stock[o.Sku])
		o.Stock = &s
	}
}
