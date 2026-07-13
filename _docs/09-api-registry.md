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

The same call works from application or pipeline code in any language, returning
exactly the status code the CI gate keys off:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// RegistryClient.java — register a new version; the registry enforces the rule
@Component
public class RegistryClient {
    private static final String REGISTRY =
        "http://apicurio.registry.svc/apis/registry/v3";
    private final RestClient rest = RestClient.create();

    public int publish(String group, String artifactId, byte[] schema) {
        var resp = rest.post()
            .uri(REGISTRY + "/groups/{g}/artifacts/{a}/versions", group, artifactId)
            .contentType(MediaType.APPLICATION_JSON)
            .body(schema)
            .retrieve()
            .toBodilessEntity();
        return resp.getStatusCode().value();   // 200 if compatible, 409 if rejected
    }
}
```

```java
// RegistryClient.java — Quarkus REST client; the registry enforces the rule
@RegisterRestClient(baseUri = "http://apicurio.registry.svc/apis/registry/v3")
@Path("/groups/{group}/artifacts/{artifactId}/versions")
public interface RegistryClient {

    @POST @Consumes(MediaType.APPLICATION_JSON)
    Response publish(@PathParam("group") String group,
                     @PathParam("artifactId") String artifactId,
                     byte[] schema);
    // caller checks response.getStatus(): 200 = compatible, 409 = rejected
}
```

```csharp
// RegistryClient.cs — register a new version; the registry enforces the rule
public class RegistryClient(HttpClient http)
{
    private const string Registry =
        "http://apicurio.registry.svc/apis/registry/v3";

    public async Task<int> PublishAsync(string group, string artifactId, byte[] schema)
    {
        var content = new ByteArrayContent(schema);
        content.Headers.ContentType = new("application/json");
        var resp = await http.PostAsync(
            $"{Registry}/groups/{group}/artifacts/{artifactId}/versions", content);
        return (int)resp.StatusCode;       // 200 if compatible, 409 if rejected
    }
}
```

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

{% raw %}
```cpp
// registry_client.h — register a new version; the registry enforces the rule
#include <cpr/cpr.h>

inline int publish(std::string_view group, std::string_view artifact_id,
                   std::string_view schema) {
  auto url = fmt::format(
      "http://apicurio.registry.svc/apis/registry/v3"
      "/groups/{}/artifacts/{}/versions", group, artifact_id);
  auto r = cpr::Post(cpr::Url{url},
                      cpr::Header{{"Content-Type", "application/json"}},
                      cpr::Body{std::string(schema)});
  return r.status_code;          // 200 if compatible, 409 if rejected
}
```
{% endraw %}

```go
// registry_client.go — register a new version; the registry enforces the rule
func publish(group, artifactID string, schema []byte) (int, error) {
	url := fmt.Sprintf(
		"http://apicurio.registry.svc/apis/registry/v3/groups/%s/artifacts/%s/versions",
		group, artifactID)
	resp, err := http.Post(url, "application/json", bytes.NewReader(schema))
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	return resp.StatusCode, nil // 200 if compatible, 409 if rejected
}
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

## Schema evolution strategies

The compatibility rules tell you *whether* a change is safe; a strategy tells you
*how* to evolve a schema over time without breaking consumers. Four practices, in
order of increasing cost:

1. **Additive-only** — add optional fields with defaults; never remove or rename. This
   is the cheapest evolution: old consumers ignore the new field, new consumers fall
   back to the default when reading old data. If every change is additive, the
   compatibility rule never fires.

2. **Deprecation workflow** — when a field must go, mark it `@deprecated` (GraphQL,
   proto) or add a `deprecation` annotation in the schema. Publish the deprecation,
   monitor usage (field-level metrics, consumer-group offsets), and remove the field
   only once all consumers have migrated. This is the same add → deprecate → watch →
   retire cycle from **Appendix B**.

3. **Default values for new required fields** — if a new field must be present in all
   messages, add it with a default so old data on the topic can still be deserialized.
   Without the default, every consumer that encounters a message written before the
   field existed will fail to deserialize it.

4. **Union types for polymorphism** — when a single topic carries multiple event shapes
   (e.g. `OrderPlaced`, `OrderCancelled`), use Avro unions or protobuf `oneof` so the
   schema accommodates each variant. This keeps the topic type-safe without splitting
   it into per-event topics.

