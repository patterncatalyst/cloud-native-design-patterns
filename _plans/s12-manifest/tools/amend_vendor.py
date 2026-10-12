#!/usr/bin/env python3
"""Apply user decision 7 (plan, 2026-10-12): vendor-neutral language decks.

- No Appendix S (OpenShift Local) slides: the clone_slide / set_* ops of S are dropped, the agenda says
  "Appendix R" only, and the Appendix R notes no longer point at OpenShift Local.
- No AWS, Azure, Google Cloud or other managed-service framing: valet key and claim check follow
  examples/12-security/<lang> (a ticket the service signs and verifies itself; a generic object store),
  and every other vendor mention is rewritten vendor-neutrally.
- OpenShift mentions outside Appendix S are rewritten to generic Kubernetes.

Run order: amend_decisions.py, then this script (it removes its own ops, tagged "_vendor", and re-inserts
them just before the first agenda / Appendix R op, so they see the text after every earlier op).
Replace ops find their slides and counts in the pre-decision-7 text copies, BASE/<deck>.md (the
verify_all.py output of the edit files at 39a5b1e), default M/work/vendor-base.

    python3 amend_vendor.py [M]
"""
import json
import re
import sys
from pathlib import Path

REPO = Path("~/Dev/cloud-native-design-patterns")
EDITS = REPO / "lgtm-presentation" / "edits"
M = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
BASE = M / "work" / "vendor-base"
TAG = "S12 decision 7"
P = "lgtm-presentation/edits/png/"
DECKS = ["Python", "Quarkus", "Spring", "DotNet", "Go", "Cpp"]

# ------------------------------------------------------------------ text pairs (all six decks)
# (find, repl, cat); a pair may match in any number of decks, but must match somewhere.
GLOBAL = [
    # overview / title notes: no Appendix S
    (" and run Example 05 on minikube and OpenShift Local.", " and run Example 05 on minikube.", "new"),
    ("Tell people the deep-dive appendices A to S (protocols, versioning, WebSockets, sagas, errors, caching, "
     "failure modes, feature flags, API testing, minikube, OpenShift Local) are there to jump to.",
     "Tell people the deep-dive appendices A to R (protocols, versioning, WebSockets, sagas, errors, caching, "
     "failure modes, feature flags, API testing, minikube) are there to jump to.", "new"),
    # event-driven tools landscape
    ("'I need to get data from SFTP to Kafka to S3 with these transforms in the middle'",
     "'I need to get data from SFTP to Kafka to an object store with these transforms in the middle'", "stack"),
    # 4C's
    ("KMS for keys, CloudTrail / audit logging, region", "KMS for keys, audit logging, region", "stack"),
    ("'someone left an S3 bucket open'", "'someone left a storage bucket open to the internet'", "stack"),
    # valet key concept
    ("Cons: requires the storage service to validate tokens (S3, Azure Blob, GCS all do); ",
     "Cons: requires the storage side to validate tokens; ", "stack"),
    ("The canonical implementations: S3 pre-signed URLs (15-minute upload tokens for a specific bucket+key+method), "
     "Azure SAS tokens (Shared Access Signatures with per-resource scoping), GCS signed URLs, AWS STS AssumeRole "
     "with a tight scoping policy.",
     "Every implementation has the same shape: sign the operation, the object key and the expiry with a key the "
     "storage side can check. Example 12 mints and verifies such a ticket in the service itself (HMAC-SHA256, an "
     "HS256 JWT in Go and C++), and most object stores, open-source ones included, accept signed URLs of the same "
     "shape.", "stack"),
    # strangler fig (auth)
    ("validates JWTs from a modern IdP (Keycloak, Auth0, Azure AD)", "validates JWTs from a modern IdP (Keycloak, Dex)",
     "stack"),
    # zero-trust
    ("Edge (IAP): Google IAP, Cloudflare Access, Pomerium, AWS Verified Access — ",
     "Edge (IAP): Pomerium or OAuth2 Proxy in front of an OIDC provider such as Keycloak — ", "stack"),
    ("Pomerium is open source; Google IAP / Cloudflare Access / AWS Verified Access are managed services.",
     "Pomerium (Apache 2.0) and OAuth2 Proxy (MIT) are open source too.", "stack"),
    ("Pomerium open source; Google IAP / Cloudflare Access / AWS Verified Access are managed.",
     "Pomerium (Apache 2.0) and OAuth2 Proxy (MIT) are open source too.", "stack"),
    ("they authenticate against your IdP (Keycloak, Auth0, Azure AD, Google Workspace)",
     "they authenticate against your IdP (Keycloak, or Dex federating an existing directory)", "stack"),
    ("an Identity-Aware Proxy (Google IAP, Cloudflare Access, Pomerium, AWS Verified Access)",
     "an Identity-Aware Proxy (Pomerium or OAuth2 Proxy)", "stack"),
    # claim check concept
    ("into a secure object store (S3, Azure Blob, GCS) and publishes", "into a secure object store and publishes",
     "stack"),
    # choosing the right pattern (notes)
    ("Valet key requires storage-side validation — S3, Azure Blob, GCS all support it natively, so the cost is "
     "usually just understanding the SDK.",
     "Valet key requires storage-side validation: the store, or a small gateway in front of it, must check the "
     "signature, the operation and the expiry.", "stack"),
    # glossary
    ("; SAS (Shared Access Signature, Azure's scoped token)", "", "stack"),
    ("SAS is Azure's valet-key token; ", "", "stack"),
    # Appendix I gateways
    ("(Kong, Apigee, Istio gateway, ", "(Kong, Istio gateway, ", "stack"),
    # Appendix M references
    ("AWS Builders' Library (timeouts, retries, backoff with jitter)",
     "the gRPC retry design, gRFC A6 (retry policy, backoff with jitter, retry throttling)", "stack"),
    ("the AWS Builders' Library has excellent practical articles on timeouts and backoff-with-jitter;",
     "the gRPC retry design (gRFC A6) writes retry policy, backoff with jitter and retry throttling down as a "
     "protocol;", "stack"),
]

