"""S12 fix round A: the rules fixA_build.py turns into fixup ops (see that file).

base_ops(d)    validator inputs in _plans/s12-manifest/fixA/ (Quarkus Q.fix1 + Q.fix2, capsfix)
content_ops(d) figure, code accuracy, notes drift, advisory and polish ops; a replace without
               sldIds and with "locate": true is placed on every slide/notes body where it matches
               (0 matches is allowed); "code_subst" is turned into a set_code of the box's lines
caps_pairs(d)  (find, repl, sldIds or None) pairs that lower-case ALL-CAPS emphasis or remove a
               soft positional reference; located the same way
"""
import json
from pathlib import Path

FIXA = Path(__file__).resolve().parent.parent / "fixA"
PNG = "lgtm-presentation/edits/png"


def _load(fn):
    return json.loads((FIXA / fn).read_text())["ops"]


def base_ops(d):
    if d == "Quarkus":
        return ([("Q.fix1", o) for o in _load("quarkus-q.fix1.json")]
                + [("Q.fix2", o) for o in _load("quarkus-q.fix2.json")])
    return [("capsfix", o) for o in _load(f"{d}.capsfix.json")]


def loc(find, repl, cat, why, scope=None):
    o = {"op": "replace", "locate": True, "find": find, "repl": repl, "cat": cat, "_why": why}
    if scope:
        o["scope"] = scope
    return o


# replace ops located in every deck where the text exists
COMMON_CONTENT = [
    # advisory: OAuth2 Proxy (and Pomerium's open-source core) do not assess device posture
    loc("validate identity (OAuth/OIDC against your IdP), check device posture, then issue a JWT",
        "validate identity (OAuth/OIDC against your IdP), apply the route's access policy, then issue a JWT",
        "code", "OAuth2 Proxy has no device-posture check; the proxies enforce per-route identity policy"),
    loc("validate identity (OIDC against your IdP), check device posture, issue a JWT",
        "validate identity (OIDC against your IdP), apply the route's access policy, issue a JWT",
        "code", "OAuth2 Proxy has no device-posture check (C++ slide wording)"),
    loc("validates identity against your IdP (OIDC), checks device posture, and issues a JWT",
        "validates identity against your IdP (OIDC), applies the route's access policy, and issues a JWT",
        "code", "OAuth2 Proxy has no device-posture check"),
    # advisory: vendor framework citation -> vendor-neutral reference already used in the decks' family
    loc("; Microsoft Cloud Adoption Framework: security patterns.", "; OWASP Microservices Security Cheat Sheet.",
        "stack", "vendor-neutral reference (decision 7)"),
    # notes / caption drift ("persisted FAILED state" and the header-injection caption are in the capsfix files)
]

DECK_CONTENT = {
    "Python": [
        loc("Semaphore(50))", "Semaphore(5))", "code", "examples/12-security/python BULKHEAD_LIMIT = 5"),
        loc("# 50 concurrent requests per tenant;", "# 5 concurrent requests per tenant;", "code", "bulkhead 5"),
        loc("once 50 are running", "once 5 are running", "code", "bulkhead 5"),
    ],
    "Spring": [
        loc("tracer.start_span(...), span.set_attribute(...), span.add_event(...)", "tracer.spanBuilder(...).startSpan(), span.setAttribute(...), span.addEvent(...)", "code", "OpenTelemetry Java API names, not Python's", "slide"),
        loc("// 50 by default", "// maxConcurrentCalls: 5", "code",
            "examples/12-security/spring-boot CAPACITY = 5; Resilience4j's own default is 25, not 50"),
    ],
    "DotNet": [
        loc("tracer.start_span(...), span.set_attribute(...), span.add_event(...)", "activitySource.StartActivity(...), activity.SetTag(...), activity.AddEvent(...)", "code", "System.Diagnostics Activity API (OpenTelemetry .NET), not Python's", "slide"),
        loc("new SemaphoreSlim(20));  // 20 / tenant", "new SemaphoreSlim(5));   // 5 / tenant", "code",
            "examples/12-security/dotnet bulkheadLimit = 5"),
        loc("its own twenty slots", "its own five slots", "code", "bulkhead 5"),
        loc('app.MapHealthChecks("/healthz/live",  new()', 'app.MapHealthChecks("/healthz", new()', "code",
            "examples/01-cloud-native-principles/dotnet maps /healthz and /readyz"),
        loc('app.MapHealthChecks("/healthz/ready", new()', 'app.MapHealthChecks("/readyz",  new()', "code",
            "examples/01-cloud-native-principles/dotnet maps /healthz and /readyz"),
        loc("// /healthz/ready → 503", "// /readyz → 503", "code",
            "examples/21-graceful-shutdown/dotnet maps /readyz"),
        loc("Map health checks at /healthz/live and /healthz/ready;", "Map health checks at /healthz and /readyz;", "code",
            "the examples' probe paths"),
        loc('s.Status = "FAILED";', 's.Status = "COMPENSATED";', "code",
            "examples/17-sagas/dotnet ends a compensated saga in COMPENSATED (the notes say so after capsfix)"),
    ],
    "Go": [
        loc("make(chan struct{}, 20)) // 20 per tenant", "make(chan struct{}, 5))  // 5 per tenant", "code",
            "examples/12-security/go bulkheadCapacity = 5"),
        loc("at most 20 requests per tenant", "at most 5 requests per tenant", "code", "bulkhead 5"),
    ],
    "Cpp": [
        loc("std::make_unique<Sem>(50));     // 50 / tenant", "std::make_unique<Sem>(5));      // 5 / tenant", "code",
            "examples/12-security/cpp CAPACITY = 5"),
        loc("50 concurrent requests per tenant", "5 concurrent requests per tenant", "code", "bulkhead 5"),
    ],
    "Quarkus": [
        loc("tracer.start_span(...), span.set_attribute(...), span.add_event(...)", "tracer.spanBuilder(...).startSpan(), span.setAttribute(...), span.addEvent(...)", "code", "OpenTelemetry Java API names, not Python's", "slide"),
        {"op": "code_subst", "sldId": 298, "cat": "code",
         "_why": "Kafka Streams: the windowed Double result needs explicit serdes on .to(...)",
         "subst": [["    StreamsBuilder b = new StreamsBuilder();",
                    ["    StreamsBuilder b = new StreamsBuilder();",
                     "    var windowSerde = WindowedSerdes.timeWindowedSerdeFrom(String.class, 300_000L);"]],
                   ["     .to(\"revenue.by-merchant\");",
                    ["     .to(\"revenue.by-merchant\", Produced.with(windowSerde, Serdes.Double()));"]]]},
    ],
}

