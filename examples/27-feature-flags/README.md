# Example 27 — Feature Flags & Progressive Delivery

Demonstrates **OpenFeature + flagd** for runtime feature flagging: release
flags with percentage rollout and sticky assignment, kill switches for
operational control, and fail-safe behaviour when the flag system is
unavailable.

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) with
  [podman-compose](https://github.com/containers/podman-compose) or the
  Docker Compose plugin
- `curl` and `jq` for driving the API
- ~512 MB free memory (flagd + 1 app service)

See the [shared infrastructure README](../_infra/README.md) for ports,
credentials, and the container naming convention.

## What it shows

| Pattern | Flag | Behaviour |
|---------|------|-----------|
| Release flag | `new-checkout` | Default off; enterprise always on; 25% fractional rollout for others |
| Kill switch | `recommendations-enabled` | Default on (fail open); disable feature instantly without deploy |
| Simple toggle | `dark-mode` | Default off; demonstrates basic boolean evaluation |
| Sticky assignment | `new-checkout` | Same user always resolves same variant (hash bucketing) |
| Fail-safe | all flags | flagd outage returns coded defaults; service keeps serving 200s |

## Architecture

```
 Client → flag-service (FastAPI + OpenFeature SDK)
              │
              └──→ flagd (gRPC :8013)
                      │
                      └── flags/flags.json (flag definitions)
```

## Flag configuration

Edit `flags/flags.json` to change flag rules at runtime — flagd watches
the file and syncs within seconds. No redeploy needed.

## Run it

```bash
podman compose up --build -d
```

## Drive it

```bash
# Free user → legacy checkout (default off)
curl -s -X POST -H 'X-User: user-1' -H 'X-Plan: free' \
  localhost:8080/checkout | jq .

# Enterprise user → new checkout (always on)
curl -s -X POST -H 'X-User: user-1' -H 'X-Plan: enterprise' \
  localhost:8080/checkout | jq .

# Kill switch: edit flags/flags.json, change recommendations-enabled
# state to "DISABLED", wait a few seconds, then:
curl -s -H 'X-User: user-1' localhost:8080/recommendations | jq .

# All flags at once
curl -s -H 'X-User: user-1' -H 'X-Plan: enterprise' \
  localhost:8080/flags | jq .
```

## Verify

```bash
./verify.sh
```

## Ports

| Service | Port |
|---------|------|
| flag-service | 8080 |
| flagd (gRPC) | 8013 |
