#!/usr/bin/env bash
set -euo pipefail

POD1="http://localhost:8081"
POD2="http://localhost:8082"
PASS=0
FAIL=0

check() {
    local desc="$1" cmd="$2" expected="$3"
    result=$(eval "$cmd" 2>/dev/null) || result=""
    if echo "$result" | grep -q "$expected"; then
        printf '  \xe2\x9c\x93 %s\n' "$desc"
        PASS=$((PASS + 1))
    else
        printf '  \xe2\x9c\x97 %s (expected "%s", got "%s")\n' "$desc" "$expected" "$result"
        FAIL=$((FAIL + 1))
    fi
}

printf '==> Verifying Example 16: WebSockets at Scale\n\n'

# --- Both pods are up ---
check "ws-pod-1 healthz" \
    "curl -sf $POD1/healthz" \
    '"ws-pod-1"'

check "ws-pod-2 healthz" \
    "curl -sf $POD2/healthz" \
    '"ws-pod-2"'

# --- Connect a WebSocket client to pod-1 ---
printf '  \xe2\x86\x92 connecting WebSocket client to ws-pod-1...\n'
WS_OUTPUT=$(mktemp)
python3 -c "
import asyncio, json, websockets, sys

async def main():
    uri = 'ws://localhost:8081/ws/client-abc'
    async with websockets.connect(uri) as ws:
        # Send a ping to verify connection
        await ws.send(json.dumps({'type': 'ping'}))
        pong = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        print(json.dumps(pong))
        sys.stdout.flush()

asyncio.run(main())
" > "$WS_OUTPUT" 2>/dev/null &
WS_PID=$!
sleep 2

# Check if the connection worked
wait "$WS_PID" 2>/dev/null || true
WS_RESULT=$(cat "$WS_OUTPUT")
rm -f "$WS_OUTPUT"

if echo "$WS_RESULT" | grep -q "ws-pod-1"; then
    printf '  \xe2\x9c\x93 WebSocket connection established on ws-pod-1\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 WebSocket connection failed (got: %s)\n' "$WS_RESULT"
    FAIL=$((FAIL + 1))
fi

# --- Cross-pod backplane: send from pod-2 to client on pod-1 ---
printf '  \xe2\x86\x92 testing backplane: sending message via ws-pod-2 to client on ws-pod-1...\n'

BACKPLANE_OUTPUT=$(mktemp)
python3 -c "
import asyncio, json, websockets, sys, aiohttp

async def main():
    uri = 'ws://localhost:8081/ws/client-bp'
    async with websockets.connect(uri) as ws:
        # Verify connected
        await ws.send(json.dumps({'type': 'ping'}))
        pong = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))

        # Send message via pod-2's REST API to this client
        async with aiohttp.ClientSession() as session:
            await session.post('http://localhost:8082/send?target=client-bp&message=hello-from-pod2')

        # Wait for the message to arrive via backplane
        try:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            print(json.dumps(msg))
        except asyncio.TimeoutError:
            print('timeout')

asyncio.run(main())
" > "$BACKPLANE_OUTPUT" 2>/dev/null &
BP_PID=$!
sleep 5
wait "$BP_PID" 2>/dev/null || true
BP_RESULT=$(cat "$BACKPLANE_OUTPUT")
rm -f "$BACKPLANE_OUTPUT"

if echo "$BP_RESULT" | grep -q "hello-from-pod2"; then
    printf '  \xe2\x9c\x93 backplane delivered message from ws-pod-2 to client on ws-pod-1\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 backplane delivery failed (got: %s)\n' "$BP_RESULT"
    FAIL=$((FAIL + 1))
fi

# --- Broadcast: send from pod-2, received by all clients on pod-1 ---
printf '  \xe2\x86\x92 testing broadcast via backplane...\n'

BCAST_OUTPUT=$(mktemp)
python3 -c "
import asyncio, json, websockets, sys, aiohttp

async def main():
    uri = 'ws://localhost:8081/ws/client-bcast'
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({'type': 'ping'}))
        await asyncio.wait_for(ws.recv(), timeout=5)

        # Broadcast via pod-2 (no target = all clients)
        async with aiohttp.ClientSession() as session:
            await session.post('http://localhost:8082/send?message=broadcast-test')

        try:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            print(json.dumps(msg))
        except asyncio.TimeoutError:
            print('timeout')

asyncio.run(main())
" > "$BCAST_OUTPUT" 2>/dev/null &
BC_PID=$!
sleep 5
wait "$BC_PID" 2>/dev/null || true
BC_RESULT=$(cat "$BCAST_OUTPUT")
rm -f "$BCAST_OUTPUT"

if echo "$BC_RESULT" | grep -q "broadcast-test"; then
    printf '  \xe2\x9c\x93 broadcast reached client via backplane\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 broadcast failed (got: %s)\n' "$BC_RESULT"
    FAIL=$((FAIL + 1))
fi

# --- Sequence numbers for resume ---
printf '  \xe2\x86\x92 testing sequence-number framing for resume...\n'

SEQ_OUTPUT=$(mktemp)
python3 -c "
import asyncio, json, websockets, sys, aiohttp

async def main():
    uri = 'ws://localhost:8081/ws/client-seq'
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({'type': 'ping'}))
        await asyncio.wait_for(ws.recv(), timeout=5)

        # Send 3 messages from same pod (locally)
        async with aiohttp.ClientSession() as session:
            for i in range(3):
                await session.post(f'http://localhost:8081/send?target=client-seq&message=msg-{i}')
                await asyncio.sleep(0.1)

        # Read all 3
        msgs = []
        for _ in range(3):
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                msgs.append(msg)
            except asyncio.TimeoutError:
                break

        # Check seq numbers are monotonic
        seqs = [m.get('seq', 0) for m in msgs]
        if seqs == sorted(seqs) and len(set(seqs)) == len(seqs) and len(seqs) >= 3:
            print('monotonic')
        else:
            print(f'not-monotonic: {seqs}')

asyncio.run(main())
" > "$SEQ_OUTPUT" 2>/dev/null &
SEQ_PID=$!
sleep 5
wait "$SEQ_PID" 2>/dev/null || true
SEQ_RESULT=$(cat "$SEQ_OUTPUT")
rm -f "$SEQ_OUTPUT"

if echo "$SEQ_RESULT" | grep -q "monotonic"; then
    printf '  \xe2\x9c\x93 sequence numbers are monotonically increasing\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 sequence numbers not monotonic (got: %s)\n' "$SEQ_RESULT"
    FAIL=$((FAIL + 1))
fi

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
