#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from step8 import rep, Env, MalNumber, READ

repl_env = Env()

# Add arithmetic functions
def add_fn(*args):
    result = 0
    for a in args:
        if not isinstance(a, MalNumber):
            raise Exception("+ requires numeric arguments")
        result += a.value
    return MalNumber(result)

repl_env.set('+', add_fn)
repl_env.set('*ARGV*', [])

# Define not function
rep("(def! not (fn* (a) (if a false true)))", repl_env)

# Load cond macro definition from file
with open('define_cond.txt', 'r') as f:
    cond_def = f.read().strip()

print("Cond macro definition:", repr(cond_def))
print("\nDefining cond macro...")
result = rep(cond_def, repl_env)
print("Result:", repr(result))

# Test cond
test_input = "(cond false \"no\" true \"yes\")"
print("\nInput:", repr(test_input))
try:
    result = rep(test_input, repl_env)
    print("Result:", repr(result))
except Exception as e:
    print("Error:", e)
