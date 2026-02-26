---
name: deck-formatter
description: Format vF deck — banners, dollars, PDF. Uses deck_engine.py.
model: haiku
---

Format the vF intro deck for **[COMPANY_NAME]** using `deck_engine.py`. No inline python-pptx.

Inputs from caller: `vf_deck_path`, `research_json`, `pdf_output`.

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"

# 1. Fill bracket placeholders from research JSON
python3 "$WS/.claude/scripts/deck_engine.py" fill-banners --file "[vf_deck_path]" --research "[research_json]"

# 2. Reformat raw dollars ($1M+ → $X.XMM, $1K-$999K → $XXXk)
python3 "$WS/.claude/scripts/deck_engine.py" format-dollars --file "[vf_deck_path]"

# 3. Verify clean
python3 "$WS/.claude/scripts/deck_engine.py" find-placeholders --file "[vf_deck_path]"
```

If placeholders remain, report and stop.

User exports PDF manually (File → Export → Create PDF/XPS), then:

```bash
python3 "$WS/.claude/scripts/deck_engine.py" set-pdf-title --file "[pdf_output]" --from-pptx "[vf_deck_path]"
```

Open both files. Report: banner values, dollar replacements, placeholders remaining, PDF status.
