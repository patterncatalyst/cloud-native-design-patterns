package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"sync/atomic"
	"syscall"

	"github.com/coder/websocket"
	"github.com/redis/go-redis/v9"
)

type wsClient struct {
	conn *websocket.Conn
	seq  atomic.Int64
}

func (c *wsClient) sendMsg(ctx context.Context, data string) {
	seq := c.seq.Add(1)
	msg, _ := json.Marshal(map[string]any{"seq": seq, "data": data})
	c.conn.Write(ctx, websocket.MessageText, msg)
}

var (
	podName string
	rdb     *redis.Client
	clients sync.Map
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	podName = os.Getenv("POD_NAME")
	if podName == "" {
		podName = "ws-pod"
	}

	opt, _ := redis.ParseURL(os.Getenv("REDIS_URL"))
	rdb = redis.NewClient(opt)
	defer rdb.Close()

	go subscribeBackplane(ctx)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok", "pod": podName})
	})
	mux.HandleFunc("GET /info", handleInfo)
	mux.HandleFunc("POST /send", handleSend)
	mux.HandleFunc("/ws/{clientID}", handleWS)

	srv := &http.Server{Addr: ":8080", Handler: mux}
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGTERM, syscall.SIGINT)
		<-sigCh
		slog.Info("shutting down")
		cancel()
		srv.Shutdown(context.Background())
	}()

	slog.Info("starting ws-server", "pod", podName)
	if err := srv.ListenAndServe(); err != http.ErrServerClosed {
		slog.Error("server error", "err", err)
	}
}

func handleWS(w http.ResponseWriter, r *http.Request) {
	clientID := r.PathValue("clientID")
	conn, err := websocket.Accept(w, r, &websocket.AcceptOptions{
		InsecureSkipVerify: true,
	})
	if err != nil {
		slog.Error("ws accept failed", "err", err)
		return
	}

	c := &wsClient{conn: conn}
	clients.Store(clientID, c)
	slog.Info("client connected", "id", clientID, "pod", podName)

	defer func() {
		clients.Delete(clientID)
		conn.Close(websocket.StatusNormalClosure, "")
		slog.Info("client disconnected", "id", clientID)
	}()

	ctx := r.Context()
	for {
		_, data, err := conn.Read(ctx)
		if err != nil {
			break
		}

		var req map[string]any
		if err := json.Unmarshal(data, &req); err != nil {
			continue
		}

		if req["type"] == "ping" {
			pong, _ := json.Marshal(map[string]any{"type": "pong", "pod": podName})
			conn.Write(ctx, websocket.MessageText, pong)
		}
	}
}

func handleSend(w http.ResponseWriter, r *http.Request) {
	target := r.URL.Query().Get("target")
	message := r.URL.Query().Get("message")

	payload, _ := json.Marshal(map[string]any{
		"pod": podName, "target": target, "data": message,
	})
	rdb.Publish(r.Context(), "ws:broadcast", string(payload))

	deliverLocal(r.Context(), target, message)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "sent"})
}

func handleInfo(w http.ResponseWriter, _ *http.Request) {
	ids := make([]string, 0)
	clients.Range(func(key, _ any) bool {
		ids = append(ids, key.(string))
		return true
	})
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{"pod": podName, "clients": ids})
}

func deliverLocal(ctx context.Context, target, message string) {
	if target == "" {
		clients.Range(func(_, val any) bool {
			val.(*wsClient).sendMsg(ctx, message)
			return true
		})
	} else if val, ok := clients.Load(target); ok {
		val.(*wsClient).sendMsg(ctx, message)
	}
}

func subscribeBackplane(ctx context.Context) {
	sub := rdb.Subscribe(ctx, "ws:broadcast")
	defer sub.Close()
	ch := sub.Channel()

	for {
		select {
		case <-ctx.Done():
			return
		case msg, ok := <-ch:
			if !ok {
				return
			}
			var payload struct {
				Pod    string `json:"pod"`
				Target string `json:"target"`
				Data   string `json:"data"`
			}
			if err := json.Unmarshal([]byte(msg.Payload), &payload); err != nil {
				continue
			}
			if payload.Pod == podName {
				continue
			}
			deliverLocal(ctx, payload.Target, payload.Data)
		}
	}
}
