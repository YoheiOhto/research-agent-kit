#!/usr/bin/env python3
"""Read-only environment metadata audit for explicitly selected repository roots.

No environment/data tree is traversed; no package is imported, executable run,
cache modified, dependency installed or file deleted. Import checks are plans
only and require an explicit interpreter and explicit module names.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

CACHE_PATHS = (".uv_cache", ".uv-cache", "uv_cache", ".cache/uv", "envs/.store/cache/uv")
STALE = re.compile(r"^(?:\.venv|venv|env)(?:[._-](?:stale|old|bak|backup|prev))(?:[._-].*)?$")
REBUILD_HINT = ("Review the repository's pinned lock and approved environment-maintenance procedure. "
                "setup_venv.sh already refuses shared/existing .venv and supports ENV_SMOKE_IMPORTS. "
                "No environment/cache is removed or rebuilt by this audit.")


def metadata(path: Path, root: Path) -> dict:
    """Inspect named paths only, stopping at a symlinked parent."""
    row = {"path": str(path), "kind": "absent", "resolved": str(path), "target_exists": None, "target_kind": None}
    current = root
    for component in path.relative_to(root).parts:
        current = current / component
        try:
            info = current.lstat()
        except FileNotFoundError:
            return row
        except OSError:
            return {**row, "kind": "unreadable"}
        if stat.S_ISLNK(info.st_mode):
            try:
                target = (current.parent / os.readlink(current)).resolve()
                resolved = target / path.relative_to(current)
                row.update(resolved=str(resolved), symlink_path=str(current), target=str(target))
                if current != path:
                    return {**row, "kind": "symlink_parent"}
                try:
                    target_info = target.stat()
                    row["target_exists"] = True
                    row["target_kind"] = ("directory" if stat.S_ISDIR(target_info.st_mode) else
                                          "file" if stat.S_ISREG(target_info.st_mode) else "nonregular")
                except FileNotFoundError:
                    row["target_exists"] = False
                except OSError:
                    row["target_exists"] = None
                return {**row, "kind": "symlink"}
            except (OSError, RuntimeError):
                return {**row, "kind": "unresolved_symlink"}
    return {**row, "kind": "directory" if stat.S_ISDIR(info.st_mode) else "file" if stat.S_ISREG(info.st_mode) else "nonregular"}


def import_plan(python: Path | None, modules: list[str]) -> dict | None:
    if python is None and not modules:
        return None
    if python is None or not modules or not python.is_absolute() or ".." in python.parts:
        raise ValueError("import planning requires an absolute --python and at least one --module")
    if len(modules) > 100 or any(not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", name, re.ASCII) for name in modules):
        raise ValueError("modules must be explicit dotted Python names (at most 100)")
    code = "import importlib,sys; [importlib.import_module(name) for name in sys.argv[1:]]; print('Import checks passed')"
    return {"executed": False, "python": str(python), "interpreter_available": python.is_file() and os.access(python, os.X_OK),
            "modules": list(dict.fromkeys(modules)), "argv": [str(python), "-I", "-B", "-c", code, *dict.fromkeys(modules)],
            "note": "Plan only. Imports execute package code if separately run; this audit never runs them. "
                    "A plan does not establish CUDA/container compatibility or authorize environment changes."}


def audit(roots: list[Path], shared_cache: Path | None = None, max_root_entries: int = 2048,
          python: Path | None = None, modules: list[str] | tuple = ()) -> dict:
    if not roots or len(roots) > 100 or type(max_root_entries) is not int or max_root_entries <= 0:
        raise ValueError("select 1..100 explicit --repo roots and a positive entry limit")
    selected = sorted({root.expanduser().resolve(strict=True) for root in roots})
    if any(not root.is_dir() for root in selected):
        raise ValueError("every selected repository root must be a directory")
    source = "argument" if shared_cache is not None else "UV_CACHE_DIR" if os.environ.get("UV_CACHE_DIR") else "unknown"
    configured = str(shared_cache) if shared_cache is not None else os.environ.get("UV_CACHE_DIR")
    if configured and (not Path(configured).expanduser().is_absolute() or ".." in Path(configured).parts):
        raise ValueError("the configured shared UV cache must be an absolute path without traversal")
    try:
        shared = Path(configured).expanduser().resolve() if configured else None
    except (OSError, RuntimeError) as error:
        raise ValueError("configured shared cache could not be resolved") from error
    findings, warnings, repositories, targets = [], [], [], {}
    for root in selected:
        environment = metadata(root / ".venv", root)
        record = {"repo": str(root), "environment": environment, "stale_environments": [], "local_uv_caches": []}
        repositories.append(record)
        if environment["kind"] != "absent":
            targets.setdefault(environment["resolved"], []).append(str(root / ".venv"))
        if environment["kind"] in {"symlink", "symlink_parent", "unresolved_symlink"}:
            broken = environment["kind"] == "symlink" and environment["target_exists"] is False
            findings.append({"repo": str(root), "path": str(root / ".venv"), "kind": "broken_venv_symlink" if broken else "shared_venv_symlink",
                             "hint": "Inspect the selected references before changing the target; deleting it can break other repositories."})
        if environment["kind"] in {"unreadable", "unresolved_symlink"} or environment["kind"] == "symlink" and environment["target_exists"] is None:
            warnings.append(f"environment target could not be inspected: {root / '.venv'}")
        if environment["kind"] in {"file", "nonregular"}:
            findings.append({"repo": str(root), "path": str(root / ".venv"), "kind": "invalid_venv_path", "hint": REBUILD_HINT})
        try:
            with os.scandir(root) as entries:
                names = []
                for entry in entries:
                    if len(names) >= max_root_entries:
                        warnings.append(f"root entry limit {max_root_entries} reached: {root}")
                        break
                    names.append(entry.name)
            for name in sorted(names):
                if STALE.fullmatch(name):
                    item = metadata(root / name, root)
                    if item["kind"] in {"directory", "symlink", "unresolved_symlink"}:
                        record["stale_environments"].append(item)
                        findings.append({"repo": str(root), "path": item["path"], "kind": "stale_named_environment",
                                         "hint": "A stale name does not prove disuse; inspect jobs, plans and references before any cleanup."})
        except OSError:
            warnings.append(f"repository root entries could not be read: {root}")
        for relative in CACHE_PATHS:
            cache = metadata(root / relative, root)
            if cache["kind"] == "absent":
                continue
            cache["matches_shared_cache"] = cache["resolved"] == str(shared) if shared is not None else None
            record["local_uv_caches"].append(cache)
            if cache["kind"] == "symlink" and cache["target_exists"] is False:
                findings.append({"repo": str(root), "path": cache["path"], "kind": "broken_uv_cache_symlink",
                                 "hint": "The named cache target is missing; review its configured location without deleting the link."})
            if (cache["kind"] in {"file", "nonregular"} or
                    cache["kind"] == "symlink" and cache["target_kind"] in {"file", "nonregular"}):
                findings.append({"repo": str(root), "path": cache["path"], "kind": "invalid_uv_cache_path",
                                 "hint": "A UV cache must be a directory. Preserve this path and inspect its owner/configuration."})
            if (cache["kind"] in {"unreadable", "unresolved_symlink"} or
                    cache["kind"] == "symlink" and cache["target_exists"] is None):
                warnings.append(f"cache path could not be inspected: {cache['path']}")
            if cache["kind"] == "symlink_parent":
                warnings.append(f"nested cache target through a symlinked parent was not traversed: {cache['path']}")
            if shared is None:
                warnings.append(f"shared cache is unconfigured; divergence is unknown: {cache['path']}")
            elif not cache["matches_shared_cache"]:
                findings.append({"repo": str(root), "path": cache["path"], "kind": "divergent_uv_cache",
                                 "hint": "Check repository setup/config before selecting the shared UV_CACHE_DIR. No cache is changed or deleted."})
    for record in repositories:
        for item in [record["environment"], *record["stale_environments"]]:
            item["selected_references"] = targets.get(item["resolved"], [])
    plan = import_plan(python, list(modules))
    if plan is not None and not plan["interpreter_available"]:
        warnings.append(f"planned interpreter is unavailable: {python}")
    return {"schema_version": 1, "read_only": True, "repositories": repositories,
            "shared_uv_cache": str(shared) if shared is not None else None, "shared_cache_source": source,
            "venv_references": targets, "findings": findings, "warnings": warnings, "incomplete": bool(warnings),
            "import_plan": plan, "rebuild_hint": REBUILD_HINT,
            "scope": {"repository_roots": [str(root) for root in selected], "max_root_entries": max_root_entries,
                      "cache_paths": list(CACHE_PATHS), "recursive_scans": False, "unselected_references": "unknown"}}


def render(report: dict) -> str:
    lines = [f"environment audit: {len(report['repositories'])} explicitly selected repositories",
             f"shared UV cache: {report['shared_uv_cache'] or 'unknown'}"]
    lines.extend(f"{row['kind']}: {row['path']}\n  {row['hint']}" for row in report["findings"])
    lines.extend(f"warning: {warning}" for warning in report["warnings"])
    if report["import_plan"]:
        lines.append("Import plan (not executed): " + json.dumps(report["import_plan"]["argv"], ensure_ascii=False))
    lines.append("No recursive scan, imports, installation, rebuild or deletion was performed.")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, action="append", required=True)
    parser.add_argument("--shared-uv-cache", type=Path)
    parser.add_argument("--max-root-entries", type=int, default=2048)
    parser.add_argument("--python", type=Path)
    parser.add_argument("--module", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = audit(args.repo, args.shared_uv_cache, args.max_root_entries, args.python, args.module)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else render(result))
    return 2 if result["incomplete"] else 1 if result["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
