#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from step7 import tokenize, READ

test_input = "'7"
print("Input:", repr(test_input))
tokens = tokenize(test_input)
print("Tokens:", tokens)
result = READ(test_input)
print("READ result:", result)
print("READ result type:", type(result).__name__)
if hasattr(result, 'items'):
    print("Items:", result.items)
