#!/usr/bin/env python3
import re

# The pattern from the file
symbol_pattern = r'[^\s{}\[\]()()"`,;@~^]+'

# Test with apostrophe
test_str = "'"
match = re.match(symbol_pattern, test_str)
print(f"Pattern: {symbol_pattern}")
print(f"Test string: {repr(test_str)} (ord={ord(test_str)})")
print(f"Match: {match.group() if match else 'None'}")

# Test with backtick
test_str2 = "`"
match2 = re.match(symbol_pattern, test_str2)
print(f"Test string: {repr(test_str2)} (ord={ord(test_str2)})")
print(f"Match: {match2.group() if match2 else 'None'}")

# Check each character
chars_to_test = [
    ("'", "apostrophe"),
    ("`", "backtick"),
    ("!", "exclamation"),
    ("a", "letter a"),
]

print("\nDetailed test:")
for char, name in chars_to_test:
    match = re.match(symbol_pattern, char)
    status = "MATCHES" if match else "excluded"
    print(f"  {name} {repr(char)} (ord={ord(char)}): {status}")

# Verify pattern character by character
print(f"\nPattern characters that should exclude:")
excluded = [' ', '{', '}', '[', ']', '(', ')', '"', '`', ',', ';', '@', '~', '^']
for char in excluded:
    match = re.match(symbol_pattern, char)
    print(f"  {repr(char)} (ord={ord(char)}): {'FAILS - matches!' if match else 'excluded'}")
