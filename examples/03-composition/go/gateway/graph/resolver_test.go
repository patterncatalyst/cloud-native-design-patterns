package graph

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"

	"github.com/99designs/gqlgen/graphql/handler"
	"github.com/99designs/gqlgen/graphql/handler/transport"
	pb "github.com/patterncatalyst/cloud-native-design-patterns/examples/03-composition/go/gateway/pb"
	"google.golang.org/grpc"
)

type fakeInventory struct{ batchCalls atomic.Int32 }

func (f *fakeInventory) GetStock(context.Context, *pb.GetStockRequest, ...grpc.CallOption) (*pb.GetStockReply, error) {
	return nil, nil
}

func (f *fakeInventory) GetStockBatch(_ context.Context, in *pb.GetStockBatchRequest, _ ...grpc.CallOption) (*pb.GetStockBatchReply, error) {
	f.batchCalls.Add(1)
	reply := &pb.GetStockBatchReply{}
	for _, sku := range in.Skus {
		reply.Items = append(reply.Items, &pb.GetStockReply{Sku: sku, Available: 42})
	}
	return reply, nil
}

func run(t *testing.T, query string) (string, *fakeInventory) {
	t.Helper()
	api := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/orders":
			w.Write([]byte(`[{"id":"ord-001","sku":"widget-a","quantity":2,"status":"NEW"},{"id":"ord-002","sku":"widget-a","quantity":1,"status":"NEW"},{"id":"ord-003","sku":"widget-b","quantity":1,"status":"NEW"}]`))
		case "/orders/ord-001":
			w.Write([]byte(`{"id":"ord-001","sku":"widget-a","quantity":2,"status":"NEW"}`))
		default:
			http.NotFound(w, r)
		}
	}))
	t.Cleanup(api.Close)
	inv := &fakeInventory{}
	h := handler.New(NewExecutableSchema(Config{Resolvers: &Resolver{OrderAPIURL: api.URL, Inventory: inv, HTTP: api.Client()}}))
	h.AddTransport(transport.POST{})
	body, _ := json.Marshal(map[string]string{"query": query})
	req := httptest.NewRequest(http.MethodPost, "/graphql", strings.NewReader(string(body)))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec.Body.String(), inv
}

func TestOrdersWithoutStockSkipsInventory(t *testing.T) {
	out, inv := run(t, `{ orders { id sku status } }`)
	if !strings.Contains(out, `"sku":"widget-a"`) || strings.Contains(out, `"stock"`) || inv.batchCalls.Load() != 0 {
		t.Fatalf("unexpected: %s calls=%d", out, inv.batchCalls.Load())
	}
}

func TestOrdersWithStockBatchesOneCall(t *testing.T) {
	out, inv := run(t, `{ orders { sku stock } }`)
	if !strings.Contains(out, `"stock":42`) || inv.batchCalls.Load() != 1 {
		t.Fatalf("unexpected: %s calls=%d", out, inv.batchCalls.Load())
	}
}

func TestLimitAndSingleOrder(t *testing.T) {
	out, _ := run(t, `{ orders(limit: 1) { id } }`)
	if strings.Count(out, `"id"`) != 1 {
		t.Fatalf("limit not applied: %s", out)
	}
	out, _ = run(t, `{ order(id: "ord-001") { id sku quantity } }`)
	if !strings.Contains(out, `"ord-001"`) {
		t.Fatalf("unexpected: %s", out)
	}
	out, _ = run(t, `{ order(id: "nope") { id } }`)
	if !strings.Contains(out, `"order":null`) {
		t.Fatalf("unexpected: %s", out)
	}
}
