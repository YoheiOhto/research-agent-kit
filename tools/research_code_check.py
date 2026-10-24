#!/usr/bin/env python3
"""Risk-based, dependency-free checks for research repositories."""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import os
import pathlib
import re
import shlex
import subprocess
import stat
import sys
import warnings
from dataclasses import asdict, dataclass
from typing import Any

SKIP_PARTS = {".git", ".venv", "venv", "node_modules", "outputs", "reports", "logs", ".research"}
TEXT_SUFFIXES = {".py", ".sh", ".bash", ".json", ".yaml", ".yml", ".toml", ".md"}
SECRET_PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("generic-secret", re.compile(r"(?i)(?:api[_-]?key|secret|token|password)\s*=\s*['\"][^'\"]{8,}['\"]")),
)
STATIC_SKIP_PARTS = SKIP_PARTS | {"data", "datasets", "models", "envs", ".cache", "__pycache__"}


class ScanLimit(Exception):
    pass


def static_sources(root: pathlib.Path, scopes: list[str], max_files: int, max_bytes: int,
                   max_entries: int) -> tuple[dict[pathlib.Path, str], dict]:
    """Read bounded explicitly selected source, without Git or project commands."""
    selected = {}
    scan = {"complete": True, "warnings": [], "entries": 0, "bytes": 0,
            "limits": {"files": max_files, "bytes": max_bytes, "entries": max_entries, "depth": 64}}

    def warn(message):
        scan["complete"] = False
        if message not in scan["warnings"]:
            scan["warnings"].append(message)

    def consume():
        if scan["entries"] >= max_entries:
            warn("metadata entry limit reached; source coverage is incomplete")
            raise ScanLimit()
        scan["entries"] += 1

    def inspect(parent, name, relative):
        consume()
        if STATIC_SKIP_PARTS.intersection(relative.parts):
            return
        if len(relative.parts) > 64:
            warn("source depth limit reached")
            return
        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if stat.S_ISLNK(info.st_mode):
            warn("symlink source excluded")
            return
        if stat.S_ISDIR(info.st_mode):
            directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        try:
                            inspect(directory, entry.name, relative / entry.name)
                        except OSError:
                            warn("unreadable or replaced source entry")
            finally:
                os.close(directory)
            return
        if relative.suffix.lower() not in TEXT_SUFFIXES:
            return
        if not stat.S_ISREG(info.st_mode):
            warn("symlink or nonregular source excluded")
            return
        path = root / relative
        if path in selected:
            return
        if len(selected) >= max_files:
            warn("source file limit reached; source coverage is incomplete")
            raise ScanLimit()
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                warn("source changed during inspection")
                return
            remaining = max_bytes - scan["bytes"]
            if opened.st_size > remaining:
                warn("source byte limit reached; source coverage is incomplete")
                raise ScanLimit()
            with os.fdopen(os.dup(descriptor), "rb") as handle:
                data = handle.read(remaining + 1)
            if len(data) > remaining:
                warn("source byte limit reached; source coverage is incomplete")
                raise ScanLimit()
            scan["bytes"] += len(data)
            after = os.fstat(descriptor)
            if (after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns):
                warn("source changed during inspection")
                return
            try:
                selected[path] = data.decode("utf-8")
            except UnicodeDecodeError:
                warn("non-UTF-8 source excluded")
        finally:
            os.close(descriptor)

    for scope in scopes:
        path = pathlib.Path(scope)
        if not scope or path.is_absolute() or ".." in path.parts:
            raise ValueError("static --include must be repository-relative without parent traversal")
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for scope in scopes:
            parent = os.dup(directory)
            path = pathlib.Path(scope)
            try:
                for part in path.parts[:-1]:
                    consume()
                    if part in STATIC_SKIP_PARTS:
                        break
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                    os.close(parent)
                    parent = child
                else:
                    inspect(parent, path.name or ".", path if path.parts else pathlib.Path("."))
            except OSError:
                warn("missing, unreadable or symlinked include scope")
            finally:
                os.close(parent)
    except ScanLimit:
        pass
    finally:
        os.close(directory)
    return selected, scan


