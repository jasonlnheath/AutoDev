# AutoDev Autonomous Agent - Quick Reference

## What Is It?

A fully autonomous development agent that:
- **Runs the OODA loop** without manual intervention
- **Generates patches** using Claude Code (Sonnet/Opus)
- **Learns from experience** (MEMORY.md + git history)
- **Works until tests pass** (max 20 iterations per run)

## How to Use

### Method 1: Direct Invocation (Recommended)
```bash
# In Claude Code, simply invoke the agent by stating your goal:
"Use the autodev-autonomous agent to complete step6.py"
```

### Method 2: Python Script
```bash
cd C:\dev\AutoDev
python run_autonomous.py -f step6.py --max-iterations 20
```

### Method 3: Through Task Tool
```
[Use Task tool]
Subagent type: general-purpose
Prompt: "Use the autodev-autonomous agent to implement Step 7"
```

## Agent Capabilities

### Context Provided
- ✅ Project structure (C:\dev\AutoDev)
- ✅ Working patterns (TCO, EVAL structure, special forms)
- ✅ Test framework (Docker-based Mal tests)
- ✅ Git workflow (commit, history)
- ✅ Reference implementations (`mal/_mal/impls/`)

### Tools Available
- **Read**: Access any file
- **Edit**: Apply patches with fuzzy matching
- **Bash**: Run tests, git, Docker commands
- **Grep/Glob**: Search codebase
- **Write**: Create test files

### Skills Built-In
1. Parse test output (missing functions, errors)
2. Recognize code patterns (TCO, variadic, special forms)
3. Generate minimal patches (no refactoring)
4. Handle fuzzy diffs (adjust line numbers)
5. Create test data files
6. Update MEMORY.md with learnings

## What the Agent Does

### Per Iteration

```
[OBSERVE] cd mal && python test.py tests/step6_*.mal python step6.py
          → Tests: 45 passed, 12 failed
          → Missing: slurp, read-string, atom, atom?, ...

[ORIENT]  Read step6.py
          → Read mal/_mal/impls/python3/step6_*.py
          → Analyze patterns (special forms go in EVAL)

[DECIDE]  Use Edit tool to add missing functions
          → Add MalAtom class
          → Add slurp special form
          → Add atom, atom?, deref, reset!, swap!
          → Add metadata support

[ACT]     Run tests again
          → Tests: 52 passed, 5 failed
          → Progress: +7 functions added
          → Commit: git commit -m "AutoDev iteration 1"

[LOOP]    Repeat until tests pass or max iterations
```

### Success Indicators
- ✅ Fewer missing functions each iteration
- ✅ More tests passing
- ✅ No regressions
- ✅ Code follows existing patterns
- ✅ Git commits show progress

### Failure Recovery
- Hunk mismatch → Try more context lines
- Tests still failing → Analyze why, try different approach
- Regression → Revert and try again
- 3 failed attempts → Ask for help

## Configuration

### File Locations
```
C:\dev\AutoDev\
├── .claude\
│   └── agents\
│       └── autodev-autonomous\
│           ├── SKILL.md          # Agent context/skills
│           └── README.md         # This file
├── autodev_autonomous.py        # Original loop (manual)
├── run_autonomous.py             # New runner script
├── mal\
│   ├── step*.py                  # Implementation files
│   └── tests\
│       └── step*_*.mal           # Test files
├── MEMORY.md                     # Auto-updated learning
└── ooda/                          # OODA phase implementations
```

### Environment Variables (Optional)
```bash
# Not required - agent uses Claude Code's built-in tools
# But can be set for custom behavior:
export AUTODEV_MAX_ITERATIONS=20
export AUTODEV_TARGET_FILE=step6.py
```

## Example Session

### User Prompt
```
"Use the autodev-autonomous agent to complete step6.py"
```