# deck-only pairs
DECK = {
    "Cpp": [
        ("the service hands the client a pre-signed PUT URL with a short expiry and a scoped key",
         "the service hands the client a signed ticket with a short expiry, scoped to one key and one operation",
         "stack"),
        ("the C++ service mints the URL in microseconds, the upload happens directly to S3 or MinIO,",
         "the C++ service mints the ticket in microseconds, the upload goes directly to the object store,", "stack"),
        ("uri: 's3://claims/abc-123'", "uri: 'https://objects.internal/claims/abc-123'", "stack"),
        ("where you can use bucket policies, KMS keys, audit logs", "where you can use per-object access policies, "
         "KMS keys, audit logs", "stack"),
        ("; AWS SDK for C++ enables valet-key and claim-check directly.",
         "; Example 12 mints valet-key tickets with jwt-cpp, and a claim check carries the same ticket.", "stack"),
        ("(Drogon, gRPC, librdkafka, OpenTelemetry C++, AWS SDK for C++)",
         "(Drogon, gRPC, librdkafka, OpenTelemetry C++, jwt-cpp)", "stack"),
    ],
    "DotNet": [
        ("Runs on Kubernetes as a regular ASP.NET Core Pod — no Azure App Service, no Azure SignalR Service.",
         "Runs on Kubernetes as a regular ASP.NET Core Pod, with no managed hosting and no managed SignalR service.",
         "stack"),
        ("What we explicitly avoid: Azure SignalR Service (cloud-coupled, paid), Azure App Service hosting "
         "(Kubernetes is the deployment target), Azure Static Web Apps (Blazor WASM is hosted as static files inside "
         "an nginx Pod or the ASP.NET Core process itself).",
         "What it avoids: a managed SignalR service and managed app hosting (Kubernetes is the deployment target); "
         "Blazor WASM is hosted as static files inside an nginx Pod or the ASP.NET Core process itself.", "stack"),
        ("Azure SignalR Service is not used: it is the cloud-coupled option, and the open-source Redis backplane is "
         "what runs on your own Kubernetes.",
         "A managed, cloud-hosted SignalR service is not used: the open-source Redis backplane is what runs on your "
         "own Kubernetes.", "stack"),
        ("and neither needs Azure SignalR Service.", "and neither needs a managed SignalR service.", "stack"),
        ("both work without ANY Azure service — no Azure SignalR Service, no Azure App Service, no Azure Static Web "
         "Apps. Open Redis for the backplane is all you need.",
         "both work without any managed cloud service. Open-source Redis for the backplane is all you need.",
         "stack"),
        ("The bold final line is the one to leave up: nothing here requires Azure.",
         "The bold final line is the one to leave up: nothing here requires a managed cloud service.", "stack"),
        ("If your team is moving off Azure App Service to Kubernetes, you don't lose Blazor — you just stop paying "
         "for Azure SignalR Service and run Redis yourself, with the same throughput characteristics.",
         "A team moving from managed app hosting to Kubernetes keeps Blazor: it runs Redis itself as the backplane "
         "instead of a managed SignalR service.", "stack"),
        ("with no commercial-only dependency and no Azure-only service.",
         "with no commercial-only dependency and no cloud-only service.", "stack"),
        ("nothing requires Azure or any other cloud-specific service.", "nothing requires a cloud-specific service.",
         "stack"),
        ("(open-source, Apache 2.0, not Confluent Cloud)", "(open-source, Apache 2.0)", "stack"),
        ("UBI images are freely redistributable, based on RHEL 9, and supported by Red Hat on OpenShift.",
         "UBI images are freely redistributable, based on RHEL 9, and run on any Kubernetes cluster.", "stack"),
        ("UBI images are freely redistributable, supported by Red Hat on OpenShift, and carry",
         "UBI images are freely redistributable, run on any Kubernetes cluster, and carry", "stack"),
        ("freely redistributable, commercially supported on OpenShift.",
         "freely redistributable, and run on any Kubernetes cluster.", "stack"),
        ("freely redistributable and supported on OpenShift;", "freely redistributable and run on any Kubernetes "
         "cluster;", "stack"),
    ],
}

