# Byterover Skill

**Purpose:** Intelligent context retrieval using GLM-4.5-Air as a search and curation engine.

## Overview

Byterover provides precise context to AI coding agents by using GLM-4.5-Air to:
1. Search your codebase and web
2. Summarize findings
3. Return only relevant information

This reduces token costs, improves context relevance, and eliminates hallucinations.

## Prerequisites

- GLM Coding Plan API key set in `GLM_CODING_API_KEY` environment variable
- Python with `requests` installed

## Commands

### `/query` - Search Context Tree + Codebase

Search your codebase and Context Tree for relevant information.

```bash
/query "How does AmpBender load reverb IR files?"
/query "What's the pattern for adding AudioProcessorParameters?"
```

**Behavior:**
1. GLM-4.5-Air analyzes your question
2. Searches Context Tree for relevant knowledge
3. Searches codebase (Grep/Glob/Read) if needed
4. Returns summarized, relevant context

### `/query --web` - Search Including Web

```bash
/query --web "What are the latest JUCE 8 changes?"
```

**Behavior:**
1. All local search (above)
2. PLUS web search via SearXNG
3. Synthesizes local + web findings

### `/curate` - Populate Context Tree

```bash
/curate "JUCE convolution reverb patterns"
/curate "WebView2 integration with JUCE"
```

**Behavior:**
1. GLM-4.5-Air searches codebase
2. Extracts patterns, decisions, API usage
3. Creates structured entries in Context Tree
4. Returns summary of what was curated

### `/index-history` - Index Conversation History

```bash
python .claude/tools/index_history.py
python .claude/tools/index_history.py --days 30
```

**Behavior:**
1. Parses history.jsonl files from Claude projects
2. Uses GLM-4.5-Air to extract knowledge from conversations
3. Categorizes into: patterns, decisions, troubleshooting, apis, architecture
4. Deduplicates against existing entries
5. Adds to Context Tree for future `/query` searches

## Context Tree Structure

```
.claude/byterover/
├── knowledge/
│   ├── architecture/      # System architecture docs
│   ├── patterns/          # Reusable code patterns
│   ├── decisions/         # Architectural decision records
│   ├── apis/              # API documentation
│   └── troubleshooting/   # Known issues & solutions
└── config/
    └── settings.json      # Search parameters
```

## Model Architecture

```
┌─────────────────────────────────────────┐
│  Claude Code (Any Model)                │
│  - Anthropic Opus ✓                     │
│  - Anthropic Sonnet ✓                   │
│  - GLM-4.7 ✓                            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Byterover Skill                        │
│  (GLM-4.5-Air does the heavy lifting)   │
└─────────────────────────────────────────┘
```

## Implementation

The skill is implemented as:
- **skill.md** (this file) - Interface documentation
- **query.py** - Local + web search implementation
- **curate.py** - Context tree population
- **glm_client.py** - GLM-4.5-Air API client
- **context_tree.py** - Context tree management

## Configuration

Set your GLM Coding Plan API key:

```bash
export GLM_CODING_API_KEY="your-key-here"
```

Or create `~/.claude/byterover/config.json`:

```json
{
  "glm_coding_api_key": "your-key-here"
}
```

## API Endpoint

```
https://api.z.ai/api/coding/paas/v4/chat/completions
```

## See Also

- PRD: `.claude/plans/2026-01-13-plan-created-byterover-prd.md`
- Test: `.claude/scripts/test-byterover-api.py`

---

## Integration Examples

### Example 1: /continue Session Bootstrap

```python
# In /continue skill Step 0.6
from skills.byterover import query

ctx = query(f"{plugin_name} workflow state, recent patterns, architecture")
# Returns curated ~300 tokens of relevant context
```

### Example 2: /improve Investigation

```python
# In /improve skill Phase 0.5
from skills.byterover import query

result = query(f"{plugin_name} {issue_description} root cause patterns")
# HIGH confidence → Skip to Phase 0.9
# LOW confidence → Continue to direct tools
```

### Example 3: Deep Research Level 0

```python
# In deep-research skill Level 0
from skills.byterover import query

result = query(f"JUCE {problem_description} solution patterns")
# HIGH confidence → Skip Levels 1-3, present solution directly
# LOW confidence → Proceed to Level 1
```

### Example 4: Post-Implementation Curation

```python
# In /improve skill Phase 8 (Completion)
from skills.byterover import curate

curate(
    topic=f"{plugin_name} {change_description} solution",
    search_paths=[f"plugins/{plugin_name}"],
    category="patterns"  # or "architecture", "troubleshooting"
)
# Captures learned patterns for future /query calls
```

### Example 5: Maintenance Pattern Capture

```python
# In /maintenance skill after updates
from skills.byterover import curate

curate(
    topic=f"{plugin_name} {new_pattern_name}",
    search_paths=[f"plugins/{plugin_name}"],
    category="patterns"
)
# Ensures maintenance work benefits future sessions
```

---

## Quick Reference Card

```
BEFORE implementing/researching:
  → /query "topic" (check Context Tree first)

AFTER implementing/learning:
  → /curate "topic" (capture for future)

FOR known file paths:
  → Read (direct)

FOR exact string searches:
  → Grep (direct)
```
