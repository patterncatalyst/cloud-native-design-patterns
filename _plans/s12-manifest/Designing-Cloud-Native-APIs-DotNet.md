# Designing-Cloud-Native-APIs-DotNet — S12 manifest

> Amended 2026-10-12 for user decision 7 (vendor-neutral): see the last section, which supersedes the rows here
> on the valet-key and claim-check slides, the cloud-SDK pins and Appendix S.

Deck: `lgtm-presentation/Designing-Cloud-Native-APIs-DotNet.pptx`, 303 slides at 8c86d61. Slide numbers here
are the 8c86d61 numbers; the edit files address sldIds.

## Summary

- MassTransit removed from every slide and note (user decision during S4): Kafka producers and consumers are
  Confluent.Kafka 2.16.0, stream processing is Streamiz.Kafka.Net 1.8.2, the in-app router is a Confluent.Kafka
  consumer with NRules, the decorator uses StackExchange.Redis + Confluent.Kafka. Three notes keep MassTransit
  as history on purpose (see the ledger).
- Appendix C now follows `examples/16-websockets/dotnet` (raw ASP.NET Core WebSockets and protobuf frames);
  SignalR stays the subject of Appendix Q and of the Blazor slides.
- 22 code boxes rewritten (site codetab or example excerpt), 3 fixed by token (outbox comment, Stateless
  `OnEntryAsync`, `KafkaEventPublisher`); every replacement fits the box capacity deck_edit computes and 95 columns.
- Appendix P: UBI 9 reason (no UBI 10 .NET image) and the pinned image tags; Containerfile wording.
- Speaker notes written for the 17 slides that had none (sldIds 542–558, Appendices P and Q); remove the deck
  from `KNOWN_MISSING_NOTES` in `scripts/deck_text.py` after applying.
- 63 deck-exclusive voice/positional/engine rewrites (by category {'voice': 54, 'positional': 8, 'engine': 1}); the other
  26 exclusive units sit on notes or text that an op rewrites (ledger: `rewrites/ledger-deck-DotNet.tsv`).
- Ops in `ops-30-deck` by category: {'stack': 39, 'code': 38, 'notes': 42, 'version': 5, 'voice': 1}. Dry run of the ops alone on a copy of the deck: OK
  (`deck_edit.py --dry-run`, 125 ops); applied together with the exclusive rewrites, the text keeps 0 ban-tier,
  positional or old-engine hits outside sentences owned by the voice forks, Appendix O and the agenda.

## Code map

Status counts: {'matches': 18, 'replaced': 22, 'owner: shared-code': 14, 'owner: planner (App O)': 4}

