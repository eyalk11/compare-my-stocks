#!/usr/bin/env python
"""Test runner for test_common.py"""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "src/compare_my_stocks/tests/test_common.py", "-v", "--tb=short"],
    cwd="/workspace/compare-my-stocks"
)
sys.exit(result.returncode)
