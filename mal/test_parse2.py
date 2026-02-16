#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from test import parse_test_file

tests = parse_test_file('tests/step7_quote.mal')

# Find tests with line numbers around 33-40
for i, test in enumerate(tests):
    if 33 <= test['line'] <= 40:
        print(f"Index {i}: Line {test['line']}: input={repr(test['input'])}, expected={repr(test['expected'])}")
