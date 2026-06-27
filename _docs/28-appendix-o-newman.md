---
title: "API Testing with Newman"
marker: "O"
label: "Appendix O"
order: 28
part: "Deep-dive appendices"
description: "Turning Postman collections into an automated API test gate with Newman: the anatomy of a collection, writing assertions, running one collection against all five implementations, data-driven tests, schema and contract validation, and wiring it into CI on plain Podman — no new test framework to learn."
duration: 20 minutes
---

Postman is already one of the tools this book reaches for to exercise an API by hand. **Newman**
is its command-line runner: it executes the very same Postman collection headlessly, which turns
the requests your team already pokes at interactively into an automated test gate you can run on
every change. The payoff is that the assertions live in one place — the collection — and the same
file serves three audiences: a developer clicking through Postman, a reviewer reading the tests,
and a CI pipeline failing the build when an assertion breaks.

## Why Newman

A Postman collection is an executable contract, not just a saved list of requests. Newman runs it
without the GUI and emits machine-readable results.

{% include excalidraw.html
   file="27-newman-run"
   alt="A collection.json (requests + tests) and an environment.json (base_url, tokens) feed into 'newman run', the headless CLI, which produces reporters — cli for humans, junit.xml for CI, html to share — feeding a CI gate that passes or fails. The same collection the team runs by hand becomes an automated gate with no new test framework."
   caption="Figure O.1 — Newman runs a Postman collection headlessly and emits CI-readable results" %}

There is no new test framework to learn: the tests are the JavaScript assertions already
supported inside Postman, and Newman is the bridge from "works when I click it" to "verified on
every pull request."

## Anatomy of a collection

A collection nests folders and requests; each request can carry a pre-request script, the HTTP
call itself, and a block of tests that run against the response. Environment variables supply the
parts that change between runs.

{% include excalidraw.html
   file="27-collection-anatomy"
   alt="A collection contains folders that group requests by resource; each request has a pre-request script, the HTTP call, and tests; the tests are JavaScript using pm.test and pm.expect to assert status, schema, and response time; environment variables like base_url and token are resolved at run time."
   caption="Figure O.2 — A collection is folders of requests, each with assertions; the environment supplies the variables" %}

The tests are small JavaScript blocks using Postman's `pm` API. A request that creates an order
might assert the status, the response time, and the shape of the body:

```json
{% raw %}{
  "name": "Create order",
  "request": {
    "method": "POST",
    "header": [{ "key": "Idempotency-Key", "value": "{{$guid}}" }],
    "url": "{{base_url}}/orders",
    "body": { "mode": "raw", "raw": "{\"sku\":\"A-1\",\"qty\":2}" }
  },
  "event": [{
    "listen": "test",
    "script": { "exec": [
      "pm.test('201 Created', () => pm.response.to.have.status(201));",
      "pm.test('under 300ms', () => pm.expect(pm.response.responseTime).to.be.below(300));",
      "const body = pm.response.json();",
      "pm.test('returns an id', () => pm.expect(body).to.have.property('id'));",
      "pm.collectionVariables.set('order_id', body.id);"
    ] }
  }]
}{% endraw %}
```

That last line stores the new id in a variable so a later request — fetch, cancel, or pay for the
order — can chain off it. Chaining requests through variables is how a collection models a whole
flow, not just isolated calls.

## One collection, five backends

Because Newman exercises the API as a black box over HTTP, the collection does not know or care
which language implements the service. The same collection is the conformance suite for every
implementation in this book.

{% include excalidraw.html
   file="27-black-box"
   alt="One collection running under Newman tests the same HTTP API (/orders, /payments) against five order-service implementations — Spring Boot, Quarkus, .NET, Python, and C++. Because Newman tests the API as a black box, one collection validates every implementation; the contract is the spec, not the code."
   caption="Figure O.3 — One collection is the conformance suite for all five implementations" %}

This is a quietly powerful idea: the collection *is* the API specification made executable. Point
it at whichever implementation is running and the assertions are identical. Bringing the service
under test up is the only language-specific step; the Newman command that follows is the same.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

```bash
# Spring Boot — start the service under test, then run the same collection
./mvnw spring-boot:run &           # http://localhost:8080
newman run orders.postman_collection.json -e local.postman_environment.json
```