# strings inside the agenda and Appendix R ops (cat "new"), patched in place
NEW_PATCH = [
    ("Appendices R–S · Example 05 on minikube and OpenShift Local", "Appendix R · Example 05 on minikube"),
    ("Appendices P–S · .NET on Linux, Blazor, minikube, OpenShift Local",
     "Appendices P–R · .NET on Linux, Blazor, minikube"),
    ("Appendices R and S run Example 05 on minikube and on OpenShift Local with the same verify.sh as compose.",
     "Appendix R runs Example 05 on minikube with the same verify.sh as compose."),
    (" OpenShift Local (Appendix S in the other decks) covers Spring Boot, Quarkus, .NET, Python and Go, not C++.",
     ""),
    (" Appendix S then reuses the same contract on OpenShift Local.", ""),
    (" OpenShift Local (Appendix S) is not part of the C++ deck: that appendix covers the other five languages, "
     "and C++ runs here on minikube.", ""),
    ("That contract is what carries over to OpenShift Local, and it is why the application code is unchanged.",
     "That contract is what carries over to any conformant Kubernetes cluster, and it is why the application code "
     "is unchanged."),
    (" C++ stops here: OpenShift Local covers the other five languages.", ""),
]

# ------------------------------------------------------------------ valet key and claim check
NOTES_TAIL_VALET = (
    "The application stays out of the data path: the client presents the ticket to the storage side directly. "
    "Most object stores, open-source ones included, accept signed URLs of the same shape: the method, the object "
    "key and the expiry signed into the URL. A user-scoped resource path also lets the store's policy restrict "
    "each user to their own prefix as defence in depth.")


def hmac_notes(where, compare):
    return [
        "The handler mints a ticket that authorises one operation (GET or PUT) on one resource for 300 seconds; "
        "after that it is worthless. In Example 12 the ticket is an HMAC-SHA256 signature over "
        f"resource:operation:expires, keyed with VALET_SECRET ({where}). POST /valet-key returns the resource, the "
        "operation, the expiry and the token.",
        "The verifier (GET /verify-valet in the example, the storage gateway in a real system) rejects an expired "
        f"ticket first, recomputes the signature and compares the two with {compare}, a constant-time comparison. "
        "A changed resource, operation or expiry gives a different signature, so any tampering is a 403.",
        NOTES_TAIL_VALET,
    ]


def claim_notes(client, mint):
    return [
        "Two halves. The producer writes the payload to an encrypted object store under payloads/<order id>, mints "
        f"a GET-only ticket for that key with {mint}, and publishes only a small claim (order id, URI and the "
        f"ticket) to order.documents with {client}. The PII is never on Kafka's wire.",
        "The consumer decodes the claim, fetches the payload with the token, processes it, then commits the offset "
        "(at-least-once delivery, so the handler must be idempotent). The store verifies the ticket before it "
        "serves the object and logs every fetch with the principal, an audit trail plain Kafka does not give.",
        "Size the ticket's lifetime to the consumer's worst-case lag. No runnable example covers claim-check; store "
        "stands for any encrypted object store. Set a lifecycle rule that expires claims after the retention "
        "period, so a replayed message points at nothing.",
    ]


