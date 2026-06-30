# Runnable Examples Implementation Plan

Created: 2026-06-29
Status: Planning → Implementation

## Overview

Build 20 runnable examples referenced by the tutorial site, each demonstrating patterns from its corresponding chapter. Each example must run standalone, verify behavior with automated tests, and flip its chapter's verification footer from "unverified" to "verified".

## The 20 Examples

### Core Chapters (01-06)

#### 01 — Cloud-Native Principles
- **Path**: `examples/01-cloud-native-principles/`
- **Stack**: Minimal (likely just docs + simple app showing 12-factor)
- **Language**: Python (FastAPI)
- **Infra**: Podman — base app, maybe Postgres
- **Demonstrates**: 12-factor app, health endpoints, config externalization
- **Priority**: Low (theory-heavy chapter)

#### 02 — Communications
- **Path**: `examples/02-communications/`
- **Stack**: REST + gRPC + GraphQL + async/Kafka
- **Language**: Python (FastAPI + grpcio + Strawberry GraphQL + aiokafka)
- **Infra**: Podman — Postgres + Kafka + LGTM
- **Demonstrates**: Four interaction styles with one service
- **Priority**: HIGH (foundational pattern proof-of-concept)

#### 03 — Composition
- **Path**: `examples/03-composition/`
- **Stack**: GraphQL gateway fanning out to REST + gRPC backends
- **Language**: Python (Strawberry GraphQL gateway)
- **Infra**: Podman — Postgres + LGTM
- **Demonstrates**: Schema stitching, resolver fan-out
- **Priority**: Medium

#### 04 — Data
- **Path**: `examples/04-data/`
- **Stack**: Transactional outbox + CDC (Debezium)
- **Language**: Python (FastAPI + asyncpg) OR Go (pgx)
- **Infra**: Podman — Postgres + Kafka + **Debezium** + LGTM
- **Demonstrates**: Read/write separation, outbox pattern, Debezium CDC
- **Priority**: HIGH (critical data pattern)
- **New infra needed**: Debezium connector in Kafka Connect

#### 05 — Event-Driven
- **Path**: `examples/05-event-driven/`
- **Stack**: Event backbone with producers and consumers
- **Language**: Python (FastAPI + aiokafka + faust-streaming)
- **Infra**: Podman — Postgres + Kafka + LGTM
- **Demonstrates**: Event production, consumption, commit-after-side-effect, schemas
- **Priority**: HIGH (event-driven is central to the book)

#### 06 — Stream Processing
- **Path**: `examples/06-stream-processing/`
- **Stack**: Stateful stream processing + KEDA-like scaling
- **Language**: Python (faust-streaming) OR Java (Kafka Streams)
- **Infra**: Podman — Kafka + LGTM (KEDA scaling is K8s-native, demonstrate lag-based concept)
- **Demonstrates**: Windowed aggregation, changelog-backed state, consumer lag monitoring
- **Priority**: Medium

### API Management & Observability (09, 11, 12)

#### 09 — API Registry
- **Path**: `examples/09-api-registry/`
- **Stack**: Apicurio schema registry + multi-protocol schemas
- **Language**: Python (for producers/consumers)
- **Infra**: **Minikube** — Kafka + Apicurio + LGTM
- **Demonstrates**: OpenAPI, .proto, AsyncAPI, schema compatibility rules
- **Priority**: Medium
- **New infra needed**: Apicurio (already opt-in in minikube-stack)

#### 11 — Observability
- **Path**: `examples/11-observability/`
- **Stack**: LGTM stack showcase with instrumented services
- **Language**: Python (opentelemetry-distro auto-instrumentation)
- **Infra**: Podman — LGTM + Postgres + Kafka
- **Demonstrates**: Traces, metrics, logs, W3C context propagation, sampling
- **Priority**: HIGH (observability is foundational)

#### 12 — Security
- **Path**: `examples/12-security/`
- **Stack**: Istio sidecar + OPA + JWT validation
- **Language**: Python (FastAPI with auth middleware)
- **Infra**: **Minikube** — Istio + OPA + LGTM
- **Demonstrates**: Four security layers, sidecar pattern, policy-as-code
- **Priority**: Medium

### Deep-Dive Appendices (16-28)

#### 16 — WebSockets at Scale
- **Path**: `examples/16-websockets/`
- **Stack**: WebSocket server + Redis pub/sub backplane
- **Language**: Python (FastAPI WebSockets + redis-py)
- **Infra**: Podman — **Redis** + LGTM
- **Demonstrates**: Long-lived connections, scale-out with backplane, resume protocol
- **Priority**: Medium
- **New infra needed**: Redis

