#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from stepA import rep, Env, MalNumber

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

# Add time-ms
import time
def time_ms_fn():
    return MalNumber(int(time.time() * 1000))

repl_env.set('time-ms', time_ms_fn)

# Test
test = "(time-ms)"
print(f"Test: {test}")
result = rep(test, repl_env)
print(f"Result: {result}")
print(f"Result type: {type(result)}")

# Also test def!
test2 = "(def! start-time (time-ms))"
print(f"\nTest: {test2}")
result2 = rep(test2, repl_env)
print(f"Result: {result2}")

test3 = "start-time"
print(f"\nTest: {test3}")
result3 = rep(test3, repl_env)
print(f"Result: {result3}")
