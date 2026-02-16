#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from test import parse_test_file

tests = parse_test_file('tests/step7_quote.mal')

# Find tests around line 33-40
for i, test in enumerate(tests[20:35], start=20):
    print(f"{i}: Line {test['line']}: input={repr(test['input'][:40])}, expected={repr(test['expected'])}")
