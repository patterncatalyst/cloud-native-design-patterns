package main

import (
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"github.com/jackc/pgx/v5/pgxpool"
)

type stepDef struct {
	Name     string
	CompName string
}

var steps = []stepDef{
	{Name: "charge_payment", CompName: "refund_payment"},
	{Name: "reserve_stock", CompName: "release_stock"},
	{Name: "book_shipping", CompName: "cancel_shipping"},
}

var pool *pgxpool.Pool

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	var err error
	pool, err = pgxpool.New(ctx, os.Getenv("DATABASE_URL"))
	if err != nil {
		slog.Error("db connect failed", "err", err)
		os.Exit(1)
	}
	defer pool.Close()

	resumeRunningSagas(ctx)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /sagas", handleCreateSaga)
	mux.HandleFunc("GET /sagas/{id}", handleGetSaga)
	mux.HandleFunc("GET /sagas/{id}/log", handleGetSagaLog)

	srv := &http.Server{Addr: ":8080", Handler: mux}
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGTERM, syscall.SIGINT)
		<-sigCh
		slog.Info("shutting down saga-orchestrator")
		srv.Shutdown(context.Background())
	}()

	slog.Info("starting saga-orchestrator")
	if err := srv.ListenAndServe(); err != http.ErrServerClosed {
		slog.Error("server error", "err", err)
	}
}

func handleCreateSaga(w http.ResponseWriter, r *http.Request) {
	var input map[string]any
	json.NewDecoder(r.Body).Decode(&input)

	id := newUUID()
	ctxData, _ := json.Marshal(input)

	pool.Exec(r.Context(),
		"INSERT INTO sagas (id, status, step_index, context) VALUES ($1, 'RUNNING', 0, $2)",
		id, ctxData)

	runSaga(r.Context(), id)

	saga := getSaga(r.Context(), id)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(saga)
}

