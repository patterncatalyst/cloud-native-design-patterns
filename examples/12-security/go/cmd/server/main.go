package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"strconv"
	"sync"
	"sync/atomic"
	"time"
)

var (
	valetSecret  string
	orders       sync.Map
	orderCounter atomic.Int64
	bulkheads    sync.Map // tenant -> *bulkhead
)

const bulkheadCapacity = 5

type bulkhead struct {
	sem chan struct{}
}

func getTenantBulkhead(tenant string) *bulkhead {
	v, _ := bulkheads.LoadOrStore(tenant, &bulkhead{sem: make(chan struct{}, bulkheadCapacity)})
	return v.(*bulkhead)
}

type orderData struct {
	ID       string `json:"id"`
	SKU      string `json:"sku"`
	Quantity int    `json:"quantity"`
	Tenant   string `json:"tenant"`
	Identity string `json:"identity"`
	Subject  string `json:"subject"`
}

type orderIn struct {
	SKU      string `json:"sku"`
	Quantity int    `json:"quantity"`
	Tenant   string `json:"tenant"`
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

var openPaths = map[string]bool{"/healthz": true}

func sidecarTrust(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if openPaths[r.URL.Path] {
			next.ServeHTTP(w, r)
			return
		}
		spiffe := r.Header.Get("X-Forwarded-Client-Cert")
		if spiffe == "" {
			writeJSON(w, http.StatusForbidden, map[string]string{"detail": "no validated identity"})
			return
		}
		r.Header.Set("X-Identity", spiffe)
		sub := r.Header.Get("X-Jwt-Claim-Sub")
		if sub == "" {
			sub = "anonymous"
		}
		r.Header.Set("X-Subject", sub)
		next.ServeHTTP(w, r)
	})
}

func mintValet(resource, operation string) map[string]any {
	expires := time.Now().Unix() + 300
	payload := fmt.Sprintf("%s:%s:%d", resource, operation, expires)
	mac := hmac.New(sha256.New, []byte(valetSecret))
	mac.Write([]byte(payload))
	token := hex.EncodeToString(mac.Sum(nil))
	return map[string]any{
		"resource":  resource,
		"operation": operation,
		"expires":   expires,
		"token":     token,
	}
}

func verifyValet(resource, operation string, expires int64, token string) bool {
	if time.Now().Unix() > expires {
		return false
	}
	payload := fmt.Sprintf("%s:%s:%d", resource, operation, expires)
	mac := hmac.New(sha256.New, []byte(valetSecret))
	mac.Write([]byte(payload))
	expected := hex.EncodeToString(mac.Sum(nil))
	return hmac.Equal([]byte(token), []byte(expected))
}

func main() {
	valetSecret = os.Getenv("VALET_SECRET")
	if valetSecret == "" {
		valetSecret = "demo-secret-do-not-use-in-prod"
	}

	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})

	mux.HandleFunc("POST /orders", func(w http.ResponseWriter, r *http.Request) {
		var in orderIn
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil || in.SKU == "" || in.Quantity <= 0 || in.Tenant == "" {
			writeJSON(w, http.StatusBadRequest, map[string]string{"detail": "invalid input"})
			return
		}

		bh := getTenantBulkhead(in.Tenant)
		bh.sem <- struct{}{}
		defer func() { <-bh.sem }()

		time.Sleep(10 * time.Millisecond)

		id := strconv.FormatInt(orderCounter.Add(1), 10)
		o := orderData{
			ID:       id,
			SKU:      in.SKU,
			Quantity: in.Quantity,
			Tenant:   in.Tenant,
			Identity: r.Header.Get("X-Identity"),
			Subject:  r.Header.Get("X-Subject"),
		}
		orders.Store(id, o)
		writeJSON(w, http.StatusCreated, o)
	})

	mux.HandleFunc("GET /orders/{order_id}", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("order_id")
		v, ok := orders.Load(id)
		if !ok {
			writeJSON(w, http.StatusNotFound, map[string]string{"detail": "not found"})
			return
		}
		writeJSON(w, http.StatusOK, v)
	})

	mux.HandleFunc("POST /valet-key", func(w http.ResponseWriter, r *http.Request) {
		resource := r.URL.Query().Get("resource")
		operation := r.URL.Query().Get("operation")
		if operation == "" {
			operation = "GET"
		}
		writeJSON(w, http.StatusOK, mintValet(resource, operation))
	})

	mux.HandleFunc("GET /verify-valet", func(w http.ResponseWriter, r *http.Request) {
		resource := r.URL.Query().Get("resource")
		operation := r.URL.Query().Get("operation")
		expiresStr := r.URL.Query().Get("expires")
		token := r.URL.Query().Get("token")

		expires, _ := strconv.ParseInt(expiresStr, 10, 64)

		if verifyValet(resource, operation, expires, token) {
			writeJSON(w, http.StatusOK, map[string]any{"valid": true, "resource": resource, "operation": operation})
		} else {
			writeJSON(w, http.StatusForbidden, map[string]string{"detail": "invalid or expired valet key"})
		}
	})

	mux.HandleFunc("GET /bulkhead-state", func(w http.ResponseWriter, _ *http.Request) {
		state := map[string]any{}
		bulkheads.Range(func(key, value any) bool {
			tenant := key.(string)
			bh := value.(*bulkhead)
			state[tenant] = map[string]any{
				"available": bulkheadCapacity - len(bh.sem),
				"capacity":  bulkheadCapacity,
			}
			return true
		})
		writeJSON(w, http.StatusOK, state)
	})

	slog.Info("starting order-service", "pid", os.Getpid())
	if err := http.ListenAndServe(":8080", sidecarTrust(mux)); err != nil {
		slog.Error("server error", "err", err)
		os.Exit(1)
	}
}
