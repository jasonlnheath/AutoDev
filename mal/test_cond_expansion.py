#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from step8 import rep, Env, MalNumber, READ, MalMacro, EVAL, MalList

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

# Get the cond macro from the environment
cond_macro = repl_env.get('cond')
print("Cond macro:", cond_macro)
print("Is MalMacro?", isinstance(cond_macro, MalMacro))

# Read the test expression
test_expr = READ("(cond true 7)")
print("\nTest expression:", test_expr)
print("Test expression type:", type(test_expr))
print("Test expression items:", [str(x) for x in test_expr.items])

# Manually expand the macro
print("\nManually expanding macro...")
macro_func = cond_macro.func
args = test_expr.items[1:]  # (true 7)
print("Args:", [str(x) for x in args])

# Create environment for macro call
macro_env = Env(outer=macro_func.env)
param_items = macro_func.params.items
print("Params:", [str(x) for x in param_items])

# Bind & xs
xs_arg = MalList(args)
print("xs arg:", xs_arg)
macro_env.set('&', MalSymbol('&'))
macro_env.set('xs', xs_arg)

# Evaluate the macro body
body_items = macro_func.body.items
print("Body items:", [str(x) for x in body_items])
for body_expr in body_items[:-1]:
    print(f"  Evaluating {body_expr}...")
    EVAL(body_expr, macro_env)
expanded = EVAL(body_items[-1], macro_env)
print("\nExpanded form:", expanded)
print("Expanded form type:", type(expanded))
if hasattr(expanded, 'items'):
    print("Expanded items:", [str(x) for x in expanded.items])

# Now evaluate the expanded form
print("\nEvaluating expanded form...")
final_result = EVAL(expanded, repl_env)
print("Final result:", final_result)