func handleGetSaga(w http.ResponseWriter, r *http.Request) {
	saga := getSaga(r.Context(), r.PathValue("id"))
	if saga == nil {
		http.Error(w, "not found", 404)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(saga)
}

func handleGetSagaLog(w http.ResponseWriter, r *http.Request) {
	rows, err := pool.Query(r.Context(),
		"SELECT step, action, result FROM saga_log WHERE saga_id=$1 ORDER BY id",
		r.PathValue("id"))
	if err != nil {
		http.Error(w, "internal error", 500)
		return
	}
	defer rows.Close()

	logs := make([]map[string]any, 0)
	for rows.Next() {
		var step, action string
		var result json.RawMessage
		rows.Scan(&step, &action, &result)
		entry := map[string]any{"step": step, "action": action}
		if result != nil {
			entry["result"] = json.RawMessage(result)
		}
		logs = append(logs, entry)
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(logs)
}

func getSaga(ctx context.Context, id string) map[string]any {
	var status string
	var stepIndex int
	var ctxData json.RawMessage
	err := pool.QueryRow(ctx,
		"SELECT status, step_index, context FROM sagas WHERE id=$1", id).
		Scan(&status, &stepIndex, &ctxData)
	if err != nil {
		return nil
	}
	var sagaCtx map[string]any
	json.Unmarshal(ctxData, &sagaCtx)
	return map[string]any{
		"id": id, "status": status, "step_index": stepIndex, "context": sagaCtx,
	}
}

func runSaga(ctx context.Context, sagaID string) {
	for {
		tx, err := pool.Begin(ctx)
		if err != nil {
			return
		}

		var status string
		var stepIndex int
		var ctxData json.RawMessage
		err = tx.QueryRow(ctx,
			"SELECT status, step_index, context FROM sagas WHERE id=$1 FOR UPDATE",
			sagaID).Scan(&status, &stepIndex, &ctxData)
		if err != nil {
			tx.Rollback(ctx)
			return
		}

		if status != "RUNNING" {
			tx.Rollback(ctx)
			return
		}

		if stepIndex >= len(steps) {
			tx.Exec(ctx,
				"UPDATE sagas SET status='COMPLETED', updated_at=NOW() WHERE id=$1", sagaID)
			tx.Commit(ctx)
			slog.Info("saga completed", "id", sagaID)
			return
		}

		var sagaCtx map[string]any
		json.Unmarshal(ctxData, &sagaCtx)

		step := steps[stepIndex]
		result, execErr := executeStep(step.Name, sagaCtx)

		if execErr != nil {
			failResult, _ := json.Marshal(map[string]any{
				"error": execErr.Error(), "failed": true,
			})
			tx.Exec(ctx,
				"INSERT INTO saga_log (saga_id, step, action, result) VALUES ($1, $2, 'execute', $3)",
				sagaID, step.Name, failResult)
			tx.Exec(ctx,
				"UPDATE sagas SET status='COMPENSATING', updated_at=NOW() WHERE id=$1", sagaID)
			tx.Commit(ctx)
			slog.Info("saga step failed, compensating", "id", sagaID, "step", step.Name)
			compensateSaga(ctx, sagaID, stepIndex)
			return
		}

		sagaCtx[step.Name] = result
		newCtxData, _ := json.Marshal(sagaCtx)
		resultData, _ := json.Marshal(result)

		tx.Exec(ctx,
			"INSERT INTO saga_log (saga_id, step, action, result) VALUES ($1, $2, 'execute', $3)",
			sagaID, step.Name, resultData)
		tx.Exec(ctx,
			"UPDATE sagas SET step_index=$1, context=$2, updated_at=NOW() WHERE id=$3",
			stepIndex+1, newCtxData, sagaID)
		tx.Commit(ctx)
	}
}

func compensateSaga(ctx context.Context, sagaID string, failedAt int) {
	var ctxData json.RawMessage
	pool.QueryRow(ctx,
		"SELECT context FROM sagas WHERE id=$1", sagaID).Scan(&ctxData)
	var sagaCtx map[string]any
	json.Unmarshal(ctxData, &sagaCtx)

	for i := failedAt - 1; i >= 0; i-- {
		step := steps[i]
		result := compensateStep(step.CompName, sagaCtx)
		resultData, _ := json.Marshal(result)
		pool.Exec(ctx,
			"INSERT INTO saga_log (saga_id, step, action, result) VALUES ($1, $2, 'compensate', $3)",
			sagaID, step.CompName, resultData)
		slog.Info("compensated", "id", sagaID, "step", step.CompName)
	}

	pool.Exec(ctx,
		"UPDATE sagas SET status='COMPENSATED', updated_at=NOW() WHERE id=$1", sagaID)
	slog.Info("saga compensated", "id", sagaID)
}

func executeStep(name string, ctx map[string]any) (map[string]any, error) {
	switch name {
	case "charge_payment":
		total, _ := ctx["total"].(float64)
		return map[string]any{"payment_id": newUUID(), "amount": total}, nil
	case "reserve_stock":
		sku, _ := ctx["sku"].(string)
		return map[string]any{"reservation_id": newUUID(), "sku": sku}, nil
	case "book_shipping":
		if fail, ok := ctx["fail_shipping"].(bool); ok && fail {
			return nil, fmt.Errorf("shipping unavailable")
		}
		orderID, _ := ctx["order_id"].(string)
		return map[string]any{"shipment_id": newUUID(), "order_id": orderID}, nil
	}
	return nil, fmt.Errorf("unknown step: %s", name)
}

func compensateStep(name string, ctx map[string]any) map[string]any {
	switch name {
	case "refund_payment":
		if charge, ok := ctx["charge_payment"].(map[string]any); ok {
			return map[string]any{"refunded_payment": charge["payment_id"]}
		}
	case "release_stock":
		if reserve, ok := ctx["reserve_stock"].(map[string]any); ok {
			return map[string]any{"released_reservation": reserve["reservation_id"]}
		}
	case "cancel_shipping":
		if ship, ok := ctx["book_shipping"].(map[string]any); ok {
			return map[string]any{"cancelled_shipment": ship["shipment_id"]}
		}
	}
	return map[string]any{}
}

func resumeRunningSagas(ctx context.Context) {
	rows, err := pool.Query(ctx, "SELECT id FROM sagas WHERE status='RUNNING'")
	if err != nil {
		return
	}
	defer rows.Close()

	var ids []string
	for rows.Next() {
		var id string
		rows.Scan(&id)
		ids = append(ids, id)
	}

	for _, id := range ids {
		slog.Info("resuming saga", "id", id)
		go runSaga(ctx, id)
	}
}

func newUUID() string {
	b := make([]byte, 16)
	rand.Read(b)
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}