PY_VALET = [
    "# main.py (excerpt), examples/12-security/python: an HMAC-SHA256 valet key",
    "VALET_SECRET = os.environ.get(\"VALET_SECRET\", \"demo-secret-do-not-use-in-prod\")",
    "",
    "def _mint_valet(resource: str, operation: str, ttl: int = 300) -> dict:",
    "    expires = int(time.time()) + ttl                        # time-bound",
    "    payload = f\"{resource}:{operation}:{expires}\"           # one object, one operation",
    "    sig = hmac.new(VALET_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()",
    "    return {\"resource\": resource, \"operation\": operation, \"expires\": expires, \"token\": sig}",
    "",
    "def _verify_valet(resource: str, operation: str, expires: int, token: str) -> bool:",
    "    if time.time() > expires:",
    "        return False                                        # expired: worthless",
    "    payload = f\"{resource}:{operation}:{expires}\"",
    "    expected = hmac.new(",
    "        VALET_SECRET.encode(), payload.encode(), hashlib.sha256",
    "    ).hexdigest()",
    "    return hmac.compare_digest(token, expected)             # constant-time compare",
    "",
    "@app.post(\"/valet-key\")",
    "async def mint_key(resource: str, operation: str = \"GET\"):",
    "    return _mint_valet(resource, operation)",
    "# GET /verify-valet answers 403 for an expired or tampered key",
]
PY_CLAIM = [
    "# claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key",
    "async def publish_with_claim(producer: AIOKafkaProducer, order_id: str, body: bytes):",
    "    key = f\"payloads/{order_id}\"",
    "    await store.put(key, body, encrypt=True)                # encrypted at rest, ACL'd",
    "    claim = {",
    "        \"order_id\": order_id,",
    "        \"uri\": f\"https://objects.internal/{key}\",",
    "        **_mint_valet(key, \"GET\", ttl=900),                  # resource, op, expires, token",
    "    }",
    "    await producer.send_and_wait(                           # only the claim goes on the topic",
    "        \"order.documents\", json.dumps(claim).encode(), key=order_id.encode())",
    "",
    "# consumer: read the claim, fetch the body out of band",
    "async for msg in consumer:",
    "    claim = json.loads(msg.value)",
    "    body = await store.get(claim[\"uri\"], token=claim[\"token\"])   # the store checks the ticket",
    "    await handle(body)                                      # PII never touched the topic",
    "    await consumer.commit()                                 # after the side effect",
]


def java_valet(ann, file, inject):
    return [
        f"// ValetKeyService.java (excerpt), examples/12-security/{file}: HMAC-SHA256 valet key",
        ann,
        "public class ValetKeyService {",
        "    private static final int TTL_SECONDS = 300;                       // time-bound",
        f"    private final byte[] secret;          // VALET_SECRET, injected through {inject}",
        "    public Map<String, Object> mint(String resource, String operation) {",
        "        long expires = System.currentTimeMillis() / 1000 + TTL_SECONDS;",
        "        String payload = resource + \":\" + operation + \":\" + expires;  // one object, one op",
        "        Map<String, Object> result = new LinkedHashMap<>();",
        "        result.put(\"resource\", resource);",
        "        result.put(\"operation\", operation);",
        "        result.put(\"expires\", expires);",
        "        result.put(\"token\", hmac(payload));               // HmacSHA256, hex-encoded",
        "        return result;",
        "    }",
        "    public boolean verify(String resource, String operation, long expires, String token) {",
        "        if (System.currentTimeMillis() / 1000 > expires) return false;   // expired",
        "        String expected = hmac(resource + \":\" + operation + \":\" + expires);",
        "        return MessageDigest.isEqual(token.getBytes(), expected.getBytes()); // constant time",
        "    }",
        "}",
    ]


SPRING_VALET = java_valet("@Service", "spring-boot", "@Value") + [
    "// OrderController maps POST /valet-key to mint() and GET /verify-valet to verify()"]
QUARKUS_VALET = java_valet("@ApplicationScoped", "quarkus", "@ConfigProperty") + [
    "// OrderResource maps POST /valet-key to mint() and GET /verify-valet to verify()"]

SPRING_CLAIM = [
    "// claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key",
    "@Service",
    "public class ClaimPublisher {",
    "    private final ObjectStore store;                           // any encrypted object store",
    "    private final KafkaTemplate<String, Map<String, Object>> kafka;",
    "    private final ValetKeyService valet;                       // examples/12-security",
    "    // constructor injection omitted",
    "    public void publish(String orderId, byte[] body) {",
    "        String key = \"payloads/\" + orderId;",
    "        store.put(key, body, true);                            // encrypted at rest, ACL'd",
    "        Map<String, Object> claim = new LinkedHashMap<>(valet.mint(key, \"GET\"));",
    "        claim.put(\"order_id\", orderId);",
    "        claim.put(\"uri\", \"https://objects.internal/\" + key);",
    "        kafka.send(\"order.documents\", orderId, claim);         // only the claim on the topic",
    "    }",
    "}",
    "// consumer: read the claim, fetch the body out of band",
    "@KafkaListener(topics = \"order.documents\", groupId = \"documents\")",
    "public void onClaim(Map<String, Object> claim) {",
    "    byte[] body = store.get((String) claim.get(\"uri\"), (String) claim.get(\"token\"));",
    "    handle(body);                                              // PII never touched the topic",
    "}",
]
QUARKUS_CLAIM = [
    "// claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key",
    "@ApplicationScoped",
    "public class ClaimPublisher {",
    "    @Inject ObjectStore store;                                 // any encrypted object store",
    "    @Inject ValetKeyService valet;                             // examples/12-security",
    "    @Inject @Channel(\"documents-out\") Emitter<JsonObject> claims;   // topic order.documents",
    "    public void publish(String orderId, byte[] body) {",
    "        String key = \"payloads/\" + orderId;",
    "        store.put(key, body, true);                            // encrypted at rest, ACL'd",
    "        JsonObject claim = new JsonObject(valet.mint(key, \"GET\"))",
    "            .put(\"order_id\", orderId)",
    "            .put(\"uri\", \"https://objects.internal/\" + key);",
    "        claims.send(claim);                                    // only the claim on the topic",
    "    }",
    "}",
    "@ApplicationScoped",
    "public class ClaimConsumer {",
    "    @Inject ObjectStore store;",
    "    @Incoming(\"documents-in\")                                  // topic order.documents",
    "    public void onClaim(JsonObject claim) {",
    "        byte[] body = store.get(claim.getString(\"uri\"), claim.getString(\"token\"));",
    "        handle(body);                                          // PII never touched the topic",
    "    }",
    "}",
]