#### 17 — Saga State & Compensation
- **Path**: `examples/17-sagas/`
- **Stack**: Saga orchestrator + compensating transactions
- **Language**: Go (with state machine pattern) OR Python
- **Infra**: Podman — Postgres + Kafka + LGTM
- **Demonstrates**: Orchestrated saga, compensation flow, state persistence
- **Priority**: HIGH (saga is a key distributed pattern)

#### 18 — API Error Handling
- **Path**: `examples/18-errors/`
- **Stack**: Multi-protocol error contract (REST/gRPC/GraphQL/Kafka)
- **Language**: Python (FastAPI + grpcio + Strawberry + aiokafka)
- **Infra**: Podman — Kafka + LGTM
- **Demonstrates**: Unified error shape, retryable flags, trace propagation
- **Priority**: Medium

#### 19 — DDD & Hexagonal Architecture
- **Path**: `examples/19-ddd-hexagonal/`
- **Stack**: Hexagonal architecture with multiple adapters
- **Language**: Python (domain-first structure) OR Go
- **Infra**: Podman — Postgres + LGTM
- **Demonstrates**: Port/adapter separation, domain model, strategic DDD boundaries
- **Priority**: Low (architectural pattern, less runnable-demo-shaped)

#### 21 — Graceful Shutdown
- **Path**: `examples/21-graceful-shutdown/`
- **Stack**: Kubernetes-aware graceful shutdown protocol
- **Language**: Go (signal handling with context) OR Python
- **Infra**: Podman (simulating K8s SIGTERM) — Kafka + LGTM
- **Demonstrates**: Readiness fail-first, drain protocol, idempotency on hard kill
- **Priority**: Medium

#### 22 — L7 Routing & Traffic Management
- **Path**: `examples/22-l7-routing/`
- **Stack**: Istio four-layer routing (edge/gateway/mesh/in-app)
- **Language**: Python (FastAPI with rule engine)
- **Infra**: **Minikube** — Istio + LGTM
- **Demonstrates**: VirtualService, DestinationRule, header-based routing, canary
- **Priority**: Medium

#### 24 — Monolith to Microservices
- **Path**: `examples/24-monolith-to-microservices/`
- **Stack**: Strangler fig pattern, modular monolith decomposition
- **Language**: Python (FastAPI monolith + extracted services)
- **Infra**: **Minikube** — Istio + Postgres + LGTM
- **Demonstrates**: Content-based routing, strangler facade, decorating collaborator
- **Priority**: Medium

#### 25 — Caching Patterns
- **Path**: `examples/25-caching/`
- **Stack**: All six caching patterns with Redis
- **Language**: Python (FastAPI + redis-py + asyncpg)
- **Infra**: Podman — Postgres + **Redis** + LGTM
- **Demonstrates**: Cache-aside, read-through, write-through, write-around, write-back, refresh-ahead
- **Priority**: HIGH (caching is fundamental, Redis needed)
- **New infra needed**: Redis

#### 26 — Failure Modes
- **Path**: `examples/26-failure-modes/`
- **Stack**: Defensive toolkit (timeouts, retries, circuit breakers, bulkheads)
- **Language**: Go (with sony/gobreaker) OR Python
- **Infra**: Podman or Minikube — LGTM (chaos injection optional)
- **Demonstrates**: Timeout patterns, jittered backoff, circuit breaker states, bulkhead isolation
- **Priority**: HIGH (resilience patterns)

#### 27 — Feature Flags & Progressive Delivery
- **Path**: `examples/27-feature-flags/`
- **Stack**: OpenFeature + flagd
- **Language**: Go (OpenFeature Go SDK) OR Python
- **Infra**: Podman — flagd + LGTM
- **Demonstrates**: Four flag types, targeting, percentage rollouts, kill switches
- **Priority**: Medium
- **New infra needed**: flagd daemon

#### 28 — API Testing with Newman
- **Path**: `examples/28-newman/`
- **Stack**: Newman runner for Postman collections
- **Language**: N/A (JSON collections)
- **Infra**: Podman — test target services + LGTM
- **Demonstrates**: Postman collection anatomy, assertions, schema validation, CI integration
- **Priority**: HIGH (testing is the validation gate)

## Infrastructure Summary

### Podman Stack (17 examples)
- **Base**: LGTM + Postgres + Kafka (covered by `lgtm-podman-stack`)
- **Additions needed**:
  - Redis (examples 16, 25)
  - Debezium (example 04)
  - flagd (example 27)

### Minikube Stack (3 examples)
- **Base**: Istio + KEDA + Strimzi + CloudNativePG + LGTM (covered by `lgtm-minikube-stack`)
- **Opt-ins**:
  - Apicurio (example 09)
  - OPA (example 12)
