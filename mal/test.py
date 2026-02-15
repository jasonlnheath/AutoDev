#!/usr/bin/env python
"""
Simple test harness for Mal implementation on Windows
"""

import subprocess
import sys
import re


def parse_test_file(filename):
    """Parse a .mal test file into test cases"""
    with open(filename, 'r') as f:
        content = f.read()

    tests = []
    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip comments and empty lines
        if not line or line.startswith(';') and not line.startswith(';>>>'):
            i += 1
            continue

        # Check for test directives
        if line.startswith(';>>>'):
            # Test directive line
            if 'soft=True' in line or 'deferrable=True' in line:
                # Skip these for now
                pass
            i += 1
            continue

        # Regular test case - input line
        if line and not line.startswith(';'):
            # Look ahead for expected output
            expected = None
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if next_line.startswith(';=>'):
                    expected = next_line[3:].strip()
                    break
                elif next_line and not next_line.startswith(';'):
                    # Non-output, non-comment line means no expected output
                    break
                j += 1

            tests.append({
                'input': line,
                'expected': expected,
                'line': i + 1
            })
            i = j + 1
        else:
            i += 1

    return tests


def run_all_tests(mal_command, test_cases):
    """Run all test cases in a single session to preserve environment"""
    # Build input with all test cases
    all_input = '\n'.join(t['input'] for t in test_cases) + '\n'

    try:
        result = subprocess.run(
            mal_command,
            input=all_input,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Get all output lines
        output_lines = result.stdout.strip().split('\n')
        return output_lines
    except subprocess.TimeoutExpired:
        return ['TIMEOUT']
    except Exception as e:
        return [f'ERROR: {e}']


def main():
    if len(sys.argv) < 3:
        print("Usage: python test.py <test_file> <mal_command> [args...]")
        sys.exit(1)

    test_file = sys.argv[1]
    mal_command = sys.argv[2:]

    print(f"Running tests from: {test_file}")
    print(f"Mal command: {' '.join(mal_command)}\n")

    tests = parse_test_file(test_file)

    # Run all tests in a single session
    outputs = run_all_tests(mal_command, tests)

    passed = 0
    failed = 0

    for i, test in enumerate(tests):
        if i < len(outputs):
            actual = outputs[i].strip()
        else:
            actual = 'MISSING OUTPUT'

        expected = test['expected']

        # For Step 0, we expect the input to be echoed back
        if expected is None:
            # No expected output, test passed if no error
            status = "PASS" if actual and not actual.startswith('ERROR') else "FAIL"
        else:
            status = "PASS" if actual == expected else "FAIL"

        if status == "PASS":
            passed += 1
            print(f"[PASS] Line {test['line']}: {test['input'][:30]}")
        else:
            failed += 1
            print(f"[FAIL] Line {test['line']}: {test['input'][:30]}")
            print(f"  Expected: {expected}")
            print(f"  Got:      {actual}")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
