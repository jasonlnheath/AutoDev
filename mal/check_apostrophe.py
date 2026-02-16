#!/usr/bin/env python3
# Extract the exact pattern from step7.py
with open('step7.py', 'r') as f:
    content = f.read()

# Find the tokenizer function
import re
pattern_match = re.search(r'pattern = r\'\'\'[\s\S]*?\'\'\'', content)
if pattern_match:
    pattern_text = pattern_match.group()
    print("Found pattern definition:")
    print(pattern_text)
    print("\n" + "="*60)
    # Find just the symbol line
    lines = pattern_text.split('\n')
    for line in lines:
        if 'Symbols' in line or 'everything else' in line:
            print(f"\nSymbol line: {repr(line)}")
            # Find the character class
            cc_match = re.search(r'\[([^\]]+)\]', line)
            if cc_match:
                cc = cc_match.group(1)
                print(f"Character class content: {repr(cc)}")
                print(f"Characters:")
                for i, c in enumerate(cc):
                    print(f"  {i}: {repr(c)} (ord={ord(c)})")
