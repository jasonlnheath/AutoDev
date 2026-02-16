#!/usr/bin/env python3
import re

# Test what the character class matches
pattern = r"[^\s{}\[\]()\"`,;@~^]"
test_chars = ["'", "`", "\"", "!", "a", " ", "(", ")"]
print("Character class: [^\\s{}\\[\\]()\\\"\\`,;@~^]")
print()
for char in test_chars:
    match = re.match(pattern, char)
    print(f"'{char}' (ord={ord(char)}): {'MATCHES' if match else 'does NOT match'}")
