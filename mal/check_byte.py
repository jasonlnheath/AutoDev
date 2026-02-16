#!/usr/bin/env python3
# Check what's actually in the file
with open('step7.py', 'r') as f:
    content = f.read()

# Find the line with the symbol pattern
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'Symbols.*everything' in line or ('Symbols' in line and 'everything else' in line):
        print(f"Line {i+1}: {repr(line)}")
        # Show the next few lines too
        for j in range(1, 4):
            if i+j < len(lines):
                print(f"Line {i+j+1}: {repr(lines[i+j])}")