```bash
# Quarkus — dev mode, then the same collection
./mvnw quarkus:dev &               # http://localhost:8080
newman run orders.postman_collection.json -e local.postman_environment.json
```

```bash
# .NET — run the service, then the same collection
dotnet run &                       # http://localhost:8080
newman run orders.postman_collection.json -e local.postman_environment.json
```

```bash
# Python / FastAPI — serve, then the same collection
uvicorn app.main:app --port 8080 & # http://localhost:8080
newman run orders.postman_collection.json -e local.postman_environment.json
```

```bash
# C++ / Drogon — build and run, then the same collection
cmake --build build && ./build/order-service &   # http://localhost:8080
newman run orders.postman_collection.json -e local.postman_environment.json
```

## Running Newman

The runner takes the collection and an environment file, and you choose reporters for the
audience. `cli` is for a human watching; `junit` emits the XML that CI systems turn into test
reports; `htmlextra` (a community reporter) produces a shareable page.

```bash
# install once (Node.js): npm i -g newman newman-reporter-htmlextra
newman run orders.postman_collection.json \
  --environment local.postman_environment.json \
  --reporters cli,junit,htmlextra \
  --reporter-junit-export results/newman.xml \
  --bail \                         # stop on first failure (fail fast in CI)
  --timeout-request 5000           # per-request ceiling
```

`--bail` stops at the first failed assertion, which is usually what you want in a gate; drop it
when you would rather see every failure in one run.

## Data-driven tests

A single set of requests can be run repeatedly over a table of inputs with `--iteration-data`.
This is how you cover boundary values, bad input, and edge cases without duplicating requests.

{% include excalidraw.html
   file="27-data-driven"
   alt="A collection of one request set, combined with an iteration-data.csv of rows (id and qty values including a zero and a very large number), runs once per row under newman, producing N result sets — one per case."
   caption="Figure O.4 — Data-driven runs: one request set, many inputs via --iteration-data" %}

```bash
{% raw %}newman run orders.postman_collection.json -e local.postman_environment.json \
  --iteration-data cases.csv       # columns become {{variables}} in the requests
# cases.csv:  sku,qty,expected_status
#             A-1,2,201
#             A-1,0,422        # zero quantity must be rejected
#             A-1,99999,422    # over stock must be rejected{% endraw %}
```

The expected value travels in the data too, so a single test can assert
`pm.response.to.have.status(Number(pm.iterationData.get('expected_status')))` and the one request
becomes a table of positive and negative cases.

## Contract and schema validation

Beyond status codes, a test can validate the response *shape* against a JSON Schema — which is how
you turn the metadata and error-format work from earlier appendices into an enforced contract. A
`Problem Details` error body or an order representation can be checked field by field.

```json
"pm.test('error is RFC 9457 Problem Details', () => {",
"  const schema = {",
"    type: 'object',",
"    required: ['type', 'title', 'status'],",
"    properties: {",
"      type:   { type: 'string' },",
"      title:  { type: 'string' },",
"      status: { type: 'integer' }",
"    }",
"  };",
"  pm.expect(pm.response.json()).to.be.jsonSchema(schema);",
"});"
```

Asserting against the schema rather than exact values keeps the test stable as data changes while
still catching a contract break — a removed field, a wrong type, a renamed property — the moment
it appears.

## Newman in CI

The runner exits non-zero when any assertion fails, which is all a pipeline needs to gate a merge.
The services come up on Podman exactly as they do on a laptop — no managed cloud — and Newman runs
against them.

{% include excalidraw.html
   file="27-ci-gate"
   alt="A pipeline: pull request, build image, podman compose up of the order/payment/inventory services, newman run of the collection, then a gate where pass merges and fail blocks. The services run on Podman in CI exactly as on a laptop, and a failed assertion fails the build."
   caption="Figure O.5 — Newman as a merge gate: bring the stack up on Podman, run the collection, fail the build on a broken contract" %}