@dataclass
class Finding:
    severity: str
    check: str
    path: str
    line: int | None
    message: str
    suggestion: str


def git_lines(root: pathlib.Path, *args: str) -> list[str]:
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True)
    return [line for line in result.stdout.splitlines() if line] if result.returncode == 0 else []


def candidate_files(root: pathlib.Path, mode: str, base: str, include: list[str] | None = None, scope_only: bool = False) -> list[pathlib.Path]:
    if scope_only:
        if not include:
            raise ValueError("--scope-only requires explicit --include scopes")
        names = []
    elif mode == "full":
        names = git_lines(root, "ls-files", "--cached", "--others", "--exclude-standard")
    else:
        names = sorted(set(git_lines(root, "diff", "--name-only", "--diff-filter=ACMR", base) + git_lines(root, "ls-files", "--others", "--exclude-standard")))
    # Explicit scopes include committed files, but only tracked/unignored source.
    if include:
        for scope in include:
            path = (root / scope).resolve()
            if not path.is_relative_to(root):
                raise ValueError("--include must stay within the repository")
        names = sorted(set(names + git_lines(root, "ls-files", "--cached", "--others", "--exclude-standard", "--", *include)))
    files = []
    for name in names:
        path = root / name
        if path.is_file() and path.resolve().is_relative_to(root) and path.suffix.lower() in TEXT_SUFFIXES and not SKIP_PARTS.intersection(path.relative_to(root).parts):
            files.append(path)
    return files


def risk_for(paths: list[pathlib.Path], root: pathlib.Path) -> tuple[str, list[str]]:
    score = 0
    reasons = []
    for path in paths:
        relative = str(path.relative_to(root))
        executable = path.suffix.lower() in {".py", ".sh", ".bash", ".toml", ".json", ".yaml", ".yml"}
        if executable and any(part in path.parts for part in ("templates", "scripts", "lib", "experiments")):
            score += 1
        if executable and re.search(r"(?:run_|train|submit|slurm|qsub|dataset|preprocess|metric|eval)", path.name, re.I):
            score += 2; reasons.append(relative)
        if path.name in {"pyproject.toml", "uv.lock", "requirements.txt", "Dockerfile", "Apptainer.def"}:
            score += 3; reasons.append(relative)
    return ("high" if score >= 6 else "medium" if score >= 2 else "low", sorted(set(reasons))[:12])


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def check_secrets(path: pathlib.Path, text: str, relative: str) -> list[Finding]:
    is_example = "example" in path.name.lower() or "examples" in path.parts
    findings = []
    for name, pattern in SECRET_PATTERNS:
        if is_example and name == "generic-secret":
            continue
        for match in pattern.finditer(text):
            findings.append(Finding("error", name, relative, line_number(text, match.start()), "Possible committed credential or private key", "Remove it from the repository and rotate the credential if it was real"))
    return findings


class PythonVisitor(ast.NodeVisitor):
    def __init__(self, relative: str) -> None:
        self.relative = relative
        self.findings: list[Finding] = []
        self.builtin_modules = {"builtins"}
        self.dynamic_aliases = {"eval", "exec"}

    def visit_Module(self, node: ast.Module) -> None:
        # Collect imports before calls, including function-local aliases.
        for child in ast.walk(node):
            if isinstance(child, ast.Import):
                self.builtin_modules.update(alias.asname or alias.name for alias in child.names if alias.name == "builtins")
            elif isinstance(child, ast.ImportFrom) and child.module == "builtins":
                self.dynamic_aliases.update(alias.asname or alias.name for alias in child.names if alias.name in {"eval", "exec"})
        self.generic_visit(node)

    def add(self, node: ast.AST, severity: str, check: str, message: str, suggestion: str) -> None:
        self.findings.append(Finding(severity, check, self.relative, getattr(node, "lineno", None), message, suggestion))

    def visit_Call(self, node: ast.Call) -> None:
        name = ""
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        builtin_dynamic = isinstance(node.func, ast.Name) and name in self.dynamic_aliases
        qualified_dynamic = (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                             and node.func.value.id in self.builtin_modules and name in {"eval", "exec"})
        if builtin_dynamic or qualified_dynamic:
            self.add(node, "error", "dynamic-code", f"Use of {name}() can execute untrusted content", "Replace it with explicit parsing or a constrained dispatch table")
        if name in {"run", "Popen", "call", "check_call", "check_output"}:
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    self.add(node, "warning", "subprocess-shell", "subprocess uses shell=True", "Pass an argument list and avoid shell expansion")
        if name == "fit_transform" and isinstance(node.func, ast.Attribute):
            text = ast.unparse(node).lower() if hasattr(ast, "unparse") else ""
            if re.search(r"\b(test|valid|validation|holdout)", text):
                self.add(node, "error", "possible-data-leakage", "fit_transform appears to run on evaluation data", "Fit preprocessing on training data and transform evaluation data separately")
        if name == "load" and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id in {"pickle", "joblib"}:
            self.add(node, "warning", "unsafe-deserialization", f"{node.func.value.id}.load can execute code from untrusted artifacts", "Load only trusted artifacts or use a non-executable format")
        self.generic_visit(node)


