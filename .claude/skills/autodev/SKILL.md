---
name: autodev
description: Multi-agent autonomous development workflow with hybrid OODA + Red-Green-Refactor for test-driven development
---

# AutoDev v4 - Hybrid OODA + Red-Green-Refactor

**Purpose:** Orchestrate parallel multi-agent workflow with test-first methodology, automatic iteration, and code quality refinement.

## Invocation

```
/autodev [project_name] [--mode=test-first|standard] [--backend=sonnet|opus|haiku] [--frontend=sonnet|opus|haiku] [--test=sonnet|opus|haiku]
```

**Modes:**
- `test-first` (default for DSP): RED → GREEN → REFACTOR cycle
- `standard`: Direct implementation with post-hoc testing

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Opus - Main Session)               │
│  Role: Strategic oversight, task classification, escalation         │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ PHASE 0: Task Classification
         ▼
    ┌────────────────────────────────────────┐
    │  Test-First Eligible?                  │
    │  • DSP components, algorithms          │
    │  • Signal processing                   │
    │  • Audio engine changes                │
    └────────────────────────────────────────┘
         │                    │
         │ YES                │ NO
         ▼                    ▼
┌─────────────────┐    ┌─────────────────┐
│  TEST-FIRST     │    │   STANDARD      │
│  WORKFLOW       │    │   WORKFLOW      │
└─────────────────┘    └─────────────────┘
         │                    │
         ▼                    │
┌─────────────────┐           │
│ PHASE 1A: SPEC  │           │
│ Generate test   │           │
│ specification   │           │
└─────────────────┘           │
         │                    │
         ▼                    │
┌─────────────────┐           │
│ PHASE 1B: RED   │           │
│ Confirm test    │           │
│ FAILS           │           │
└─────────────────┘           │
         │                    │
         └────────┬───────────┘
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PHASE 2: GREEN (OODA Loop)                      │
│                                                                     │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│   │ OBSERVE  │ → │ ORIENT   │ → │ DECIDE   │ → │   ACT    │        │
│   │ Build &  │   │ Analyze  │   │ Generate │   │ Apply &  │        │
│   │ Test     │   │ Patterns │   │ Patch    │   │ Verify   │        │
│   └──────────┘   └──────────┘   └──────────┘   └──────────┘        │
│         ↑                                              │            │
│         └──────────────────────────────────────────────┘            │
│                     Loop until PASS (max 10 iter)                   │
└─────────────────────────────────────────────────────────────────────┘
                  │
                  ▼ PASS
┌─────────────────┐
│ PHASE 3: TEST   │
│ Independent     │
│ verification    │
│ (clean context) │
└─────────────────┘
         │
         ▼ PASS
┌─────────────────┐
│ PHASE 4:        │
│ REFACTOR        │
│ Code quality    │
│ (preserve tests)│
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ PHASE 5: VERIFY │
│ Final build +   │
│ commit          │
└─────────────────┘
```

---

## Phase 0: Task Classification

Determine workflow mode based on task type:

### Test-First Eligible
- New DSP components
- Algorithm implementations
- Signal processing changes
- Audio engine modifications
- Filter/transform code
- Any code with measurable I/O

### Standard Workflow
- UI changes
- Configuration files
- Build system updates
- Documentation
- File structure changes
- Visual/design work

**Implementation:**
```python
def classify_task(task_description: str) -> str:
    """Determine if task needs test-first approach."""

    test_first_keywords = [
        'dsp', 'audio', 'signal', 'process', 'filter',
        'transform', 'algorithm', 'meter', 'gain',
        'mix', 'reverb', 'delay', 'compressor'
    ]

    if any(kw in task_description.lower() for kw in test_first_keywords):
        return "test-first"
    return "standard"
```

---

## Phase 1A: SPEC Agent (Test-First Only)

Generate test specification BEFORE implementation.

**Input:** Component requirements
**Output:** `tests/spec/{component}_spec.md`

### Specification Template

```markdown
# Test Specification: {ComponentName}

## Overview
Brief description of what's being tested.