FIGURE = {  # the outbox figure whose heading said "Dual-write is a lie"
    "Python": (286, "Google Shape;349;p33", "04-dual-write-outbox.png"),
    "Quarkus": (286, "Google Shape;349;p33", "04-dual-write-outbox.png"),
    "Spring": (286, "Google Shape;349;p33", "04-dual-write-outbox.png"),
    "DotNet": (288, "Google Shape;370;p35", "04-dual-write-outbox.png"),
    "Go": (286, "Google Shape;349;p33", "04-dual-write-outbox.png"),
    "Cpp": (286, "Google Shape;349;p33", "04-dual-write-outbox-cpp.png"),
}

TOPOLOGY = {"Python": 531, "Spring": 535, "DotNet": 562, "Go": 531, "Cpp": 531}  # Quarkus: Q.fix2


def _polish(d):
    ops = [
        loc("Event-driven tools landscape  —  Kafka", "Event-driven tools landscape — Kafka", "voice",
            "title spacing (one space around the dash, as the other titles)", "slide"),
        loc("Valet key  —  scoped", "Valet key — scoped", "voice", "title spacing (Q.fix2 in Quarkus)", "slide"),
        loc("Glossary of acronyms  (1 of 2)  —  protocols", "Glossary of acronyms (1 of 2) — protocols", "voice",
            "title spacing, as the (2 of 2) title", "slide"),
    ]
    if d in TOPOLOGY:
        ops.append({"op": "set_geometry", "sldId": TOPOLOGY[d], "shape": "Image 1", "x": 2.16, "y": 1.95,
                    "w": 9.01, "h": 4.30, "cat": "fit",
                    "_why": "Appendix R topology figure enlarged to the free area, as Q.fix2 does in Quarkus"})
    return ops


def content_ops(d):
    sid, shape, png = FIGURE[d]
    ops = [{"op": "replace_picture", "sldId": sid, "shape": shape, "png": f"{PNG}/{png}", "cat": "voice",
            "_why": "figure heading 'Dual-write is a lie' -> 'Dual-write is unsafe' (src/04-dual-write-outbox.svg)"}]
    ops += COMMON_CONTENT + DECK_CONTENT.get(d, []) + _polish(d)
    return [("content", o) for o in ops]


def P(find, repl):
    return (find, repl, None)


