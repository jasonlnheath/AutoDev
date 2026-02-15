# AutoDev - Autonomous Development Loop

**Project Goal:** Build an autonomous development loop that uses the OODA (Observe, Orient, Decide, Act) cycle to iteratively improve code with minimal human intervention.

**Status:** Project initialized. Ready to begin implementation.

---

## Project Context

This project builds on the Mal interpreter implementation (Steps 0-3) and demonstrates an autonomous development loop architecture. The goal is to create a system that can:

1. **Observe**: Read code, run tests, capture errors
2. **Orient**: Query context/pattern memory for relevant information
3. **Decide**: Generate code patches using an LLM
4. **Act**: Apply patches and verify tests pass

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        OODA Loop                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  OBSERVE  ──→  ORIENT  ──→  DECIDE  ──→  ACT            │
│     │            │           │          │                   │
│     ▼            ▼           ▼          ▼                   │
│  Read code   Query    Generate    Apply                   │
│  Run tests   context   patches    patches                │
│  Capture     memory    (LLM)      Verify                 │
│  errors                                                       │
│     │            │           │          │                   │
│     └────────────┴───────────┴──────────┘                   │
│                      │                                       │
│                      ▼                                       │
│                 Tests Pass?                                 │
│                    / \                                       │
│                   No   Yes                                    │
│                  /       \                                    │
│            Repeat     Complete                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites Already Met

