---
name: next
description: Fetch top Ready issue and run autodev
argument-hint: [--dry-run] [--issue N] [--worktree PATH]
---

# /next

Fetch the top issue from the "ready" column and run autodev to implement it.
Can also be called with `--issue N` to target a specific issue.
When called by `/batch`, includes `--worktree PATH` for isolated execution.

## Workflow

1. **Fetch top ready issue:**
   ```bash
   # Default: top ready issue
   gh issue list --label ready --state open --limit 1 --json number,title,body

   # Or: specific issue (used by /batch)
   gh issue view N --json number,title,body,labels
   ```

2. **AI Overrule Check:**
   - Parse issue body for `Depends on: #N` - verify dependency is closed
   - Parse for `Conflicts with: #N` - verify #N is not currently in-progress
   - Parse for `Prerequisite: path/to/file` - verify file exists
   - If blocked: Log reason, inform user, suggest alternative

3. **Parse test checkboxes:**
   - Extract checked tests from issue body
   - Store for validation during/after autodev

4. **Create worktree (if --worktree specified or /batch mode):**
   ```bash
   git worktree add .claude/worktrees/task-N -b task-N
   ```

5. **Move to in-progress:**
   ```bash
   gh issue edit N --add-label in-progress --remove-label ready
   ```

6. **Invoke autodev:**
   ```bash
   # Default (main branch)
   /autodev "issue description from body"

   # Worktree mode (from /batch)
   /autodev "issue description" --worktree .claude/worktrees/task-N
   ```

## AI Overrule Logic

Before starting work on an issue, evaluate if it's appropriate:

### Dependency Check
```
If issue body contains "Depends on: #N":
  - Fetch issue #N state
  - If #N is not CLOSED:
    - BLOCK with message: "Issue #N depends on open issue #N"
    - Suggest: "Complete #N first, or remove dependency"
```

### Conflict Check
```
If issue body contains "Conflicts with: #N":
  - Fetch issue #N labels
  - If #N has label "in-progress":
    - BLOCK with message: "Issue #M conflicts with in-progress #N (same files)"
    - Suggest: "Wait for #N to complete, or use /batch for automatic scheduling"
```

### Prerequisite Check
```
If issue body contains "Prerequisite: path/to/file":
  - Check if file exists
  - If missing:
    - BLOCK with message: "Missing prerequisite: path/to/file"
    - Suggest: "Create the prerequisite first"
```

### Context Check
```
If current project state doesn't support this task:
  - Example: Task requires a component that doesn't exist yet
  - BLOCK with message explaining why
  - Suggest: "Start with foundation tasks first"
```

### Parallel Eligibility Check (for /batch)
```
When called with --batch-mode:
  - Return ELIGIBLE or BLOCKED status (don't prompt user)
  - BLOCKED reasons: unresolved dependencies, active conflicts
  - ELIGIBLE: all checks pass, can start immediately
```

## Test Extraction

Parse the issue body for checked test checkboxes:

```
## Tests to Run
- [x] unit_tests        ← This one is checked
- [ ] integration_tests  ← This one is not
```

Store checked tests in `logs/kanban_state.json`:
```json
{
  "current_issue": 42,
  "tests_to_run": ["unit_tests", "integration_tests"]
}
```

## --dry-run Option

If `--dry-run` is specified:
- Show which issue would be fetched
- Show dependency/conflict/prerequisite check results
- Show what autodev would be invoked with
- Show worktree path that would be created
- DO NOT create worktree, move issue, or run autodev

## Example Output

```
/next

📋 Fetching top Ready issue...

Issue #42: Add user authentication
Labels: ready
Tests: unit_tests, integration_tests

✓ No dependencies blocking
✓ No conflicts with in-progress tasks
✓ No prerequisites missing

Moving to in-progress...
Running autodev...
```

## Error Handling

**No ready issues:**
```
No issues found in "ready" column.
Create a new task issue with label "ready",
or move existing backlog issues to ready.
```

**Blocked by dependency:**
```
Issue #42 is blocked by open issue #40.
Complete #40 first, or update #42 to remove the dependency.
```

**Blocked by conflict:**
```
Issue #42 conflicts with in-progress issue #44 (same files).
Wait for #44 to complete, or use /batch for automatic scheduling.
```

**Missing prerequisite:**
```
Issue #42 requires missing file: src/auth/auth_service.py
Create this file first or update the issue.
```