- **Addition needed**:
  - Redis deployment (if needed for any minikube example)

## Implementation Strategy

### Phase 1: Infrastructure Prep
1. ✅ Create feature branch (`feature/runnable-examples`)
2. ⬜ Add Redis to `lgtm-podman-stack` skill templates
3. ⬜ Add Redis to `lgtm-minikube-stack` skill templates
4. ⬜ Add Debezium compose template to `lgtm-podman-stack`
5. ⬜ Add flagd compose snippet
6. ⬜ Create `examples/_infra/` shared base

### Phase 2: Proof-of-Concept
Build **one end-to-end example first** to validate the pattern. Recommended: **Example 02 (Communications)** or **Example 05 (Event-Driven)**.

- Demonstrates multi-protocol integration
- Uses core stack (Postgres + Kafka + LGTM)
- No exotic dependencies
- Covers the "running example domain" (order/payment/inventory/notification/shipping)

Deliverables:
- `examples/NN-<slug>/compose.yaml`
- Service code (Python default)
- `README.md` (how to run, what to observe)
- `verify.sh` (automated assertions)
- Chapter footer flipped to "verified"

### Phase 3: Rollout (remaining 19)
Order by priority (HIGH → Medium → Low) and infra grouping:

**Batch 1: Core Podman examples (HIGH priority)**
- 02 (Communications) — PoC
- 04 (Data/CDC + Debezium)
- 05 (Event-Driven)
- 11 (Observability)
- 17 (Sagas)
- 25 (Caching + Redis)
- 26 (Failure Modes)
- 28 (Newman)

**Batch 2: Minikube examples**
- 09 (API Registry + Apicurio)
- 12 (Security + Istio + OPA)
- 22 (L7 Routing + Istio)
- 24 (Monolith migration)

**Batch 3: Remaining Podman examples**
- 03 (Composition)
- 06 (Stream Processing)
- 16 (WebSockets + Redis)
- 18 (Error Handling)
- 21 (Graceful Shutdown)
- 27 (Feature Flags + flagd)

**Batch 4: Low-priority / docs-heavy**
- 01 (Cloud-Native Principles)
- 19 (DDD/Hexagonal)

## Language Defaults

Per CLAUDE.md locked stacks, default to **Python** for most examples unless:
- The pattern emphasizes concurrency/performance → **Go**
- The pattern is JVM-specific (Kafka Streams native) → **Java/Quarkus**
- The chapter explicitly calls out a language (e.g., C++ for performance-critical stream processing)

**Locked stacks** (do not substitute):
- Go 1.26: stdlib `net/http`, franz-go, pgx v5, go-redis v9, gqlgen, OTel Go
- Python: FastAPI, aiokafka, faust-streaming, grpcio, asyncpg, redis-py, OTel distro
- Java: Spring Boot, Quarkus, Kafka Streams
- C++: Drogon, libpq (not libpqxx), sw/redis++, modern-cpp-kafka
- .NET: MassTransit, Streamiz

## Testing Convention

Every example ships with:
1. **README.md** — how to run, expected behavior, ports
2. **verify.sh** — automated test using house tools (curl, hey, ghz, newman)
3. **compose.yaml** — extends `_infra/` or self-contained

House test tools (prefer these):
- curl + Postman/Newman for API tests
- **hey** for HTTP load
- **ghz** for gRPC load
- Avoid: HTTPie/xh, k6, Locust

## Verification Footer Convention

Each chapter ends with:
```markdown
*Verification status: unverified — [reason]*
```

After the example runs green, flip to:
```markdown
*Verification status: **verified** — `examples/NN-<slug>/` runs green as of [date]*
```

## GitHub Tracking

- **Project**: "Runnable Examples"
- **Issues**: One per example (20 issues) + infrastructure prep issues
- **Labels**: `podman-stack`, `minikube-stack`, `high-priority`, `redis`, `debezium`, `apicurio`, etc.
- **Milestones**:
  - M1: Infrastructure Prep
  - M2: Proof-of-Concept (example 02 or 05)
  - M3: Batch 1 (core HIGH priority)
  - M4: Batch 2 (minikube)
  - M5: Batch 3 (remaining podman)
  - M6: Batch 4 (low priority)

## Success Criteria

- [ ] All 20 examples run standalone
- [ ] All `verify.sh` scripts pass
- [ ] All chapter footers flipped to "verified"
- [ ] No unguarded `{{` or validation errors in docs
- [ ] Examples use locked language stacks (no substitutions)
- [ ] Examples follow house test-tool conventions
- [ ] Each example ships both `.svg` and `.excalidraw` for any new diagrams
- [ ] Conventional Commits throughout (`feat(demo-NN): add runnable example NN`)
