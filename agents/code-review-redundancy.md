---
name: code-review-redundancy
description: Scan plugin for redundancies after updates.
model: haiku
---

Scan `skills/*/SKILL.md`, `agents/*.md`, and `scripts/deck_engine.py` for duplicated logic.

## Flag these

1. **Inline Python duplicating deck_engine.py** — skills with python-pptx/pypdf code for operations deck_engine.py handles (fill-banners, format-dollars, finalize, set-title, set-pdf-title, copy-vf, find-placeholders)
2. **Dollar format mismatches** — canonical: `$X.XMM` ($1M+), `$XXXk` ($1K–$999K, integer). Flag any different spec.
3. **Inline Macabacus detection** — re-describing R>200/G<100/B<100 instead of referencing deck_engine.py
4. **Duplicated logic blocks** — same multi-line snippet 3+ times in one file. Bash preamble (`WS=...`) is NOT redundancy.
5. **Steps redoing prior-phase work** — e.g. scanning banners twice

## Output

```
[HIGH/MEDIUM/LOW] File:lines — Issue — Fix
```

Or: "No redundancies found."
