#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from step8 import rep, Env, MalNumber, READ, MalMacro, MalList, MalSymbol

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
result = rep(cond_def, repl_env)
print("Result:", repr(result))

# Check if cond is in the environment
print("\nChecking environment...")
try:
    cond_val = repl_env.get('cond')
    print(f"cond in environment: {cond_val}")
    print(f"Is MalMacro? {isinstance(cond_val, MalMacro)}")
except Exception as e:
    print(f"Error getting 'cond': {e}")

# Test rep directly
test = "(cond true 7)"
print(f"\nTest: {test}")
result = rep(test, repl_env)
print(f"Result: {repr(result)}")

# Test READ
print(f"\nREAD test:")
ast = READ(test)
print(f"AST: {ast}")
print(f"AST items: {ast.items}")
print(f"First: {ast.items[0]}")
print(f"First value: {ast.items[0].value if isinstance(ast.items[0], MalSymbol) else 'N/A'}")