DOTNET_VALET = [
    "// Program.cs (excerpt), examples/12-security/dotnet: an HMAC-SHA256 valet key",
    "var valetSecret = Environment.GetEnvironmentVariable(\"VALET_SECRET\")",
    "    ?? \"demo-secret-do-not-use-in-prod\";",
    "app.MapPost(\"/valet-key\", (HttpContext ctx) =>",
    "{",
    "    var resource = ctx.Request.Query[\"resource\"].ToString();",
    "    var operation = ctx.Request.Query[\"operation\"].FirstOrDefault() ?? \"GET\";",
    "    var expires = DateTimeOffset.UtcNow.ToUnixTimeSeconds() + 300;      // time-bound",
    "    var payload = $\"{resource}:{operation}:{expires}\";                 // one object, one op",
    "    var sig = ComputeHmac(valetSecret, payload);",
    "    return Results.Ok(new { resource, operation, expires, token = sig });",
    "});",
    "// GET /verify-valet: 403 once expired, then a constant-time compare",
    "    if (DateTimeOffset.UtcNow.ToUnixTimeSeconds() > expires)",
    "        return Results.Json(new { detail = \"expired valet key\" }, statusCode: 403);",
    "    var expected = ComputeHmac(valetSecret, $\"{resource}:{operation}:{expires}\");",
    "    if (!CryptographicOperations.FixedTimeEquals(",
    "            Encoding.UTF8.GetBytes(token), Encoding.UTF8.GetBytes(expected)))",
    "        return Results.Json(new { detail = \"invalid or expired valet key\" }, statusCode: 403);",
    "// ComputeHmac: HMACSHA256 keyed with the secret, Convert.ToHexStringLower of the hash",
]
DOTNET_CLAIM = [
    "// claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key",
    "var key = $\"payloads/{orderId}\";",
    "await store.PutAsync(key, largePayload, encrypt: true);   // encrypted at rest, ACL'd",
    "var expires = DateTimeOffset.UtcNow.ToUnixTimeSeconds() + 900;",
    "var token = ComputeHmac(valetSecret, $\"{key}:GET:{expires}\");   // GET only, 15 minutes",
    "await producer.ProduceAsync(\"order.documents\",",
    "    new Message<Null, string> { Value = JsonSerializer.Serialize(new {",
    "        order_id = orderId,",
    "        uri = $\"https://objects.internal/{key}\",",
    "        resource = key, operation = \"GET\", expires, token,",
    "    }) });                                             // claim only: small, routable",
    "// consumer: read the claim, fetch the body out of band",
    "var claim = JsonSerializer.Deserialize<Claim>(cr.Message.Value)!;",
    "var body = await store.GetAsync(claim.Uri, claim.Token);  // PII never touched the topic",
    "consumer.Commit(cr);",
]

