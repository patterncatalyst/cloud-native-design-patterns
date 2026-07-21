#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Python wrapper for the C++ CLI binary.

The verify.sh script expects to run `python cli_place_order.py <sku> <qty>`,
so we provide this thin wrapper that just delegates to the C++ binary.
"""
import subprocess
import sys

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: cli_place_order.py <sku> <quantity>", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        ["/usr/local/bin/cli-place-order"] + sys.argv[1:],
        capture_output=True,
        text=True
    )

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    sys.exit(result.returncode)
