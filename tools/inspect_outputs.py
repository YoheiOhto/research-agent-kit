#!/usr/bin/env python3
"""Bounded, scheduler-free output metadata inspection for a selected repository."""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outputs_audit import main


if __name__ == "__main__":
    arguments = sys.argv[1:]
    if not any(value == "--repo" or value.startswith("--repo=") for value in arguments) and not any(
            value in {"--help", "-h"} for value in arguments):
        print("--repo must explicitly select the inspection root", file=sys.stderr)
        raise SystemExit(2)
    try:
        raise SystemExit(main([*arguments, "--no-scheduler", "--max-scan-entries", "5000", "--max-seconds", "2"]))
    except (OSError, ValueError):
        print("output inspection unavailable; no files changed", file=sys.stderr)
        raise SystemExit(2)
