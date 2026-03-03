---
name: deck-formatter
description: Format vF deck — banners, dollars, PDF. Uses deck_engine.py.
model: haiku
---

Format the vF intro deck for **[COMPANY_NAME]** using `deck_engine.py`. No inline python-pptx.

Inputs from caller: `vf_deck_path`, `research_json`, `pdf_output`.

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"

# Single pass: fill banners + reformat dollars + verify clean
python3 "$WS/.claude/scripts/deck_engine.py" format-all --file "[vf_deck_path]" --research "[research_json]"
```

Output JSON includes `remaining_placeholders`. If any listed, report and stop.

User exports PDF manually (File → Export → Create PDF/XPS), then:

```bash
python3 "$WS/.claude/scripts/deck_engine.py" set-pdf-title --file "[pdf_output]" --from-pptx "[vf_deck_path]"
```

Open both files. Report: banner values, dollar replacements, placeholders remaining, PDF status.