CPP_VALET = [
    "// valet.hpp (excerpt), examples/12-security/cpp: the valet key is an HS256 JWT (jwt-cpp)",
    "inline Minted mint(const std::string& secret, const std::string& resource,",
    "                   const std::string& operation,",
    "                   std::chrono::seconds ttl = std::chrono::minutes(5)) {   // time-bound",
    "    const auto now = std::chrono::system_clock::now();",
    "    const auto exp = std::chrono::time_point_cast<std::chrono::seconds>(now + ttl);",
    "    auto token = jwt::create()",
    "                     .set_type(\"JWT\")",
    "                     .set_issuer(kIssuer)                         // \"order-service\"",
    "                     .set_issued_at(now)",
    "                     .set_expires_at(exp)",
    "                     .set_payload_claim(\"res\", jwt::claim(resource))   // one object",
    "                     .set_payload_claim(\"op\", jwt::claim(operation))   // one operation",
    "                     .sign(jwt::algorithm::hs256{secret});",
    "    return {std::move(token), exp.time_since_epoch().count()};",
    "}",
    "// verify(): HS256 pinned (\"none\" and RS256 never reach the verifier), then iss, res, op",
    "const auto decoded = jwt::decode(token);",
    "if (decoded.get_algorithm() != \"HS256\") return false;",
    "jwt::verify().allow_algorithm(jwt::algorithm::hs256{secret}).with_issuer(kIssuer)",
    "    .with_claim(\"res\", jwt::claim(resource)).with_claim(\"op\", jwt::claim(operation))",
    "    .verify(decoded);                                  // signature + exp; throws on failure",
]
CPP_CLAIM = [
    "// claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key",
    "void publish_with_claim(const std::string& order_id, const std::string& body) {",
    "  const auto key = \"payloads/\" + order_id;",
    "  store_.put(key, body, /*encrypt=*/true);                     // 1. store: encrypted, ACL'd",
    "  auto ticket = cndp::valet::mint(VALET_SECRET, key, \"GET\", std::chrono::minutes(15));",
    "  auto claim = nlohmann::json{{\"order_id\", order_id},",
    "                              {\"uri\", \"https://objects.internal/\" + key},",
    "                              {\"token\", ticket.token}, {\"expires\", ticket.expires}}.dump();",
    "  producer_->produce(\"order.documents\", RdKafka::Topic::PARTITION_UA,",
    "                     RdKafka::Producer::RK_MSG_COPY, claim.data(), claim.size(),",
    "                     order_id.data(), order_id.size(), 0, nullptr);   // 2. claim only",
    "}",
    "// Consumer: consume the claim, fetch the payload, then handle",
    "std::unique_ptr<RdKafka::Message> msg(consumer_->consume(100));",
    "if (msg->err() == RdKafka::ERR_NO_ERROR) {",
    "  auto claim = nlohmann::json::parse(payload_of(*msg));",
    "  auto body = store_.get(claim[\"uri\"].get<std::string>(),",
    "                         claim[\"token\"].get<std::string>());     // the store checks the ticket",
    "  handle(body);                                                // PII never touched the topic",
    "  consumer_->commitSync(msg.get());                            // after handle",
    "}",
]

VALET_TITLE = "Valet key  —  scoped, time-bound, op-restricted"
# the valet-key concept figure named S3, Azure SAS, GCS and STS: replaced by the site figure with neutral labels
VALET_FIG = {"Python": (332, 856), "Quarkus": (332, 856), "Spring": (332, 856), "Go": (332, 856),
             "DotNet": (334, 877), "Cpp": (332, 854)}
# the zero-trust figure listed Google IAP, Cloudflare Access, AWS Verified Access: the site figure (neutral)
ZT_FIG = {"Python": (335, 889), "Quarkus": (335, 889), "Spring": (335, 889), "Go": (335, 889),
          "DotNet": (337, 910), "Cpp": (335, 888)}
# the Appendix I layered-stack figure named Apigee in three decks: the site figure the other three decks use
L7_FIG = {"Python": (427, 1891), "Quarkus": (427, 1891), "Spring": (431, 1936)}
# .NET Appendix J tables (authored figures) named Azure: re-rendered with neutral wording
DOTNET_FIGS = [(462, "70-appJ-pinned-libraries-dn"), (464, "72-appJ-migration-reference-dn")]
# deck: (valet sldId, title, chip, code, notes-shape), (claim sldId, chip, code, caption)
SLIDES = {
    "Python": dict(
        valet=(333, 866, 868, 869, VALET_TITLE, "python · FastAPI + hmac (stdlib)", PY_VALET,
               hmac_notes("hmac.new with hashlib.sha256", "hmac.compare_digest"),
               "examples/12-security/python/order-service/main.py (_mint_valet, _verify_valet, /valet-key)"),
        claim=(342, 968, 969, "python · aiokafka + Example 12 valet key", PY_CLAIM,
               claim_notes("aiokafka's send_and_wait", "Example 12's _mint_valet (900 seconds)"), None, None)),
    "Quarkus": dict(
        valet=(333, 866, 868, 869, VALET_TITLE, "java · Quarkus REST + javax.crypto (HmacSHA256)", QUARKUS_VALET,
               hmac_notes("javax.crypto.Mac with HmacSHA256", "MessageDigest.isEqual"),
               "examples/12-security/quarkus/order-service/src/main/java/com/cndp/order/ValetKeyService.java"),
        claim=(342, 968, 969, "java · Quarkus + SmallRye Reactive Messaging", QUARKUS_CLAIM,
               claim_notes("a Reactive Messaging Emitter", "Example 12's ValetKeyService.mint (300 seconds)"),
               None, None)),
    "Spring": dict(
        valet=(333, 866, 868, 869, VALET_TITLE, "java · Spring Boot 4 + javax.crypto (HmacSHA256)", SPRING_VALET,
               hmac_notes("javax.crypto.Mac with HmacSHA256", "MessageDigest.isEqual"),
               "examples/12-security/spring-boot/order-service/src/main/java/com/example/orderservice/"
               "ValetKeyService.java"),
        claim=(342, 968, 969, "java · Spring Boot 4 + Spring Kafka", SPRING_CLAIM,
               claim_notes("KafkaTemplate", "Example 12's ValetKeyService.mint (300 seconds)"), None, None)),
    "DotNet": dict(
        valet=(335, 887, 889, 890, VALET_TITLE, "csharp · ASP.NET Core 10 + HMACSHA256", DOTNET_VALET,
               hmac_notes("HMACSHA256", "CryptographicOperations.FixedTimeEquals"),
               "examples/12-security/dotnet/OrderService/Program.cs (/valet-key, /verify-valet, ComputeHmac)"),
        claim=(344, 989, 990, "csharp · ASP.NET Core 10 + Confluent.Kafka", DOTNET_CLAIM,
               claim_notes("Confluent.Kafka's ProduceAsync", "Example 12's ComputeHmac (900 seconds)"),
               None, None)),
    "Cpp": dict(
        valet=(333, 864, 866, 867, "Valet key — scoped, time-bound, op-restricted", "c++ · Drogon + jwt-cpp",
               CPP_VALET, [
                   "The handler mints a ticket that authorises one operation (GET or PUT) on one resource for "
                   "five minutes; after that it is worthless. In Example 12 the ticket is an HS256 JWT signed with "
                   "jwt-cpp: the res and op claims carry the scope, exp the expiry, iss the issuer. POST /valet-key "
                   "returns the resource, the operation, the expiry and the token.",
                   "The verifier (GET /verify-valet in the example, the storage gateway in a real system) reads the "
                   "header first and rejects anything but HS256, so alg=none or an RS256 token never reaches the "
                   "verifier; then jwt::verify checks the signature, the expiry, the issuer and the res and op "
                   "claims, and the exp must equal the expiry the client presents. Any mismatch is a 403.",
                   NOTES_TAIL_VALET + " What this saves: the Drogon worker thread is back in the pool before the "
                   "upload starts.",
               ], "examples/12-security/cpp/order-service/src/valet.hpp (mint, verify)"),
        claim=(342, 969, 970, "c++ · rdkafka++ + jwt-cpp", CPP_CLAIM,
               claim_notes("rdkafka++", "Example 12's cndp::valet::mint (15 minutes)"), 971,
               "Payloads sit in encrypted object storage; Kafka carries only the claim and its ticket. PII never "
               "crosses the broker."),
        ),
}


