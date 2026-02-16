#!/usr/bin/env python3

cond_def1 = '(defmacro! cond (fn* (& xs) (if (> (count xs) 0) (list \'if (first xs) (if (> (count xs) 1) (nth xs 1) (throw "odd number of forms to cond")) (cons \'cond (rest (rest xs))))))'
cond_def2 = "(defmacro! cond (fn* (& xs) (if (> (count xs) 0) (list 'if (first xs) (if (> (count xs) 1) (nth xs 1) (throw \"odd number of forms to cond\")) (cons 'cond (rest (rest xs)))))))"

print("cond_def1 bytes:")
for i, c in enumerate(cond_def1):
    if c == "'":
        print(f"  Position {i}: {repr(c)} (ord={ord(c)})")

print("\ncond_def2 bytes:")
for i, c in enumerate(cond_def2):
    if c == "'":
        print(f"  Position {i}: {repr(c)} (ord={ord(c)})")

print("\ncond_def1 around 'if':")
idx = cond_def1.find('if')
print(f"  '{cond_def1[max(0,idx-5):idx+5]}'")

print("\ncond_def2 around 'if':")
idx = cond_def2.find('if')
print(f"  '{cond_def2[max(0,idx-5):idx+5]}'")
