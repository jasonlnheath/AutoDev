#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

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
rep("(fn* (a) (if a false true))", repl_env)
not_fn = rep("(def! not (fn* (a) (if a false true)))", repl_env)

# Define cond macro using rep
cond_def = '(defmacro! cond (fn* (& xs) (if (> (count xs) 0) (list \'if (first xs) (if (> (count xs) 1) (nth xs 1) (throw "odd number of forms to cond")) (cons \'cond (rest (rest xs))))))'
print("Defining cond macro...")
print(rep(cond_def, repl_env))

# Test cond
test_input = "(cond false \"no\" true \"yes\")"
print("\nInput:", repr(test_input))
try:
    result = rep(test_input, repl_env)
    print("Result:", repr(result))
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()
