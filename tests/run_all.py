#!/usr/bin/env python3
"""Run the unit tests and the repo checks. Standard library only.

    python3 tests/run_all.py

Touches nothing outside temporary folders.
"""
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent

suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=1).run(suite)
repo_checks = subprocess.run([sys.executable, str(HERE / "check_repo.py")])
sys.exit(0 if result.wasSuccessful() and repo_checks.returncode == 0 else 1)
