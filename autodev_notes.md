# AutoDev Field Test - Mal Step 4 Implementation

**Goal:** Use AutoDev to complete Mal Lisp Step 4 (if, fn, do, list functions)

**Date:** 2026-02-15

## LLM Integration Options

AutoDev supports cloud-based LLMs (no local model required). Configure via environment:

### Option 1: OpenAI (Recommended)
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
python autodev.py -f step4.py
```

### Option 2: Anthropic Claude
```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python autodev.py -f step4.py
```

### Option 3: OpenRouter (access to 100+ models)
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-or-...
export OPENAI_ENDPOINT=https://openrouter.ai/api/v1/chat/completions
export OPENAI_MODEL=anthropic/claude-3.5-sonnet
python autodev.py -f step4.py
```

### Option 4: Local LLM (Ollama)
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=ollama
export OPENAI_ENDPOINT=http://localhost:11434/v1/chat/completions
export OPENAI_MODEL=codellama:13b
python autodev.py -f step4.py
```

### Option 5: Existing GLM (Zhipu)
```bash
export LLM_PROVIDER=glm
export GLM_CODING_API_KEY=...
python autodev.py -f step4.py
```

---

## Setup

- Target: `mal/step4.py`
- Starting point: Copy of `step3.py`
- Test file: `tests/step4_if_fn_do.mal`
- Running via Docker for Unix dependencies

## Test Results - What's Missing

```
[FAIL] 'list' not found
[FAIL] 'list?' not found
[FAIL] 'empty?' not found
[FAIL] 'count' not found
[FAIL] 'if' not found
[FAIL] '=' not found
[FAIL] 'fn' not found (later in tests)
[FAIL] 'do' not found (later in tests)
```

---

## Notes

### Issues Found (Needs Improvement)

1. **Docker Path Issues on Windows** ⚠️
   - Git Bash translates `/workspace` incorrectly
   - **Workaround:** Use `bash -c "cd /workspace && ..."`
   - **Fix Needed:** Better cross-platform path handling

2. **Test Output Parsing**
   - Mal test format: `[FAIL] Line N: (test)`
   - `get_failed_tests()` doesn't parse this
   - **Fix Needed:** Update parser for Mal format

3. **Observer.run_tests() Needs Updating**
   - Currently returns compilation status
   - Should return actual Mal test results via Docker
   - **Partial Fix:** Added Docker support, needs integration

### What Works

1. **Docker Test Execution** ✅
   - Mal tests run successfully via Docker
   - Proper error output captured
   - 33/33 tests pass for Step 3

2. **Project Structure** ✅
   - Clean separation of OODA phases
   - Easy to understand and extend

3. **Configuration System** ✅
   - JSON config files work well
   - Easy to adjust limits and settings

4. **Context Memory** ✅
   - `LocalContextTree` persists patterns
   - Similarity search works

5. **Diff Application** ✅
   - Pure Python diff parser works
   - Patch application is reliable
   - Rollback works correctly

---

## Running AutoDev with Real LLM

Once you set an API key, run:

```bash
cd C:/dev/AutoDev

# Set your provider and key
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# Run AutoDev
python autodev.py -f step4.py --max-iterations 10 --verbose
```

The DECIDE phase will call the LLM to generate actual patches for Step 4!

---

## Required Patterns for Step 4

When AutoDev sees `'X not found`, it should:

1. **Recognize the missing function**
2. **Look up implementation pattern** from similar functions
3. **Add to appropriate location:**
   - Special forms (`if`, `fn`, `do`) → Add to EVAL's special form handling
   - Built-ins (`list`, `count`, `=`) → Add as built-in function
4. **Generate and apply patch**
5. **Verify with Docker test run**

---

## Docker + GLM Integration Complete ✅

**Status:** Integration working as of 2026-02-15

### What Works
- GLM-4.5-Air generates patches for missing Mal functions
- Docker runs Mal tests in isolated environment
- System detects 19 missing functions: list, list?, empty?, count, if, fn*, do, =, etc.
- Patches validated and applied

### Fixes Applied
1. **Progress Monitor KeyError** ✅
   - Fixed path for `success` field: `h.get("act", {}).get("success")`
   - Replaced Unicode symbols with ASCII: [OK] / [FAIL]

2. **Docker Path Translation** ✅
   - Windows paths converted to Docker format (C:\ → /c)
   - bash -c wrapper for proper command execution

3. **LLM Universal Client** ✅
   - Supports GLM, OpenAI, Anthropic, OpenRouter, Ollama
   - Configurable via LLM_PROVIDER env var

### Known Issues (Needs Improvement)
1. **Diff Application with Large Patches**
   - Hunk range mismatches when file content differs from expected
   - Fuzzy matching needed for better resilience

2. **LLM Prompt Engineering**
   - Generated patches sometimes don't match expected format
   - Could add more examples to prompt template

3. **Test Output Parsing**
   - Some edge cases in Mal output format not handled
   - Could improve regex patterns

---

## Test Run Results

```
Final State: max_iterations
Iterations: 3
Successful Patches: 1
Failed Patches: 2
Duration: 162.7 seconds
```

The system is operational and improving. Each iteration learns from previous attempts.
