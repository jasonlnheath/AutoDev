#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from stepA import tokenize, READ, EVAL, Env, MalNumber

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

# Test load-file
file_path = "../tests/computations.mal"
print(f"Loading file: {file_path}")
try:
    with open(file_path, 'r') as f:
        content = f.read()
    print(f"File content: {repr(content)}")

    tokens = tokenize(content)
    print(f"Tokens: {tokens}")

    # Try to read and evaluate
    expr = READ(content)
    print(f"Read expression: {expr}")

    result = EVAL(expr, repl_env)
    print(f"Result: {result}")

    # Check if sumdown is defined
    sumdown = repl_env.get('sumdown')
    print(f"sumdown in env: {sumdown}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