## Test Cases

### Test 1: {test_name}
**Input:** {description}
**Expected Output:** {description}
**Tolerance:** {acceptable deviation}

### Test 2: {test_name}
...

## Edge Cases
- Silence input
- Maximum signal
- Rapid parameter changes
- Sample rate transitions

## Pass Criteria
- All test cases pass within tolerance
- No crashes or assertions
- Performance within limits
```

### SPEC Agent Prompt

```python
spec_agent_prompt = """
You are the **SPEC Agent** generating test specifications.

## Component: {component_name}
## Requirements:
{requirements}

## Your Task
Generate a comprehensive test specification at:
  {project_path}/tests/spec/{component_name}_spec.md

Include:
1. Test cases with inputs/expected outputs
2. Tolerance values for floating-point comparisons
3. Edge cases (silence, max signal, rapid changes)
4. Performance criteria (CPU, latency)

Output JSON state to: {project_path}/logs/spec_state.json
"""
```

---

## Phase 1B: RED Phase (Test-First Only)

Confirm test fails before implementation.

```bash
# Run the test (should FAIL)
python tests/{component}_test.py

# Expected output:
# FAILED - {component} not implemented

# If test PASSES unexpectedly:
# - Test may be wrong (fix test)
# - Component may already exist (skip to GREEN)
```

### RED Phase Agent

```python
red_agent_prompt = """
You are the **RED Agent** verifying test failure.

## Test File: {test_file}

## Your Task
1. Run: python {test_file}
2. Verify test FAILS (expected - component not implemented)
3. Report failure details

## Output
Write to: {project_path}/logs/red_state.json

```json
{
  "status": "red",  // Test failed as expected
  "test_file": "{test_file}",
  "failures": ["list of failing assertions"],
  "ready_for_green": true
}
```

If test unexpectedly passes, set ready_for_green: false and explain.
"""
```

---

## Phase 2: GREEN Phase (OODA Loop)

Implement until tests pass using OODA cycle.

### OODA Cycle Implementation

```
┌─────────────────────────────────────────────────────────────┐
│                      OODA LOOP                              │
│                                                             │
│  OBSERVE: Run tests, capture errors                         │
│      ↓                                                      │
│  ORIENT: Analyze failure, find patterns, check context      │
│      ↓                                                      │
│  DECIDE: Generate minimal patch to fix                      │
│      ↓                                                      │
│  ACT: Apply patch, rebuild, retest                          │
│      ↓                                                      │
│  PASS? ── YES ──→ Exit GREEN phase                          │
│      │                                                      │
│      NO                                                     │
│      ↓                                                      │
│  Loop (max 10 iterations)                                   │
└─────────────────────────────────────────────────────────────┘
```

### OBSERVE

```bash
# Build
cmake --build build --config Release

# Run tests
ctest --test-dir build -C Release
# OR for audio tests:
python tests/{component}_test.py
```

### ORIENT

```python
def orient(error_output: str, project_context: dict):
    """Analyze failure and find relevant patterns."""

    return {
        "error_type": classify_error(error_output),
        "similar_failures": check_history(error_output),
        "relevant_patterns": search_codebase(error_output),
        "suggested_fix": generate_hypothesis(error_output)
    }
```

### DECIDE

```python
def decide(observe_data: dict, orient_data: dict):
    """Generate minimal patch to fix the issue."""

    return {
        "patch": generate_minimal_patch(
            error=observe_data["error"],
            patterns=orient_data["relevant_patterns"],
            hypothesis=orient_data["suggested_fix"]
        ),
        "files_to_modify": [...],
        "confidence": 0.0-1.0
    }