### Agent Response
```
[AUTONOMOUS AGENT ACTIVATED]

Iteration 1/20:
[OBSERVE] Running tests...
  Tests: 45 passed, 8 failed
  Missing: slurp, read-string, atom, atom?, deref, reset!, swap!, with-meta

[ORIENT] Analyzing codebase...
  Current special forms: 15
  Reference: mal/_mal/impls/python3/step6_readstring.py
  Pattern: File ops go in special forms section

[DECIDE] Generating patch...
  [EDIT] Adding MalAtom class to step6.py
  [EDIT] Adding slurp special form
  [EDIT] Adding atom functions
  ... (7 edits total)

[ACT] Verifying...
  Tests: 52 passed, 1 failed
  Progress: +7 functions added
  [GIT] Committed as "AutoDev iteration 1"

Iteration 2/20:
  [OBSERVE] Tests: 52 passed, 1 failed
  Missing: eval

  [DECIDE] Adding eval special form...
  [EDIT] Added eval to EVAL function

  [ACT] Verifying...
  Tests: 55 passed, 0 failed
  [SUCCESS] All tests passing!

[MEMORY] Updated with:
  - Atom implementation pattern
  - File I/O with slurp
  - Metadata attachment pattern
  - eval requires root environment access
```

## Tips for Best Results

### 1. Start Fresh
```bash
# Ensure clean state
git checkout mal/step*.py
git pull
```

### 2. Set Realistic Expectations
- Simple steps (0-3): 1-3 iterations
- Medium steps (4-6): 5-10 iterations
- Complex steps (7-A): 10-20 iterations

### 3. Monitor Progress
```bash
# Watch git history
git log --oneline -5

# Check MEMORY.md for learnings
cat MEMORY.md | tail -50
```

### 4. Handle Blocks
If agent gets stuck (3 failed attempts):
- Check test file for specific requirements
- Look at reference implementation more carefully
- Try running tests manually to see actual errors
- Consider if step is incomplete (missing dependencies)

### 5. Verify Results
```bash
# Run full test suite for the step
cd mal
python test.py tests/step6_*.mal python step6.py
```

## Troubleshooting

### Agent not activating?
- Check SKILL.md exists at `.claude/agents/autodev-autonomous/SKILL.md`
- Ensure Claude Code has access to the project directory
- Try explicit invocation: "Use the autodev-autonomous agent..."

### Edit tool failing?
- Agent will automatically retry with more context
- Can adjust line numbers manually if needed
- Check for recent changes that shifted line numbers

### Tests not running?
- Check Docker is available: `docker ps`
- Verify test file exists: `ls mal/tests/step*_*.mal`
- Try manual test: `cd mal && python test.py ...`

### Git commits failing?
- Configure git: `git config user.email && git config user.name`
- Check git status: `git status`
- Ensure repo is clean: `git diff`

## Advanced Usage

### Custom Iteration Count
```bash
python run_autonomous.py -f step7.py -n 30
```

### Focus on Specific Features
```
"Use autodev-autonomous agent to add metadata support to step6.py"
```

### Continue Previous Session
```
"Use autodev-autonomous agent to continue from where we left off on step6.py"
```

### Debug Mode
```bash
# Add verbose output
AUTODEV_DEBUG=1 python run_autonomous.py -f step6.py
```

## Performance

### Typical Iteration Time
- Observe: 2-5 seconds (Docker startup)
- Orient: 1-3 seconds (code analysis)
- Decide: 5-15 seconds (patch generation)
- Act: 2-5 seconds (verification + commit)
- **Total**: 10-28 seconds per iteration

### For a 20-iteration step
- Expected time: 3-10 minutes
- Parallelizable: Run multiple steps in parallel

## Limitations

### What the Agent CAN Do
- Add new functions and special forms
- Fix bugs and errors
- Implement new features step-by-step
- Follow code patterns and conventions
- Learn from previous iterations

### What the Agent CANNOT Do
- Major architectural refactors
- Changes affecting multiple files significantly
- Design decisions requiring domain knowledge
- Performance optimizations
- Adding entirely new test frameworks

### When to Intervene
- Agent asks for help (3 failed attempts)
- Git conflicts or repo issues
- Environment setup problems
- Requirements clarification needed
- Security concerns

## Version History

- **v1.0** (2025-02-15): Initial autonomous agent
  - Full OODA loop automation
  - Claude Code integration
  - MEMORY.md auto-updates
  - Git commit integration

---

## Support

For issues or questions:
1. Check MEMORY.md for relevant patterns
2. Review git commit history
3. Check reference implementations
4. Consult SKILL.md for detailed guidelines