def check_python(path: pathlib.Path, text: str, relative: str, *, compile_syntax: bool = False) -> list[Finding]:
    try:
        with warnings.catch_warnings():
            if compile_syntax:
                warnings.simplefilter("ignore")  # Compiler warnings can echo source lines.
            tree = ast.parse(text, filename=relative)
            if compile_syntax:
                compile(tree, relative, "exec")  # Validate only; never execute this code object.
    except SyntaxError as exc:
        return [Finding("error", "python-syntax", relative, exc.lineno, exc.msg, "Fix the syntax error before running other checks")]
    visitor = PythonVisitor(relative)
    visitor.visit(tree)
    findings = visitor.findings
    for match in re.finditer(r"['\"]/(?:workspace|scratch|home|Users)/[^'\"]+['\"]", text):
        findings.append(Finding("warning", "hardcoded-path", relative, line_number(text, match.start()), "Machine-specific absolute path", "Move the path to configuration or an environment variable"))
    random_calls = bool(re.search(r"\b(?:random|numpy\.random|np\.random|torch\.rand)", text))
    seed_calls = bool(re.search(r"\b(?:seed|manual_seed|set_seed)\s*\(", text))
    if random_calls and not seed_calls and re.search(r"(?:train|experiment|eval)", relative, re.I):
        findings.append(Finding("warning", "missing-seed", relative, None, "Randomness is used without an obvious seed in an experiment-related file", "Set and record seeds for Python, NumPy, and the active ML framework"))
    return findings


def check_shell(path: pathlib.Path, relative: str) -> list[Finding]:
    result = subprocess.run(["bash", "-n", str(path)], text=True, capture_output=True)
    return [] if result.returncode == 0 else [Finding("error", "shell-syntax", relative, None, result.stderr.strip() or "Invalid shell syntax", "Fix the syntax error")]


def check_structured(path: pathlib.Path, text: str, relative: str) -> list[Finding]:
    if path.suffix == ".json" or (path.suffix in {".yaml", ".yml"} and text.lstrip().startswith(("{", "["))):
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            return [Finding("error", "structured-syntax", relative, exc.lineno, exc.msg, "Fix the JSON or JSON-compatible YAML syntax")]
    return []


