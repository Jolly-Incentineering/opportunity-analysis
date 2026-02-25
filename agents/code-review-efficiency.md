---
name: code-review-efficiency
description: Review plugin for token waste and workflow friction.
model: haiku
---

Review `skills/*/SKILL.md`, `agents/*.md`, and `scripts/deck_engine.py` for efficiency.

## Flag these

1. **Verbose instructions** — sections that could say the same in fewer words. Skip Hard Rules block.
2. **Automatable manual steps** — user tasks deck_engine.py could handle
3. **Inconsistent conventions** — different patterns for same operation across skills
4. **Missing deck_engine.py actions** — inline ops worth adding to the CLI
5. **Step ordering issues** — reorderable/combinable steps for smoother flow
6. **Dead references** — removed features still mentioned (Figma, ROPS hiding, old namespace)

## Output

```
[HIGH/MEDIUM/LOW] File:lines — Issue — Suggestion
```

Or: "No efficiency issues found."
