---
title: "Runnable Examples"
description: "Twenty runnable examples demonstrating cloud-native patterns — each with automated verification."
marker: "▶"
label: "Examples"
permalink: /examples/
order: 1
---

Each example lives in `examples/NN-slug/` and ships with a language-agnostic
`verify.sh` that tests the running system end-to-end. Choose a language
implementation, start the stack, and run the verifier.

```bash
cd examples/01-cloud-native-principles/python
podman compose up --build -d      # start the stack
cd ..
./verify.sh                       # run the automated checks
```

See [Prerequisites & Setup]({{ '/examples/prerequisites/' | relative_url }})
for install instructions.

---

## Foundations & the system

| # | Example | Demonstrates | Python | Spring Boot | Infra |
|---|---------|-------------|:------:|:-----------:|-------|
| 01 | [Cloud-Native Principles]({{ '/docs/01-cloud-native-principles/' | relative_url }}) | 12-factor config, liveness vs readiness probes | ✓ | ✓ | Podman |
| 02 | [Communications]({{ '/docs/02-communications/' | relative_url }}) | REST, gRPC, GraphQL, and Kafka in one service | ✓ | ✓ | Podman |
| 03 | [Composition]({{ '/docs/03-composition/' | relative_url }}) | GraphQL gateway fan-out to REST + gRPC backends | ✓ | ✓ | Podman |
| 04 | [Data Patterns]({{ '/docs/04-data/' | relative_url }}) | Transactional outbox + Debezium CDC | ✓ | ✓ | Podman |
| 05 | [Event-Driven]({{ '/docs/05-event-driven/' | relative_url }}) | Kafka event fan-out, commit-after-side-effect | ✓ | ✓ | Podman |
| 06 | [Stream Processing]({{ '/docs/06-stream-processing/' | relative_url }}) | Windowed aggregation, changelog-backed state | ✓ | ✓ | Podman |

## The operational platform

| # | Example | Demonstrates | Python | Spring Boot | Infra |
|---|---------|-------------|:------:|:-----------:|-------|
| 09 | [API Registry]({{ '/docs/09-api-registry/' | relative_url }}) | Apicurio schema registry, compatibility rules | n/a | n/a | Podman |
| 11 | [Observability]({{ '/docs/11-observability/' | relative_url }}) | Traces, metrics, logs with OTel + LGTM | ✓ | ✓ | Podman |

## Security

| # | Example | Demonstrates | Python | Spring Boot | Infra |
|---|---------|-------------|:------:|:-----------:|-------|
| 12 | [Security Patterns]({{ '/docs/12-security/' | relative_url }}) | JWT validation, RBAC, OPA policy | ✓ | ✓ | Podman |

## Deep-dive appendices

| # | Example | Demonstrates | Python | Spring Boot | Infra |
|---|---------|-------------|:------:|:-----------:|-------|
| 16 | [WebSockets at Scale]({{ '/docs/16-appendix-c-websockets/' | relative_url }}) | WebSocket scale-out with Redis pub/sub backplane | ✓ | ✓ | Podman |
| 17 | [Saga State & Compensation]({{ '/docs/17-appendix-d-sagas/' | relative_url }}) | DB-backed saga orchestrator with compensation | ✓ | ✓ | Podman |
| 18 | [API Error Handling]({{ '/docs/18-appendix-e-errors/' | relative_url }}) | Unified error contract across REST and gRPC | ✓ | ✓ | Podman |
| 19 | [DDD & Hexagonal]({{ '/docs/19-appendix-f-ddd-hexagonal/' | relative_url }}) | Ports and adapters, domain isolation | ✓ | ✓ | Podman |
| 21 | [Graceful Shutdown]({{ '/docs/21-appendix-h-shutdown/' | relative_url }}) | SIGTERM handling, readiness flip, in-flight drain | ✓ | ✓ | Podman |
| 22 | [L7 Routing]({{ '/docs/22-appendix-i-l7-routing/' | relative_url }}) | Header-based routing, traffic splitting, canary | ✓ | ✓ | Podman |
| 24 | [Monolith to Microservices]({{ '/docs/24-appendix-k-monolith-to-microservices/' | relative_url }}) | Content-based routing, strangler fig, decorator | ✓ | ✓ | Podman |
| 25 | [Caching Patterns]({{ '/docs/25-appendix-l-caching/' | relative_url }}) | Cache-aside, read/write-through, TTL, pub/sub refresh | ✓ | ✓ | Podman |
| 26 | [Failure Modes]({{ '/docs/26-appendix-m-failure-modes/' | relative_url }}) | Timeout, retry, circuit breaker, bulkhead, fallback | ✓ | ✓ | Podman |
| 27 | [Feature Flags]({{ '/docs/27-appendix-n-feature-flags/' | relative_url }}) | OpenFeature + flagd, targeting rules, rollout | ✓ | ✓ | Podman |
| 28 | [Newman API Testing]({{ '/docs/28-appendix-o-newman/' | relative_url }}) | Postman collection runner, schema validation, CI | n/a | n/a | Podman |

**Legend:** ✓ = available, n/a = language-agnostic (no application code)

---

## Directory structure

```
examples/
  _infra/                    # shared composable infrastructure (Postgres, Kafka, LGTM, Redis, ...)
  NN-slug/
    verify.sh                # language-agnostic automated checks
    README.md                # how to run + what to observe
    db/init/                 # shared SQL schema (where applicable)
    python/
      compose.yaml           # starts infra + Python services
      Dockerfile / services  # FastAPI application code
    spring-boot/
      compose.yaml
      Dockerfile / services
```

Every language implementation exposes the **same HTTP API** on the same ports
with the same container names, so a single `verify.sh` validates all of them.

---

## Source code

All examples are in the
[`examples/`](https://github.com/{{ site.github_username }}/{{ site.github_repo }}/tree/main/examples)
directory of the GitHub repository.