COMMON_CAPS = [
    P("a field with a NEW number", "a field with a new number"),
    P("SAFE: brand-new field", "safe: brand-new field"),
    P("SAFE: new field; old clients", "safe: new field; old clients"),
    P("BREAKING (don't)", "breaking (don't)"),
    P("per-POD state", "per-pod state"),
    P("per-POD registry", "per-pod registry"),
    P("IDENTIFY: pick", "Identify: pick"),
    P("MOVE: build", "Move: build"),
    P("caches THAT — the canonical value", "caches that row — the canonical value"),
    P("because you DO want", "because you do want"),
    P("stops sending NEW traffic", "stops sending new traffic"),
    P("an EXPLICIT timeout", "an explicit timeout"),
    P("a DIFFERENT, denormalised", "a different, denormalised"),
    P("nulls THIS field only", "nulls this field only"),
    P("fail readiness FIRST", "fail readiness first"),
    P("deliberately NOT writing to cache", "no cache write here"),
    P("Retry ONLY idempotent calls", "Retry only idempotent calls"),
    P("Do NOT decorate a non-idempotent POST", "Do not decorate a non-idempotent POST"),
    P("Do NOT retry a non-idempotent POST", "Do not retry a non-idempotent POST"),
    P("flip to NOT ready while draining", "flip to not-ready while draining"),
    P("// NOT write store", "// read store only"),
    P("projections AND the outbox pattern (covered next) work", "projections and the outbox pattern work"),
    P("plain Java that LOOKS synchronous", "plain Java that looks synchronous"),
    P("workflow-local variable AND in Temporal's", "workflow-local variable and in Temporal's"),
    P("always invokes the method AND writes", "always invokes the method and writes"),
    P("Always runs the method body AND writes", "Always runs the method body and writes"),
    P("the constraint AND eventual durability is acceptable AND you", "the constraint, eventual durability is acceptable and you"),
    P("is the constraint AND eventual durability is acceptable.", "is the constraint and eventual durability is acceptable."),
    P("only ONE instance flushes", "only one instance flushes"),
    P("only ONE flusher Pod", "only one flusher Pod"),
    P("only ONE Pod refreshing", "only one Pod refreshing"),
    P("ALWAYS pair retry with a breaker", "always pair retry with a breaker"),
    P("Pods — OR ", "Pods — or "),
    # .NET
    P("SCALING THE BLAZOR SERVER POOL", "scaling the Blazor Server pool"),
    P("this REPLACES the MSDTC", "this replaces the MSDTC"),
    P("this REPLACES the old MSDTC", "this replaces the old MSDTC"),
    P("'save the order AND queue the event'", "'save the order and queue the event'"),
    P("this is THE most important pattern", "this is the most important pattern"),
    P("You DON'T want one", "You don't want one"),
    P("write the state change AND an outbox row in ONE local", "write the state change and an outbox row in one local"),
    P("server-side WITHOUT persisting it", "server-side without persisting it"),
    P("your .NET Pods talk TO", "your .NET Pods talk to"),
    P("SET, not REMOVE", "set, not remove"),
    P("on all OTHER Pods", "on all other Pods"),
    P("read STILL returns", "read still returns"),
    P("when EITHER the caller", "when either the caller"),
    P("backoff WITH jitter", "backoff with jitter"),
    P("IDistributedCache  OR  + FusionCache", "IDistributedCache or FusionCache"),
    P("sorted set  OR  FusionCache", "sorted set or FusionCache"),
    # soft positional references
    P(" and give you the mesh CRDs we'll see next.", " and give you the mesh CRDs (VirtualService, DestinationRule)."),
    P("Pair with a circuit breaker (next slides) so a down dep stops retries entirely.",
      "Pair with a circuit breaker so a down dependency stops retries entirely."),
    P("Strength is a ladder we'll see next (intrusive to contract).", "Strength is a ladder (intrusive to contract)."),
    P(" (write-through, covered later in this appendix)", " (write-through)"),
    P("(and the one we'll see code for)", "(and the one the code models)"),
    P("the scaling problem the following slides solve with a Redis backplane",
      "the scaling problem a Redis backplane solves"),
    P("The next slides cover each with code; the final matrix maps patterns to modes.",
      "Each one gets code, and a matrix maps patterns to modes."),
    P("The next slides cover three ways to do the redirect:", "There are three ways to do the redirect:"),
    P("The next slides give each its own diagram and per-language code", "Each gets its own diagram and per-language code"),
    P("The next slides give you a decision rule and then show each protocol in code",
      "The section gives a decision rule and then shows each protocol in code"),
    P("ties back to the stickiness point covered earlier.", "ties back to the session-affinity trade-off."),
    P("payload modification that we'll see more of — the L7 router", "payload modification — the L7 router"),
    P("state, which is the next section.", "state, the subject of stream processing."),
    P("that the next slides alternate between pattern-and-implementation pairs",
      "that the section alternates between pattern-and-implementation pairs"),
]

