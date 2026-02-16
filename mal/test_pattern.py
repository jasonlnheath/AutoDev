#!/usr/bin/env python3
import re

pattern = r"[^\s{}\[\]()\"`,;@~^]+"
test_str = "'7"
match = re.match(pattern, test_str)
if match:
    print(f"Pattern matches: {match.group()}")
else:
    print("Pattern does not match")

# Check what the pattern actually matches
all_matches = re.findall(pattern, "'7 hello world")
print(f"All matches: {all_matches}")
