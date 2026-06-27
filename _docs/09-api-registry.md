---
title: "API Registry"
order: 9
part: "The operational platform"
description: "One authoritative, versioned home for every contract — OpenAPI, .proto, AsyncAPI, and event schemas — with Apicurio's compatibility rules gating breaking changes in CI before code ships."
duration: 17 minutes
---

The Communications chapter kept insisting that the contract is the boundary. A
boundary needs one authoritative home. The registry is the difference between
"we have contracts *somewhere* in git" and "contracts are **enforced** before code
ships."

## One versioned home for every contract

Every contract type lands in the same place: REST OpenAPI specs, GraphQL SDL, gRPC
`.proto` files, and event schemas (Avro or JSON). In this stack the registry is
**Apicurio**. Each artifact carries versions and a **compatibility rule** —
`BACKWARD`, `FORWARD`, or `FULL`. Producers register; consumers fetch and generate
stubs from the registered version, so no one hand-writes parsing and everyone is
reading the same source of truth. The Kafka serde libraries do this automatically:
a producer's serializer registers the schema, a consumer's deserializer fetches
it.

{% include excalidraw.html
   file="09-one-registry"
   alt="REST design (OpenAPI), gRPC (.proto), and events (AsyncAPI) all register into one Apicurio Registry that holds OpenAPI, AsyncAPI, proto, Avro, and JSON Schema artifacts with versions and compatibility rules. The registry fans out to three consumers: a CI gate that blocks breaking changes, client codegen for typed stubs, and runtime resolution that serdes by schema-id."
   caption="Figure 9.1 — One registry for every contract type, feeding the CI gate, code generation, and runtime serde" %}

Read it design-first: every contract type — REST, gRPC, and events alike — is
registered *before* code depends on it, and three different consumers read from that
one home. CI gates breaking changes against it, client builds generate typed stubs
from it, and at runtime the Kafka serde resolves the exact schema by the id carried on
each message. One authoritative source, three jobs.

Because every artifact is just bytes addressed by group and id, you talk to the
registry over plain HTTP — the same `curl` you already use, from any language or a
pipeline step:

```bash
# set the compatibility rule once per artifact
# BACKWARD = a new consumer can still read data written to the old schema
curl -sf -X POST \
  http://apicurio.registry.svc/apis/registry/v3/groups/orders/artifacts/order-placed/rules \
  -H "Content-Type: application/json" \
  -d '{ "ruleType": "COMPATIBILITY", "config": "BACKWARD" }'

# register a new version; the registry checks it against the rule
curl -s -o /dev/null -w "%{http_code}" -X POST \
  http://apicurio.registry.svc/apis/registry/v3/groups/orders/artifacts/order-placed/versions \
  -H "Content-Type: application/json" \
  --data-binary @order-placed.avsc        # → 200 if compatible, 409 if not
```

The same call works from application or pipeline code in any language — here in
Python, returning exactly the status code the CI gate keys off:

```python
# registry_client.py — register a new version; the registry enforces the rule
import requests

REGISTRY = "http://apicurio.registry.svc/apis/registry/v3"

def publish(group: str, artifact_id: str, schema: bytes) -> int:
    r = requests.post(
        f"{REGISTRY}/groups/{group}/artifacts/{artifact_id}/versions",
        headers={"Content-Type": "application/json"},
        data=schema,
    )
    return r.status_code        # 200 if compatible, 409 if the rule rejects it
```

## Gate breaking changes in CI

This is the guardrail that makes the whole contract story real. The CI pipeline
posts the new schema version to the registry; if it violates the artifact's
compatibility rule, Apicurio returns **`409 Conflict`** and the step fails the
build, blocking the merge. The contract is enforced *before* code ships — not
discovered broken in production by a downstream team three days later.

{% include excalidraw.html
   file="09-registry-gate"
   alt="A pull request with a schema change posts the new version to the Apicurio registry; the registry checks it against the compatibility rule and either allows merge and publish, or returns 409 and blocks the merge; consumers then fetch the published schema and generate stubs"
   caption="Figure 9.2 — The registry checks compatibility at publish time and blocks the merge on a breaking change" %}

```yaml
# .github/workflows/contracts.yml — block breaking changes before merge
- name: Gate the contract against the registry
  run: |
    code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
      "$REGISTRY/groups/orders/artifacts/order-placed/versions" \
      -H "Content-Type: application/json" --data-binary @order-placed.avsc)
    if [ "$code" = "409" ]; then
      echo "::error::Incompatible schema change — blocking the merge"
      exit 1
    fi
```

The rule is the contract about the contract. `BACKWARD` (new consumers can read
old data) is the common default for events, because consumers upgrade on their own
schedule and must tolerate data already on the topic. `FORWARD` flips it for cases
where old consumers must read new data, and `FULL` demands both. Picking the rule
is a design decision; once picked, the registry enforces it for you and the `409`
is non-negotiable.

### Cross-check it yourself

Prove the gate bites. Register `order-placed.avsc`, then make a genuinely breaking
change — rename a required field — and `curl` the new version: you should get a
`409`, and the CI step should exit non-zero. Then make an additive change — a new
*optional* field — and confirm it returns `200` and publishes a new version. The
breaking change failing the build and the additive change passing it is the entire
point of the registry.

---
*Verification status: unverified — the `curl` and CI-gate flows are transcribed
from the source decks against an Apicurio v3 API, not yet run. The
`examples/09-api-registry/` runner moves it to verified.*
