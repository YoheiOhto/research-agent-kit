#!/usr/bin/env python3
"""Opt-in aggregate observations; never store hook payloads or model text."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True

CLIENTS = ("codex", "claude", "gemini", "antigravity", "manual")
PROFILES = ("local", "qsub", "slurm", "unknown", "portable")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
MAX_INPUT = 1024 * 1024
SKILLS_ROOT = Path(__file__).resolve().parent.parent / "skills"


def record(**dimensions):
    if os.environ.get("RESEARCH_AGENT_USAGE") != "1":
        return
    try:
        from invocation_counts import increment
        increment(**dimensions)
    except Exception:
        # Recording must never replace the hook's output or decision.
        pass


def hook_exit(client, profile, name, status):
    record(client=client, profile=profile, kind="hook", name=name,
           event="invocation", outcome={0: "exit0", 2: "exit2"}.get(status, "error"),
           evidence="wrapper")


def observe(payload, client, profile):
    if client != "claude" or not isinstance(payload, dict):
        return
    event = payload.get("hook_event_name")
    events = {"PreToolUse": ("pre_tool", "attempt"),
              "PostToolUse": ("post_tool", "success"),
              "PostToolUseFailure": ("tool_failure", "failure")}
    if event in events and payload.get("tool_name") == "Skill":
        inputs = payload.get("tool_input")
        name = inputs.get("skill") if isinstance(inputs, dict) else None
        mapped, outcome = events[event]
        evidence = "native-skill"
    elif event == "UserPromptExpansion" and payload.get("expansion_type") == "slash_command":
        name = payload.get("command_name")
        # Slash commands also include custom commands. Only observe installed skill names,
        # and keep this evidence separate from Skill tool success.
        if not isinstance(name, str) or not NAME.fullmatch(name) or not (SKILLS_ROOT / name / "SKILL.md").is_file():
            return
        mapped, outcome, evidence = "user_expansion", "observed", "user-expansion"
    else:
        return
    if isinstance(name, str) and NAME.fullmatch(name):
        record(client=client, profile=profile, kind="skill", name=name,
               event=mapped, outcome=outcome, evidence=evidence)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for operation in ("observe", "hook-exit", "wrap"):
        command = commands.add_parser(operation)
        command.add_argument("--client", choices=CLIENTS, required=True)
        command.add_argument("--profile", choices=PROFILES, default="portable")
        if operation != "observe":
            command.add_argument("--name", required=True)
        if operation == "hook-exit":
            command.add_argument("--status", type=int, required=True)
        if operation == "wrap":
            command.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.operation == "wrap":
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        if not command:
            parser.error("wrap requires a hook command after --")
        try:
            # Inherit stdin/stdout/stderr directly; do not parse or capture the hook's payload.
            result = subprocess.run(command, check=False)
        except OSError:
            return 127
        hook_exit(args.client, args.profile, args.name, result.returncode)
        return result.returncode if result.returncode >= 0 else 128 - result.returncode
    if args.operation == "hook-exit":
        hook_exit(args.client, args.profile, args.name, args.status)
        return 0
    if os.environ.get("RESEARCH_AGENT_USAGE") != "1":
        return 0
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) <= MAX_INPUT:
            observe(json.loads(raw), args.client, args.profile)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
