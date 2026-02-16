#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from step8 import READ, EVAL, Env, MalMacro, rep

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

# Define not function
not_fn_code = READ("(fn* (a) (if a false true))")
not_fn = EVAL(not_fn_code, repl_env)
repl_env.set('not', not_fn)

# Define cond macro
cond_macro_code = READ("(fn* (& xs) (if (> (count xs) 0) (list 'if (first xs) (if (> (count xs) 1) (nth xs 1) (throw \"odd number of forms to cond\")) (cons 'cond (rest (rest xs)))))")
cond_macro = EVAL(cond_macro_code, repl_env)
repl_env.set('cond', MalMacro(cond_macro))

# Test cond
test_input = "(cond false \"no\" true \"yes\")"
print("Input:", repr(test_input))
try:
    result = rep(test_input, repl_env)
    print("Result:", repr(result))
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()