```

### ACT

```bash
# Apply patch
# Rebuild
cmake --build build --config Release
# Retest
ctest --test-dir build -C Release
```

---

## Phase 3: TEST Agent (Independent Verification)

Fresh context verification that tests pass.

```python
test_agent_prompt = """
You are the **TEST Agent** - independent verification with clean context.

## CRITICAL RULES
- NEVER change test criteria
- NEVER adjust thresholds
- ONLY report pass/fail with measurements

## Component: {component_name}
## Test File: {test_file}

## Your Task
1. Run: python {test_file}
2. Report exact results
3. If FAIL, provide specific measurements

## Output
Write to: {project_path}/logs/test_state.json

```json
{
  "status": "passed|failed",
  "tests_run": 5,
  "tests_passed": 5,
  "tests_failed": 0,
  "failures": [],
  "measurements": {...}
}
```
"""
```

---

## Phase 4: REFACTOR Agent (NEW in v4)

Code quality improvements AFTER tests pass.

### Refactor Focus Areas

1. **DRY Violations** - Extract repeated code
2. **Magic Numbers** → Named constants
3. **Complex Conditionals** → Early returns
4. **Long Functions** → Smaller units
5. **Dead Code** → Remove
6. **Naming** → Clearer names

### Constraints

- **Preserve passing tests** (run after each change)
- **No functional changes** (behavior identical)
- **One refactoring at a time**
- **Rollback if tests fail**

### REFACTOR Agent Prompt

```python
refactor_agent_prompt = """
You are the **REFACTOR Agent** improving code quality.

## Component: {component_name}
## Files: {files_to_refactor}

## CRITICAL CONSTRAINTS
1. Tests MUST continue to pass
2. NO functional changes
3. Run tests after EACH refactoring
4. One refactoring at a time

## Focus Areas (in priority order)
1. DRY violations - extract repeated code
2. Magic numbers → named constants
3. Complex conditionals → early returns
4. Long functions → smaller units
5. Dead code removal
6. Unclear naming

## Process
For each refactoring:
1. Identify issue
2. Make minimal change
3. Run: python {test_file}
4. If PASS: commit, continue
5. If FAIL: rollback, skip this refactoring

## Output
Write to: {project_path}/logs/refactor_state.json

```json
{
  "status": "success|failed",
  "refactorings_applied": [
    {
      "type": "extract_constant",
      "description": "Extracted SAMPLE_RATE constant",
      "file": "processor.cpp",
      "tests_passed": true
    }
  ],
  "refactorings_skipped": [...],
  "final_test_status": "passed"
}
```
"""
```

---

## Phase 5: VERIFY & Commit

Final verification and commit.

```bash
# Final build
cmake --build build --config Release

# Run all tests
ctest --test-dir build -C Release

# Commit
git add -A
git commit -m "feat({component}): implement with tests

- Add {component} implementation
- Add test specification and tests
- Refactor for code quality

AutoDev: GREEN + REFACTOR complete"
```

---

## Parallel Execution (Backend + Frontend)

For full plugin development, Backend and Frontend run in parallel:

```python
# Spawn both agents
backend_agent = Task(
    subagent_type="general-purpose",
    description="Backend Agent",
    run_in_background=True,
    prompt=backend_prompt
)

frontend_agent = Task(
    subagent_type="general-purpose",
    description="Frontend Agent",
    run_in_background=True,
    prompt=frontend_prompt
)

# Wait for both
backend_result = TaskOutput(task_id=backend_agent, block=True, timeout=300000)
frontend_result = TaskOutput(task_id=frontend_agent, block=True, timeout=300000)
```

### Parallel Workflow

```
     ┌──────────────┐
     │ CLASSIFY     │
     │ (Phase 0)    │
     └──────────────┘
            │
    ┌───────┴───────┐
    ▼               ▼
┌────────┐     ┌────────┐
│BACKEND │     │FRONTEND│
│Test-   │     │Standard│
│First   │     │        │
└────────┘     └────────┘
    │               │
    ▼               ▼
 SPEC/RED        IMPLEMENT
    │               │
    ▼               ▼
 GREEN           GREEN
 (OODA)          (OODA)
    │               │
    ▼               ▼
 TEST            TEST
    │               │
    ▼               ▼
 REFACTOR       REFACTOR
    │               │
    └───────┬───────┘
            ▼
     ┌──────────────┐
     │ CONNECTION   │
     │ (Bridge)     │
     └──────────────┘
            │
            ▼
     ┌──────────────┐
     │ FINAL VERIFY │
     └──────────────┘
