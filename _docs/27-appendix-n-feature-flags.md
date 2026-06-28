---
title: "Feature Flags & Progressive Delivery"
marker: "N"
label: "Appendix N"
order: 27
part: "Deep-dive appendices"
description: "Decoupling deploy from release with feature flags: the four flag types, evaluating flags with OpenFeature and flagd, targeting and sticky-bucketed percentage rollouts, kill switches, flags as a control plane over the book's patterns, and the lifecycle discipline that keeps flags from becoming debt."
duration: 22 minutes
---

A feature flag is the runtime switch that separates *shipping code* from *releasing a
feature*. Once an artifact is in production, a flag decides — per request, per user, per
cohort — whether the new path is taken. That one decoupling is the spine of progressive
delivery: you deploy continuously and dark, then release gradually and reversibly, with no
redeploy on the critical path of either the rollout or the rollback. This appendix covers the
flag types, how to evaluate flags in a vendor-neutral, open-source way with OpenFeature and
flagd, how targeting and percentage rollouts work, and the lifecycle discipline that keeps
flags from turning into permanent debt.

## Deploy is not release

The reframe that makes everything else work: **deploying an artifact and releasing a feature
are different events**, and a flag is what splits them.

{% include excalidraw.html
   file="26-deploy-release"
   alt="A pipeline: build and deploy with the flag off, then release to 1% with the flag on, then ramp the percentage, then GA at 100%, then retire the flag. The deploy is decoupled from the release; every release and rollback is a config change, not a new deploy."
   caption="Figure N.1 — Deploy ships the code dark; release is a runtime flag flip — and so is rollback" %}

The artifact ships to production with the new path turned off — a non-event, observable only in
the deploy log. Releasing is then a runtime flag flip: on for 1%, then a wider cohort, then
everyone, each step reversible by narrowing the flag rather than rolling back a deployment. This
is what lets a team merge to main many times a day yet release on its own cadence, and it is the
mechanism behind every canary and every safe cutover in the book.

## Four kinds of flag

"Feature flag" covers four genuinely different tools, and conflating them is the root of most
flag messes. They differ along two axes — how long the flag lives, and who decides to flip it.

{% include excalidraw.html
   file="26-flag-types"
   alt="A two-by-two of flag types by lifetime and owner: release flags (short-lived, dev-owned, ship dark and remove); experiment/A-B flags (short-lived, data-owned, split variants and measure); ops/kill-switch flags (long-lived, SRE-owned, disable a feature or dependency fast); permission/entitlement flags (long-lived, product-owned, gate by plan or tier)."
   caption="Figure N.2 — Four flag types by lifetime and owner — each wants different defaults and lifecycle" %}

**Release flags** are temporary and developer-owned: they exist to ship new code dark, ramp it,
and then be removed. **Experiment (A/B) flags** are temporary and data-owned: they split traffic
across variants so a metric can be measured, and they *require* sticky assignment. **Ops /
kill-switch flags** are long-lived and SRE-owned: a permanent control to disable a feature or a
dependency fast under load or incident. **Permission / entitlement flags** are long-lived and
product-owned: they gate functionality by plan, tier, or region, and are really part of the
product model rather than a rollout. The defaults differ too: a release flag fails *off* (new
code stays dark if the flag system is unreachable), while a kill-switch usually fails *on* (the
feature stays available unless someone deliberately kills it).

## Evaluating a flag: OpenFeature and flagd

Evaluation should not couple your code to a vendor. **OpenFeature** is the CNCF vendor-neutral
API standard — one SDK surface across languages — and **flagd** is its lightweight open-source
backend that evaluates flags from a file, ConfigMap, or synced source, in-cluster. Together they
keep the whole feature-flag story open-source and running on plain Kubernetes, with no managed
SaaS, consistent with the rest of this book; swapping flagd for another provider later is a
configuration change, not a code change.

