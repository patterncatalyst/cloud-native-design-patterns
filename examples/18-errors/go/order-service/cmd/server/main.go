package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"strconv"

	"github.com/google/uuid"
	pb "github.com/patterncatalyst/cloud-native-design-patterns/examples/18-errors/go/order-service/pb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"
)

var invClient pb.InventoryServiceClient

func randomTraceID() string {
	b := make([]byte, 16)
	rand.Read(b)
	return hex.EncodeToString(b)
}

type problemResponse struct {
	Type      string `json:"type"`
	Title     string `json:"title"`
	Status    int    `json:"status"`
	Code      string `json:"code"`
	TraceID   string `json:"traceId"`
	Retryable bool   `json:"retryable"`
	RetryAfter *int  `json:"retryAfter,omitempty"`
}

func writeProblem(w http.ResponseWriter, status int, code, message string, retryable bool, retryAfter *int) {
	w.Header().Set("Content-Type", "application/problem+json")
	if retryAfter != nil {
		w.Header().Set("Retry-After", strconv.Itoa(*retryAfter))
	}
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(problemResponse{
		Type:       "urn:error:" + code,
		Title:      message,
		Status:     status,
		Code:       code,
		TraceID:    randomTraceID(),
		Retryable:  retryable,
		RetryAfter: retryAfter,
	})
}

type orderIn struct {
	SKU      string `json:"sku"`
	Quantity int32  `json:"quantity"`
}

func main() {
	invAddr := os.Getenv("INVENTORY_ADDR")
	if invAddr == "" {
		invAddr = "inventory:50051"
	}

	conn, err := grpc.NewClient(invAddr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		slog.Error("grpc dial failed", "err", err)
		os.Exit(1)
	}
	defer conn.Close()
	invClient = pb.NewInventoryServiceClient(conn)

	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	mux.HandleFunc("POST /orders", func(w http.ResponseWriter, r *http.Request) {
		var in orderIn
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
			writeProblem(w, 422, "VALIDATION_ERROR", "invalid request body", false, nil)
			return
		}
		if in.SKU == "" || in.Quantity <= 0 {
			writeProblem(w, 422, "VALIDATION_ERROR", "sku must be non-empty and quantity must be positive", false, nil)
			return
		}

		resp, err := invClient.ReserveStock(context.Background(), &pb.ReserveRequest{
			Sku:      in.SKU,
			Quantity: in.Quantity,
		})
		if err != nil {
			st, ok := status.FromError(err)
			if ok {
				switch st.Code() {
				case codes.Unavailable:
					retryAfter := 2
					writeProblem(w, 503, "INVENTORY_UNAVAILABLE",
						"inventory service is temporarily unavailable", true, &retryAfter)
					return
				case codes.FailedPrecondition:
					writeProblem(w, 409, "STOCK_UNAVAILABLE", st.Message(), false, nil)
					return
				}
			}
			retryAfter := 5
			writeProblem(w, 502, "UPSTREAM_ERROR",
				"unexpected error from inventory service", true, &retryAfter)
			return
		}

		if !resp.Confirmed {
			writeProblem(w, 409, "STOCK_UNAVAILABLE",
				"insufficient stock for "+in.SKU, false, nil)
			return
		}

		orderID := uuid.New().String()
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]any{
			"id":              orderID,
			"sku":             in.SKU,
			"quantity":        in.Quantity,
			"status":          "confirmed",
			"remaining_stock": resp.Remaining,
		})
	})

	slog.Info("starting order-service", "pid", os.Getpid())
	if err := http.ListenAndServe(":8080", mux); err != nil {
		slog.Error("server error", "err", err)
		os.Exit(1)
	}
}
