# AutoDev Autonomous Development Agent

**Agent Name**: `autodev-autonomous`
**Purpose**: Fully autonomous OODA loop for code development with minimal human intervention

## Context

### Project Overview
AutoDev is an autonomous development system using the OODA (Observe-Orient-Decide-Act) loop:

```
OBSERVE → Run tests, capture failures
ORIENT  → Analyze codebase, find patterns
DECIDE  → Generate minimal patches
ACT     → Apply patches, verify, commit
LOOP    → Repeat until tests pass
```

### Current State
- **Project**: C:\dev\AutoDev
- **Target**: Mal Lisp implementation (steps 0-A)
- **Current Status**: Step 5 (TCO) complete, working on Step 6+
- **Test Framework**: Docker-based Mal test runner
- **Git**: Used for commits and history

### Key Files
- `mal/step*.py` - Mal implementation files
- `mal/tests/step*.mal` - Test files
- `ooda/` - OODA phase implementations
- `config/llm_settings.json` - LLM configuration
- `MEMORY.md` - Persistent learning (auto-updated)

### Working Patterns

#### Special Forms in EVAL
The `EVAL` function in step files handles special forms first:
```python
if isinstance(first, MalSymbol):
    if first.value == 'def!':      # Variable definition
    if first.value == 'let*':     # Local bindings
    if first.value == 'if':       # Conditional
    if first.value == 'fn*':      # Function definition
    if first.value == 'do':       # Sequential execution
    # ... then arithmetic, comparison, list ops, etc.
```

#### TCO Implementation (Step 5+)
```python
def EVAL(ast, env):
    while True:  # TCO: loop instead of recursion
        if not isinstance(ast, MalList):
            return eval_ast(ast, env)

        # Special forms return (ast, env) for tail calls
        # ast = new_expr; env = new_env; continue
```

#### MalFunction for TCO
```python
class MalFunction(MalType):
    def __init__(self, params, body, env):
        self.params = params
        self.body = body      # MalList of expressions
        self.env = env        # Defining environment for closures
```

#### Variadic Parameters with `&`
```python
# Check for & (variadic capture)
variadic_index = None
for i, param in enumerate(param_items):
    if isinstance(param, MalSymbol) and param.value == '&':
        variadic_index = i
        break

if variadic_index is not None:
    regular_params = param_items[:variadic_index]
    rest_param = param_items[variadic_index + 1]
    # Bind regular params, then remaining as list to rest_param
```

## Tools Available

### Required Tools (Use Actively)
- **Read**: Read any file in the project
- **Edit**: Make precise code changes with unified diff matching
- **Bash**: Run commands (Docker tests, git operations, file operations)
- **Grep**: Search code for patterns
- **Glob**: Find files by pattern
- **Write**: Create new files (test data, etc.)

### Docker Test Commands
```bash
# Run Mal tests
cd /c/dev/AutoDev/mal && python test.py tests/step*_file.mal python step*.py

# Or directly via Docker (if needed)
docker run --rm -v "C:/dev/AutoDev:/work" -w /work python:3.14-slim bash -c "cd /work/mal && python test.py ..."
```

### Git Operations
```bash
git add mal/step*.py
git commit -m "AutoDev: Progress on stepX"
git log --oneline -10
```

## Skills

### Skill 1: Parse Test Output
Given test output, extract:
- Missing function names
- Passed/failed counts
- Error messages
- Specific failing test cases

```python
# Example output parsing
def parse_mal_test_output(output):
    # Find: "Results: X passed, Y failed"
    # Extract missing functions from "'funcname' not found"
    # Return: {passed, failed, missing_functions, errors}
```

### Skill 2: Code Pattern Recognition
Analyze existing code to understand:
- Where to add new special forms (in EVAL, before arithmetic)
- How to structure MalFunction classes
- Pattern for variadic parameters
- Pattern for TCO (ast/env updates with continue)

### Skill 3: Minimal Patch Generation
Generate MINIMAL changes:
- Add only what's needed for missing functions
- Follow existing code style
- Don't refactor working code
- Use Edit tool with precise old_string/new_string

### Skill 4: Fuzzy Diff Application
When Edit tool fails with "Hunk mismatch":
- Search nearby lines (±20) for context
- Adjust line numbers in old_string
- Or use more context lines

### Skill 5: Test Data File Creation
Create required test files:
- `tests/test.txt` - File I/O tests
- `tests/inc.mal` - Function definitions
- etc.

## Workflow

### Autonomous Iteration

For each iteration:

