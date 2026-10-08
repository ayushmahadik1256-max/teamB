#!/usr/bin/env python3
"""
Test Runner for Team B - Deduplication & Integrity Engine
"""
import sys
import os
import unittest

def main():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(test_dir, ".."))
    sys.path.insert(0, project_root)

    print("=" * 70)
    print("SMART FILE BACKUP SYSTEM - TEAM B TEST SUITE")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=test_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)

    if not result.wasSuccessful():
        sys.exit(1)
    print("ALL TEAM B TESTS PASSED!")

if __name__ == "__main__":
    main()