```yaml
# .github/workflows/api-tests.yml (any runner that has Podman + Node works)
jobs:
  api-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: podman compose up -d           # order, payment, inventory, …
      - run: ./scripts/wait-for-ready.sh     # poll /readyz before testing
      - run: npm i -g newman
      - run: |
          newman run orders.postman_collection.json \
            -e ci.postman_environment.json \
            --reporters cli,junit \
            --reporter-junit-export results/newman.xml
      - uses: actions/upload-artifact@v4      # keep the report even on failure
        if: always()
        with: { name: newman-results, path: results/ }
```

The readiness poll matters: start testing only once the services report ready (the readiness
endpoint from the Observability and Graceful Shutdown material), or the first requests race the
boot and fail spuriously.

## Where Newman fits

Newman is not a replacement for unit tests — it is the layer above them. It owns the
API/contract tier: real HTTP against a running service, fast enough to run on every pull request.

{% include excalidraw.html
   file="27-test-pyramid"
   alt="A test pyramid: a wide base of unit tests (many, fast, cheap), then service/integration tests, then API/contract tests where Newman runs, then a narrow top of E2E tests (few, slow, brittle). Newman owns the API/contract tier and complements unit tests rather than replacing them."
   caption="Figure O.6 — Newman owns the API/contract tier — above unit tests, below full end-to-end" %}

Keep the base of fast unit tests broad, use Newman for the contract and integration behaviour that
only shows up over real HTTP, and reserve a thin layer of full end-to-end tests for the few
journeys that genuinely need the whole system. Pushing everything into Newman makes a slow,
brittle suite; ignoring it leaves the contract untested.

## Negative and authentication testing

The cases that matter most are the ones that are easy to skip. Assert the **failure** paths as
deliberately as the happy path: a `401` with a `WWW-Authenticate` header when the token is missing,
a `403` when it is present but unauthorised, a `409` or `422` on a business-rule violation, and a
`429` carrying `RateLimit` headers when a client exceeds its budget. Confirm idempotency by sending
the same `Idempotency-Key` twice and asserting the second response matches the first rather than
creating a duplicate. These tie the testing appendix back to the error-format, security,
idempotency, and rate-limiting material — a contract is only enforced if its error behaviour is
tested, not just its success behaviour.

## Take-aways and references

Treat the Postman collection as the executable specification of your API, and let Newman run it
headlessly so the same assertions guard every change. Because Newman tests over HTTP, one
collection is the conformance suite for all five implementations. Validate response *shape* against
a schema, not just status codes; drive edge cases from data rather than duplicated requests; and
assert the failure paths as carefully as the happy path. Wire it into CI on plain Podman so the
build fails on a broken contract, and keep Newman in its lane — the API/contract tier, above unit
tests and below a thin end-to-end layer. The canonical references are the Postman documentation and
the Newman command-line documentation (install, reporters, and the `--iteration-data` and
`--bail` flags), and the Postman Learning Center's guides on writing tests with the `pm` API and on
JSON-schema validation.

### Cross-check it yourself

Prove the gate end to end against the running stack. Bring the services up with `podman compose up`,
then `newman run` the orders collection with `--reporters cli,junit` and confirm a green run and a
`newman.xml` you could hand to CI. Now make the contract break on purpose — have the service return
`200` instead of `201` on create, or drop the `id` field — and confirm Newman exits non-zero and
the failing assertion names the exact expectation. Finally, add a negative row to your
`--iteration-data` (a zero-quantity order expecting `422`) and confirm it passes against a correct
service and fails against one that wrongly accepts it. A suite that goes red on a real contract
break, and only then, is the whole value of this appendix.

---
*Verification status: unverified — this is net-new material, not transcribed from the decks, and
the commands have not been run here. Confirm against current releases before publishing: the Newman
CLI flags (`--reporters`, `--reporter-junit-export`, `--iteration-data`, `--bail`,
`--timeout-request`), the `newman-reporter-htmlextra` package name, the `pm` test API
(`pm.response.to.have.status`, `pm.expect`, `pm.collectionVariables`, `pm.iterationData`) and the
`tv4`/`ajv`-backed `jsonSchema` matcher's availability in the current Postman sandbox, and the
GitHub Actions action versions. An `examples/28-newman/` collection plus a `wait-for-ready.sh` runner
against the Podman stack moves this to verified.*
