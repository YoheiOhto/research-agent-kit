#!/usr/bin/env python3
"""Aggregate observed invocations; no prompts, arguments, sessions or event log.

Explicit record calls write one local SQLite database. Report is read-only and
does not initialize missing state. Metrics are best effort, never a guard.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import time

TIMEZONE = "UTC"
BUSY_SECONDS = 0.1
QUERY_SECONDS = 0.25
DIMENSIONS = ("day", "client", "profile", "kind", "name", "event", "outcome", "evidence")
CHOICES = {
    "client": ("codex", "claude", "gemini", "antigravity", "manual"),
    "profile": ("local", "qsub", "slurm", "unknown", "portable"),
    "kind": ("hook", "skill"),
    "event": ("invocation", "pre_tool", "post_tool", "tool_failure", "user_expansion"),
    "outcome": ("observed", "exit0", "exit2", "error", "success", "failure", "attempt"),
    "evidence": ("wrapper", "native-skill", "user-expansion", "manual"),
}
SCHEMA = ("CREATE TABLE counts (day TEXT NOT NULL, client TEXT NOT NULL, profile TEXT NOT NULL, "
          "kind TEXT NOT NULL, name TEXT NOT NULL, event TEXT NOT NULL, outcome TEXT NOT NULL, "
          "evidence TEXT NOT NULL, count INTEGER NOT NULL CHECK(typeof(count)='integer' AND count>0), "
          "PRIMARY KEY(day,client,profile,kind,name,event,outcome,evidence)) WITHOUT ROWID")


def database_path() -> Path:
    home = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state").expanduser()
    if not home.is_absolute():
        raise ValueError("absolute state home required")
    return home / "research-agent/invocations.sqlite3"


def _safe_paths(path: Path) -> None:
    for parent in reversed(path.parents):
        if parent.is_symlink():
            raise ValueError("symlink state ancestor")
        if parent.exists() and not parent.is_dir():
            raise ValueError("non-directory state ancestor")
    if path.parent.exists():
        info = path.parent.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise ValueError("unsafe state directory")
    for suffix in ("", "-journal", "-wal", "-shm"):
        candidate = Path(str(path) + suffix)
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                info.st_uid != os.getuid() or info.st_mode & 0o022):
            raise ValueError("unsafe database or sidecar")
        if suffix in ("-wal", "-shm"):
            raise ValueError("WAL state unsupported")


def _validate_schema(connection: sqlite3.Connection) -> None:
    objects = connection.execute(
        "SELECT name,type,sql FROM sqlite_master WHERE name NOT GLOB 'sqlite_*' LIMIT 2").fetchall()
    if objects != [("counts", "table", SCHEMA)] or connection.execute("PRAGMA user_version").fetchone() != (1,):
        raise ValueError("unexpected counter schema")


def _valid(values: dict) -> bool:
    return (all(isinstance(values[key], str) and values[key] in choices for key, choices in CHOICES.items())
            and isinstance(values["name"], str)
            and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}", values["name"]) is not None)


def _connection(path: Path, *, write: bool) -> sqlite3.Connection:
    connection = sqlite3.connect(path.as_uri() + ("?mode=rw" if write else "?mode=ro"),
                                 uri=True, timeout=BUSY_SECONDS, isolation_level=None)
    try:
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA temp_store=MEMORY")
        if connection.execute("PRAGMA journal_mode").fetchone() != ("delete",):
            raise ValueError("unexpected journal mode")
        if write:
            connection.execute("PRAGMA synchronous=FULL")
        else:
            connection.execute("PRAGMA query_only=ON")
        deadline = time.monotonic() + QUERY_SECONDS
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        return connection
    except BaseException:
        connection.close()
        raise


def increment(*, client: str, kind: str, name: str, event: str, outcome: str,
              evidence: str, profile: str = "unknown") -> bool:
    """Atomically count one observation. Failure is silent and must not gate work."""
    connection = None
    try:
        values = dict(client=client, profile=profile, kind=kind, name=name,
                      event=event, outcome=outcome, evidence=evidence)
        if not _valid(values):
            return False
        values["day"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
        path = database_path()
        _safe_paths(path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        _safe_paths(path)
        fresh = False
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(descriptor)
            fresh = True
        _safe_paths(path)
        connection = _connection(path, write=True)
        connection.execute("BEGIN IMMEDIATE")
        if fresh:
            connection.execute(SCHEMA)
            connection.execute("PRAGMA user_version=1")
        _validate_schema(connection)
        connection.execute(
            "INSERT INTO counts VALUES (?,?,?,?,?,?,?,?,1) ON CONFLICT(day,client,profile,kind,name,event,outcome,evidence) "
            "DO UPDATE SET count=count+1", tuple(values[key] for key in DIMENSIONS))
        connection.commit()
        return True
    except (OSError, ValueError, TypeError, RuntimeError, sqlite3.Error):
        return False
    finally:
        if connection is not None:
            connection.close()


def report(*, limit: int = 100) -> dict:
    """Read aggregate rows only; totals cover all rows when status is ok."""
    result = {"schema_version": 1, "timezone": TIMEZONE, "status": "unavailable",
              "rows": [], "total_rows": None, "total_observations": None, "truncated": False}
    connection = None
    try:
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("invalid limit")
        path = database_path()
        _safe_paths(path)
        if not path.exists():
            result.update(status="absent", total_rows=0)
            return result
        connection = _connection(path, write=False)
        connection.execute("BEGIN")
        _validate_schema(connection)
        total_rows, total = connection.execute("SELECT count(*),coalesce(sum(count),0) FROM counts").fetchone()
        rows = connection.execute("SELECT * FROM counts ORDER BY day DESC,client,profile,kind,name,event,outcome,evidence LIMIT ?",
                                  (limit,)).fetchall()
        decoded = [dict(zip((*DIMENSIONS, "count"), row)) for row in rows]
        if any(not _valid(row) or dt.date.fromisoformat(row["day"]).isoformat() != row["day"] or
               type(row["count"]) is not int or row["count"] <= 0 for row in decoded):
            raise ValueError("invalid aggregate row")
        result.update(status="ok", total_rows=total_rows, total_observations=total,
                      rows=decoded, truncated=total_rows > limit)
    except (OSError, ValueError, TypeError, RuntimeError, sqlite3.Error):
        pass
    finally:
        if connection is not None:
            connection.close()
    return result


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "invalid arguments (see --help)\n")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__)
    sub = parser.add_subparsers(dest="command")
    show = sub.add_parser("report", help="read-only counts; missing database stays absent")
    show.add_argument("--json", action="store_true")
    show.add_argument("--limit", type=int, default=100)
    record = sub.add_parser("record", help="explicitly record one observation")
    for key, choices in CHOICES.items():
        record.add_argument("--" + key, choices=choices, required=key != "profile",
                            **({"default": "unknown"} if key == "profile" else {}))
    record.add_argument("--name", required=True)
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] not in ("record", "report", "-h", "--help"):
        arguments.insert(0, "report")
    args = parser.parse_args(arguments)
    if args.command == "record":
        ok = increment(**{key: getattr(args, key) for key in (*CHOICES, "name")})
        print("recorded" if ok else "unavailable")
        return 0 if ok else 1
    result = report(limit=args.limit)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"{result['status']}: {result['total_observations']} observations; {result['total_rows']} aggregate rows ({TIMEZONE})")
        for row in result["rows"]:
            print(" ".join(str(row[key]) for key in (*DIMENSIONS, "count")))
        if result["truncated"]:
            print("truncated: increase --limit (maximum 1000)")
    return 1 if result["status"] == "unavailable" else 0


if __name__ == "__main__":
    raise SystemExit(main())
