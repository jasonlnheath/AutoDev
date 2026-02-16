#!/usr/bin/env python3

cond_def1 = '(defmacro! cond (fn* (& xs) (if (> (count xs) 0) (list \'if (first xs) (if (> (count xs) 1) (nth xs 1) (throw "odd number of forms to cond")) (cons \'cond (rest (rest xs))))))'
cond_def2 = "(defmacro! cond (fn* (& xs) (if (> (count xs) 0) (list 'if (first xs) (if (> (count xs) 1) (nth xs 1) (throw \"odd number of forms to cond\")) (cons 'cond (rest (rest xs)))))))"

print("Finding differences...")
for i in range(max(len(cond_def1), len(cond_def2))):
    c1 = cond_def1[i] if i < len(cond_def1) else None
    c2 = cond_def2[i] if i < len(cond_def2) else None
    if c1 != c2:
        print(f"Position {i}: cond_def1={repr(c1)}, cond_def2={repr(c2)}")
        if i > 0:
            print(f"  Context: ...{repr(cond_def1[max(0,i-10):i+10])}...")
