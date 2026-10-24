"""Small synthetic checks; no native agent, model, scheduler or network call."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
IMPORTED = {
    'biopython', 'experimental-design', 'exploratory-data-analysis', 'gget',
    'scikit-learn', 'statistical-analysis', 'statistical-power', 'yomiyasu',
}


class DistributionTests(unittest.TestCase):
    def test_manifest_inventory_and_bytes(self):
        manifest = json.loads((ROOT / 'MANIFEST.json').read_text())
        expected = manifest['files']
        actual = set()
        for directory, names, files in os.walk(ROOT, followlinks=False):
            names[:] = [n for n in names if n not in {'.git', '__pycache__'}]
            for name in names:
                self.assertFalse((Path(directory) / name).is_symlink())
            for name in files:
                p = Path(directory) / name
                relative = p.relative_to(ROOT).as_posix()
                if relative == 'MANIFEST.json' or name.endswith(('.pyc', '.pyo')):
                    continue
                self.assertTrue(stat.S_ISREG(p.lstat().st_mode), relative)
                actual.add(relative)
        self.assertEqual(actual, set(expected))
        for name, record in expected.items():
            with self.subTest(path=name):
                self.assertFalse(Path(name).is_absolute())
                self.assertNotIn('..', Path(name).parts)
                data = (ROOT / name).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), record['sha256'])
                self.assertEqual(len(data), record['size'])
                mode = stat.S_IMODE((ROOT / name).stat().st_mode)
                self.assertEqual(mode & 0o7000, 0, 'special permission bits are unexpected')
                self.assertIn(record['mode'], {'0644', '0755'})
                # Git preserves the executable bit; clone permissions vary with umask.
                git_mode = '0755' if mode & stat.S_IXUSR else '0644'
                self.assertEqual(git_mode, record['mode'])

    def test_imported_skill_provenance_and_licenses(self):
        self.assertEqual({p.name for p in (ROOT / 'skills').iterdir()}, IMPORTED | {'research-workflow'})
        for skill in IMPORTED:
            directory = ROOT / 'skills' / skill
            source = json.loads((directory / 'SOURCE.json').read_text())
            expected = source['files_sha256']
            actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()
                      and '__pycache__' not in p.parts and p.suffix not in {'.pyc', '.pyo'}}
            self.assertEqual(actual, set(expected) | {'LICENSE', 'SOURCE.json'}, skill)
            for name, digest in {**expected, 'LICENSE': source['license_sha256']}.items():
                self.assertEqual(hashlib.sha256((directory / name).read_bytes()).hexdigest(), digest, (skill, name))
            self.assertRegex(source['revision'], r'^[0-9a-f]{40}$')

    def test_first_party_workflow_and_example(self):
        directory = ROOT / 'skills/research-workflow'
        self.assertEqual((ROOT / 'LICENSE').read_bytes(), (directory / 'LICENSE').read_bytes())
        self.assertTrue((directory / 'references/example.md').is_file())
        self.assertFalse((directory / 'SOURCE.json').exists())

    def test_no_personal_runtime_directories(self):
        for name in ('.codex', '.claude', '.gemini', 'agents/profiles', '99-agent', 'data', 'outputs'):
            self.assertFalse((ROOT / name).exists(), name)

    def test_python_sources_parse_without_execution(self):
        for path in ROOT.rglob('*.py'):
            if '.git' in path.parts:
                continue
            with self.subTest(path=str(path.relative_to(ROOT))):
                ast.parse(path.read_bytes(), filename=str(path.relative_to(ROOT)))


class ToolBoundaryTests(unittest.TestCase):
    def run_tool(self, path, *arguments, env=None, isolated=True):
        flags = ['-I', '-S', '-B'] if isolated else ['-B']
        return subprocess.run([sys.executable, *flags, str(ROOT / path), *map(str, arguments)],
                              capture_output=True, text=True, timeout=15, env=env)

    def test_static_inspection_does_not_execute_source_or_project_commands(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'src').mkdir()
            source_marker, command_marker = root / 'source-ran', root / 'command-ran'
            (root / 'src/probe.py').write_text(f'from pathlib import Path\nPath({str(source_marker)!r}).touch()\n')
            (root / 'src/broken.py').write_text('def broken(:\n')
            (root / '.research').mkdir()
            command = [sys.executable, '-c', f'from pathlib import Path; Path({str(command_marker)!r}).touch()']
            (root / '.research/code-check.json').write_text(json.dumps({'commands': [
                {'name': f'fixture-{mode}', 'mode': mode, 'command': command} for mode in ('fast', 'full')]}))
            for mode in ('fast', 'full'):
                with self.subTest(mode=mode):
                    result = self.run_tool('tools/static_code_check.py', '--root', root, '--scope-only',
                                           '--include', 'src', '--mode', mode)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    report = json.loads(result.stdout)
                    self.assertTrue(report['static_only'])
                    self.assertEqual(report['declared_checks'], [])
                    self.assertFalse(source_marker.exists())
                    self.assertFalse(command_marker.exists())
                    self.assertFalse((root / '.research/code-check/latest.json').exists())

    def test_static_truncation_remains_incomplete(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for i in range(3):
                (root / f'file{i}.py').write_text('x = 1\n')
            result = self.run_tool('tools/static_code_check.py', '--root', root, '--scope-only',
                                   '--include', '.', '--max-files', 1, '--no-fail')
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(json.loads(result.stdout)['scan_complete'])

    def test_environment_inspection_does_not_import_or_repair(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / 'import-ran'
            (root / 'poison.py').write_text(f'from pathlib import Path\nPath({str(marker)!r}).touch()\n')
            (root / '.venv').symlink_to(root / 'missing-venv', target_is_directory=True)
            result = self.run_tool('tools/environment_audit.py', '--repo', root, '--python',
                                   sys.executable, '--module', 'poison', '--json')
            self.assertIn(result.returncode, (0, 1, 2), result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report['read_only'])
            self.assertIsNotNone(report['import_plan'])
            self.assertFalse(marker.exists())
            self.assertTrue((root / '.venv').is_symlink())
            self.assertFalse((root / 'missing-venv').exists())

    def test_output_inspection_requires_explicit_root(self):
        self.assertEqual(self.run_tool('tools/inspect_outputs.py', '--json').returncode, 2)

    def test_output_inspection_does_not_run_scheduler_or_change_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / 'bin'
            binary.mkdir()
            marker = root / 'scheduler-ran'
            command = binary / 'sacct'
            command.write_text(f'#!{sys.executable}\nfrom pathlib import Path\nPath({str(marker)!r}).touch()\n')
            command.chmod(0o755)
            run = root / 'outputs/exp/run'
            run.mkdir(parents=True)
            (run / 'metrics.csv').write_text('value\n1\n')
            (run / 'completion.json').write_text(json.dumps({'status': 'running', 'job_id': '123'}))
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            env = {**os.environ, 'PATH': str(binary)}
            result = self.run_tool('tools/inspect_outputs.py', '--repo', root, '--json',
                                   '--max-scan-entries', 1, '--max-seconds', 9999, env=env)
            self.assertEqual(result.returncode, 1, result.stderr)  # Fixture lacks provenance.
            report = json.loads(result.stdout)
            self.assertTrue(report['scan_complete'])
            self.assertGreater(report['scanned_entries'], 1)
            self.assertFalse(marker.exists())
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before, after)

    def test_absent_counter_report_does_not_create_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / 'state'
            env = {**os.environ, 'XDG_STATE_HOME': str(state), 'RESEARCH_AGENT_USAGE': '0'}
            result = self.run_tool('hooks/invocation_counts.py', 'report', '--json', env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['status'], 'absent')
            self.assertIsNone(report['total_observations'])
            self.assertFalse(state.exists())

    def test_counter_records_only_after_opt_in(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / 'state'
            env = {**os.environ, 'XDG_STATE_HOME': str(state), 'RESEARCH_AGENT_USAGE': '0'}
            arguments = ('hook-exit', '--client', 'manual', '--profile', 'portable',
                         '--name', 'fixture', '--status', 0)
            self.assertEqual(self.run_tool('hooks/usage_hook.py', *arguments, env=env, isolated=False).returncode, 0)
            self.assertFalse(state.exists())
            env['RESEARCH_AGENT_USAGE'] = '1'
            for _ in range(2):
                self.assertEqual(self.run_tool('hooks/usage_hook.py', *arguments, env=env, isolated=False).returncode, 0)
            result = self.run_tool('hooks/invocation_counts.py', 'report', '--json', env=env)
            report = json.loads(result.stdout)
            self.assertEqual(report['total_observations'], 2)
            self.assertEqual(report['total_rows'], 1)
            self.assertEqual(set(report['rows'][0]), {'day', 'client', 'profile', 'kind', 'name', 'event',
                                                     'outcome', 'evidence', 'count'})


if __name__ == '__main__':
    unittest.main()
