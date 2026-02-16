#!/usr/bin/env python3

# Test different ways to represent the quote character
cond_def1 = '(defmacro! cond (fn* (& xs) (if (> (count xs) 0) (list \'if (first xs) (if (> (count xs) 1) (nth xs 1) (throw "odd number of forms to cond")) (cons \'cond (rest (rest xs))))))'
cond_def2 = "(defmacro! cond (fn* (& xs) (if (> (count xs) 0) (list 'if (first xs) (if (> (count xs) 1) (nth xs 1) (throw \"odd number of forms to cond\")) (cons 'cond (rest (rest xs)))))))"

print("cond_def1:", repr(cond_def1))
print("cond_def2:", repr(cond_def2))
print()
print("Are they equal?", cond_def1 == cond_def2)
print()
print("cond_def1 length:", len(cond_def1))
print("cond_def2 length:", len(cond_def2))