{% include excalidraw.html
   file="26-evaluation-architecture"
   alt="A request carrying user, plan, and region reaches the application, which calls getBooleanValue(flag, default, context) through the OpenFeature SDK; the flagd provider evaluates locally in-cluster against a flag source (ConfigMap, file, or sync). The default is returned if the provider is unreachable, so a flag-system outage never takes the app down, and the SDK is vendor-neutral."
   caption="Figure N.3 — OpenFeature SDK + flagd: local evaluation, vendor-neutral, fail-safe to the default" %}

The two properties that matter most: evaluation returns the **default** if the provider is
unreachable — a flag-system outage must never take the application down — and the SDK is
**vendor-neutral**, so the app calls `getBooleanValue(flag, default, context)` and never names
the backend. The evaluation *context* carries the targeting inputs (a stable targeting key plus
attributes like plan and region) that the rules act on.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// build.gradle: dev.openfeature:sdk, dev.openfeature.contrib.providers:flagd
@Configuration
public class FeatureFlags {
    @Bean
    Client openFeatureClient() {
        OpenFeatureAPI api = OpenFeatureAPI.getInstance();
        api.setProviderAndWait(new FlagdProvider(            // flagd, in-cluster
            FlagdOptions.builder().host("flagd").port(8013).build()));
        return api.getClient();
    }
}

@RestController
@RequestMapping("/checkout")
public class CheckoutController {
    private final Client flags;
    public CheckoutController(Client flags) { this.flags = flags; }

    @PostMapping
    public Receipt checkout(@RequestBody Cart cart,
                            @RequestHeader("X-User") String userId) {
        EvaluationContext ctx = new MutableContext(userId)   // targeting key
            .add("plan", cart.plan()).add("region", cart.region());
        boolean useNew = flags.getBooleanValue("new-checkout", false, ctx);  // default off
        return useNew ? newCheckout(cart) : legacyCheckout(cart);
    }
}
```

```java
// pom.xml: quarkus-openfeature + the flagd provider
// application.properties:
//   quarkus.openfeature.flagd.host=flagd
//   quarkus.openfeature.flagd.port=8013
@Path("/checkout")
public class CheckoutResource {
    @Inject Client flags;                          // OpenFeature client, CDI-provided

    @POST
    public Receipt checkout(Cart cart, @HeaderParam("X-User") String userId) {
        EvaluationContext ctx = new MutableContext(userId)
            .add("plan", cart.plan()).add("region", cart.region());
        boolean useNew = flags.getBooleanValue("new-checkout", false, ctx);  // default off
        return useNew ? newCheckout(cart) : legacyCheckout(cart);
    }
}
```

```csharp
// dotnet add package OpenFeature OpenFeature.Contrib.Providers.Flagd
// Program.cs — set the provider once at startup
await Api.Instance.SetProviderAsync(new FlagdProvider(new Uri("http://flagd:8013")));

[ApiController, Route("checkout")]
public class CheckoutController : ControllerBase
{
    private readonly FeatureClient _flags = Api.Instance.GetClient();

    [HttpPost]
    public async Task<Receipt> Checkout(
        Cart cart, [FromHeader(Name = "X-User")] string userId)
    {
        var ctx = EvaluationContext.Builder()
            .SetTargetingKey(userId)                       // sticky key
            .Set("plan", cart.Plan).Set("region", cart.Region).Build();
        var useNew = await _flags.GetBooleanValueAsync("new-checkout", false, ctx);
        return useNew ? NewCheckout(cart) : LegacyCheckout(cart);
    }
}
```

```python
# pip install openfeature-sdk openfeature-provider-flagd
from openfeature import api
from openfeature.contrib.provider.flagd import FlagdProvider
from openfeature.evaluation_context import EvaluationContext

api.set_provider(FlagdProvider(host="flagd", port=8013))   # once, at startup
flags = api.get_client()

@app.post("/checkout")
async def checkout(cart: Cart, x_user: str = Header()):
    ctx = EvaluationContext(
        targeting_key=x_user,                              # sticky key
        attributes={"plan": cart.plan, "region": cart.region})
    use_new = flags.get_boolean_value("new-checkout", False, ctx)  # default off
    return await (new_checkout(cart) if use_new else legacy_checkout(cart))