CPP_CAPS = [
    P("NO in-process", "no in-process"),
    P("parsed ONCE in main()", "parsed once in main()"),
    P("configured ONCE per artifact", "configured once per artifact"),
    P("Set ONCE at the edge", "Set once at the edge"),
    P("Push the aggregation OUT to the edge", "Push the aggregation out to the edge"),
    P("things to design OUT of a C++ service", "things to design out of a C++ service"),
    P("writes the row AND an outbox row", "writes the row and an outbox row"),
    P("write state AND an outbox row", "write state and an outbox row"),
    P("Event STREAMING means", "Event streaming means"),
    P("are TRANSPORTED", "are transported"),
    P("use event STREAMING (with", "use event streaming (with"),
    P("There is NO first-class Temporal C++ SDK", "There is no first-class Temporal C++ SDK"),
    P("as ACTIVITIES, invoked", "as activities, invoked"),
    P("for THIS tenant?", "for this tenant?"),
    P("// BATCH, not Simple", "// batch, not simple"),
    P("To FILTER traces", "To filter traces"),
    P("ONE trace_id binds", "One trace_id binds"),
    P("ESSENTIAL: stops", "Essential: stops"),
    P("audit logging UNIFORMLY across", "audit logging uniformly across"),
    P("uploading a file THROUGH the C++", "uploading a file through the C++"),
    P("lives in YOUR logs", "lives in your logs"),
    P("record WHO made each request", "record who made each request"),
    P("and WHAT they were", "and what they were"),
    P("are a SEPARATE bulkhead", "are a separate bulkhead"),
    P("use the field NAMES for accessor", "use the field names for accessor"),
    P("for any tag number AND name", "for any tag number and name"),
    P("stubs are BUILD output", "stubs are build output"),
    P("// THIS pod now owns this user", "// this pod now owns the user"),
    P("when ANY pod wants", "when any pod wants"),
    P("produce IDENTICAL output", "produce identical output"),
    P("a STABLE machine code", "a stable machine code"),
    P("you've LOST the record", "you've lost the record"),
    P("Other fields STILL RETURN", "Other fields still return"),
    P("clients ALL retry now", "clients all retry now"),
    P("the LANGUAGE to talk about WHERE service", "the language to talk about where service"),
    P("business: CORE (your", "business: core (your"),
    P("goes), SUPPORTING (necessary", "goes), supporting (necessary"),
    P("shipping), GENERIC (commoditised", "shipping), generic (commoditised"),
    P("Inside the context, ONE model.", "Inside the context, one model."),
    P("boundaries SHOULD match", "boundaries should match"),
    P("published language for ALL consumers", "published language for all consumers"),
    P("published TO?", "published to?"),
    P("injection by REFERENCE, not", "injection by reference, not"),
    P("An AGGREGATE is a consistency", "An aggregate is a consistency"),
    P("stay within ONE aggregate", "stay within one aggregate"),
    P("through DOMAIN EVENTS (asynchronously", "through domain events (asynchronously"),
    P("name what BUSINESS-LEVEL happened", "name what happened at the business level"),
    P("framing is BALANCED coupling", "framing is balanced coupling"),
    P("change TOGETHER need", "change together need"),
    P("shared database: AVOID.", "shared database: avoid."),
    P("services have INDEPENDENT volatility", "services have independent volatility"),
    P("by REAL DDD-bounded contexts and INDEPENDENT volatility", "by real DDD-bounded contexts and independent volatility"),
    P("Two things that DO change together", "Two things that do change together"),
    P("are MODERATE strength", "are moderate strength"),
    P("are LOW strength on read", "are low strength on read"),
    P("but MODERATE on write paths", "but moderate on write paths"),
    P("are LOWEST strength", "are lowest strength"),
    P("stubs are GENERATED C++", "stubs are generated C++"),
    P("in one service is FREE", "in one service is free"),
    P("between modules is FREE", "between modules is free"),
    P("Kubernetes ASSUMES this", "Kubernetes assumes this"),
    P("Fail readiness FIRST.", "Fail readiness first."),
    P("start the countdown EARLY", "start the countdown early"),
    P("continue on OTHER pods", "continue on other pods"),
    P("should have ONE shutdown coordinator", "should have one shutdown coordinator"),
    P("Failing it RESTARTS the pod", "Failing it restarts the pod"),
    P("and TEST it under load", "and test it under load"),
    P("happens WITHOUT modifying your binary", "happens without modifying your binary"),
    P("a unit of DEPLOYMENT, not", "a unit of deployment, not"),
    P("splitting the data FIRST while", "splitting the data first while"),
    P("(1) IDENTIFY the seam", "(1) Identify the seam"),
    P("(2) MOVE — implement", "(2) Move — implement"),
    P("a USEFUL INTERMEDIATE state", "a useful intermediate state"),
    P("is often FASTER and more", "is often faster and more"),
    P("health to OBSERVED traffic", "health to observed traffic"),
    P("shutdown IS a failure mode", "shutdown is a failure mode"),
    P("How to SEE the failure modes", "How to see the failure modes"),
    P("reads the payload AND business context", "reads the payload and business context"),
]


def caps_pairs(d):
    return COMMON_CAPS + (CPP_CAPS if d == "Cpp" else [])
