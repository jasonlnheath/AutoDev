# AutoDev - Claude Code Instructions

**Project:** Autonomous Development Loop (OODA) + Kanban Workflow
**Status:** Active

---

## Kanban + AutoDev Workflow

This repo contains the global kanban/autodev workflow, usable on any project.

### Commands

| Command | Description |
|---------|-------------|
| `/next` | Fetch top Ready issue → run autodev |
| `/batch` | Process all Ready issues in parallel (worktree-isolated) |
| `/autodev` | Run OODA loop on a task |

### Kanban Labels

| Label | Column |
|-------|--------|
| `backlog` | Not yet ready |
| `ready` | Ready to work on |
| `in-progress` | Being worked on |
| `review` | Complete, awaiting review |

### Batch Cycle

```
1. Move issues to "ready"     (GitHub Projects board)
2. /batch                      (AI works through all ready issues)
3. Review issues in "review"   (close or send back)
4. Repeat
```

### Issue Template Fields

- **Product Spec** - link to spec file + section
- **Acceptance Criteria** - checkboxes that must pass
- **Tests to Run** - which tests to run for validation
- **Dependencies** - `Depends on: #N` (blocks if #N is open)
- **Conflicts** - `Conflicts with: #N` (serializes if #N is in-progress)

### PostToolUse Hook

`hooks/PostToolUse.js` runs after every autodev completion:
- Moves issue from `in-progress` → `review`
- Checks if batch is complete (no remaining ready/in-progress)
- Prints batch completion banner when done

### Setup for a New Project

1. Copy `.claude/commands/next.md` and `batch.md` to project
2. Copy `.claude/hooks/PostToolUse.js` to project
3. Copy `.github/ISSUE_TEMPLATE/task.md` to project
4. Configure `hooks` in `.claude/settings.json`:
   ```json
   {
     "hooks": {
       "PostToolUse": [{ "command": "node .claude/hooks/PostToolUse.js" }]
     }
   }
   ```

---

## Quick Reference

When you ask me to work on this project, I'll reference:

- **NEXT_STEPS.md** - Full implementation plan with 6 phases
- **README.md** - Project overview
- **mal/** - Mal implementation (will copy from mal-python-impl)
- **byterover/** - Local byterover integration (will copy from HeathAudio)
- **ooda/** - OODA loop implementation (will build)

---

## Current Phase: Ready to Start Phase 1

**To begin, say:**
> "Implement Phase 1: Project Setup"

This will:
1. Copy Mal implementation from `C:\dev\mal-python-impl\`
2. Create local byterover integration
3. Set up configuration files

---

## Project Goals

Build an autonomous development loop that:
- **Observes**: Code, tests, errors
- **Orients**: Queries context memory for patterns
- **Decides**: Generates patches using LLM
- **Acts**: Applies patches, verifies success

---

## Key Files

| File | Purpose |
|------|---------|
| `NEXT_STEPS.md` | Detailed implementation plan (START HERE) |
| `README.md` | Project overview |
| `.claude/CLAUDE.md` | This file (project instructions) |

---

## Architecture

```
OODA Loop:
  OBSERVE → Read code, run tests, capture errors
  ORIENT  → Query context memory, find patterns
  DECIDE  → Generate patches (GLM-4.5/5)
  ACT     → Apply patches, verify
  → Repeat until tests pass
```

---

## When You Launch Claude Code Here

First time setup:
1. Say "Implement Phase 1: Project Setup"
2. I'll copy files and create structure
3. Then we'll implement each phase sequentially

---

## Notes

- **No other projects are affected** - This is a clean workspace
- **Local byterover copy** - We'll modify it for AutoDev needs
- **Mal tests passing** - 185 tests from Steps 0-3

---

## Technical Notes

- **Don't use bun** - It crashes. Use npm or python instead.

---

## Screenshot Tool (DPI-Aware)

**File:** `frontend/screenshot.py`

Capture plugin windows as JPG for frontend development and debugging.

```bash
# Basic capture (outputs to WindowTitle.jpg)
python frontend/screenshot.py "HeathAudioPluginTemplate"

# Specify output path
python frontend/screenshot.py "HeathAudioPluginTemplate" output.jpg

# With grid overlay (for measurements)
python frontend/screenshot.py "HeathAudioPluginTemplate" output.jpg --grid

# Adjust quality (lower = smaller file)
python frontend/screenshot.py "HeathAudioPluginTemplate" output.jpg --quality 75

# Verify process (avoid wrong window)
python frontend/screenshot.py "MyPlugin" output.jpg --process MyPlugin.exe

# List available windows
python frontend/screenshot.py --list
```

**Python API:**
```python
from frontend.screenshot import PluginScreenshot, capture_plugin

screenshot = PluginScreenshot()
img = screenshot.capture("WindowTitle", grid=True)
img.save("output.jpg", quality=85)

# Or quick capture
capture_plugin("WindowTitle", "output.jpg", quality=85)
```

---

## Monitor Scaling Note

**Monitor is scaled at 185%** - When analyzing mockup images:
- Captured dimensions must be divided by 1.85 to get actual GUI pixels
- Example: Mockup at 929x628 → Actual GUI at 502x340
- Target plugin size: **500 x 340 pixels**

---

## Current Project: HeathAudioPluginTemplate

Creating a reusable JUCE plugin template extracted from AmpBender.

**Deliverables:**
1. Specification document (YAML)
2. C++ template project (push to GitHub, clone for new projects)

**Includes from AmpBender:**
- Header bar (presets, save/load, zoom, OS, IN/OUT trim)
- Input/output meters
- LookAndFeel class
- WebView infrastructure
- About screen
- Backend functions (preset management, zoom, oversampling, trim)

**Center panel:** Empty placeholder (plugin-specific content)

---

**Created:** 2025-02-15
**Claude Code Workspace:** C:\dev\AutoDev\
