#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

# Patch the EVAL function to add debug output
import step8
original_eval = step8.EVAL

call_count = [0]

def debug_eval(ast, env):
    call_count[0] += 1
    if call_count[0] <= 20 or (call_count[0] % 100 == 0):
        print(f"[{call_count[0]}] EVAL: {ast}")
    result = original_eval(ast, env)
    if call_count[0] <= 20 or (call_count[0] % 100 == 0):
        print(f"[{call_count[0]}] RESULT: {result}")
    return result

step8.EVAL = debug_eval

from step8 import rep, Env, MalNumber

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

# Define cond macro
cond_def = "(defmacro! cond (fn* (& xs) (if (> (count xs) 0) (list 'if (first xs) (if (> (count xs) 1) (nth xs 1) (throw \"odd number of forms to cond\")) (cons 'cond (rest (rest xs)))))))"
print("Defining cond macro...")
call_count[0] = 0
result = rep(cond_def, repl_env)
print("Result:", repr(result))
print()

# Test cond
test = "(cond true 7)"
print(f"Test: {test}")
call_count[0] = 0
result = rep(test, repl_env)
print(f"Result: {repr(result)}")
