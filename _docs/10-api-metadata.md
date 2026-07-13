---
title: "API Metadata"
order: 10
part: "The operational platform"
description: "The discovery and trust plane — a searchable catalog of every API, topic, and table with ownership, automated lineage, and quality signals, so you can answer 'if I change this field, who breaks?' before you change it."
duration: 14 minutes
---

A contract that is enforced but undiscoverable is half useless. If a consumer
can't find your API and decide whether to trust it, they'll build their own or
screen-scrape yours — and the boundary you worked to establish quietly erodes.
Metadata is the **discovery and trust plane**: a searchable catalog of every API,
topic, and table, with ownership, lineage, and quality signals attached.

## Discovery, lineage, and ownership

In this stack the catalog is **OpenMetadata**. It ingests from many sources —
OpenAPI specs, the Apicurio registry, Kafka topics, Postgres schemas — through
*scheduled connectors*, and builds one searchable catalog that stays current
without manual upkeep. That last point matters: a wiki is stale the day after it's
written; an ingested catalog is not.

{% include excalidraw.html
   file="10-metadata-catalog"
   alt="OpenMetadata ingests from OpenAPI specs, the Apicurio registry, Kafka topics, and Postgres schemas through scheduled connectors, building one searchable catalog that delivers discovery, trust, lineage, and ownership to consumers"
   caption="Figure 10.1 — One catalog, fed by connectors, answering the change-safety question" %}

The real differentiator over a wiki is **automated lineage**. OpenMetadata knows
that *this* topic feeds *that* table feeds *this* API — column- and topic-level. So
it can answer the question that otherwise gets answered the hard way, in
production:

> if I change this field, who breaks?

— and answer it *before* you make the change, not after a downstream team's
dashboard goes blank. OpenMetadata derives this graph automatically from what it
ingests — parsing schemas, topic configurations, and query history — so the lineage
stays accurate as the system changes, with no one drawing a dependency diagram by
hand.

## What the catalog gives every consumer

Four concrete payoffs, each replacing a thing teams currently do by asking around:

{% include excalidraw.html
   file="10-catalog-payoffs"
   alt="Four columns of what the catalog gives every consumer. Discovery: search across APIs, topics, and tables, find the owning team and how to get access. Trust: published SLOs, data-quality results, freshness, and a criticality tier. Lineage: column- and topic-level impact analysis answering who breaks if I change this. Ownership: tags and PII classification, an accountable owner, and compliance-readiness."
   caption="Figure 10.2 — Four payoffs the catalog gives every consumer: discovery, trust, lineage, and ownership" %}

- **Discovery** — search across APIs, topics, and tables, and find the owning team
  and how to get access. No more hunting through Slack for who owns `inventory`.
- **Trust** — published SLOs, data-quality test results, freshness, and a
  criticality tier tell you whether this thing is safe to depend on.
- **Lineage** — column- and topic-level impact analysis answers the change-safety
  question proactively, for both producers and consumers.
- **Ownership and governance** — tags, PII classifications, and an accountable
  owner on every asset. This is also exactly what a compliance team needs, so the
  catalog does double duty.

## Working with the catalog API

OpenMetadata exposes a REST API for everything the UI does. Two operations every
service team reaches for: **tagging an asset** (mark a field as PII so governance
knows about it) and **querying lineage** (find out who depends on a topic before
changing its schema). Both are simple HTTP calls from any language:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// MetadataClient.java — tag an asset and query lineage via OpenMetadata REST API
@Service
public class MetadataClient {
    private static final String CATALOG = "http://openmetadata.svc/api/v1";
    private final RestClient rest = RestClient.create();

    public void tagAsPii(String tableId, String column) {
        rest.patch()
            .uri(CATALOG + "/tables/{id}", tableId)
            .contentType(MediaType.valueOf("application/json-patch+json"))
            .body(List.of(Map.of("op", "add",
                "path", "/columns/" + column + "/tags/-",
                "value", Map.of("tagFQN", "PII.Sensitive"))))
            .retrieve().toBodilessEntity();
    }

    public JsonNode lineage(String topicFqn) {
        return rest.get()
            .uri(CATALOG + "/lineage/topic/name/{fqn}", topicFqn)
            .retrieve().body(JsonNode.class);          // upstream + downstream graph
    }
}
```

```java
// MetadataClient.java — Quarkus REST client for OpenMetadata
@RegisterRestClient(baseUri = "http://openmetadata.svc/api/v1")
public interface MetadataClient {

    @PATCH @Path("/tables/{id}")
    @Consumes("application/json-patch+json")
    Response tagAsPii(@PathParam("id") String tableId, JsonArray patch);

