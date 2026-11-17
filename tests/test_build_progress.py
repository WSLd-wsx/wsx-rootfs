"""Log visibility must preserve compiler failure and avoid repeated log flooding."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_progress',ROOT/'scripts/watch-component-build.py')
monitor=importlib.util.module_from_spec(spec);spec.loader.exec_module(monitor)


class BuildProgress(unittest.TestCase):
    def test_real_child_failure_is_preserved_after_heartbeat(self):
        with tempfile.TemporaryDirectory() as temporary,contextlib.redirect_stdout(io.StringIO()) as output:
            code=monitor.watch([sys.executable,'-c','import time;time.sleep(0.08);raise SystemExit(7)'],Path(temporary),interval=0.02)
        self.assertEqual(code,7)
        self.assertIn('process alive',output.getvalue())
        self.assertIn('exited 7',output.getvalue())

    def test_only_changed_logs_are_reported_and_tail_is_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);folder=root/'mesa';folder.mkdir();log=folder/'compile.log'
            log.write_text('old line\n'*1000+'latest compiler progress\n')
            with contextlib.redirect_stdout(io.StringIO()) as first:
                state=monitor.snapshot(root,{})
            self.assertIn('latest compiler progress',first.getvalue())
            self.assertLess(len(first.getvalue()),1000)
            with contextlib.redirect_stdout(io.StringIO()) as second:
                monitor.snapshot(root,state)
            self.assertEqual(second.getvalue(),'')
