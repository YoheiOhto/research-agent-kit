#!/usr/bin/env python3
"""Read-only audit of an experiment repository's `outputs/<exp>/<variant>/` directories.

Reports, per run directory: file count, size (a hard-linked file counts once), the
`completion.json` status, and an optional `lifecycle.json` state. It flags runs that are
still marked running after their job ended, run directories with too many files, runs that
lack a completion record or its recommended provenance keys, and superseded/rejected runs
old enough to be deletion candidates. It never deletes or rewrites anything.

`lifecycle.json` (next to `completion.json`):
    {"state": "active|superseded|archived|rejected", "reason": "...", "decided_at": "YYYY-MM-DD",
     "superseded_by": "<variant>"}
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import date
import math
from pathlib import Path

STATES = {"active", "superseded", "archived", "rejected"}
PROVENANCE_KEYS = ("job_id", "plan_sha256", "code_commit", "input_sha256", "manifest_sha256")
DONE_STATES = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL", "BOOT_FAIL", "DEADLINE"}
COMPRESSED_SUFFIXES = {".gz", ".zst", ".zstd", ".zip", ".xz", ".bz2", ".parquet", ".sif", ".png", ".jpg", ".jpeg", ".pdf"}
CONTROL_FILES = {"completion.json", "lifecycle.json", "identity.json", "MANIFEST.sha256", ".claimed-by"}


class ScanStopped(RuntimeError):
    pass


class ScanBudget:
    """Bound metadata traversal, never turn a partial inventory into a clean one."""

    def __init__(self, entries=None, seconds=None):
        if entries is not None and (type(entries) is not int or entries <= 0):
            raise ValueError("max_scan_entries must be a positive integer")
        if seconds is not None and (not math.isfinite(seconds) or seconds <= 0):
            raise ValueError("max_seconds must be finite and positive")
        self.limit = entries
        self.deadline = time.monotonic() + seconds if seconds is not None else None
        self.entries = 0
        self.complete = True
        self.warnings = []

    def consume(self):
        if not self.complete:
            raise ScanStopped()
        if ((self.limit is not None and self.entries >= self.limit) or
                (self.deadline is not None and time.monotonic() >= self.deadline)):
            self.incomplete("metadata traversal limit reached; counts are lower bounds, not a full inventory")
            raise ScanStopped()
        self.entries += 1

    def incomplete(self, message):
        self.complete = False
        if message not in self.warnings:
            self.warnings.append(message)


def scan(directory: Path, seen: set[tuple[int, int]], packing: dict | None = None,
         budget: ScanBudget | None = None) -> tuple[int, int]:
    """Return (file count, bytes not already counted through another hard link)."""
    files = size = 0
    stack = [directory]
    try:
        while stack:
            with os.scandir(stack.pop()) as entries:
                for entry in entries:
                    if budget:
                        budget.consume()
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
                        continue
                    files += 1
                    info = entry.stat(follow_symlinks=False)
                    if packing is not None:
                        if entry.is_symlink():
                            packing["symlinks"] += 1
                        elif entry.name not in CONTROL_FILES and Path(entry.name).suffix.lower() not in COMPRESSED_SUFFIXES:
                            packing["uncompressed_files"] += 1
                            packing["uncompressed_logical_bytes"] += info.st_size
                    key = (info.st_dev, info.st_ino)
                    if info.st_nlink > 1:
                        if key in seen:
                            continue
                        seen.add(key)
                    size += info.st_size
    except ScanStopped:
        pass
    except OSError as error:
        if budget is None:
            raise
        budget.incomplete(f"cannot inspect {directory}: {type(error).__name__}")
    return files, size


def read_json(path: Path) -> dict | None:
    try:
        if path.is_symlink() or path.stat().st_size > 5 * 1024 * 1024:
            return None
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def slurm_job_states(job_ids: list[str]) -> dict[str, str]:
    """Final or current states from sacct (read-only). Unknown jobs are simply absent."""
    if not job_ids:
        return {}
    result = subprocess.run(["sacct", "-n", "-P", "-X", "-o", "JobID,State", "-j", ",".join(job_ids)],
                            capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError("sacct failed: " + result.stderr.strip())
    states = {}
    for line in result.stdout.splitlines():
        job, _, state = line.partition("|")
        states[job.strip()] = state.split()[0] if state.strip() else ""
    return states


def run_directories(repo: Path, budget: ScanBudget | None = None) -> list[Path]:
    """Enumerate the documented two-level layout without traversing symlinks."""
    root = repo / "outputs"
    variants = []
    if root.is_symlink():
        if budget:
            budget.incomplete("outputs root is a symlink and was not traversed")
        return variants
    if not root.is_dir():
        return variants
    try:
        with os.scandir(root) as experiments:
            for experiment in experiments:
                if budget:
                    budget.consume()
                if experiment.is_symlink():
                    if not directory_alias(Path(experiment.path), root) and budget:
                        budget.incomplete(f"excluded experiment symlink: {experiment.name}")
                    continue
                if not experiment.is_dir(follow_symlinks=False):
                    continue
                with os.scandir(experiment.path) as children:
                    for child in children:
                        if budget:
                            budget.consume()
                        if child.is_symlink():
                            if not directory_alias(Path(child.path), Path(experiment.path)) and budget:
                                budget.incomplete(f"excluded output directory or file symlink: {child.name}")
                            continue
                        if child.name != "reports" and child.is_dir(follow_symlinks=False):
                            variants.append(Path(child.path))
    except ScanStopped:
        pass
    except OSError as error:
        if budget is None:
            raise
        budget.incomplete(f"cannot enumerate outputs: {type(error).__name__}")
    return sorted(variants)


def directory_alias(path: Path, parent: Path) -> bool:
    """An alias to an actual sibling directory adds no uninspected output tree."""
    try:
        target = path.resolve(strict=True)
        return target.parent == parent.resolve() and target.is_dir() and not (parent / target.name).is_symlink()
    except (OSError, RuntimeError):
        return False


def audit(repo: Path, max_files: int, candidate_days: int, job_states: dict[str, str] | None,
          today: date | None = None, *, max_scan_entries: int | None = None,
          max_seconds: float | None = None, scan_budget: ScanBudget | None = None) -> dict:
    today = today or date.today()
    runs, seen = [], set()
    budget = scan_budget if scan_budget is not None else ScanBudget(max_scan_entries, max_seconds)
    if not repo.is_dir():
        budget.incomplete("repository directory is missing or is not a directory")
    variants = run_directories(repo, budget)
    for variant in variants:
        if not budget.complete:
            break
        packing = {"uncompressed_files": 0, "uncompressed_logical_bytes": 0, "symlinks": 0}
        files, size = scan(variant, seen, packing, budget)
        completion = read_json(variant / "completion.json")
        lifecycle = read_json(variant / "lifecycle.json") or {}
        recorded_state = lifecycle.get("state", "active")
        state = recorded_state if isinstance(recorded_state, str) else "invalid"
        run = {"path": str(variant.relative_to(repo)), "files": files, "bytes": size, "state": state,
               "status": completion.get("status") if completion else None, "findings": [],
               "packing": packing, "scan_complete": budget.complete}
        findings = run["findings"]
        if state not in STATES:
            findings.append(f"unknown lifecycle state {recorded_state!r}")
        if files > max_files:
            findings.append(f"{files} files exceeds {max_files}; pack small outputs into jsonl/parquet shards")
        if completion is None:
            findings.append("no readable completion.json")
        else:
            missing = [key for key in PROVENANCE_KEYS if not completion.get(key)]
            if missing:
                findings.append("completion.json lacks provenance keys: " + ", ".join(missing))
            job = str(completion.get("job_id") or "")
            if completion.get("status") == "running" and job_states is not None:
                final = job_states.get(job)
                if final in DONE_STATES:
                    findings.append(f"marked running but job {job} ended as {final}")
                elif final is None:
                    findings.append(f"marked running and job {job} is unknown to the scheduler")
        if state in ("superseded", "rejected"):
            try:
                age = (today - date.fromisoformat(str(lifecycle.get("decided_at")))).days
            except ValueError:
                findings.append(f"{state} without a valid decided_at date")
            else:
                if age >= candidate_days:
                    findings.append(f"deletion candidate: {state} for {age} days (a person decides)")
        try:
            age = (today - date.fromisoformat(str(lifecycle.get("decided_at")))).days
        except ValueError:
            age = -1
        packing["review_candidate"] = bool(
            budget.complete and completion and completion.get("status") == "completed" and state in {"archived", "superseded", "rejected"}
            and isinstance(lifecycle.get("reason"), str) and lifecycle["reason"].strip() and age >= candidate_days
            and packing["uncompressed_files"] and not packing["symlinks"])
        runs.append(run)
    totals: dict[str, dict] = {}
    for run in runs:
        bucket = totals.setdefault(run["state"], {"runs": 0, "files": 0, "bytes": 0})
        bucket["runs"] += 1
        bucket["files"] += run["files"]
        bucket["bytes"] += run["bytes"]
    experiments = {}
    for run in runs:
        name = Path(run["path"]).parts[1]
        bucket = experiments.setdefault(name, {"files": 0, "bytes": 0, "runs": 0, "report_files": 0, "findings": []})
        for key in ("files", "bytes"):
            bucket[key] += run[key]
        bucket["runs"] += 1
    root = repo / "outputs"
    if root.is_dir() and not root.is_symlink() and budget.complete:
        try:
            with os.scandir(root) as entries:
                for entry in entries:
                    budget.consume()
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    path = Path(entry.path)
                    bucket = experiments.setdefault(path.name, {"files": 0, "bytes": 0, "runs": 0, "report_files": 0, "findings": []})
                    reports = path / "reports"
                    if reports.is_symlink():
                        budget.incomplete(f"excluded report bundle symlink: {path.name}/reports")
                        break
                    if reports.is_dir() and not reports.is_symlink():
                        files, size = scan(reports, seen, budget=budget)
                        bucket["report_files"] += files
                        bucket["files"] += files
                        bucket["bytes"] += size
                    if budget.complete:
                        with os.scandir(path) as children:
                            for child in children:
                                budget.consume()
                                if child.is_dir(follow_symlinks=False):
                                    continue
                                info = child.stat(follow_symlinks=False)
                                bucket["files"] += 1
                                identity = (info.st_dev, info.st_ino)
                                if identity not in seen:
                                    bucket["bytes"] += info.st_size
                                    if info.st_nlink > 1:
                                        seen.add(identity)
                    if not budget.complete:
                        break
        except ScanStopped:
            pass
        except OSError as error:
            budget.incomplete(f"cannot inspect report bundles: {type(error).__name__}")
    for bucket in experiments.values():
        if bucket["files"] > max_files:
            bucket["findings"].append(f"experiment total {bucket['files']} files exceeds {max_files} across runs and report bundles")
    return {"repo": str(repo), "runs": runs, "totals_by_state": totals, "experiments": experiments,
            "scan_complete": budget.complete, "scanned_entries": budget.entries, "warnings": budget.warnings,
            "note": "bytes count each hard-linked file once, in scan order"}


def compression_plan(report: dict) -> dict:
    """Propose inspection work, never claim safe packing or estimated savings."""
    return {"repo": report["repo"], "read_only": True,
            "scan_complete": report.get("scan_complete", True), "warnings": report.get("warnings", []),
            "candidates": [{"path": row["path"], **row["packing"]}
                           for row in report["runs"] if report.get("scan_complete", True) and row["packing"]["review_candidate"]],
            "required_before_execution": [
                "Read the approved plan's preservation policy; obtain scoped packing/deletion approval.",
                "Check running/queued/resume jobs and all plan/config/code path references.",
                "Verify readers support the packed format before changing the original representation.",
                "Inside an approved scheduler allocation, compare inventory and all file SHA-256 values with the archive.",
                "Keep the original until verification and separate deletion approval; record unpacking in PACKED.txt."],
            "note": "Metadata-only review candidates. No compression, deletion, SHA scan, savings estimate or monthly schedule is executed. "
                    "Logical uncompressed bytes can include hard-link duplicates; preserved results are unchanged."}


def render(report: dict) -> str:
    lines = [f"{report['repo']}: {len(report['runs'])} run directories"]
    if not report.get("scan_complete", True):
        lines.append("INCOMPLETE: counts are lower bounds; do not treat this as a clean or full inventory")
    lines.extend(f"warning: {message}" for message in report.get("warnings", []))
    for name, bucket in sorted(report.get("experiments", {}).items()):
        lines.extend(f"outputs/{name}: {message}" for message in bucket["findings"])
    for state, bucket in sorted(report["totals_by_state"].items()):
        lines.append(f"  {state}: {bucket['runs']} runs, {bucket['files']} files, {bucket['bytes'] / 1e9:.2f} GB")
    for run in report["runs"]:
        if run["findings"]:
            lines.append(run["path"])
            lines.extend(f"  - {finding}" for finding in run["findings"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--max-files", type=int, default=100_000)
    parser.add_argument("--candidate-days", type=int, default=28)
    parser.add_argument("--no-scheduler", action="store_true", help="skip the sacct check for stale running runs")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--compression-plan", action="store_true", help="read-only JSON review plan; never compresses or deletes")
    parser.add_argument("--max-scan-entries", type=int, help="bound visited directory entries; incomplete scans exit 2")
    parser.add_argument("--max-seconds", type=float, help="metadata traversal time limit checked between entries")
    args = parser.parse_args(argv)
    if args.max_files <= 0 or args.candidate_days < 0:
        parser.error("--max-files must be positive and --candidate-days nonnegative")
    repo = args.repo.resolve()
    try:
        budget = ScanBudget(args.max_scan_entries, args.max_seconds)
    except ValueError as error:
        parser.error(str(error))
    states = None
    if not args.no_scheduler:
        running = []
        for run in run_directories(repo, budget):
            data = read_json(run / "completion.json")
            if data and data.get("status") == "running" and data.get("job_id"):
                running.append(str(data["job_id"]))
        try:
            states = slurm_job_states(sorted(set(running)))
        except (OSError, RuntimeError) as error:
            print(f"warning: scheduler check skipped ({error})", file=sys.stderr)
    report = audit(repo, args.max_files, args.candidate_days, states,
                   scan_budget=budget)
    if args.compression_plan:
        print(json.dumps(compression_plan(report), ensure_ascii=False, indent=2))
        return 0 if report["scan_complete"] else 2
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render(report))
    if not report["scan_complete"]:
        return 2
    return int(any(run["findings"] for run in report["runs"]) or
               any(bucket["findings"] for bucket in report["experiments"].values()))


if __name__ == "__main__":
    sys.exit(main())