```

```cpp
{% raw %}// OpenFeature C++ SDK + flagd. If the SDK is unavailable, call flagd's gRPC
// ResolveBoolean directly via grpc++ — same evaluation, more boilerplate.
#include <openfeature/openfeature.h>
using namespace openfeature;

// once, at startup
getApi().setProvider(std::make_unique<FlagdProvider>(
    FlagdOptions{.host = "flagd", .port = 8013}));
auto flags = getApi().getClient();

Task<> Checkout::post(HttpRequestPtr req, auto cb) {
  auto cart = req->bodyJson();
  EvaluationContext ctx{ req->getHeader("X-User"),          // targeting key
                         {{"plan", cart["plan"]}, {"region", cart["region"]}} };
  bool use_new = flags->getBooleanValue("new-checkout", false, ctx);  // default off
  co_await (use_new ? new_checkout(cart) : legacy_checkout(cart));
  cb(json_response({{"ok", true}}));
}{% endraw %}
```

```go
// OpenFeature Go SDK + flagd
func init() { // once, at startup
	_ = openfeature.SetProviderAndWait(
		flagd.NewProvider(flagd.WithHost("flagd"), flagd.WithPort(8013)))
}

var flags = openfeature.NewClient("checkout")

func checkout(w http.ResponseWriter, r *http.Request) {
	cart := parseCart(r)
	evalCtx := openfeature.NewEvaluationContext(
		r.Header.Get("X-User"), // sticky targeting key
		map[string]any{"plan": cart.Plan, "region": cart.Region})
	useNew, _ := flags.BooleanValue( // default off
		r.Context(), "new-checkout", false, evalCtx)
	if useNew {
		newCheckout(w, r, cart)
	} else {
		legacyCheckout(w, r, cart)
	}
}
```

The crucial thing to notice: the application code is the *same* one line regardless of whether
the flag is a simple on/off, a per-plan entitlement, or a 5% rollout. All of that lives in the
flag's configuration, not the code.

## Targeting, segmentation, and sticky rollouts

Because the rules live in flagd, changing *who* sees a feature never touches the application. A
flagd flag definition is a set of variants, a default, and a targeting expression. Two operators
do most of the work: a conditional for segmentation (by plan, region, or any context attribute),
and a `fractional` operator for percentage rollouts.

```json
{
  "flags": {
    "new-checkout": {
      "state": "ENABLED",
      "variants": { "on": true, "off": false },
      "defaultVariant": "off",
      "targeting": {
        "if": [
          { "==": [ { "var": "plan" }, "enterprise" ] }, "on",
          { "fractional": [
              { "var": "targetingKey" },
              [ "on", 25 ],
              [ "off", 75 ]
          ] }
        ]
      }
    },
    "payments-v2": {
      "state": "DISABLED",
      "variants": { "on": true, "off": false },
      "defaultVariant": "off"
    }
  }
}
```

This single definition does three things at once: enterprise-plan users always get the new
checkout (an *entitlement*), everyone else is split 25/75 (a *rollout*), and a second flag is
turned off entirely (a *kill switch*, via `state`). The `fractional` operator buckets on the
`targetingKey`, which is what gives **sticky assignment** — the same user hashes to the same
bucket every time.

{% include excalidraw.html
   file="26-progressive-rollout"
   alt="A stable userId is hashed into a bucket 0 to 99; the flag returns the new variant if the bucket is below the rollout threshold (5, then 25, then 100) and the old variant otherwise. The same user always lands in the same bucket, so assignment is consistent across repeat visits, and widening or narrowing the threshold ramps or rolls back instantly without a deploy."
   caption="Figure N.4 — Percentage rollout via sticky bucketing: consistent per-user assignment, instant ramp and rollback" %}

Sticky bucketing matters for two reasons. For a **rollout**, it prevents flicker — a user who
got the new checkout on their first visit keeps getting it, rather than bouncing between variants
on refresh. For an **experiment**, it is a correctness requirement — a user must stay in one arm
of the test for the measurement to mean anything. Ramping the rollout is editing the `25` upward;
rolling back is editing it down — both take effect in the running fleet within flagd's sync
interval, with no redeploy.

## The kill switch

A kill switch is the operational flag you reach for during an incident: wrap a risky or expensive
dependency in a flag so it can be disabled instantly without a deploy. It is the deliberate,
human-driven complement to the circuit breaker from the Failure Modes appendix — the breaker
trips automatically on errors; the kill switch is flipped on purpose.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// Ops kill-switch — default TRUE (fail open): the feature stays on unless killed.
public Recommendations recommend(String userId) {
    if (!flags.getBooleanValue("recommendations-enabled", true, ctx(userId)))
        return Recommendations.empty();          // shed the feature, still serve the page
    return recommendationClient.fetch(userId);   // pairs with a circuit breaker
}
```

