#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from step7 import tokenize

input_str = '(def! a (list 1 2))'
tokens = tokenize(input_str)
print('Input:', repr(input_str))
print('Tokens:', tokens)
