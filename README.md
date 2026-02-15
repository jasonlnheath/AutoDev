# AutoDev

**Autonomous Development Loop using OODA (Observe, Orient, Decide, Act)**

## Quick Start

1. Launch Claude Code in this directory
2. Read `NEXT_STEPS.md` for the implementation plan
3. Start with: "Implement Phase 1: Project Setup"

## Project Goal

Build an AI system that can autonomously:
- Read code and run tests
- Learn from errors and previous fixes
- Generate working code patches
- Apply patches and verify success
- Iterate until all tests pass

## Status

✅ **Phase 6 Complete** - All phases implemented and validated (91 tests passing)

### Completed Phases
- [x] Phase 1: Project Setup
- [x] Phase 2: Orient Phase - Context Memory (18 tests passing)
- [x] Phase 3: Decide Phase - LLM Integration (24 tests passing)
- [x] Phase 4: Act Phase - Patch Application (25 tests passing)
- [x] Phase 5: Full Loop Integration (14 tests passing)
- [x] Phase 6: Testing & Validation (10 tests passing)

### Test Coverage Summary

| Phase | Module | Tests | Status |
|-------|--------|-------|--------|
| 1 | Project Setup | - | ✅ Complete |
| 2 | Orient Phase | 18 | ✅ All passing |
| 3 | Decide Phase | 24 | ✅ All passing |
| 4 | Act Phase | 25 | ✅ All passing |
| 5 | Loop Integration | 14 | ✅ All passing |
| 6 | Validation | 10 | ✅ All passing |
| **Total** | | **91** | **✅ All passing** |

## Quick Start

```bash
# Run AutoDev with defaults
python autodev.py

# Fix a specific file
python autodev.py -f test.py

# Limit iterations
python autodev.py --max-iterations 5

# Verbose output
python autodev.py --verbose

# Require human approval for patches
python autodev.py --approve

# Watch progress
python autodev.py --watch
```

## Architecture

```
OBSERVE → ORIENT → DECIDE → ACT → (repeat)
  ↓         ↓        ↓       ↓
Code     Context   LLM    Patches
Tests    Memory          Verify
Errors
```

## Documentation

- **NEXT_STEPS.md** - Full implementation plan
- **docs/** - Detailed documentation (coming soon)

## Related Projects

- **mal-python-impl** - Mal interpreter (Steps 0-3)
- **HeathAudio/.claude/skills/byterover** - Context tree and GLM integration

---

**Created:** 2025-02-15
**Location:** C:\dev\AutoDev\
