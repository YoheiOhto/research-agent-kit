#!/usr/bin/env python3
"""Portable entry point that always disables project and shell execution."""
import sys

sys.dont_write_bytecode = True
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from research_code_check import main


if __name__ == "__main__":
    try:
        raise SystemExit(main(["--static-only", *sys.argv[1:]]))
    except (OSError, ValueError) as error:
        print(f"static check unavailable: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(2)
