#!/usr/bin/env python3
"""Run all tests for pyapple2.

Discovers tests in:
  - tests/  (emulator core, analysis toolkit)
"""

import os
import sys
import unittest

# Run from the src/ directory
src_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(src_dir)
sys.path.insert(0, src_dir)

loader = unittest.TestLoader()
suite = unittest.TestSuite()
suite.addTests(loader.discover(os.path.join(src_dir, "tests"), top_level_dir=src_dir))
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
