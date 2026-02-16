# AutoDev Run Analysis - Mal Step 4

**Date:** 2026-02-15
**Iterations:** 14
**Successful:** 3 | **Failed:** 11

---

## The Problem: Patches "Succeed" But Don't Add Code

### Root Cause: Weak Verification

The `VerificationSuite.verify_all()` only checks:
1. **Syntax** - Is Python valid?
2. **Compilation** - Does it compile?

It does **NOT** check if the required functions were actually added!

### What Happened

| Iteration | Status | Result |
|-----------|--------|--------|
| 1 | SUCCESS | Patch applied & verified ✓ - **BUT functions still missing!** |
| 2 | FAIL | Hunk start out of range: 785 |
| 3 | FAIL | Hunk mismatch at line 434 |
| 4 | SUCCESS | Patch applied & verified ✓ - **BUT functions still missing!** |
| 5 | SUCCESS | Patch applied & verified ✓ - **BUT functions still missing!** |
| 6-14 | FAIL | All hunk mismatches |

### Evidence

```bash
# After 3 "successful" patches:
$ grep "def list(" mal/step4.py
# (empty - not found)

$ grep "elif first.value == 'if':" mal/step4.py
# (empty - not found)

# All backups are identical (15960 bytes) - no actual changes
```

---

## Secondary Issue: Hunk Mismatches

After each patch, the file changes. But LLM generates patches based on the *original* file, so line numbers become wrong.

```
Iteration 1: LLM sees 522 lines, generates patch for line 434
  → Patch "succeeds" (empty or no real change)

Iteration 2: LLM still sees 522 lines (context wasn't updated)
  → Generates patch for line 785
  → FAIL: "Hunk start out of range"
```

---

## Issues Found

### 1. Verification Doesn't Test Functionality ⚠️ **CRITICAL**

**Current:** Only checks syntax and compilation
**Needed:** Run actual Mal tests to verify functions work

```python
# Current verification (ooda/act.py:238-262)
def verify_all(self, file_path: str):
    # 1. Syntax check
    # 2. Import check
    # MISSING: Actual test run!
```

### 2. Patches Not Logged for Debugging

**Problem:** Can't see what the LLM actually generated
**Solution:** Save patches to iteration logs

### 3. Context Not Updated Between Iterations

**Problem:** LLM thinks file still has 522 lines after changes
**Solution:** Refresh context with actual current code

### 4. Prompt Doesn't Require Implementation

**Problem:** LLM might generate placeholder code
**Solution:** Explicitly require "working implementation, not placeholders"

---

## Fixes Needed

### Fix 1: Run Actual Tests for Verification

```python
# In ooda/act.py, modify verify_all()
def verify_all(self, file_path: str) -> Tuple[bool, List[str]]:
    messages = []
    all_passed = True

    # 1. Syntax check
    syntax_ok, syntax_msg = self.check_syntax(file_path)
    messages.append(f"Syntax: {'[OK]' if syntax_ok else '[FAIL]'} {syntax_msg}")
    if not syntax_ok:
        return False, messages

    # 2. RUN ACTUAL TESTS via Docker
    from ooda.observe import Observer
    observer = Observer(self.project_root)
    success, output = observer.run_tests()

    messages.append(f"Tests: {'[OK]' if success else '[FAIL]'}")

    # Parse and show what's still missing
    if not success:
        parsed = observer.parse_mal_test_output(output)
        missing = parsed.get("missing_functions", [])
        if missing:
            messages.append(f"Still missing: {', '.join(missing[:5])}")

    return success, messages
```

### Fix 2: Log Patches for Debugging

```python
# In ooda/decide.py, when logging iteration
entry = {
    "iteration": iteration,
    "decide": {
        "model": model,
        "attempts": attempt,
        "patch": patch,  # ADD THIS
        "patch_size": len(patch)
    },
    ...
}
```

### Fix 3: Better Prompt Engineering

Update `prompts/mal_patch_generation.txt`:

```
## CRITICAL REQUIREMENTS
- Generate WORKING CODE, not placeholders
- Include complete function implementations
- Add special forms to EVAL's first.value checks
- Add built-ins as actual functions
- NO "TODO" comments or stubs
```

---

## Test Results After Run

```
[FAIL] Line 5: (list)           → 'list' not found
[FAIL] Line 7: (list? (list))   → 'list?' not found
[FAIL] Line 9: (list? nil)      → 'list?' not found
[FAIL] Line 11: (empty? (list)) → 'empty?' not found
[FAIL] Line 13: (empty? (list 1)) → 'empty?' not found
[FAIL] Line 15: (list 1 2 3)    → 'list' not found
[FAIL] Line 17: (count ...)     → 'count' not found
[FAIL] Line 23: (if ...)        → 'if' not found
... (and more)
```

**Status:** All 19 functions still missing

---

## Recommended Next Steps

1. **Update Verification** - Run actual Mal tests instead of just syntax check
2. **Log Patches** - Save what LLM actually generates for debugging
3. **Refresh Context** - Update current_code in observe phase after each patch
4. **Improve Prompt** - Be more explicit about needing working implementations

---

## What Worked

- ✅ Docker test execution
- ✅ Error parsing (correctly identified 19 missing functions)
- ✅ LLM integration (GLM-4.5-Air responded)
- ✅ Progress monitoring
- ✅ Rollback on failed patches

## What Didn't Work

- ❌ Verification (passed empty/no-op patches)
- ❌ Patch application (hunk mismatches after file changes)
- ❌ Context refresh (LLM not seeing updated code)
- ❌ Debugging (can't see what LLM generated)
