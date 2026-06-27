---
title: "Acronyms"
marker: "★"
label: "Glossary"
order: 29
part: "Deep-dive appendices"
description: "Every acronym used across the book, expanded and placed in context — grouped by where it shows up: the wire, the data layer, events, the platform, security, observability, and the domain."
---

Every acronym the book leans on, expanded and put in context. They are grouped by the
layer they belong to — the wire, the data store, messaging, the platform, security,
observability, and the domain — so a term is easy to find by the part of the system it
describes. Where an acronym means something specific *in this book*, the third column says
what, because a few of them (notably `ACL`) carry a different meaning here than the one you
might expect.

## Protocols, APIs, and the wire

| Acronym | Expands to | In this book |
|---|---|---|
| API | Application Programming Interface | The contract a service exposes — the whole subject of the book |
| REST | Representational State Transfer | Resource-oriented HTTP; the public, cacheable, browser-native default |
| gRPC | gRPC Remote Procedure Call | Procedure-oriented, HTTP/2, protobuf binary; the internal-call default |
| RPC | Remote Procedure Call | Calling a typed method on another process as if it were local |
| HTTP, HTTP/1.1, HTTP/2 | HyperText Transfer Protocol | The /1.1 and /2 suffixes are protocol versions; gRPC requires /2 |
| TLS | Transport Layer Security | Encryption on the wire; an L7 router usually terminates it |
| mTLS | mutual TLS | Both sides present certificates — workload-to-workload identity in the mesh |
| SNI | Server Name Indication | The hostname an L4 balancer can route on without terminating TLS |
| TCP | Transmission Control Protocol | The L4 connection an L7 router rides on top of |
| JSON | JavaScript Object Notation | Text encoding for REST and GraphQL payloads |
| SDL | Schema Definition Language | GraphQL's typed schema — its published contract |
| URL / URI | Uniform Resource Locator / Identifier | The address of a resource; a URI identifies, a URL also locates |
| DTO | Data Transfer Object | A shape passed across a boundary; sharing one is *model coupling* |
| BFF | Backend for Frontend | An API tailored to one client, often a GraphQL gateway |
| SOAP / WSDL | Simple Object Access Protocol / Web Services Description Language | Legacy XML RPC and its contracts, migrated away from |
| WCF | Windows Communication Foundation | The legacy .NET service framework replaced by minimal APIs and gRPC |
| W3C | World Wide Web Consortium | Owner of standards like the `traceparent` trace-context header |

## Data and persistence

| Acronym | Expands to | In this book |
|---|---|---|
| DB | Database | A service's private store; sharing one is the *intrusive* coupling anti-pattern |
| SQL | Structured Query Language | The query language of the relational stores (Postgres) |
| CQRS | Command Query Responsibility Segregation | Separate write and read models, often fed by events |
| CDC | Change Data Capture | Streaming a database's changes out as events, via Debezium |
| WAL | Write-Ahead Log | The commit log a database tails to emit those changes |
| OLTP | Online Transaction Processing | The transactional workload a primary store serves |
| ORM | Object-Relational Mapping | Mapping rows to objects; Entity Framework on .NET, JPA on the JVM |
| EF | Entity Framework | The .NET ORM used in the examples |
| JPA | Jakarta Persistence API | The JVM persistence standard |
| PII | Personally Identifiable Information | Data that defines a privacy and encryption boundary |
| TTL | Time To Live | How long a cached entry or record stays valid before expiry |
| MSDTC | Microsoft Distributed Transaction Coordinator | The two-phase-commit coordinator that sagas replace across services |
| N+1 | the N+1 query problem | One query per row instead of one batched query — fixed with batching |

## Events, messaging, and streaming

| Acronym | Expands to | In this book |
|---|---|---|
| DLQ | Dead-Letter Queue | Where a poison record goes after bounded retries, so the partition keeps moving |
| EIP | Enterprise Integration Patterns | The messaging-pattern vocabulary (router, translator, aggregator) |
| MSMQ | Microsoft Message Queuing | The legacy Windows queue replaced by Kafka |
| NATS | a lightweight messaging system | An alternative broker named alongside Kafka |

## Platform, delivery, and infrastructure

