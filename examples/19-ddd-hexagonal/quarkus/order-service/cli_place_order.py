#!/usr/bin/env python3
"""CLI driving adapter wrapper — invokes the Java CliPlaceOrder main class
from the Quarkus fast-jar classpath so verify.sh can call
`python cli_place_order.py`."""
import os
import subprocess
import sys

if len(sys.argv) < 3:
    print("Usage: python cli_place_order.py <sku> <quantity>", file=sys.stderr)
    sys.exit(1)

env = dict(os.environ)
if "DATABASE_URL" not in env:
    env["DATABASE_URL"] = "postgres://appuser:apppass@postgres:5432/appdb"

result = subprocess.run(
    [
        "java", "-cp",
        "/deployments/app/*:/deployments/lib/main/*",
        "com.cndp.order.CliPlaceOrder",
        sys.argv[1], sys.argv[2],
    ],
    capture_output=True,
    text=True,
    env=env,
)

if result.stdout:
    print(result.stdout, end="")
if result.stderr:
    print(result.stderr, end="", file=sys.stderr)

sys.exit(result.returncode)
