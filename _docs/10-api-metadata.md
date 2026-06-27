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