```

---

## Agent Models

**Default Model Assignment:**
- **Orchestrator:** Opus (strategic decisions, classification)
- **SPEC Agent:** Sonnet (test generation)
- **Backend Agent:** Sonnet (code implementation)
- **Frontend Agent:** Sonnet (GUI design)
- **TEST Agent:** Sonnet (verification)
- **REFACTOR Agent:** Sonnet (code quality)

---

## State File Schema

```json
{
  "project_name": "ComponentName",
  "workflow_mode": "test-first|standard",
  "created": "2026-03-01T12:00:00",

  "phases": {
    "classify": {
      "status": "completed",
      "mode": "test-first",
      "reason": "DSP component detected"
    },
    "spec": {
      "status": "completed",
      "spec_file": "tests/spec/component_spec.md"
    },
    "red": {
      "status": "completed",
      "test_failed": true
    },
    "green": {
      "status": "completed",
      "iterations": 3,
      "patches_applied": 3
    },
    "test": {
      "status": "passed",
      "tests_passed": 5,
      "tests_failed": 0
    },
    "refactor": {
      "status": "completed",
      "refactorings_applied": 4,
      "refactorings_skipped": 1
    },
    "verify": {
      "status": "completed",
      "committed": true
    }
  },

  "completed": true
}
```

---

## Progress Dashboard

```
==================================================
AutoDev v4 Progress: {component_name}
==================================================
Mode: test-first

✅ Phase 0: Classify → test-first (DSP)
✅ Phase 1A: SPEC → tests/spec/processor_spec.md
✅ Phase 1B: RED → Test failed as expected
⏳ Phase 2: GREEN (iteration 2/10)
    └─ Patch applied, rebuilding...
⬜ Phase 3: TEST
⬜ Phase 4: REFACTOR
⬜ Phase 5: VERIFY
==================================================
```

---

## Status Icons

- ⬜ Pending
- 🔄 Spawning
- ⏳ Running
- ✅ Passed
- ❌ Failed
- ⏱️ Timeout
- ⚠️ Warning
- 🔴 RED (test failing)
- 🟢 GREEN (test passing)
- 🔵 REFACTOR (improving)

---

## Completion Checklist

**Before declaring complete, verify:**

### Test-First Workflow
- [ ] Task classified correctly
- [ ] Test specification generated
- [ ] RED phase confirmed (test fails)
- [ ] GREEN phase completed (test passes)
- [ ] Independent TEST verification passed
- [ ] REFACTOR completed (tests still pass)
- [ ] Final build succeeds
- [ ] Changes committed

### Standard Workflow
- [ ] Task classified as standard
- [ ] Implementation completed
- [ ] Tests pass (post-hoc)
- [ ] REFACTOR completed
- [ ] Final build succeeds
- [ ] Changes committed

---

## Key Differences from v3

| v3 (Old) | v4 (Current) |
|----------|--------------|
| No test-first option | Hybrid: test-first OR standard |
| No SPEC phase | SPEC Agent generates test specs |
| No RED phase | RED confirms test fails first |
| GREEN only | GREEN via OODA loop |
| No REFACTOR phase | REFACTOR Agent for code quality |
| Single workflow | Adaptive based on task type |

---

## Tools Used

| Tool | Purpose |
|------|---------|
| AskUserQuestion | Classification clarification |
| Task | Spawn agents |
| TaskOutput | Get agent results |
| TaskStop | Kill hung agents |
| Read/Write/Edit | Source code, specs |
| Bash | Build, test, git |
| mcp__pencil__* | Frontend design |
| mcp__zai-mcp-server__* | Screenshot analysis |

---

## Notes

- **Test-First is default for DSP** - ensures correctness
- **OODA loop powers GREEN** - iterative problem solving
- **REFACTOR is mandatory** - code quality after functionality
- **Tests gate each phase** - can't skip to next without passing
- **State files enable resume** - interrupted workflows recoverable