# ------------------------------------------------------------------ helpers
def sections(path):
    secs, sid, hdr = {}, None, ""
    for line in path.read_text().split("\n"):
        m = re.match(r"^## \[\d+\] (.*) \(sldId (\d+)\)$", line)
        if m:
            sid, hdr = int(m.group(2)), m.group(1)
            secs[sid] = {"hdr": hdr, "lines": []}
            continue
        if sid is not None:
            secs[sid]["lines"].append(line)
    return secs


def original_sids(deck):
    t = (REPO / "lgtm-presentation" / "text" / f"Designing-Cloud-Native-APIs-{deck}.md").read_text()
    return {int(x) for x in re.findall(r"\(sldId (\d+)\)$", t, re.M)}


def rep(sid, find, repl, n, cat, scope="both"):
    return {"op": "replace", "scope": scope, "find": find, "repl": repl, "expect": n, "sldIds": [sid], "cat": cat,
            "_vendor": TAG}


def patch_str(v, used):
    if isinstance(v, str):
        for a, b in NEW_PATCH:
            if a in v:
                used.add(a)
                v = v.replace(a, b)
        return v
    if isinstance(v, list):
        return [patch_str(x, used) for x in v]
    if isinstance(v, dict):
        return {k: patch_str(x, used) for k, x in v.items()}
    return v


