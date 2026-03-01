---
name: batch
description: Batch process all Ready issues using worktree-isolated parallel execution
argument-hint: [--dry-run] [--max-parallel N]
---

# /batch

Fetch all issues from the "ready" column and run autodev on them in parallel using git worktrees.
Max parallel tasks: 2 (default, configurable with --max-parallel).

## Workflow

```
/batch
  │
  ├─> Fetch all "ready" issues
  │
  ├─> Sort by priority (issue number ascending = oldest first)
  │
  ├─> For each issue:
  │     ├─> Check dependencies (all "Depends on: #N" must be closed)
  │     ├─> Check conflicts (issues that share "Conflicts with: #N")
  │     │
  │     ├─> Eligible? Create git worktree → Launch autodev in background
  │     └─> Blocked? Log reason, skip for this batch
  │
  └─> After all launched tasks complete:
        ├─> Log batch completion summary
        └─> Report: "Batch complete. X tasks in review. Please review."
```

## Steps

### 1. Fetch All Ready Issues

```bash
gh issue list --label ready --state open --json number,title,body --limit 50
```

### 2. Sort & Filter

Sort by issue number (ascending). For each issue:

- **Parse dependencies:** `Depends on: #N` in the body - check if #N is closed via `gh issue view N --json state`
- **Parse conflicts:** `Conflicts with: #N` in the body - if #N is currently in-progress, defer this issue
- If blocked by unresolved dependency: skip with message
- If conflicts with in-progress: defer until next batch

### 3. Parallel/Series Logic

**Max parallel:** 2 (or --max-parallel value)

For each eligible issue (up to max-parallel limit):
1. Create a worktree: `git worktree add .claude/worktrees/task-{N} -b task-{N}`
2. Move issue to in-progress: `gh issue edit N --add-label in-progress --remove-label ready`
3. Launch autodev for this issue (in worktree context)

**Series (sequential):**
- Issue has unresolved `Depends on: #N` → wait until batch slot opens after #N completes
- Max parallel reached → queue until a slot frees up

### 4. Worktree-Based Execution

Each task runs in its own isolated worktree:

```
Task #101 → .claude/worktrees/task-101/   (branch: task-101)
Task #102 → .claude/worktrees/task-102/   (branch: task-102)
```

Benefits:
- No file conflicts between parallel tasks
- True isolation - each has its own working directory
- Easy per-task review via `git diff task-101..main`

### 5. Autodev Per Task

For each task worktree, invoke:
```
/autodev "description from issue body" --worktree .claude/worktrees/task-N
```

Autodev builds, tests, and moves the issue to "review" on success.

### 6. Batch Completion Check

After all launched tasks complete (or fail), check:

```bash
# Are there any remaining "ready" issues?
gh issue list --label ready --state open --limit 1 --json number

# Are there any "in-progress" issues?
gh issue list --label in-progress --state open --limit 1 --json number
```

If no ready AND no in-progress issues remain:
```
╔══════════════════════════════════════════════╗
║         BATCH COMPLETE                       ║
╠══════════════════════════════════════════════╣
║ Tasks moved to review: X                     ║
║ Tasks skipped (blocked): Y                   ║
║                                              ║
║ Next steps:                                  ║
║  1. Review tasks in "review" column          ║
║  2. Close completed tasks or send back       ║
║  3. Create follow-up issues if needed        ║
║  4. Run /batch again for next cycle          ║
╚══════════════════════════════════════════════╝
```

## --dry-run Option

If `--dry-run` is specified:
- Show all ready issues fetched
- Show dependency/conflict analysis for each
- Show which would run in parallel vs series
- Show worktree paths that would be created
- DO NOT create worktrees, move issues, or run autodev

## --max-parallel Option

Default: 2

```bash
/batch --max-parallel 1   # Force sequential
/batch --max-parallel 3   # Allow 3 concurrent tasks
```

## Example Output

```
/batch

📋 Fetching all Ready issues...

Found 4 ready issues:
  #101: Add user authentication module
  #102: Implement caching layer
  #103: Add OAuth support (Depends on: #101)
  #104: Write API documentation

Analyzing dependencies and conflicts...
  #101 ✓ No dependencies
  #102 ✓ No dependencies
  #103 ✗ Blocked - depends on open #101
  #104 ✓ No dependencies

Starting batch (max parallel: 2)...

Slot 1: Issue #101 → Worktree task-101 → autodev running...
Slot 2: Issue #102 → Worktree task-102 → autodev running...

[#101 complete] Moved to review. Opening slot 1...
Slot 1: Issue #104 → Worktree task-104 → autodev running...

[#102 complete] Moved to review. Opening slot 2...
[#103 is now eligible - #101 closed] Slot 2: Issue #103 → autodev running...

[#104 complete] Moved to review.
[#103 complete] Moved to review.

╔══════════════════════════════════════════════╗
║         BATCH COMPLETE                       ║
╠══════════════════════════════════════════════╣
║ Tasks moved to review: 4                     ║
║ Tasks skipped (blocked): 0                   ║
║                                              ║
║ Next steps:                                  ║
║  1. Review tasks in "review" column          ║
║  2. Close completed tasks or send back       ║
║  3. Create follow-up issues if needed        ║
║  4. Run /batch again for next cycle          ║
╚══════════════════════════════════════════════╝
```

## Error Handling

**No ready issues:**
```
No issues found in "ready" column.
Create task issues with label "ready" to begin.
```

**All blocked:**
```
All 3 ready issues are blocked by dependencies:
  #103: Blocked by open #101
  #105: Blocked by open #102
  #106: Blocked by open #101, #102

Resolve blocking issues first, then run /batch again.
```

**Partial failure:**
```
Batch complete with errors.
  ✓ #101 moved to review
  ✗ #102 autodev failed - still in-progress
  ✓ #104 moved to review

Issue #102 needs manual attention.
Run /next --issue 102 to retry.
```

## Worktree Cleanup

After the user reviews and closes issues, clean up worktrees:

```bash
# Cleanup specific worktree after merge/close
git worktree remove .claude/worktrees/task-101
git branch -d task-101

# List all task worktrees
git worktree list | grep task-
```

The `/batch` command does NOT auto-cleanup worktrees — the user reviews and decides what to merge.