```java
public Recommendations recommend(String userId) {
    if (!flags.getBooleanValue("recommendations-enabled", true, ctx(userId)))
        return Recommendations.empty();          // degrade gracefully
    return recommendationClient.fetch(userId);   // pairs with a circuit breaker
}
```

```csharp
public async Task<Recommendations> Recommend(string userId)
{
    // default true → fail open: only an explicit kill turns it off
    if (!await _flags.GetBooleanValueAsync("recommendations-enabled", true, Ctx(userId)))
        return Recommendations.Empty;            // serve the page without it
    return await _recs.FetchAsync(userId);       // pairs with a circuit breaker
}
```

```python
async def recommend(user_id: str) -> Recommendations:
    # default True → fail open: the feature stays on unless deliberately killed
    if not flags.get_boolean_value("recommendations-enabled", True, ctx(user_id)):
        return Recommendations.empty()           # degrade gracefully
    return await recommendation_client.fetch(user_id)   # pairs with a breaker
```

```cpp
Task<Recommendations> recommend(const std::string& user_id) {
  // default true → fail open: only an explicit kill disables it
  if (!flags->getBooleanValue("recommendations-enabled", true, ctx(user_id)))
    co_return Recommendations::empty();          // serve the page without it
  co_return co_await recs_.fetch(user_id);       // pairs with a circuit breaker
}
```

```go
func recommend(ctx context.Context, userID string) (Recommendations, error) {
	// default true → fail open: only an explicit kill disables it
	on, _ := flags.BooleanValue(ctx, "recommendations-enabled", true, ctxFor(userID))
	if !on {
		return Recommendations{}, nil // serve the page without it
	}
	return recsClient.Fetch(ctx, userID) // pairs with a circuit breaker
}
```

Note the default flips with the flag type: a release flag defaults *off* so half-shipped code
stays dark, while this kill switch defaults *on* so the feature survives a flag-system outage and
only a deliberate flip removes it.

## Flags over the patterns you already have

Feature flags are not a new subsystem so much as a runtime control plane over patterns already in
this book. The same decoupling expresses several of them.

{% include excalidraw.html
   file="26-flags-control-plane"
   alt="A flag control plane (flagd) sits at the centre with four spokes: a kill-switch disables a dependency (pairing with the circuit breaker), a canary combines a flag with L7 routing, a strangler cutover routes a percentage to a new service, and an experiment picks a sticky-bucketed variant."
   caption="Figure N.5 — A flag is a runtime control surface — the same lever behind canaries, cutovers, kill-switches, and experiments" %}

A **canary** is a percentage flag deciding which build a request exercises, often paired with the
L7 routing from the routing appendix. A **strangler-fig cutover** is a flag (or the proxy's
percentage) steering a widening slice from the monolith to the extracted service. A **saga step**
can be guarded by a flag to switch a new compensation path on cautiously. And an **experiment** is
a sticky-bucketed variant flag with a metric attached. Recognising flags as the control surface
for all of these keeps you from building a bespoke mechanism for each.

## The flag lifecycle and its tech debt

The failure mode of feature flags is not technical, it is organisational: flags that are never
removed. Every flag is a branch in your code and a dimension in your test matrix, and a stale one
is dead code, a hidden conditional, and a live risk surface that nobody remembers the meaning of.