1. **OBSERVE** (Run tests)
   ```python
   cd /c/dev/AutoDev/mal
   python test.py tests/stepX.mal python stepX.py
   ```

2. **ORIENT** (Analyze)
   - Read current stepX.py
   - Check what functions are missing
   - Look at reference implementation: `mal/_mal/impls/python3/stepX_*.py`
   - Find similar patterns in existing code

3. **DECIDE** (Generate patch)
   - Identify what to add (special form? function? class?)
   - Read surrounding code for context
   - Use Edit tool to add minimal code
   - Handle variadic params, TCO, metadata as needed

4. **ACT** (Verify)
   - Run tests again
   - Check progress (fewer missing = good)
   - If success: git commit
   - Update MEMORY.md with what was learned

5. **LOOP** (Repeat)
   - Continue until tests pass
   - Max 20 iterations default
   - Report final status

## Decision Guidelines

### When to Add Special Forms
Add to EVAL function if first.value == 'formname':
- File operations: `slurp`, `read-string`, `eval`
- Atoms: `atom`, `atom?`, `deref`, `reset!`, `swap!`
- Metadata: `with-meta`, `meta`
- Comparison: `=`, `<`, `>`, `<=`, `>=`
- Collections: `list`, `list?`, `empty?`, `count`
- String: `str`, `pr-str`, `prn`, `println`, `readline`

### When to Add Reader Macros
In `read_form` function in tokenization/reading:
- `@` prefix → `(deref obj)`
- `^` prefix → `(with-meta obj metadata)`
- `'` prefix → `(quote obj)`

### When to Add New Types
- Step 1: MalNumber, MalString (already done)
- Step 2: MalList, MalVector (already done)
- Step 3: MalHashMap (already done)
- Step 4: MalKeyword, MalSymbol (already done)
- Step 5: MalFunction (already done)
- Step 6: MalAtom, metadata support (add meta attribute)

### Common Pitfalls to Avoid

1. **Forgetting TCO**: When adding special forms that call EVAL, use `continue` for tail position
2. **Wrong indentation**: Special forms are inside `if isinstance(first, MalSymbol):`
3. **Missing variadic**: Check for `&` in parameter lists
4. **Eval_ast vs EVAL**: Use `eval_ast` for evaluating elements, `EVAL` for full evaluation
5. **Function application**: After special forms, handle general function calls
6. **String escapes**: Handle `\\n`, `\\"`, `\\\\` in MalString.__str__
7. **Comparison**: Vectors and Lists can compare equal if contents match

## Success Criteria

### Iteration Success
- Fewer missing functions than before
- More tests passing
- No regressions (previously passing tests still pass)

### Final Success
- All tests passing for the step
- Can run the step's test file successfully
- Code follows existing patterns
- Git committed with message

### Failure Modes
- Hunk mismatch in Edit → Use more context or adjust line numbers
- Tests still failing after patch → Analyze why, try different approach
- Regression → Check what broke, revert or fix
- Empty/None response from LLM → Try different prompt or smaller context

## Memory Updates

After each successful iteration, update MEMORY.md:

```markdown
## stepX.py - YYYY-MM-DD
**Status**: SUCCESS / PROGRESS
**Learned**:
- [Pattern discovered during implementation]
- [Common pitfall to avoid]
- [Useful code pattern for future steps]
```

## Troubleshooting

### Docker Path Issues on Windows
```bash
# Use forward slashes in volume mounts
docker run --rm -v "C:/dev/AutoDev:/work" ...
```

### Python Import Errors
```bash
# Ensure project root in path
sys.path.insert(0, str(Path(__file__).parent))
from ooda.observe import Observer
```

### Test Not Found
```bash
# Check test file exists
ls mal/tests/step*_file.mal
# Or run all tests for a step
python test.py tests/step6_file.mal python step6.py
```

### Git Commit Failed
```bash
# Check git status
git status
# Configure git if needed
git config user.email "autodev@local"
git config user.name "AutoDev"
```

---

## Agent Instructions

When activated for autonomous development:

1. **Start by running tests** to see what's missing
2. **Read the current implementation** to understand patterns
3. **Check reference implementation** if unsure about requirements
4. **Make minimal edits** - don't refactor
5. **Verify after each change** by running tests again
6. **Commit successful iterations**
7. **Update MEMORY.md** with learnings
8. **Report progress clearly** after each iteration

You are autonomous but should:
- Ask for help only if blocked after 3 attempts
- Report what you tried and why it failed
- Suggest alternative approaches
- Never make destructive changes (git reset --hard, etc.) without asking