✅ **Mal Implementation** (Steps 0-3)
- Located at: `C:\dev\mal-python-impl\`
- 185 tests passing
- Proven test infrastructure

✅ **OODA Driver Framework**
- Located at: `C:\dev\mal-python-impl\ooda_driver.py`
- Demonstrates the loop structure
- Ready for extension

✅ **Websearch Fix**
- GLM summarization now working reliably
- Token limit increased to 1500
- Retry logic with exponential backoff

✅ **Byterover System**
- Context Tree for memory
- GLM client for LLM access
- MCP server integration

---

## Immediate Next Steps

### Phase 1: Project Setup (Do This First)

1. **Copy Mal project to AutoDev workspace**
   ```bash
   cp -r C:/dev/mal-python-impl/* C:/dev/AutoDev/
   ```

2. **Create AutoDev-specific byterover integration**
   - Create local copy of byterover modules
   - Modify for autonomous loop needs
   - Keep original byterover untouched

3. **Set up project structure**
   ```
   AutoDev/
   ├── mal/              # Mal implementation
   ├── byterover/        # Local byterover copy
   ├── ooda/             # OODA loop implementation
   ├── config/           # Configuration files
   └── logs/             # Iteration logs
   ```

---

### Phase 2: Orient Phase - Context Memory

**Goal:** Build a working context/query system that learns from iterations.

**Tasks:**
- [ ] Create local Context Tree for AutoDev
- [ ] Implement pattern extraction from code changes
- [ ] Build similarity search for error patterns
- [ ] Create "lesson learned" curation system

**Files to Create:**
- `byterover/local_context.py` - Local context tree
- `ooda/orient.py` - Orient phase logic
- `config/memory_rules.json` - What to remember

---

### Phase 3: Decide Phase - LLM Integration

**Goal:** Generate working code patches using GLM-4.5/Opus.

**Tasks:**
- [ ] Design prompt template for patch generation
- [ ] Integrate GLM client for code generation
- [ ] Implement validation (generated code must be syntactically valid)
- [ ] Add fallback strategies (retry with different prompts)

**Files to Create:**
- `ooda/decide.py` - Decide phase logic
- `prompts/patch_generation.txt` - Prompt templates
- `config/llm_settings.json` - Model parameters

---

### Phase 4: Act Phase - Patch Application

**Goal:** Safely apply patches and verify they work.

**Tasks:**
- [ ] Implement diff-based patch application
- [ ] Add rollback on test failure
- [ ] Create verification suite (syntax check, type check, tests)
- [ ] Build iteration logging system

**Files to Create:**
- `ooda/act.py` - Act phase logic
- `ooda/patcher.py` - Diff application
- `logs/iteration_template.json` - Log format

---

### Phase 5: Full Loop Integration

**Goal:** Connect all phases and run autonomously.

**Tasks:**
- [ ] Create main loop orchestrator
- [ ] Add progress monitoring
- [ ] Implement safety limits (max iterations, timeout)
- [ ] Build human-in-the-loop intervention points

**Files to Create:**
- `autodev.py` - Main entry point
- `config/limits.json` - Safety parameters
- `monitor/progress.py` - Progress tracking

---

## Phase 6: Testing & Validation

**Goal:** Prove the system works end-to-end.

**Test Scenarios:**
1. **Simple Bug Fix**: Introduce a syntax error, let AutoDev fix it
2. **Feature Addition**: Add a new function to Mal, verify tests pass
3. **Refactoring**: Ask AutoDev to improve code structure
4. **Multi-Step**: Complex change requiring multiple iterations

**Success Criteria:**
- Loop completes without human intervention
- All tests pass at completion
- Iteration log shows learning
- No regression in existing functionality

---

## Implementation Priority

| Priority | Phase | Estimated Time | Dependencies |
|----------|-------|----------------|--------------|
| 🔥 High | Phase 1 | 30 min | None |
| 🔥 High | Phase 2 | 2-3 hours | Phase 1 |
| 🔥 High | Phase 3 | 2-3 hours | Phase 2 |
| Medium | Phase 4 | 2 hours | Phase 3 |
| Medium | Phase 5 | 1-2 hours | All phases |
| Low | Phase 6 | Ongoing | Working system |

---

## Key Design Decisions to Make

### 1. Context Memory Scope
**Question:** What should the system remember across iterations?

**Options:**
- A) Only error patterns and fixes (minimal)
- B) Full code snapshots with diffs (moderate)
- C) All decisions with reasoning (extensive)

**Recommendation:** Start with (A), expand to (B) if needed.

---

### 2. LLM Model Selection
**Question:** Which model for patch generation?

**Options:**
- A) GLM-4.5-Air (fast, cheap, good for simple fixes)
- B) GLM-5 (slower, more expensive, better reasoning)
- C) Hybrid: Air for simple, 5 for complex

**Recommendation:** Start with (A), use (C) if accuracy issues.

---

### 3. Safety Limits
**Question:** How to prevent infinite loops or bad patches?

**Options:**
- A) Hard limit on iterations (e.g., 10)
- B) Time-based timeout (e.g., 5 minutes)
- C) Human approval required for each patch
- D) Combination of above

**Recommendation:** (D) - 10 iteration limit + human approval option.

---

## Quick Start Command

When you launch Claude Code in this directory:

```bash
# 1. Copy the Mal implementation
cp -r C:/dev/mal-python-impl/* .

# 2. Create project structure
mkdir -p {byterover,ooda,config,prompts,logs,monitor}

# 3. Start with Phase 1
# Ask: "Implement Phase 1: Project Setup"
```

---

## Reference Materials

**Mal Implementation:**
- Location: `C:\dev\mal-python-impl\`
- Tests: 185 passing across Steps 0-3

**OODA Driver:**
- Location: `C:\dev\mal-python-impl\ooda_driver.py`
- Demonstrates loop structure

**Byterover:**
- Location: `C:\dev\HeathAudio\.claude\skills\byterover\`
- Context Tree, GLM client, MCP server

**Websearch:**
- Location: `C:\Users\jason\.claude\lib\websearch\`
- GLM summarization (now fixed)

---

## Success Metrics

When AutoDev is complete:

1. ✅ Can fix a simple bug without human help
2. ✅ Learns from previous iterations (doesn't repeat mistakes)
3. ✅ Generates syntactically valid code
4. ✅ All tests pass after loop completes
5. ✅ Complete iteration log available

---

## Next Session

Launch Claude Code in `C:\dev\AutoDev\` and start with:

> "Implement Phase 1: Project Setup - copy Mal implementation, create local byterover integration, set up project structure"

---

**Last Updated:** 2025-02-15
**Project:** AutoDev
**Status:** Initialized, ready for Phase 1
