#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from step8 import READ

cond_def = '(defmacro! cond (fn* (& xs) (if (> (count xs) 0) (list \'if (first xs) (if (> (count xs) 1) (nth xs 1) (throw "odd number of forms to cond")) (cons \'cond (rest (rest xs))))))'

print("Trying to read:", repr(cond_def))
try:
    result = READ(cond_def)
    print("Success!")
    print("Result:", result)
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()

# Try simpler version
simple_cond = '(defmacro! cond (fn* (& xs) (if (> (count xs) 0) (list \'if (first xs) (nth xs 1)))))'
print("\n\nTrying simpler version:", repr(simple_cond))
try:
    result = READ(simple_cond)
    print("Success!")
    print("Result:", result)
except Exception as e:
    print("Error:", e)