def load_config(root: pathlib.Path) -> dict[str, Any]:
    path = root / ".research/code-check.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def run_declared_checks(root: pathlib.Path, config: dict[str, Any], mode: str) -> tuple[list[dict[str, Any]], list[Finding]]:
    results = []
    findings = []
    for item in config.get("commands", []):
        if item.get("mode", "full") == "full" and mode != "full":
            continue
        command = item.get("command")
        if not isinstance(command, list) or not all(isinstance(token, str) for token in command):
            findings.append(Finding("error", "invalid-check-config", ".research/code-check.json", None, "Declared command must be a JSON array of strings", "Use an argv array; shell strings are not accepted"))
            continue
        timeout = min(int(item.get("timeout_seconds", 300)), 1800)
        try:
            completed = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=timeout)
            results.append({"name": item.get("name", shlex.join(command)), "command": command, "returncode": completed.returncode, "stdout_tail": completed.stdout[-2000:], "stderr_tail": completed.stderr[-2000:]})
            if completed.returncode != 0:
                findings.append(Finding("error", "declared-check", ".research/code-check.json", None, f"Check failed: {item.get('name', shlex.join(command))}", "Inspect the captured output and fix the underlying failure"))
        except (OSError, subprocess.TimeoutExpired) as exc:
            findings.append(Finding("error", "declared-check", ".research/code-check.json", None, f"Check could not complete: {exc}", "Verify the tool is installed or increase the bounded timeout"))
    return results, findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--mode", choices=("fast", "full"), default="fast")
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--include", action="append", default=[], help="also check committed source under this repository-relative scope")
    parser.add_argument("--scope-only", action="store_true", help="check only explicit include scopes; preserve all checks within them")
    parser.add_argument("--static-only", action="store_true", help="stdlib source inspection only; never run Git, shells or project commands")
    parser.add_argument("--max-files", type=int, default=200, help="static-only selected source file limit")
    parser.add_argument("--max-bytes", type=int, default=8 * 1024 * 1024, help="static-only total source byte limit")
    parser.add_argument("--max-entries", type=int, default=5000, help="static-only metadata entry limit")
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args(argv)
    if args.static_only and (not args.scope_only or not args.include):
        parser.error("--static-only requires --scope-only and explicit --include scopes")
    if args.static_only and min(args.max_files, args.max_bytes, args.max_entries) <= 0:
        parser.error("static scan limits must be positive")
    root = args.root.resolve()
    if args.static_only:
        texts, scan = static_sources(root, args.include, args.max_files, args.max_bytes, args.max_entries)
        files = list(texts)
    else:
        files = candidate_files(root, args.mode, args.base, args.include, args.scope_only)
    risk_level, risk_reasons = risk_for(files, root)
    findings: list[Finding] = []
    checks = ["secret-patterns", "syntax", "research-python-ast"]
    for path in files:
        relative = str(path.relative_to(root))
        try:
            text = texts[path] if args.static_only else path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(check_secrets(path, text, relative))
        suffix = path.suffix.lower() if args.static_only else path.suffix
        try:
            if suffix == ".py": findings.extend(check_python(path, text, relative, compile_syntax=args.static_only))
            elif suffix in {".sh", ".bash"} and not args.static_only: findings.extend(check_shell(path, relative))
            elif suffix in {".json", ".yaml", ".yml"}:
                findings.extend(check_structured(path.with_suffix(suffix) if args.static_only else path, text, relative))
        except RecursionError:
            if not args.static_only:
                raise
            scan["complete"] = False
            scan["warnings"].append("parser recursion limit reached; source coverage is incomplete")
    declared, declared_findings = ([], []) if args.static_only else run_declared_checks(root, load_config(root), args.mode)
    findings.extend(declared_findings)
    if declared: checks.append("declared-project-checks")
    summary = {severity: sum(item.severity == severity for item in findings) for severity in ("error", "warning", "info")}
    payload = {"schema_version": 1, "generated_at": dt.datetime.now().astimezone().isoformat(), "mode": args.mode, "included_scopes": args.include, "risk_level": risk_level, "risk_reasons": risk_reasons, "files_checked": len(files), "checks": checks, "summary": summary, "findings": [asdict(item) for item in findings], "declared_checks": declared}
    if args.static_only:
        payload.update(static_only=True, scan_complete=scan["complete"], scan_warnings=scan["warnings"],
                       scan_entries=scan["entries"], source_bytes=scan["bytes"], scan_limits=scan["limits"],
                       skipped_checks=["shell-syntax", "declared-project-checks", "non-JSON YAML", "TOML syntax"])
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        if args.static_only and (args.output.exists() or args.output.is_symlink() or
                                 any(parent.is_symlink() for parent in args.output.parents)):
            raise ValueError("static report requires a new path with real directory ancestors")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.static_only:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(rendered)
        else:
            args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
        print(f"Checked {len(files)} source files; errors={summary['error']}, warnings={summary['warning']}")
    else:
        print(rendered, end="")
    if args.static_only and not scan["complete"]:
        return 2
    return 0 if args.no_fail or summary["error"] == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
