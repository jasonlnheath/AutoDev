#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from step8 import READ, EVAL, Env, rep

repl_env = Env()

# Add arithmetic functions
def add_fn(*args):
    result = 0
    for a in args:
        if not isinstance(a, MalNumber):
            raise Exception("+ requires numeric arguments")
        result += a.value
    return MalNumber(result)

from step8 import MalNumber
repl_env.set('+', add_fn)
repl_env.set('*ARGV*', [])

# Test defmacro!
test_input = "(defmacro! one (fn* () 1))"
print("Input:", repr(test_input))
result = rep(test_input, repl_env)
print("Result:", repr(result))
print()

# Test calling the macro
test_input2 = "(one)"
print("Input:", repr(test_input2))
result2 = rep(test_input2, repl_env)
print("Result:", repr(result2))