The registry enforces the *boundary* (compatible or not), but the strategy determines
how often you approach that boundary. Teams that evolve additively rarely trigger a
`409`; teams that rename or restructure hit it constantly.

## Validate before you publish

Before registering a new version you can ask the registry to **dry-run** the
compatibility check — validate the schema without creating a version. This is useful
in local development and pre-commit hooks, where you want fast feedback without
polluting the registry with test versions.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// DryRunValidator.java — validate a schema without creating a version
public boolean isCompatible(String group, String artifactId, byte[] schema) {
    var resp = restClient.post()
        .uri(REGISTRY + "/groups/{g}/artifacts/{a}/versions", group, artifactId)
        .header("X-Registry-DryRun", "true")      // dry-run: no version created
        .contentType(MediaType.APPLICATION_JSON)
        .body(schema)
        .retrieve()
        .toBodilessEntity();
    return resp.getStatusCode().is2xxSuccessful(); // true = compatible
}
```

```java
// DryRunValidator.java — Quarkus REST client; validate without creating a version
@RegisterRestClient(baseUri = "http://apicurio.registry.svc/apis/registry/v3")
@Path("/groups/{group}/artifacts/{artifactId}/versions")
public interface DryRunValidator {

    @POST @Consumes(MediaType.APPLICATION_JSON)
    @ClientHeaderParam(name = "X-Registry-DryRun", value = "true")
    Response validate(@PathParam("group") String group,
                      @PathParam("artifactId") String artifactId,
                      byte[] schema);
    // 200 = compatible (no version created); 409 = incompatible
}
```

```csharp
// DryRunValidator.cs — validate a schema without creating a version
public async Task<bool> IsCompatibleAsync(string group, string artifactId, byte[] schema)
{
    var content = new ByteArrayContent(schema);
    content.Headers.ContentType = new("application/json");
    using var req = new HttpRequestMessage(HttpMethod.Post,
        $"{Registry}/groups/{group}/artifacts/{artifactId}/versions");
    req.Headers.Add("X-Registry-DryRun", "true");     // dry-run: no version created
    req.Content = content;
    var resp = await http.SendAsync(req);
    return resp.IsSuccessStatusCode;                   // true = compatible
}
```

```python
def is_compatible(group: str, artifact_id: str, schema: bytes) -> bool:
    r = requests.post(
        f"{REGISTRY}/groups/{group}/artifacts/{artifact_id}/versions",
        headers={
            "Content-Type": "application/json",
            "X-Registry-DryRun": "true",               # dry-run: no version created
        },
        data=schema,
    )
    return r.status_code == 200                        # True = compatible
```

{% raw %}
```cpp
// dry_run_validator.h — validate a schema without creating a version
inline bool is_compatible(std::string_view group, std::string_view artifact_id,
                           std::string_view schema) {
  auto url = fmt::format(
      "http://apicurio.registry.svc/apis/registry/v3"
      "/groups/{}/artifacts/{}/versions", group, artifact_id);
  auto r = cpr::Post(cpr::Url{url},
                      cpr::Header{{"Content-Type", "application/json"},
                                  {"X-Registry-DryRun", "true"}},
                      cpr::Body{std::string(schema)});
  return r.status_code == 200;                         // true = compatible
}
```
{% endraw %}

```go
// dry_run_validator.go — validate a schema without creating a version
func isCompatible(group, artifactID string, schema []byte) (bool, error) {
	url := fmt.Sprintf(
		"http://apicurio.registry.svc/apis/registry/v3/groups/%s/artifacts/%s/versions",
		group, artifactID)
	req, _ := http.NewRequest("POST", url, bytes.NewReader(schema))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Registry-DryRun", "true")        // dry-run: no version created
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()
	return resp.StatusCode == 200, nil                 // true = compatible
}
```

### Cross-check it yourself

Prove the gate bites. Register `order-placed.avsc`, then make a genuinely breaking
change — rename a required field — and `curl` the new version: you should get a
`409`, and the CI step should exit non-zero. Then make an additive change — a new
*optional* field — and confirm it returns `200` and publishes a new version. The
breaking change failing the build and the additive change passing it is the entire
point of the registry.

---
*Verification status: verified — [`examples/09-api-registry/`](https://github.com/patterncatalyst/cloud-native-design-patterns/tree/main/examples/09-api-registry/) passes 4/4 checks
(schema registration, compatibility validation, versioned retrieval, CI gate).*