{% include excalidraw.html
   file="26-flag-lifecycle"
   alt="A lifecycle: create the flag default off, roll it out from 0 to 100 percent with targeting, reach GA fully on, then remove the flag and its dead code. Every release flag is born with a removal ticket because a stale flag is dead code, a hidden branch, and a live risk surface."
   caption="Figure N.6 — The flag lifecycle: a release flag is born with a removal ticket" %}

The discipline that keeps it healthy: give every *release* flag an owner and an expiry from the
moment it is created, and treat removing it as part of finishing the feature, not optional
cleanup. Long-lived ops and entitlement flags are exempt — they are permanent by design — which
is exactly why distinguishing the four types matters. A short-lived flag that has reached 100%
for two weeks should be deleted along with the branch it guarded.

## Testing, observing, and anti-patterns

A flag multiplies the states your system can be in, so test **both** sides of every flag you
depend on (a test suite that only exercises the default path will not catch a bug behind the
flag), keep the number of *simultaneously interacting* flags small, and default flags off in test
environments unless a test sets them deliberately. Observability ties flags back to the
Observability chapter: record the resolved variant as a span attribute and a metric label, so a
latency or error change can be attributed to a specific flag and cohort — "the new checkout's p99
is worse for the 25% on `on`" is only visible if the variant is on the telemetry. The recurring
anti-patterns to avoid are using flags as a general configuration store (they are for *release
control*, not for tuning timeouts), letting release flags become permanent, stacking many flags
whose combinations no one reasons about, running experiments without sticky assignment (the data
is meaningless), and putting real business logic inside flag rules instead of in code.

## Take-aways and references

Decouple deploy from release: ship dark, release gradually, roll back by narrowing a flag.
Distinguish the four flag types, because they want different owners, defaults, and lifecycles.
Evaluate through a vendor-neutral SDK (OpenFeature) against an open-source backend (flagd), always
with a safe default so a flag outage cannot take the app down. Keep targeting and rollout rules in
configuration, not code, and make percentage rollouts sticky. Treat release flags as debt with a
removal ticket attached, and put the resolved variant on your telemetry. The canonical references
are the OpenFeature specification and the flagd documentation (the CNCF projects this appendix
builds on), Pete Hodgson's "Feature Toggles" article on martinfowler.com (the standard taxonomy of
flag types), and the *Accelerate* / DORA research (Forsgren, Humble, Kim) for the deploy-versus-release
distinction and progressive delivery; Unleash is a capable open-source alternative backend behind
the same OpenFeature SDK.

### Cross-check it yourself

Prove the three properties this appendix rests on, against a running flagd. **Decoupling:** with
the service running, edit the `new-checkout` flag in flagd's source from `off` to a 25% fractional
rule and confirm the running fleet changes behaviour within the sync interval — no redeploy, and
narrowing it back is your rollback. **Sticky assignment:** call the endpoint repeatedly with the
same `X-User` and confirm it always resolves the same variant, then sweep many distinct users and
confirm the split lands near 25%. **Fail-safe:** stop flagd entirely and confirm every evaluation
returns the coded default and the service keeps serving `200`s — if it instead errors, a flag
lookup is on a critical path without a default, which is the one feature-flag mistake you cannot
ship.

---
*Verification status: unverified — this is net-new material, not transcribed from the decks, and
the code has not been run. Confirm against current releases before publishing: the OpenFeature SDK
surface per language (provider registration, `EvaluationContext` construction, the
`getBooleanValue`/`GetBooleanValueAsync`/`get_boolean_value` signatures), the flagd provider package
names and default port, and the flagd flag-definition schema (`state`, `variants`, `targeting`, and
the `fractional` operator's argument shape). The C++ path is the least certain: the OpenFeature C++
SDK is the youngest of the five, so if its API differs or it is unavailable, evaluate by calling
flagd's gRPC `ResolveBoolean` directly via grpc++ — the same evaluation with more boilerplate. An
`examples/27-feature-flags/` runner against a real flagd moves this to verified.*