    @GET @Path("/lineage/topic/name/{fqn}")
    JsonObject lineage(@PathParam("fqn") String topicFqn);
}
```

```csharp
// MetadataClient.cs — tag an asset and query lineage via OpenMetadata REST API
public class MetadataClient(HttpClient http)
{
    private const string Catalog = "http://openmetadata.svc/api/v1";

    public async Task TagAsPiiAsync(string tableId, string column)
    {
        var patch = JsonSerializer.Serialize(new[] { new {
            op = "add",
            path = $"/columns/{column}/tags/-",
            value = new { tagFQN = "PII.Sensitive" } } });
        await http.PatchAsync($"{Catalog}/tables/{tableId}",
            new StringContent(patch, Encoding.UTF8, "application/json-patch+json"));
    }

    public async Task<JsonDocument> LineageAsync(string topicFqn)
    {
        var json = await http.GetStringAsync(
            $"{Catalog}/lineage/topic/name/{topicFqn}");
        return JsonDocument.Parse(json);               // upstream + downstream graph
    }
}
```

```python
import httpx

CATALOG = "http://openmetadata.svc/api/v1"

async def tag_as_pii(table_id: str, column: str):
    async with httpx.AsyncClient() as client:
        await client.patch(
            f"{CATALOG}/tables/{table_id}",
            headers={"Content-Type": "application/json-patch+json"},
            json=[{"op": "add",
                   "path": f"/columns/{column}/tags/-",
                   "value": {"tagFQN": "PII.Sensitive"}}],
        )

async def lineage(topic_fqn: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{CATALOG}/lineage/topic/name/{topic_fqn}")
        return r.json()                                # upstream + downstream graph
```

{% raw %}
```cpp
// metadata_client.h — tag an asset and query lineage via OpenMetadata REST API
#include <cpr/cpr.h>

inline void tag_as_pii(std::string_view table_id, std::string_view column) {
  auto url = fmt::format("http://openmetadata.svc/api/v1/tables/{}", table_id);
  auto patch = fmt::format(
      R"([{{"op":"add","path":"/columns/{}/tags/-","value":{{"tagFQN":"PII.Sensitive"}}}}])",
      column);
  cpr::Patch(cpr::Url{url},
             cpr::Header{{"Content-Type", "application/json-patch+json"}},
             cpr::Body{patch});
}

inline std::string lineage(std::string_view topic_fqn) {
  auto url = fmt::format(
      "http://openmetadata.svc/api/v1/lineage/topic/name/{}", topic_fqn);
  return cpr::Get(cpr::Url{url}).text;                 // upstream + downstream graph
}
```
{% endraw %}

{% raw %}
```go
// metadata_client.go — tag an asset and query lineage via OpenMetadata REST API
const catalog = "http://openmetadata.svc/api/v1"

func tagAsPII(ctx context.Context, tableID, column string) error {
	patch, _ := json.Marshal([]map[string]any{{
		"op": "add", "path": "/columns/" + column + "/tags/-",
		"value": map[string]string{"tagFQN": "PII.Sensitive"},
	}})
	req, _ := http.NewRequestWithContext(ctx, "PATCH",
		catalog+"/tables/"+tableID, bytes.NewReader(patch))
	req.Header.Set("Content-Type", "application/json-patch+json")
	_, err := http.DefaultClient.Do(req)
	return err
}

func lineage(ctx context.Context, topicFQN string) (map[string]any, error) {
	resp, err := http.Get(catalog + "/lineage/topic/name/" + topicFQN)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var result map[string]any
	json.NewDecoder(resp.Body).Decode(&result)         // upstream + downstream graph
	return result, nil
}
```
{% endraw %}

## Data contracts as code

The catalog is most valuable when its metadata lives in Git alongside the schemas it
describes — **data contracts as code**. A data contract is a YAML or JSON document
committed next to the schema that declares the asset's owner, its SLO (freshness,
completeness), its PII classification, and its criticality tier. The CI pipeline that
gates schema changes also validates the contract, so ownership and quality expectations
are version-controlled and reviewable, not hand-entered in a UI.

The throughline of the last two chapters: a contract is only as good as your
ability to **find it, trust it, and know who owns it.** The registry makes the
contract authoritative; the catalog makes it discoverable and accountable.
Together they turn "we have contracts somewhere" into a platform people can
actually build on.

### Cross-check it yourself

The catalog's value shows up as a question answered in seconds instead of a
day. With the stack running, search the catalog for the `order.placed` topic and
follow its lineage downstream — confirm you can see, without asking anyone, which
tables and APIs consume it and which team owns each. Then check that an asset
carries its owner and PII tags. Getting that impact list from the catalog rather
than from a post-incident retro is the whole point.

---
*Verification status: conceptual chapter — no per-language runnable code. The
discovery, lineage, and trust capabilities it describes are exercised against a
running OpenMetadata catalog in the example stack.*
