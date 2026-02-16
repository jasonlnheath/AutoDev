# AutoDev OODA Loop - Implementation Memory

## Project Status: Steps 7, 8, 9, A Implemented

### Overview
Successfully implemented Mal Lisp Steps 7, 8, 9, and A with partial test coverage.

## Step 7: Quote, Quasiquote, Cons, Concat
**Status:** Complete - 124/124 tests passing ✅

**Key Learnings:**
- Tokenizer pattern must carefully exclude apostrophe (') from symbols to allow quote reader macro to work
- Pattern `[^\s{}\[\]()"`,;@~^']+` excludes ' and works correctly
- Quasiquote expansion is recursive and builds up `cons`/`concat` expressions
- The `vec` function is needed to convert lists to vectors during quasiquote expansion

**Critical Fix:**
The test parser was skipping lines without expected output. Changed `i = j + 1` to `i += 1` to not skip lines.

## Step 8: Macros
**Status:** Complete - 61/61 tests passing ✅

**Key Learnings:**
- Macros are functions that return code (AST) to be evaluated
- Macro arguments are NOT evaluated before being passed to the macro
- Variadic parameters (`&`) must be handled correctly - all remaining arguments go into a list
- Macro expansion happens BEFORE regular function application
- The `cond` macro definition must use double-quoted string in Python (not single-quoted) to avoid escape issues

**Critical Implementation Details:**
1. Check for macros BEFORE evaluating arguments
2. When calling a macro, bind the unevaluated AST nodes as parameter values
3. Handle `&` (variadic) parameter by collecting remaining arguments into a MalList
4. After macro expansion, continue evaluation with the expanded form (TCO)

**Example flow for `(cond true 7)`:**
1. Detect `cond` is a macro
2. Call macro with `xs = (true 7)` (unevaluated)
3. Macro body evaluates to `(if true 7 (cond))`
4. Continue evaluation with this new AST

## Step 9: Try/Catch
**Status:** Partial - 161/173 tests passing

**Key Learnings:**
- `throw` must be a built-in FUNCTION, not a special form, to work with `map`
- Functions like `nil?`, `true?`, `false?` must also be regular functions, not special forms
- Try/catch uses Python exception handling with custom `MalThrownException`
- Hash map functions (`assoc`, `dissoc`, `get`, `keys`, `vals`) work on the internal dict structure

**Special Form vs Built-in Function:**
- Special forms are handled in the EVAL function before argument evaluation
- Built-in functions are added to the environment and can be passed as values
- If a function needs to be passed to `map` or used as a value, it must be a built-in function

**Missing Features (12 test failures):**
- Some edge cases with `apply` and `map`
- String/number conversion edge cases

## Step A: Mal Self-Host
**Status:** Partial - 78/113 tests passing

**Key Additions:**
- `time-ms` function (returns milliseconds since epoch)
- `number?` predicate
- Step A builds on all previous steps

**Missing Features:**
- Various utility functions
- Some core predicates

## Architecture Patterns

### Tokenizer
The tokenizer pattern is critical and must be exact:
```python
pattern = r'''[\s,]*(
    "(?:\\.|[^\\"])*"          |  # Strings
    ;[^\n]*                    |  # Comments
    ~@                         |  # Splice-unquote
    -?\d+                      |  # Numbers
    :[^\s{}\[\]()"`,;]+        |  # Keywords
    [^\s{}\[\]()"`,;@~^]+      |  # Symbols (IMPORTANT: no ' here)
    \[ \] \{ \} \( \)          |  # Brackets
    ` @ ~ \^                   |  # Special characters
    '                              # Quote
)'''
```

### Special Forms Order
Special forms must be checked BEFORE general evaluation:
1. def!, defmacro!, let*, if, fn*, do, quote, quasiquote, try*
2. Then check for macros
3. Then general function application

### TCO (Tail Call Optimization)
Use `while True` loop with `ast = new_ast; continue` for tail calls.
This prevents stack overflow for recursive functions.

### Variadic Parameters
When `&` is encountered in parameters:
1. Bind regular parameters before `&` normally
2. Collect all remaining arguments into a MalList
3. Bind this list to the parameter after `&`

## File Structure
- `step6.py` - File I/O, Atoms, Metadata (67/67 tests)
- `step7.py` - Quote, Quasiquote, Cons, Concat (124/124 tests) ✅
- `step8.py` - Macros (61/61 tests) ✅
- `step9.py` - Try/Catch (161/173 tests)
- `stepA.py` - Mal Self-Host (78/113 tests)

## Testing
- `test.py` - Simple test harness that runs all tests in a single session
- Tests are in `tests/stepX_*.mal` files
- Each test line has expected output on the next line with `;=>`

## Git Commits
1. Step 7: Quote, Quasiquote - All tests passing
2. Step 8: Macros - All tests passing
3. Step 9: Try/Catch - Core functionality working
4. Step A: Self-Host - Core functionality working

## Next Steps
To complete all tests, need to:
1. Fix remaining edge cases in Step 9 (12 failures)
2. Add missing functions for Step A (35 failures)
3. Possibly need to revisit hash map implementation
4. Check string/number conversion functions
