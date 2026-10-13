package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"golang.org/x/sync/semaphore"
)

var (
	valetSecret  string
	orders       sync.Map
	orderCounter atomic.Int64
	bulkheads    sync.Map // tenant -> *bulkhead
)

const bulkheadCapacity = 5

// bulkhead is one tenant's pool: 5 permits; TryAcquire refuses the sixth concurrent order at once.
type bulkhead struct {
	sem      *semaphore.Weighted
	inFlight atomic.Int64 // semaphore.Weighted does not report its count
}

func getTenantBulkhead(tenant string) *bulkhead {
	v, _ := bulkheads.LoadOrStore(tenant, &bulkhead{sem: semaphore.NewWeighted(bulkheadCapacity)})
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
	// ProcessingMs simulates slow work (default 10, at most 3000), so the bulkhead can be seen filling up.
	ProcessingMs *int `json:"processing_ms"`
}

func (in orderIn) processingTime() time.Duration {
	ms := 10
	if in.ProcessingMs != nil {
		ms = min(max(*in.ProcessingMs, 0), 3000)
	}
	return time.Duration(ms) * time.Millisecond
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

// valetClaims is the body of a valet key: a signed, time-bound token scoped to one resource
// and one operation. exp is the standard JWT expiry (epoch seconds).
type valetClaims struct {
	Resource  string `json:"res"`
	Operation string `json:"op"`
	jwt.RegisteredClaims
}

func mintValet(resource, operation string) map[string]any {
	expires := time.Now().Add(5 * time.Minute)
	token, err := jwt.NewWithClaims(jwt.SigningMethodHS256, valetClaims{
		Resource:  resource,
		Operation: operation,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(expires),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			Issuer:    "order-service",
		},
	}).SignedString([]byte(valetSecret))
	if err != nil {
		slog.Error("sign valet key", "err", err)
	}
	return map[string]any{
		"resource":  resource,
		"operation": operation,
		"expires":   expires.Unix(),
		"token":     token,
	}
}

// verifyValet accepts only an HS256 token that is unexpired and was minted for exactly this
// resource, operation and expiry.
func verifyValet(resource, operation string, expires int64, token string) bool {
	var claims valetClaims
	parsed, err := jwt.ParseWithClaims(token, &claims,
		func(*jwt.Token) (any, error) { return []byte(valetSecret), nil },
		jwt.WithValidMethods([]string{jwt.SigningMethodHS256.Alg()}),
		jwt.WithExpirationRequired(),
		jwt.WithIssuer("order-service"),
	)
	if err != nil || !parsed.Valid {
		return false
	}
	return claims.Resource == resource && claims.Operation == operation &&
		claims.ExpiresAt != nil && claims.ExpiresAt.Unix() == expires
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
		if !bh.sem.TryAcquire(1) { // the tenant's 5 permits are taken
			writeJSON(w, http.StatusTooManyRequests, map[string]string{"detail": "tenant bulkhead full"})
			return
		}
		bh.inFlight.Add(1)
		defer func() {
			bh.inFlight.Add(-1)
			bh.sem.Release(1)
		}()

		time.Sleep(in.processingTime()) // simulated processing time

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
				"available": bulkheadCapacity - bh.inFlight.Load(),
				"capacity":  bulkheadCapacity,
			}
			return true
		})
		writeJSON(w, http.StatusOK, state)
	})

	slog.Info("starting order-service", "pid", os.Getpid())
	httpSrv := &http.Server{Addr: ":8080", Handler: sidecarTrust(mux)}
	sigCtx, stopSignals := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stopSignals()
	go func() {
		<-sigCtx.Done()
		slog.Info("shutting down")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		httpSrv.Shutdown(shutdownCtx)
	}()
	if err := httpSrv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		slog.Error("server error", "err", err)
		os.Exit(1)
	}
}