| Acronym | Expands to | In this book |
|---|---|---|
| K8s | Kubernetes | The numeronym (K, eight letters, s) for the orchestration platform |
| HPA | Horizontal Pod Autoscaler | Scales replica count on CPU or custom metrics |
| KEDA | Kubernetes Event-Driven Autoscaling | Scales on queue depth and other event sources, including to zero |
| CRD | Custom Resource Definition | How an operator (or Istio) extends the Kubernetes API |
| CNCF | Cloud Native Computing Foundation | Home of Kubernetes, OpenTelemetry, OpenFeature, and the rest of the stack |
| OSS | Open-Source Software | The whole platform is OSS — no managed-cloud lock-in |
| YAML | YAML Ain't Markup Language | The configuration format for Kubernetes and Istio objects |
| LB | Load Balancer | An L4 or L7 component spreading traffic across pods |
| L4 / L7 | Layer 4 / Layer 7 (OSI) | Transport-level versus application-level routing |
| VIP | Virtual IP | A stable address an L4 balancer fronts a backend pool with |
| NAT | Network Address Translation | Why IP-hash stickiness breaks behind shared addresses |
| VPC / VPN | Virtual Private Cloud / Network | Network isolation boundaries referenced in passing |
| IIS | Internet Information Services | The Windows web host left behind in the .NET migration |
| YARP | Yet Another Reverse Proxy | The in-process .NET reverse proxy / gateway |
| CI | Continuous Integration | Where compatibility and module-boundary checks run automatically |
| SDK | Software Development Kit | A language's client library, e.g. the OpenTelemetry SDK |
| DI / CDI | Dependency Injection / Contexts and Dependency Injection | Wiring dependencies; CDI is the Jakarta standard |
| LTS | Long-Term Support | A release supported for years, e.g. .NET 10 |
| PID | Process ID | PID 1 in a container receives `SIGTERM` on shutdown |
| I/O | Input/Output | Work the domain core delegates to adapters in hexagonal architecture |
| S3 | Simple Storage Service | Object storage, e.g. the target of a valet-key upload |
| DSL | Domain-Specific Language | A focused mini-language, e.g. a business-rule ruleset |
| DMN | Decision Model and Notation | A decision-table standard for business-rule routing |
| PR | Pull Request | The review unit a schema or contract change travels in |

## Security and identity

| Acronym | Expands to | In this book |
|---|---|---|
| JWT | JSON Web Token | The signed token carrying identity and claims; lets services stay stateless |
| OIDC | OpenID Connect | The identity layer issuing those tokens |
| SPIFFE | Secure Production Identity Framework For Everyone | Workload identity the mesh binds to mTLS certificates |
| WAF | Web Application Firewall | An edge layer inspecting requests for attacks |
| RBAC | Role-Based Access Control | Authorisation by role, enforced at the gateway or in policy |
| IAM | Identity and Access Management | The broader identity and permission system |
| KMS | Key Management Service | Where encryption keys live, outside the application |
| MFA | Multi-Factor Authentication | A second identity factor at the edge |
| OPA | Open Policy Agent | The policy-as-code engine for authorisation decisions |
| AD / NTLM | Active Directory / NT LAN Manager | Windows identity and its legacy auth, replaced by OIDC and mTLS |

## Observability and reliability

| Acronym | Expands to | In this book |
|---|---|---|
| OTel | OpenTelemetry | The vendor-neutral instrumentation standard for traces, metrics, and logs |
| OTLP | OpenTelemetry Protocol | The wire format from your service to the collector |
| LGTM | Loki, Grafana, Tempo, Mimir | The open-source backend stack for logs, dashboards, traces, and metrics |
| SLO | Service Level Objective | A reliability target, measured by SLIs and promised in an SLA |
| RED | Rate, Errors, Duration | The request-centric monitoring method |
| USE | Utilization, Saturation, Errors | The resource-centric monitoring method |
| RTT | Round-Trip Time | Network latency; what locality-aware routing minimises |
| p50 / p99 | 50th / 99th percentile | Latency percentiles — p99 is where L7 hop overhead shows up |
| MDC | Mapped Diagnostic Context | Per-request fields attached to every log line, e.g. the trace id |
| SRE | Site Reliability Engineering | The discipline behind SLOs, error budgets, and these methods |
| ETW | Event Tracing for Windows | The legacy telemetry source replaced by OpenTelemetry |

## Domain, architecture, and language

| Acronym | Expands to | In this book |
|---|---|---|
| DDD | Domain-Driven Design | Bounded contexts and ubiquitous language drive where API boundaries go |
| ACL | Anticorruption Layer | **In DDD**, a translation layer keeping a foreign model out of yours — *not* an access-control list |
| XOR | exclusive OR | The coupling rule "modularity = strength XOR distance" — have one, not both |
| MVC | Model-View-Controller | The legacy web UI pattern migrated from |
| UI | User Interface | The client surface, e.g. Blazor in the .NET stack |
| AI | Artificial Intelligence | The agent context the opening chapter frames the book around |
| RAII | Resource Acquisition Is Initialization | The C++ lifetime idiom tying cleanup to scope |
| JVM | Java Virtual Machine | The runtime for the Spring Boot and Quarkus examples |

## Standards and licensing

| Acronym | Expands to | In this book |
|---|---|---|
| RFC | Request for Comments | An IETF standard, e.g. RFC 9457 Problem Details, RFC 9745 Deprecation |
| IETF | Internet Engineering Task Force | Publisher of the HTTP, Problem Details, and `Idempotency-Key` specs |
| MIT, BSD, Apache 2.0, AGPL | open-source software licenses | The licenses on the pinned toolkit and platform components |

---
*Verification status: compiled from the book's own usage — every entry appears in the
chapters or appendices. Expansions follow each technology's canonical naming; where a term
is overloaded (`ACL`), the meaning used in this book is called out explicitly.*