| Slide | sldId | Title | Chip (before) | Site doc · codetab | Example | Status |
|---|---|---|---|---|---|---|
| 15 | 270 | A 12-factor ASP.NET Core service, ready for the platform | `csharp · .NET 10 + ASP.NET Core + AspNetCore.HealthChecks` | _docs/01-cloud-native-principles.md · A twelve-factor service | examples/01-cloud-native-principles/dotnet | matches |
| 18 | 273 | REST at the edge with ASP.NET Core | `csharp · .NET 10 + ASP.NET Core minimal APIs` | _docs/02-communications.md · REST at the edge | examples/02-communications/dotnet | replaced (site codetab; WithOpenApi dropped, record moved after top-level statements) |
| 19 | 274 | gRPC for internal service-to-service calls | `protobuf + csharp · .NET 10 + Grpc.AspNetCore` | _docs/02-communications.md · gRPC for internal calls | examples/02-communications/dotnet | matches |
| 22 | 277 | Resilience as configuration, not per-call code | `yaml · istio` | see shared-code |  | owner: shared-code |
| 25 | 280 | A composing resolver in HotChocolate | `csharp · .NET 10 + HotChocolate` | _docs/03-composition.md · The resolver makes it concrete | examples/03-composition/dotnet | matches |
| 31 | 286 | CQRS in practice | `csharp · ASP.NET Core 10 + EF Core + MassTransit` | _docs/04-data.md (no CQRS codetab) | examples/04-data/dotnet | replaced (Confluent.Kafka projection; illustrative) |
| 34 | 289 | The outbox write — one transaction, no lost events | `csharp · EF Core + Debezium CDC` | _docs/04-data.md · The code, in your language | examples/04-data/dotnet | matches (last comment line now Wolverine, as the site) |
| 38 | 293 | Producing and consuming with MassTransit | `csharp · .NET 10 + MassTransit + Confluent.Kafka` | _docs/05-event-driven.md · Producing and consuming | examples/05-event-driven/dotnet/{OrderService,NotificationConsumer}/Program.cs | replaced |
| 45 | 300 | A windowed aggregation with Streamiz.Kafka.Net | `csharp · .NET 10 + Streamiz.Kafka.Net` | _docs/06-stream-processing.md · A windowed aggregation | examples/06-stream-processing/dotnet/StreamProcessor/Program.cs | replaced (excerpt of the example; site fix listed) |
| 47 | 302 | Scale on lag (events) and on RPS (HTTP) | `yaml · KEDA` | see shared-code |  | owner: shared-code |
| 57 | 312 | Gate breaking changes in CI | `yaml · CI + Apicurio v3 REST` | see shared-code |  | owner: shared-code |
| 66 | 321 | Auto-instrument with OpenTelemetry .NET | `csharp · .NET 10 + OpenTelemetry.NET` | _docs/11-observability.md · Auto-instrument your service | examples/11-observability/dotnet/OrderService/Program.cs | replaced (example's exporter config; site fix listed) |
| 68 | 323 | Baggage in practice — carry request context downstream | `csharp · .NET System.Diagnostics.Activity + OpenTelemetry` | _docs/11-observability.md · How correlation works | examples/05-event-driven/dotnet (header propagation) | replaced |
| 80 | 335 | S3 pre-signed URL — scoped, time-bound, op-restricted | `csharp · ASP.NET Core 10 + AWS SDK for .NET` | _docs/12-security.md · The valet key hands out direct access | examples/12-security/dotnet | matches |
| 85 | 340 | OPA Gatekeeper ConstraintTemplate (Rego) | `yaml · OPA Gatekeeper (language-neutral)` | see shared-code |  | owner: shared-code |
| 87 | 342 | Polly concurrency limiters in ASP.NET Core | `csharp · ASP.NET Core 10 + Polly v8` | _docs/12-security.md · Bulkhead: bound the blast radius | examples/12-security/dotnet | replaced (site codetab; the Polly version did not type-check) |
| 89 | 344 | Producer mints claim, consumer fetches payload | `csharp · ASP.NET Core 10 + AWS SDK for .NET + MassTransit` | _docs/12-security.md · Claim-check | examples/12-security/dotnet | replaced (site codetab) |
| 108 | 363 | Media-type versioning with ASP.NET Core | `csharp · .NET 10 + Asp.Versioning` | _docs/15-appendix-b-versioning.md (no REST media-type codetab) | none | replaced (illustrative-ok: Asp.Versioning template reader, NewVersionedApi) |
| 110 | 365 | Evolving a .proto safely | `protobuf` | see shared-code |  | owner: shared-code |
| 112 | 367 | Deprecating a field in HotChocolate | `csharp + graphql · .NET 10 + HotChocolate` | _docs/15-appendix-b-versioning.md · GraphQL evolves, it doesn't version | examples/03-composition/dotnet | replaced (site codetab) |
| 115 | 370 | A WebSocket endpoint with SignalR | `csharp · .NET 10 + SignalR` | _docs/16-appendix-c-websockets.md · A WebSocket endpoint | examples/16-websockets/dotnet/WsServer/Program.cs | replaced (raw WebSockets, as the example; was SignalR) |
| 119 | 374 | Binary framing with MessagePack — fast and versioned | `csharp · .NET 10 + SignalR + MessagePack` | _docs/16-appendix-c-websockets.md · Binary framing with protobuf + Receiving and dispatching | examples/16-websockets/dotnet | replaced (protobuf envelope; was SignalR MessagePack) |
| 126 | 381 | A persisted saga state machine (EF Core) | `csharp · .NET 10 + EF Core` | _docs/17-appendix-d-sagas.md · Where the saga keeps its state | examples/17-sagas/dotnet (Npgsql, same SELECT ... FOR UPDATE) | matches |
| 128 | 383 | Running compensations in reverse | `csharp · .NET 10 + EF Core` | _docs/17-appendix-d-sagas.md · Compensation unwinds a failed saga | examples/17-sagas/dotnet | matches |
| 132 | 387 | Temporal .NET workflow + activity, in ASP.NET Core | `csharp · Temporalio.Temporal + ASP.NET Core` | none (Temporal) | none | replaced (illustrative-ok: no Saga helper in the .NET SDK, StartToCloseTimeout on every call) |
| 134 | 389 | Stateless: configure and drive | `csharp · Stateless package + EF Core` | none (Stateless) | none | matches after token fix (OnEntry → OnEntryAsync; illustrative-ok) |
| 138 | 393 | REST errors with ASP.NET Core ProblemDetails | `csharp · .NET 10 + IExceptionHandler` | _docs/18-appendix-e-errors.md · REST | examples/18-errors/dotnet | replaced (problem+json media type passed to WriteAsJsonAsync; site fix listed) |
| 140 | 395 | gRPC errors with rich status details | `csharp · grpc-dotnet + Google.Rpc` | _docs/18-appendix-e-errors.md · gRPC | examples/18-errors/dotnet | matches |
| 142 | 397 | Kafka retry + DLQ with MassTransit | `csharp · .NET 10 + MassTransit + Confluent.Kafka` | _docs/18-appendix-e-errors.md · Kafka | none (18-errors/dotnet has no Kafka) | replaced (site codetab, condensed) |
| 144 | 399 | GraphQL field errors with HotChocolate | `csharp · .NET 10 + HotChocolate` | _docs/18-appendix-e-errors.md · GraphQL | none | matches |
| 154 | 409 | Ports & adapters in code | `csharp · ports & adapters in .NET` | _docs/19-appendix-f-ddd-hexagonal.md · Hexagonal architecture | examples/19-ddd-hexagonal/dotnet | matches after token fix (KafkaEventPublisher) |
| 172 | 427 | Graceful shutdown in ASP.NET Core | `csharp · .NET 10 + ASP.NET Core` | _docs/21-appendix-h-shutdown.md · The application side | examples/21-graceful-shutdown/dotnet | matches |
| 173 | 428 | The Kubernetes side: probes, preStop, grace period | `yaml · Kubernetes` | see shared-code |  | owner: shared-code |
| 183 | 438 | Content-based routing with HAProxy | `haproxy.cfg` | see shared-code |  | owner: shared-code |
| 184 | 439 | Content-based routing with Nginx | `nginx.conf` | see shared-code |  | owner: shared-code |
| 185 | 440 | Content-based routing in the mesh: Istio VirtualService | `yaml · Istio VirtualService` | see shared-code |  | owner: shared-code |
| 190 | 445 | Canary release: weighted Istio routing | `yaml · Istio canary` | see shared-code |  | owner: shared-code |
| 191 | 446 | Header-based steering: dark launches | `yaml · Istio header-based` | see shared-code |  | owner: shared-code |
| 193 | 448 | Header injection and URL rewrites | `yaml · Envoy / Istio` | see shared-code |  | owner: shared-code |
| 196 | 451 | A MassTransit RoutingSlip in .NET, calling NRules | `csharp · .NET 10 + MassTransit + NRules` | _docs/22-appendix-i-l7-routing.md · Routing inside the app (NRules + Confluent.Kafka) | examples/22-l7-routing/dotnet/RouterService (rule table) | replaced (site codetab, condensed) |
| 197 | 452 | An NRules rule: the decision, externalised | `csharp · NRules.Fluent (or external NRules.Language DSL)` | _docs/22-appendix-i-l7-routing.md · Routing inside the app (NRules rules) | examples/22-l7-routing/dotnet | matches |
| 202 | 457 | Istio for east/west: DestinationRule + VirtualService | `yaml · Istio east/west` | see shared-code |  | owner: shared-code |
| 220 | 475 | Content-based routing during migration | `csharp · ASP.NET Core 10 minimal API + IHttpClientFactory` | _docs/24-appendix-k-monolith-to-microservices.md · Content-based routing | examples/24-monolith-to-microservices/dotnet | matches |
| 222 | 477 | A decorating collaborator in ASP.NET Core | `csharp · ASP.NET Core 10 + IDistributedCache + MassTransit + IHttpClientFactory (no fence language in the text copy)` | _docs/24-appendix-k-monolith-to-microservices.md · The decorating collaborator | examples/24-monolith-to-microservices/dotnet | replaced (site codetab) |
| 227 | 482 | Cache-aside in ASP.NET Core with Redis | `csharp · ASP.NET Core 10 + EF Core + IDistributedCache` | _docs/25-appendix-l-caching.md · Cache-aside | examples/25-caching/dotnet | replaced (site codetab, fitted; `?? return` did not compile) |
| 229 | 484 | Read-through in ASP.NET Core with FusionCache | `csharp · ASP.NET Core 10 + FusionCache (MIT, open-source)` | _docs/25-appendix-l-caching.md · Read-through | examples/25-caching/dotnet | replaced (site codetab, fitted) |
| 233 | 488 | Write-around in ASP.NET Core | `csharp · ASP.NET Core 10 + EF Core + IDistributedCache` | _docs/25-appendix-l-caching.md · Write-around | examples/25-caching/dotnet | replaced (site codetab) |
| 251 | 506 | Timeouts + deadlines | `csharp · ASP.NET Core 10 + HttpClient` | _docs/26-appendix-m-failure-modes.md · Timeouts | examples/26-failure-modes/dotnet | matches |
| 253 | 508 | Retry with backoff + jitter | `csharp · ASP.NET Core 10 + Polly v8` | _docs/26-appendix-m-failure-modes.md · Retry | examples/26-failure-modes/dotnet | matches |
| 255 | 510 | Circuit breaker + fallback | `csharp · ASP.NET Core 10 + Polly v8` | _docs/26-appendix-m-failure-modes.md · Circuit breaker | examples/26-failure-modes/dotnet | matches |
| 259 | 514 | Graceful shutdown (see App. H) | `csharp · ASP.NET Core 10` | _docs/21-appendix-h-shutdown.md (concept) | examples/21-graceful-shutdown/dotnet/OrderService/Program.cs | replaced (excerpt of the example) |
| 267 | 522 | Evaluating a flag | `csharp · .NET` | _docs/27-appendix-n-feature-flags.md · Evaluating a flag | examples/27-feature-flags/dotnet/FlagService/Program.cs | replaced (site API as a minimal API) |
| 268 | 523 | Targeting and rollout live in config | `json · flagd` | see shared-code |  | owner: shared-code |
| 270 | 525 | A kill switch | `csharp · .NET` | _docs/27-appendix-n-feature-flags.md · The kill switch | examples/27-feature-flags/dotnet | matches |
| 278 | 533 | Tests live in the request | `json · Postman` | _docs/28-appendix-o-newman.md | examples/28-newman | owner: planner (App O) |
| 280 | 535 | Launch the service under test | `bash · .NET` | _docs/28-appendix-o-newman.md | examples/28-newman | owner: planner (App O) |
| 281 | 536 | Running Newman & shaping output | `bash` | _docs/28-appendix-o-newman.md | examples/28-newman | owner: planner (App O) |
| 283 | 538 | Newman in CI | `yaml · GitHub Actions` | _docs/28-appendix-o-newman.md | examples/28-newman | owner: planner (App O) |

## Change table (ops-30-deck, in apply order)

| Slide | sldId | Category | Change |
|---|---|---|---|
| 1 | [256] | stack | replace `MassTransit + Confluent.Kafka for events, Streamiz.Kafka.Net for strea` |
| 18 | 273 | code | set_code (site 02 codetab; WithOpenApi is obsolete in .NET 10, record moved after top-level statemen) |
| 27 | [282] | stack | replace `gRPC client, MassTransit consumer)` |
| 31 | 286 | stack | set_text csharp · ASP.NET Core 10 + EF Core + Confluent.Kafka |
| 31 | 286 | code | set_code (projection on a Confluent.Kafka consumer; no site codetab (illustrative, CQRS)) |
| 31 | 286 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 34 | [289] | code | replace `// MassTransit has a built-in transactional outbox if you prefer the f` |
| 34 | [289] | stack | replace `OR use MassTransit's built-in transactional outbox, which gives you th` |
| 38 | 293 | stack | set_text Producing and consuming with Confluent.Kafka |
| 38 | 293 | stack | set_text csharp · .NET 10 + Confluent.Kafka 2.16.0 |
| 38 | 293 | code | set_code (site 05 codetab, examples/05-event-driven/dotnet (topic order.placed, group notification-g) |
| 38 | 293 | stack | set_text Confluent.Kafka keeps the Kafka semantics visible: keys, par |
| 38 | 293 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 45 | 300 | version | set_text csharp · Streamiz.Kafka.Net 1.8.2 |
| 45 | 300 | code | set_code (excerpt of examples/06-stream-processing/dotnet/StreamProcessor/Program.cs) |
| 45 | 300 | version | set_notes (Streamiz 1.8.2; matches the example's contract) |
| 66 | 321 | code | set_code (examples/11-observability/dotnet/OrderService/Program.cs (env-configured OTLP to lgtm:4318) |
| 66 | 321 | code | set_text ASP.NET Core requests become spans with no code; ActivitySou |
| 66 | 321 | notes | set_notes (describes the example's setup) |
| 68 | 323 | stack | set_text csharp · OpenTelemetry Baggage + Confluent.Kafka |
| 68 | 323 | code | set_code (OpenTelemetry Baggage API (site 11 codetab) + header extraction as in Appendix S / example) |
| 68 | 323 | code | set_text Baggage.SetBaggage at the edge; extract from the record head |
| 68 | 323 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 87 | 342 | code | set_text Per-tenant bulkheads in ASP.NET Core |
| 87 | 342 | code | set_text csharp · ASP.NET Core 10 + SemaphoreSlim |
| 87 | 342 | code | set_code (site 12 codetab (the Polly version returned the wrong type: PostAsJsonAsync yields HttpRes) |
| 87 | 342 | notes | set_notes (matches the new code) |
| 89 | 344 | stack | set_text csharp · ASP.NET Core 10 + Confluent.Kafka |
| 89 | 344 | code | set_code (site 12 codetab (claim-check) plus the consumer commit) |
| 89 | 344 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 96 | [351] | stack | replace `Temporal .NET SDK (docs.temporal.io/dev-guide/dotnet), MassTransit, Ho` |
| 108 | 363 | code | set_code (Asp.Versioning: a media-type template reader and NewVersionedApi/MapToApiVersion (the old ) |
| 108 | 363 | notes | set_notes (matches the new code) |
| 112 | 367 | code | set_code (site 15 codetab (class with [GraphQLDeprecated]; the record form needed a property: target) |
| 114 | 369 | code | set_text Raw WebSockets, pod pinning, the backplane, binary framing,  |
| 114 | 369 | notes | set_notes (Appendix C now matches the example (raw WebSockets); SignalR is Appendix Q) |
| 115 | 370 | code | set_text A WebSocket endpoint in ASP.NET Core |
| 115 | 370 | code | set_text csharp · ASP.NET Core 10 WebSockets |
| 115 | 370 | code | set_code (site 16 codetab and examples/16-websockets/dotnet/WsServer/Program.cs (route /ws/{clientId) |
| 115 | 370 | code | set_text Raw ASP.NET Core WebSockets, as in the running example. The  |
| 115 | 370 | notes | set_notes (matches the new code) |
| 119 | 374 | code | set_text Binary framing with protobuf — fast and versioned |
| 119 | 374 | code | set_text csharp · Google.Protobuf + WebSockets |
| 119 | 374 | code | set_code (site 16 codetabs (push and receive/dispatch)) |
| 119 | 374 | code | set_text Protobuf frames are smaller and faster than JSON; the versio |
| 119 | 374 | notes | set_notes (matches the new code) |
| 128 | [383] | code | replace `If you use Temporal .NET instead, its Saga utility (Saga.AddCompensati` |
| 130 | [385] | stack | replace ` MassTransit Sagas is a closely-related alternative if you're already ` |
| 130 | [385] | stack | replace `on NuGet as Temporalio.Temporal)` |
| 130 | 385 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 132 | 387 | stack | set_text csharp · Temporalio + ASP.NET Core |
| 132 | 387 | code | set_code (Temporal .NET SDK: no Saga helper class; StartToCloseTimeout required on every activity ca) |
| 132 | 387 | code | set_text Workflow and activities are plain C# classes; the workflow k |
| 132 | 387 | notes | set_notes (matches the new code) |
| 133 | [388] | stack | replace ` The MassTransit Sagas callout is for shops already using MassTransit:` |
| 134 | [389] | code | replace `.OnEntry(() =>` |
| 134 | 389 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 141 | [396] | stack | replace `With MassTransit this is declarative configuration (UseMessageRetry + ` |
| 142 | 397 | stack | set_text Kafka retry + DLQ with Confluent.Kafka |
| 142 | 397 | stack | set_text csharp · Confluent.Kafka + Polly 8 |
| 142 | 397 | code | set_code (site 18 codetab (Kafka), condensed) |
| 142 | 397 | stack | set_text Bounded in-place retries, a delayed-retry topic, then a DLQ; |
| 142 | 397 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 154 | [409] | code | replace `MassTransitEventPublisher : IEventPublisher.` |
| 154 | [409] | stack | replace `(EF Core repo, MassTransit publisher)` |
| 154 | [409] | stack | replace `(EfCoreOrderRepository for persistence, MassTransitEventPublisher for ` |
| 175 | [430] | stack | replace `MassTransit consumer Stop semantics` |
| 177 | [432] | stack | replace `Traefik, YARP, MassTransit, NRules` |
| 180 | [435] | stack | replace `(.NET + MassTransit RoutingSlip + NRules)` |
| 182 | [437] | stack | replace `MassTransit RoutingSlip + NRules: when the routing logic is a business` |
| 194 | [449] | stack | replace `(MassTransit RoutingSlip, Wolverine routing, a custom dispatcher)` |
| 194 | 449 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 195 | 450 | stack | set_text .NET + Confluent.Kafka + NRules: rule-based routing |
| 195 | 450 | stack | set_text A Kafka consumer owns the plumbing; NRules owns the decision |
| 195 | 450 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 196 | 451 | stack | set_text A Kafka consumer in .NET, calling NRules |
| 196 | 451 | stack | set_text csharp · .NET 10 + Confluent.Kafka + NRules |
| 196 | 451 | code | set_code (site 22 codetab (NRules + Confluent.Kafka router)) |
| 196 | 451 | stack | set_text enrich → NRules evaluate → dispatch to Kafka or HTTP: the co |
| 196 | 451 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 197 | [452] | stack | replace `setting the WhereTo property the RoutingSlip will consume` |
| 204 | [459] | stack | replace `In-app router (MassTransit RoutingSlip + NRules)` |
| 205 | [460] | stack | replace `MassTransit documentation (RoutingSlip activities + receive endpoints)` |
| 205 | [460] | stack | replace `plus the MassTransit RoutingSlip / NRules samples (the canonical .NET ` |
| 207 | 462 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client); pinned versions) |
| 209 | 464 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 210 | 465 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 211 | [466] | stack | replace `EF Core, MassTransit, Temporalio.Temporal, OpenTelemetry` |
| 211 | 466 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 221 | 476 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 222 | 477 | stack | set_text csharp · ASP.NET Core 10 + StackExchange.Redis + Confluent.K |
| 222 | 477 | code | set_code (site 24 codetab (decorator); examples/24-monolith-to-microservices/dotnet uses StackExchan) |
| 222 | 477 | notes | set_notes (MassTransit removed (Confluent.Kafka is the Kafka client)) |
| 212 | [467] | stack | replace `IHttpClientFactory + IDistributedCache + MassTransit + FusionCache` |
| 215 | [470] | stack | replace `(typically via MediatR INotificationHandler for in-process events, or ` |
| 229 | 484 | voice | set_text GetOrSetAsync is read-through. Factory runs only on miss. Bu |
| 227 | 482 | code | set_code (site 25 codetab (the old code had `?? return NotFound()`, which does not compile)) |
| 229 | 484 | code | set_code (site 25 codetab (same `?? return` fix)) |
| 233 | 488 | code | set_code (site 25 codetab) |
| 233 | 488 | notes | set_notes (matches the new code) |
| 259 | 514 | code | set_code (excerpt of examples/21-graceful-shutdown/dotnet/OrderService/Program.cs (no Thread.Sleep i) |
| 259 | 514 | notes | set_notes (matches the new code) |
| 267 | 522 | code | set_code (site 27 codetab API, as a minimal API (examples/27-feature-flags/dotnet: SetProviderAsync,) |
| 138 | 393 | code | set_code (site 18 codetab; WriteAsJsonAsync sets the content type, so the problem+json media type is) |
| 294 | [549] | version | replace `UBI images are freely redistributable, based on RHEL 9, and supported ` |
| 294 | 549 | version | set_text ubi9/dotnet-100:9.8-1791421718 (SDK, build only) → ubi9/dotn |
| 296 | [551] | stack | replace `Multi-stage Dockerfiles separate` |
| 296 | [551] | version | replace `Red Hat UBI images are the same .NET runtime on a RHEL 9 base` |
| 287 | 542 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 288 | 543 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 289 | 544 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 290 | 545 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 291 | 546 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 292 | 547 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 293 | 548 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 294 | 549 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 295 | 550 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 296 | 551 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 297 | 552 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 298 | 553 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 299 | 554 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 300 | 555 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 301 | 556 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 302 | 557 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |
| 303 | 558 | notes | set_notes (slide had no speaker notes (KNOWN_MISSING_NOTES)) |

## MassTransit ledger

Before: 21 slides and 25 notes in the text copy (46 lines). After the exclusive rewrites and these ops: 3 lines,
all intentional history:

| Slide | Where | Sentence kept |
|---|---|---|
| 38 (sldId 293) | notes | "MassTransit was dropped: its abstraction hides the Kafka semantics this section teaches ... and version 9 moved to a commercial license." |
| 207 (sldId 462) | notes | "(MassTransit was dropped: it hides those semantics and moved to a commercial license in version 9)" |
| 210 (sldId 465) | notes | "MediatR and MassTransit both moved to commercial licenses; ... this deck uses Confluent.Kafka directly instead of MassTransit." |

Fate of every other occurrence: slide 1 notes (stack list), 27 bullet, 31 chip/code/notes, 34 code comment and
notes, 38 title/chip/code/caption/notes, 68 code and notes, 89 chip/code/notes, 96 references, 130 bullet and
notes, 133 notes, 134 notes, 141 notes, 142 title/chip/code/caption/notes, 154 code/caption/notes, 175
references, 176 notes, 177 bullet, 180 notes, 182 bullet, 194 bullet/notes, 195 title/caption/notes, 196
title/chip/code/caption/notes, 197 notes, 204 bullet, 205 references/notes, 207/209/210/211 notes and bullets,
212 notes, 215 notes, 221 notes, 222 chip/code/notes: rewritten as listed in the change table.

Images that still show MassTransit (owned by the image audit, not by this file): `58-appI-masstransit-routingslip-dn`
(slide 195, sldId 450) and the Appendix J tables `70/71/72-appJ-*-dn` (sldIds 462–464), plus any MassTransit
Sagas callout in the Stateless figure (slide 133, sldId 388). The text on those slides no longer names MassTransit.

## Version strings left in the deck

| String | Pin | Source |
|---|---|---|
| .NET 10 / ASP.NET Core 10 / net10.0 | .NET 10.0.12 (SDK 10.0.112) | modernization plan S4 |
| Confluent.Kafka 2.16.0 | 2.16.0 | S4 |
| Streamiz.Kafka.Net 1.8.2 | 1.8.2 | S4 |
| ubi9/dotnet-100:9.8-1791421718, ubi9/dotnet-100-aspnet:9.8-1791363520 | same | pins table |
| Polly 8 / Polly v8 | major label | (no pin; not used by the examples) |
| Apicurio v3 | apicurio-registry 3.3.3 | pins table (shared-code slide) |
| C# 12 (primary constructors) | history | — |
| .NET 4.x, 5, 6, 8, 9 | history ("since .NET 6", ".NET 8 added ...") | — |
| OpenFeature, flagd provider (no version on slide) | 2.14.1, 0.5.0 | S4 |

## Unresolved

- Images with MassTransit content (listed under the ledger) need the image audit's replacements; no site SVG
  exists for the .NET-only Appendix J tables, so they need regenerated images or removal.
- Slide 3 and slide 97 notes still say "four deep-dive appendices": a fact for the voice/agenda owners.
- Temporal .NET SDK license: notes now say "an open-source .NET SDK"; slides 130/131 still say "Apache 2.0"
  for the .NET SDK. The SDK repository (temporalio/sdk-dotnet) is MIT; not verified online in this pass.

## Decision 7 amendment (vendor-neutral, 2026-10-12)

Generator: `tools/amend_vendor.py` (ops tagged `_vendor`, inserted just before the agenda op; run after `amend_decisions.py`).
Find strings and counts come from the pre-decision text copy (`verify_all.py` output of the edit files at 39a5b1e).

- Appendix S removed: the `clone_slide` ops `s0`–`s9` (and `s7n`) and every `set_*` op on `$s*` are dropped (79 ops); Appendix R (9 slides) stays. Agenda line "Appendices P–R · .NET on Linux, Blazor, minikube" (same line count, so the agenda fit is unchanged); agenda notes, the title and overview notes and the R0/R1 notes no longer mention OpenShift Local ("carries over to any conformant Kubernetes cluster").
- Valet key (sldId 335): title "Valet key — scoped, time-bound, op-restricted", chip `csharp · ASP.NET Core 10 + HMACSHA256`, `set_code` = `examples/12-security/dotnet/OrderService/Program.cs` (`/valet-key`, `/verify-valet`, `ComputeHmac`), 20 lines, notes rewritten (HMAC or HS256 ticket the service mints and verifies; generic object store). Code map row: matches `examples/12-security` (condensed excerpt, first comment line says so).
- Claim check (sldId 344): chip `csharp · ASP.NET Core 10 + Confluent.Kafka`, `set_code` = the earlier generic-store version with `https://objects.internal/` and a `ComputeHmac` ticket (`resource`, `operation`, `expires`, `token` in the claim), 15 lines; the AWS SDK for .NET note is gone; notes rewritten. Same lines as the site claim-check codetab after the site fix (`site-fixes.md`, decision-7 section). No example implements the claim check (illustrative, token from Example 12).
- Removed: AWS SDK for .NET / AWSSDK.Extensions.NETCore.Setup / IAmazonS3 (slides 80, 89); the S3 pre-signed URL, STS AssumeRole, Azure SAS, GCS framing.
- Shared rewrites (where present in this deck): 4C's notes and bullet (CloudTrail, "S3 bucket open"); event-driven tools notes ("to S3" → "to an object store"); valet-key concept notes (one generic implementation sentence instead of S3/Azure/GCS/STS); strangler-fig IdPs (Keycloak, Dex instead of Auth0, Azure AD); zero-trust edge (Pomerium or OAuth2 Proxy in front of Keycloak instead of Google IAP, Cloudflare Access, AWS Verified Access; licence note Pomerium Apache-2.0, OAuth2 Proxy MIT); claim-check concept notes; choosing-the-pattern notes; glossary SAS entry and note removed; Appendix I gateway list without Apigee; Appendix M references: gRFC A6 instead of the AWS Builders' Library.
- .NET only: Blazor/SignalR slides and notes (282, 373, 377, 378) drop Azure SignalR Service / App Service / Static Web Apps ("no managed SignalR service"); toolkit notes (462, 463) drop "Azure-only" and "not Confluent Cloud"; Appendix P UBI slides (549, 551) say UBI runs on any Kubernetes cluster instead of "supported on OpenShift" (Red Hat UBI itself stays: Red Hat-led open source). Agenda: "Appendices P–R · .NET on Linux, Blazor, minikube".
- Kept (not vendor services): Heroku as the origin of the twelve-factor methodology (history), Google SRE Book (reference), gRPC / Google.Protobuf / Google.Rpc (open-source libraries), Netflix concurrency-limits (Apache-2.0 library), Red Hat UBI and the Red Hat brand frame.
- Figures (`replace_picture`, `tools/vendor_figures.py`): sldIds 334 (valet-key concept), 337 (zero-trust); the Appendix J tables 462 and 464 keep their earlier replace_picture ops, whose PNGs are re-rendered without "Azure". The valet-key figure named S3, Azure SAS, GCS and STS; the zero-trust figure listed Google IAP, Cloudflare Access and AWS Verified Access; both become the neutral site figures (`12-valet-key.png` with "object store" labels, `12-zero-trust.png`).
