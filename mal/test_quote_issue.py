#!/usr/bin/env python3
import re

# The pattern from the file
symbol_pattern = r"[^\s{}\[\]()\"`,;@~^]+"

# Test with apostrophe
test_str = "'"
match = re.match(symbol_pattern, test_str)
print(f"Pattern: {symbol_pattern}")
print(f"Test string: '{test_str}' (ord={ord(test_str)})")
print(f"Match: {match.group() if match else 'None'}")

# Test with backtick
test_str2 = "`"
match2 = re.match(symbol_pattern, test_str2)
print(f"Test string: '{test_str2}' (ord={ord(test_str2)})")
print(f"Match: {match2.group() if match2 else 'None'}")

# Check if the apostrophe is in the pattern
print(f"\nIs apostrophe in pattern? {'\"' in symbol_pattern or \"'\" in symbol_pattern}")

# Let's just check what characters the pattern should exclude
should_exclude = [' ', '{', '}', '[', ']', '(', ')', '"', '`', ',', ';', '@', '~', '^']
print("\nCharacters that should NOT match:")
for char in should_exclude:
    match = re.match(symbol_pattern, char)
    print(f"  '{char}' (ord={ord(char)}): {'MATCHES!' if match else 'excluded ✓'}")
