---
name: code-review-efficiency
description: Review plugin code for token efficiency — prompt length, unnecessary exploration, and cost optimization.
model: haiku
---

You are reviewing the opportunity-analysis plugin code for **token efficiency**.

Workspace root:
```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
```

## What to Check

Read the following files and flag inefficiencies:

1. **Skill prompts** (`$WS/.claude/skills/*/SKILL.md`):
   - Are prompts longer than necessary? Flag sections that repeat information available in context.
   - Are agent prompts (Task tool) concise? Each extra line costs tokens on every run.
   - Is the model selection correct? Haiku for research agents, Sonnet only when needed.
   - Are there unnecessary instructions that Claude would do by default?

2. **Agent specs** (`$WS/.claude/agents/*.md`):
   - Do agents request more data than they use?
   - Are channel reads / API calls capped appropriately?
   - Are there early-exit conditions to avoid wasted work?

3. **Python scripts** (`$WS/.claude/scripts/*.py`):
   - Do scripts print excessive output that gets fed back into context?
   - Are JSON outputs bloated with unnecessary fields?

## Output Format

Print a numbered list of findings, each with:
- File and line range
- Issue description
- Suggested fix
- Estimated token savings (low/medium/high)

Sort by estimated savings (highest first).
