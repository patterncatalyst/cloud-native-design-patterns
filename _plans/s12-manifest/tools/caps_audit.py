#!/usr/bin/env python3
"""ALL-CAPS emphasis audit for the deck text copies (S12 fix round A).

    caps_audit.py <text copy .md> [...] [--raw] [--all]

Lists every ALL-CAPS word of two or more letters in slide titles (the part after the eyebrow),
slide text, speaker notes and code comments of a deck text copy (lgtm-presentation/text/*.md or a
scratch copy made with deck_text.pptx_to_md) that is not on the allowlist. Code outside comments,
inline `code`, eyebrows (the red ALL-CAPS line before the title), identifiers with digits or
underscores (env vars, constants) and mixed-case words are not scanned.

Allowlist: acronyms and initialisms (HTTP, API, JWT, ...), protocol and gRPC status names
(UNAVAILABLE, ABORTED, ...), SQL keywords in SQL phrases, Redis commands, signal names, state and
mode labels the code and the diagrams use (UP, DOWN, OPEN, CLOSED, HALF-OPEN, COMPENSATED,
BACKWARD, FORWARD, FULL, ...), the failure-taxonomy labels, and Roman numerals of the twelve
factors. Anything else in capitals is emphasis and is rewritten in lower case (house voice rule).
--all prints the allowlisted words too (with "allow"). Exit 1 when a non-allowlisted word is found.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ACRONYMS = """
AB ABI ACID ACL AGPL AI AMQP AOF AOP AOT API ARR ASGI ASLR ASP BCL BFF BI BSD CA CAP CDC CDI CDN
CEP CI CIL CLI CLR CNCF CNI COBOL COM CORS CPU CQRS CRD CRM CRT CRTP CSRF CSV CVE DAL DB DDD DDL DI
DLL DLQ DMN DNS DOM DORA DSL DTO DWARF EDI EF EIP ELK EOF EROFS ESB ETL ETW EU FD FSM FTP GA GB GC
GCC GIL GUI HMAC HPA HTTP IAM IAP ID IDE IETF IIS IOPS IP ISR JAR JAX-RS JDBC JIT JPA JTA JS JSON JSONB
JVM JWT KB KEDA KIE KMS KV LB LDAP LGTM LINQ LOB LOC LRU LTO LTS MB MDC MFA MIT MLLP MSDTC MSI MSMQ
MVC NAT NATS NET NIST NTLM OHS OIDC OK OLTP OOM OPA ORM OS OSI OSS OSV OTEL OTLP OWASP PID PIE PII
POJO PR PSS RAII RBAC RDB README RED REST RFC RHEL RNG RPC RPS RST RTT SAN SBOM SDK SDL SDS SEO
SFTP SHA SLA SLI SLO SLSA SNI SOAP SPIFFE SPIRE SQL SRE SSE SSL SSO SSR SSRF STOMP TCP TLS TS TTL
UB UBI UI UID URI URL USE UTF UX VB VIP VM VPC VPN WAF WAL WASM WCF WS WSDL WSGI WWW XML XOR XXE
YAML YARP CRUD SPA RPO RTO HTML CSS PDF SMS SMTP MQTT AMQPS GRPC HTTPS JWKS JWS JWE PKI CSR CRL OCSP
ACME OAUTH SAML SCIM MTLS ECS EOL CVSS SAST DAST IAST SCA SSH SCP NFS SMB GPU RAM SSD HDD IO API
ASAP FIFO LIFO LTV ACK NACK RTT TPS QPS P99 SDLC BOM ADR RFC CNAB OCI CRI CSI PV PVC RWO RWX NIC
PMR SP JJ FEEL
""".split()
# identifiers and keywords named in prose or comments (code constants, the Apicurio rule type,
# Dockerfile instructions)
IDENTIFIERS = "BATCH STEPS COMPATIBILITY THRESHOLD RUN COPY ENTRYPOINT DEL".split()
GRPC_HTTP = """
OK CANCELLED UNKNOWN INVALID_ARGUMENT DEADLINE_EXCEEDED NOT_FOUND ALREADY_EXISTS PERMISSION_DENIED
RESOURCE_EXHAUSTED FAILED_PRECONDITION ABORTED OUT_OF_RANGE UNIMPLEMENTED INTERNAL UNAVAILABLE
DATA_LOSS UNAUTHENTICATED UNARY UNAUTHORIZED FORBIDDEN REDIRECT GET POST PUT PATCH DELETE HEAD
OPTIONS
""".split()
SQL = """
SELECT INSERT UPDATE DELETE VALUES BEGIN COMMIT ROLLBACK JOIN ALTER TABLE CREATE INDEX TRUNCATE
GRANT REVOKE SERIALIZABLE
""".split()
REDIS = "SET SETEX SADD SPOP ZADD ZREMRANGEBYSCORE HSET HGETALL GETEX EXPIRE SCAN INCR DECR HINCRBY HDEL SREM".split()
SIGNALS = "SIGTERM SIGKILL SIGINT SIGHUP".split()
LABELS = """
UP DOWN OPEN CLOSED HALF-OPEN RUNNING COMPENSATED COMPENSATING COMPLETED CREATED FAILED PENDING
BACKWARD FORWARD FULL NONE BACKWARD_TRANSITIVE FORWARD_TRANSITIVE FULL_TRANSITIVE NETWORK COMPONENT
LOAD DISTANCE STRENGTH VOLATILITY DISABLED ENABLED III IV VI VII VIII IX XI XII
""".split()
ALLOW = set(ACRONYMS) | set(IDENTIFIERS) | set(GRPC_HTTP) | set(SQL) | set(REDIS) | set(SIGNALS) | set(LABELS)
# SQL phrases whose small words (INTO, ON, DO, NOTHING, FOR, FROM, WHERE, NOT, NULL, AS) are
# keywords only in this company
SQL_PHRASES = re.compile(
    r"\bINSERT INTO\b|\bON CONFLICT\b(?: \([^)]*\))?(?: DO (?:NOTHING|UPDATE SET))?|\bFOR UPDATE\b(?: SKIP LOCKED)?"
    r"|\bSELECT\b[^;]{0,80}?\bFROM\b|\bDO (?:NOTHING|UPDATE)\b|\bFROM scratch\b|\bLANGUAGE (?:cpp|grpc)\b"
    r"|\bPLUGIN protoc|\bOR low volatility\b|\bWHERE\b(?=\s+\w+\s*[=<>])|\bNOT NULL\b|\bPRIMARY KEY\b|\bIF NOT EXISTS\b"
    r"|\bDELETE FROM\b|\bUPDATE \w+ SET\b|\bALTER TABLE\b|\bORDER BY\b|\bGROUP BY\b")
TOKEN = re.compile(r"(?<![A-Za-z0-9_$@.<])[A-Z]{2,}(?:-[A-Z]{2,})*(?![A-Za-z0-9_=\[>])")
HEAD = re.compile(r"^## \[(\d+)\] (.*) \(sldId (\d+)\)\s*$")
COMMENT = re.compile(r"(?:^|\s)(//|#|--)\s(.*)$|^\s*(?://|#|--)(.*)$")


def comment_part(line):
    s = line.rstrip("\n")
    for marker in ("//", " #", "-- "):
        i = s.find(marker)
        if marker == " #" and s.lstrip().startswith("#") and not s.lstrip().startswith("#include"):
            return s.lstrip()[1:]
        if i >= 0 and not (marker == "//" and i > 0 and s[i - 1] == ":"):  # skip http://
            return s[i + len(marker):]
    return None


def scan(path):
    out = []
    slide, sid = None, None
    fence = False
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    chip = False
    for ln, line in enumerate(lines, 1):
        m = HEAD.match(line)
        if m:
            slide, sid = int(m.group(1)), int(m.group(3))
            region, text = "title", m.group(2).split(" · ")[-1]
        elif line.startswith("```"):
            fence = not fence
            if fence:
                body = []
                for nxt in lines[ln:]:
                    if nxt.startswith("```"):
                        break
                    body.append(nxt)
                chip = len(body) == 1 and " · " in body[0]
            continue
        elif fence and chip:
            region, text = "chip", line  # a long chip label rendered as a one-line code block
        elif fence:
            c = comment_part(line)
            if c is None:
                continue
            region, text = "code", c
        elif line.startswith("{%") or line.startswith("# ") or line.startswith("Source:"):
            continue
        else:
            region = "notes" if line.startswith(">") else "slide"
            text = line
        text = re.sub(r"`[^`]*`", " ", text)
        text = SQL_PHRASES.sub(" ", text)
        for t in TOKEN.finditer(text):
            w = t.group(0)
            allowed = w in ALLOW or all(p in ALLOW for p in w.split("-"))
            out.append({"slide": slide, "sldId": sid, "region": region, "word": w, "allow": allowed,
                        "line": ln, "context": text[max(0, t.start() - 50): t.end() + 40].strip()})
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)
    bad = 0
    for f in a.files:
        hits = scan(f)
        n = 0
        for h in hits:
            if h["allow"] and not a.all:
                continue
            n += 0 if h["allow"] else 1
            print(f"{f.name}:{h['line']} [{h['slide']:03d}] sldId {h['sldId']} {h['region']:5s} "
                  f"{'allow ' if h['allow'] else ''}{h['word']} | {h['context']}")
        print(f"caps_audit: {f.name}: {n} emphasis word(s)")
        bad += n
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
