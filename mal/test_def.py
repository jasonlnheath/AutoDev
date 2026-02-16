#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from step7 import READ, EVAL, Env, PRINT, rep

repl_env = Env()
# Add arithmetic functions
def add_fn(*args):
    result = 0
    for a in args:
        if not hasattr(a, 'value'):
            raise Exception("+ requires numeric arguments")
        result += a.value
    return result

repl_env.set('+', add_fn)
repl_env.set('*ARGV*', [])

test_input = "(def! a (list 1 2))"
print("Input:", repr(test_input))
result = rep(test_input, repl_env)
print("Result:", repr(result))
