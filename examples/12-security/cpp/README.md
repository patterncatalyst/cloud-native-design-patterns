# Example 12: Security (C++)

C++ implementation demonstrating three security patterns for cloud-native services.

## Patterns Demonstrated

### 1. Sidecar Trust (Mutual TLS via Service Mesh)

In production service mesh environments (Istio, Linkerd), the sidecar proxy terminates mTLS and forwards the validated client identity via the `X-Forwarded-Client-Cert` header. The application trusts this header because:

- The sidecar runs in the same pod (shared network namespace)
- Pod-to-pod traffic is encrypted and authenticated
- Direct access to the application port is prevented by NetworkPolicy

This implementation:
- Rejects requests without the identity header (403 Forbidden)
- Extracts SPIFFE identity from the header
- Also captures JWT subject claims when present (`X-Jwt-Claim-Sub`)

**Example:**
```bash
curl -X POST http://localhost:8080/orders \
  -H 'Content-Type: application/json' \
  -H 'X-Forwarded-Client-Cert: spiffe://cluster.local/ns/orders/sa/order-service' \
  -H 'X-Jwt-Claim-Sub: user-42' \
  -d '{"sku":"widget","quantity":2,"tenant":"acme"}'
```

### 2. Valet Keys (Scoped Temporary Tokens)

Valet keys are HMAC-signed tokens that grant time-limited access to specific resources and operations. This is useful for:

- Pre-signed URLs for S3-like object storage
- Temporary download links sent via email
- Delegation to untrusted clients

The token encodes `resource|operation|expires` and is signed with a secret key.

**Minting a valet key:**
```bash
curl -X POST 'http://localhost:8080/valet-key?resource=exports/report.csv&operation=GET' \
  -H 'X-Forwarded-Client-Cert: spiffe://test'
```

**Verifying a valet key:**
```bash
curl 'http://localhost:8080/verify-valet?resource=exports/report.csv&operation=GET&expires=1234567890&token=abc...' \
  -H 'X-Forwarded-Client-Cert: spiffe://test'
```

### 3. Per-Tenant Bulkhead

Resource isolation pattern that prevents one tenant from exhausting shared resources. Each tenant gets an independent pool (capacity: 5 concurrent requests).

Benefits:
- Noisy neighbor protection
- Fair resource allocation
- Graceful degradation under load

**Check bulkhead state:**
```bash
curl http://localhost:8080/bulkhead-state \
  -H 'X-Forwarded-Client-Cert: spiffe://test'
```

## Implementation Notes

### Drogon Middleware
Drogon uses `registerPreHandlingAdvice` for request preprocessing. The sidecar trust check runs before all handlers except `/healthz`.

### HMAC with OpenSSL
Valet keys use OpenSSL's HMAC-SHA256 for signing. No external JWT library is needed for this simple use case.

### Atomic Bulkhead
The bulkhead uses `std::atomic<int>` with compare-exchange for lock-free concurrency. Each tenant has an independent counter.

## Running

```bash
cd examples/12-security/cpp
podman compose up --build
```

Wait for healthcheck to pass (~60s for cold build), then run verification:

```bash
cd ../..
./verify.sh
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│ Service Mesh Sidecar (Envoy/Linkerd)           │
│ - Terminate mTLS                                │
│ - Extract SPIFFE identity                       │
│ - Forward X-Forwarded-Client-Cert header        │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│ Order Service (Drogon + C++)                    │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Middleware: Sidecar Trust                  │  │
│ │ - Reject if no identity header             │  │
│ │ - Store identity + subject in request ctx  │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Handlers                                   │  │
│ │ - POST /orders (requires identity)         │  │
│ │ - POST /valet-key (mint HMAC token)        │  │
│ │ - GET /verify-valet (verify HMAC)          │  │
│ │ - GET /bulkhead-state (tenant pools)       │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Bulkhead Manager                           │  │
│ │ - Per-tenant atomic counters               │  │
│ │ - Capacity: 5 per tenant                   │  │
│ └────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## Security Considerations

**In Production:**

1. **Never trust client-supplied headers without sidecar validation**
   - Use NetworkPolicy to prevent direct pod access
   - Validate SPIFFE identity format
   - Log all authentication failures

2. **Rotate valet key secrets regularly**
   - Use a secret management system (Vault, k8s Secrets)
   - Set appropriate expiration times
   - Monitor for token abuse

3. **Tune bulkhead capacity per tenant SLA**
   - Monitor tenant usage patterns
   - Adjust capacity based on subscription tier
   - Alert on sustained capacity limits

## References

- SPIFFE: https://spiffe.io/
- Istio mTLS: https://istio.io/latest/docs/concepts/security/
- Azure SAS tokens (valet key pattern): https://learn.microsoft.com/en-us/azure/storage/common/storage-sas-overview
- Release It! (bulkhead pattern): Michael T. Nygard
