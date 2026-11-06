#!/usr/bin/env python3
"""Offline-only test evidence. Refuses to alter an already frozen audit."""
from pathlib import Path
import contextlib
import io
import sys
import time
import unittest
import runner

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    if (root / 'protocol/frozen.json').exists():
        raise SystemExit('Already frozen: run unittest directly; do not replace frozen audit evidence.')
    sys.path.insert(0, str(root / 'tests'))
    suite = unittest.defaultTestLoader.discover(str(root / 'tests'))
    output = io.StringIO()
    started = time.monotonic()
    with contextlib.redirect_stdout(output):
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    files = [*sorted(root.glob('harness/*.py')), *sorted(root.glob('tests/*.py')), root / 'analysis/progress.py']
    report = {'updated_utc': runner.now(), 'offline_only': True, 'real_model_calls': 0,
              'execution': 'All model subprocess calls mocked; fixtures use disposable temporary directories.',
              'passed': result.wasSuccessful(), 'tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors),
              'seconds': time.monotonic() - started,
              'source_sha256': {str(p.relative_to(root)): runner.file_sha(p) for p in files},
              'unittest_output': output.getvalue()}
    runner.dump(root / 'audits/integrity_tests.json', report)
    print(f"Offline tests: {result.testsRun}; failures={len(result.failures)}; errors={len(result.errors)}; real model calls=0")
    if not result.wasSuccessful():
        print(output.getvalue())
        raise SystemExit(1)
