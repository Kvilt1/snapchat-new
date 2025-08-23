#!/usr/bin/env python3
"""
Test runner for all Snapchat Merger V2 tests.
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Tuple

def find_test_files(test_dir: Path) -> List[Path]:
    """Find all test files in the tests directory."""
    test_files = []
    for phase_dir in ['phase0', 'phase1', 'phase2', 'phase3']:
        phase_path = test_dir / phase_dir
        if phase_path.exists():
            test_files.extend(sorted(phase_path.glob('test_*.py')))
    return test_files

def run_test(test_file: Path) -> Tuple[bool, str]:
    """Run a single test file and return success status and output."""
    try:
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=True,
            text=True,
            timeout=30
        )
        success = result.returncode == 0
        output = result.stdout if success else result.stderr
        return success, output
    except subprocess.TimeoutExpired:
        return False, "Test timed out after 30 seconds"
    except Exception as e:
        return False, f"Error running test: {e}"

def main():
    """Run all tests and report results."""
    test_dir = Path(__file__).parent
    test_files = find_test_files(test_dir)
    
    if not test_files:
        print("No test files found!")
        return 1
    
    print("=" * 60)
    print("Running All Snapchat Merger V2 Tests")
    print("=" * 60)
    print(f"\nFound {len(test_files)} test file(s)")
    print()
    
    results = []
    for test_file in test_files:
        relative_path = test_file.relative_to(test_dir)
        print(f"Running {relative_path}...", end=" ")
        
        success, output = run_test(test_file)
        results.append((test_file, success, output))
        
        if success:
            print("✅ PASSED")
        else:
            print("❌ FAILED")
            print(f"  Error: {output[:200]}...")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    
    if failed > 0:
        print("\nFailed tests:")
        for test_file, success, output in results:
            if not success:
                relative_path = test_file.relative_to(test_dir)
                print(f"  - {relative_path}")
                print(f"    {output[:100]}...")
    
    # Show sample output from successful tests
    if passed > 0:
        print("\nSample output from successful tests:")
        for test_file, success, output in results:
            if success and "✅" in output:
                relative_path = test_file.relative_to(test_dir)
                print(f"\n{relative_path}:")
                # Extract summary lines with checkmarks
                summary_lines = [line for line in output.split('\n') 
                               if '✅' in line or 'completed' in line.lower()][:3]
                for line in summary_lines:
                    print(f"  {line.strip()}")
    
    print("\n" + "=" * 60)
    if failed == 0:
        print("🎉 All tests passed successfully!")
    else:
        print(f"⚠️  {failed} test(s) failed. Please review and fix.")
    print("=" * 60)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    exit(main())