def build(deck, used_global, used_patch):
    name = f"Designing-Cloud-Native-APIs-{deck}"
    path = EDITS / f"{name}.json"
    data = json.loads(path.read_text())
    ops = [o for o in data["ops"] if not o.get("_vendor")]
    n0 = len(ops)
    # 1. Appendix S out
    ops = [o for o in ops if not (o.get("op") == "clone_slide" and str(o.get("as", "")).startswith("s"))
           and not str(o.get("sldId", "")).startswith("$s")]
    dropped_s = n0 - len(ops)
    # 2. agenda and R notes
    ops = [patch_str(o, used_patch) if o.get("cat") == "new" else o for o in ops]
    # 3. replace ops from the pre-decision text
    secs = sections(BASE / f"{name}.md")
    orig = original_sids(deck)
    new_ops = []
    spec = SLIDES.get(deck)
    notes_rewritten = set()
    if spec:
        notes_rewritten = {spec["valet"][0], spec["claim"][0]}
    for find, repl, cat in GLOBAL + DECK.get(deck, []):
        for sid, sec in secs.items():
            if sid not in orig:
                continue
            fence, n, n_notes = False, 0, 0
            for line in [sec["hdr"]] + sec["lines"]:
                if line.startswith("```"):
                    fence = not fence
                    continue
                c = line.count(find)
                if c and fence:
                    raise SystemExit(f"{deck} {sid}: find inside a code block: {find[:60]}")
                n += c
                if line.startswith(">"):
                    n_notes += c
            if not n:
                continue
            if sid in notes_rewritten:
                if n - n_notes:
                    new_ops.append(rep(sid, find, repl, n - n_notes, cat, "slide"))
            else:
                new_ops.append(rep(sid, find, repl, n, cat))
            used_global.add(find)
    # 4. valet key and claim check
    removed_super = 0
    if spec:
        vs, vt, vc, vb, title, chip, code, notes, src = spec["valet"]
        cs, cc, cb, cchip, ccode, cnotes, capid, cap = spec["claim"]
        mine = [
            {"op": "set_text", "sldId": vs, "shape_id": vt, "paragraphs": [title], "cat": "stack"},
            {"op": "set_text", "sldId": vs, "shape_id": vc, "paragraphs": [chip], "cat": "stack"},
            {"op": "set_code", "sldId": vs, "shape_id": vb, "lines": code, "cat": "code", "_src": src},
            {"op": "set_notes", "sldId": vs, "paragraphs": notes, "cat": "stack"},
            {"op": "set_text", "sldId": cs, "shape_id": cc, "paragraphs": [cchip], "cat": "stack"},
            {"op": "set_code", "sldId": cs, "shape_id": cb, "lines": ccode, "cat": "code",
             "_src": "_docs/12-security.md claim-check codetab (site-fixes.md); ticket from examples/12-security"},
            {"op": "set_notes", "sldId": cs, "paragraphs": cnotes, "cat": "stack"},
        ]
        if capid:
            mine.append({"op": "set_text", "sldId": cs, "shape_id": capid, "paragraphs": [cap], "cat": "stack"})
        for o in mine:
            o["_vendor"] = TAG
            if o["op"] == "set_code":
                bad = [x for x in o["lines"] if len(x) > 95]
                if bad or len(o["lines"]) > 31:
                    raise SystemExit(f"{deck}: code too wide or long: {bad[:1]} {len(o['lines'])}")
        keys = {(o["op"], o["sldId"], o.get("shape_id")) for o in mine}
        keep = []
        for o in ops:
            if o.get("op") in ("set_text", "set_code", "set_notes") and \
                    (o["op"], o.get("sldId"), o.get("shape_id")) in keys:
                removed_super += 1
                continue
            keep.append(o)
        ops = keep
        new_ops += mine
    vs, vshape = VALET_FIG[deck]
    figs = [{"op": "replace_picture", "sldId": vs, "shape_id": vshape, "png": P + "12-valet-key.png", "cat": "stack",
             "_vendor": TAG, "_why": "labels named S3, Azure SAS, GCS, STS (tools/vendor_figures.py)"}]
    zs, zshape = ZT_FIG[deck]
    figs.append({"op": "replace_picture", "sldId": zs, "shape_id": zshape, "png": P + "12-zero-trust.png",
                 "cat": "stack", "_vendor": TAG, "_why": "examples named Google IAP, Cloudflare Access, AWS Verified Access"})
    if deck in L7_FIG:
        ls, lshape = L7_FIG[deck]
        figs.append({"op": "replace_picture", "sldId": ls, "shape_id": lshape, "png": P + "22-l7-layers.png",
                     "cat": "stack", "_vendor": TAG, "_why": "API gateway row named Apigee; site figure as in the other decks"})
    if deck == "DotNet":
        prev = {o.get("sldId"): o for o in ops if o.get("op") == "replace_picture"}
        for sid, png in DOTNET_FIGS:
            if sid not in prev or not prev[sid]["png"].endswith(png + ".png"):
                raise SystemExit(f"DotNet: expected an earlier replace_picture of {png} on {sid}")
    new_ops += figs
    at = next(i for i, o in enumerate(ops) if o.get("cat") == "new")
    data["ops"] = ops[:at] + new_ops + ops[at:]
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    return {"added": len(new_ops), "dropped_appendix_s": dropped_s, "dropped_superseded": removed_super,
            "total": len(data["ops"])}


def main():
    used_g, used_p, out = set(), set(), {}
    for d in DECKS:
        out[d] = build(d, used_g, used_p)
    miss = [f for f, _, _ in GLOBAL if f not in used_g]
    miss += [f for d in DECK for f, _, _ in DECK[d] if f not in used_g]
    # NEW_PATCH is idempotent: a re-run finds nothing to patch; fail only if an old string survives
    for d in DECKS:
        t = (EDITS / f"Designing-Cloud-Native-APIs-{d}.json").read_text()
        miss += [f"{d}: {a}" for a, _ in NEW_PATCH if json.dumps(a, ensure_ascii=False)[1:-1] in t]
    if miss:
        raise SystemExit("unmatched: " + json.dumps(miss, indent=1, ensure_ascii=False))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
