---
name: deck-format
description: Format the PowerPoint intro deck -- populate text, update banners, apply brand colors, and export PDF.
---

You are executing the `deck-format` phase of the Jolly intro deck workflow. Follow every step exactly as written. Do not skip steps. Do not modify the deck without explicit user approval at each gate.

Set workspace root and client root:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
```

If `workspace_config.json` does not exist, tell the user: "Workspace is not configured. Run /deck-setup first." Then stop.

---

## Step 1: Load Session State and Research Output

Scan for the most recent session state file:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
ls "$WS/.claude/data/session_state_"*.md 2>/dev/null | sort | tail -1
```

Read the most recent file. Extract:
- `company_name`
- `client_root` (use this to override CLIENT_ROOT if present)
- `vertical`
- `branch`
- `phase_3_complete` -- whether Phase 3 (deck-model) has been marked complete
- Deck file path (from template paths)
- Model file path (from template paths)

If Phase 3 is not marked complete, tell the user:

```
Phase 3 is not complete. Run /deck-model first, then return to /deck-format.
```

Then stop.

Derive `company_slug` from company name: lowercase, spaces replaced with underscores, remove special characters.

Read the research output:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/Research/research_output_[company_slug].json"
```

Tell the user:

```
Resuming from [session date] -- company: [Company Name], vertical: [Vertical].
Starting Phase 4: Deck formatting.

Deck file: [deck filename]
```

---

## Step 2: Open Files

Open both the deck and the model (model is read-only reference):

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[deck filename]"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
```

Tell the user: "Both files opened. Do not edit the deck yet -- I will walk you through each section."

---

## Step 3: Detect and Populate Banner Slides

Scan the deck for slides containing banner placeholder shapes. A shape is a banner if its text content matches any of these patterns (case-insensitive):
- `$[ ]`
- `[ ] quantified`
- `$[EBITDA]`
- `quantified Jolly`

For each banner shape found, report its slide number and current text.

Map each banner to the corresponding campaign output value from the model population data in `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/Research/research_output_[company_slug].json`. Apply dollar formatting:
- Under $1M: `$X.Xk` (one decimal, lowercase k, drop decimal if zero — e.g. `$2.4k`, `$2k`, `$516k`)
- $1M and above: `$X.XXMM` (uppercase MM, no space, e.g. `$1.96MM`)

Present the banner replacement plan to the user before writing anything:

```
BANNER REPLACEMENT PLAN -- [COMPANY NAME]

Slide [N] | Shape: "[current text]" -> "$[value]" ([source campaign])
Slide [N] | Shape: "[current text]" -> "$[value]" ([source campaign])
...

Type "approve banners" to apply, or tell me what to change:
```

Wait for "approve banners" before writing. If the user requests changes, update and re-present.

Use `figma_editor.py` or `deck_format.py` to write banner values:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 "$WS/.claude/scripts/deck_format.py" \
  --company "[COMPANY_NAME]" \
  --step banners
```

---

## Step 4: Populate Text Placeholders

Scan all slides for text placeholders that contain template tokens (e.g., `[Company Name]`, `[Revenue]`, `[Unit Count]`, `[Year]`, `[Vertical]`).

For each placeholder found, map it to the correct value from `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/Research/research_output_[company_slug].json`. Apply dollar formatting where applicable.

Present the text replacement plan to the user:

```
TEXT REPLACEMENT PLAN -- [COMPANY NAME]

Slide [N] | "[Company Name]" -> "[COMPANY_NAME]"
Slide [N] | "[Revenue]" -> "$X.XXMM"
Slide [N] | "[Unit Count]" -> "XXX locations"
...

Type "approve text" to apply, or tell me what to change:
```

Wait for "approve text" before writing.

---

## Step 5: Campaign Slides -- Manual Step Checklist

Campaign slide population requires the user to do manual formatting steps in the open deck. Walk through each step and wait for "done" before presenting the next.

```
Campaign slide checklist -- complete each step in the open deck, then type "done":

1. Navigate to the Campaign Summary slide. Confirm the approved campaigns ([list]) are shown and in the correct order.
   > [wait for "done"]

2. For each RECOMMENDED campaign (highlighted evidence from Gong/Attio):
   Add the verbatim quote or evidence callout to the speaker notes or evidence text box on that slide.
   > [wait for "done"]

3. For any campaigns in the EXCLUDE list, confirm their slides are hidden or removed from the deck.
   > [wait for "done"]

4. Check all campaign slide headlines. Replace any remaining "[Campaign Name]" tokens with the actual campaign name.
   > [wait for "done"]
```

---

## Step 6: Brand Assets -- Manual Step Checklist

```
Brand asset checklist -- complete each step, then type "done":

1. Navigate to the title slide. Confirm the company logo is placed correctly. If not, find the logo at:
   [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/3. Company Resources/Logos/
   and insert it.
   > [wait for "done"]

2. Check the color scheme. If the template colors do not match [COMPANY_NAME]'s brand colors (check brand_info.json in the Logos folder), update the theme colors manually.
   > [wait for "done"]

3. If swag images are available at [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/3. Company Resources/Swag/, insert the most relevant one on the swag/merchandise slide (if present).
   > [wait for "done"]

4. Open Figma and export the branded frames for [COMPANY_NAME]:
   - Open the Jolly Figma template file
   - Find the [COMPANY_NAME] brand frames (title slide background, section headers, etc.)
   - Export them as PNG or copy-paste directly into the appropriate slides in the open deck
   - Resize and position each frame to match the template layout
   - Save the deck (Ctrl+S)
   Type "skip" if no Figma frames are needed.
   > [wait for "done" or "skip"]
```

---

## Step 7: Final Visual Review -- Manual Step Checklist

Walk through each item in the open master deck and wait for "done" before presenting the next.

```
Final visual review -- complete each step in the master deck, then type "done":

1. Run Slide Show from the beginning (F5). Check that no template tokens ([...]) remain on any slide.
   > [wait for "done"]

2. Check all dollar values in the deck. Confirm formatting: under $1M = $X.Xk (one decimal, drop if zero), $1M+ = $X.XXMM.
   > [wait for "done"]

3. Check that ROPS values are not shown on prospect slides (Branch B). ROPS is internal only.
   > [wait for "done"]

4. Save the master deck (Ctrl+S).
   > [wait for "done"]
```

---

## Step 8a: Refresh Macabacus on Master -- Manual Step

Refresh all live Macabacus links in the master deck so values are current before creating the delivery copy.

Tell the user:

```
Macabacus refresh — complete this step in the master deck, then type "done":

1. Click the Macabacus tab in the PowerPoint ribbon
2. Click Refresh All (or Refresh)
3. Wait for all slides to update — values should pull in from the populated model
4. Confirm the key banner numbers look correct at a glance
5. Save the master deck (Ctrl+S)

The master will keep its live Macabacus links. Do NOT break links here.
```

Wait for "done" before continuing.

---

## Step 8b: Create vF Copy -- Automated

Tell the user: "Creating vF delivery copy from refreshed master..."

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 - <<'EOF'
import sys, shutil
from pathlib import Path
from pptx import Presentation

ws          = sys.argv[1]
client_root = sys.argv[2]
company     = sys.argv[3]
date_str    = sys.argv[4]   # YYYY.MM.DD

src  = Path(ws) / client_root / company / "2. Presentations" / f"{company} Intro Deck ({date_str}).pptx"
dest = Path(ws) / client_root / company / "2. Presentations" / f"{company} Intro Deck ({date_str}) - vF.pptx"

shutil.copy2(src, dest)

prs = Presentation(dest)
prs.core_properties.title = f"{company} Intro Deck ({date_str}) - vF"
prs.save(dest)

print(f"vF copy created: {dest}")
EOF
python3 - "$WS" "$CLIENT_ROOT" "[COMPANY_NAME]" "[YYYY.MM.DD]"
```

Record the vF file path:
- vF file: `$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx`

Open the vF file:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx"
```

Tell the user:

```
vF copy created: [vF filename]
The vF is now open. The master deck retains all live Macabacus links — do not modify it.
```

---

## Step 8c: Break Links in vF -- Manual Step

The delivery copy (vF) must have all Macabacus links converted to static values. Break links in the vF only — never in the master.

Tell the user:

```
Break Macabacus links in the vF — complete this step in the vF deck (NOT the master), then type "done":

1. Make sure you are in the vF file: [COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx
2. Click the Macabacus tab in the PowerPoint ribbon
3. Click Break Links → confirm the dialog
4. Verify the values on key slides still look correct (they should be identical to the master)
5. Save the vF (Ctrl+S)

Do NOT break links in the master deck.
```

Wait for "done" before continuing.

---

## Step 8d: Run Deck Formatter -- Automated

Launch the deck-formatter subagent to apply dollar formatting, fill any remaining banner shapes, and export to PDF.

Record the paths:
- vF file: `$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx`
- PDF output: `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pdf`

```
Task tool — subagent_type: deck-formatter

Prompt (substitute actual values):

  Format the vF delivery deck for [COMPANY_NAME].

  company:        [COMPANY_NAME]
  vf_deck_path:   [full vF .pptx path]
  model_path:     [full .xlsx model path]
  pdf_output:     [full PDF output path]
  pdf_title:      [COMPANY_NAME] Intro Deck (YYYY.MM.DD)
  research_json:  [full path to research_output_[company_slug].json]

  Dollar formatting rules:
  - Under $1M: $X.Xk — one decimal place, drop the decimal only if it is exactly zero
    (e.g. $2,400 → $2.4k, $2,000 → $2k, $516,000 → $516k)
  - $1M and above: $X.XXMM (e.g. $1,960,000 → $1.96MM)

  Fill banner shapes from model campaign output values.
  Export the finished deck as PDF to pdf_output.
  After export, set the PDF /Title metadata to pdf_title using pypdf:
    import pypdf; writer = pypdf.PdfWriter(clone_from=pdf_output)
    writer.add_metadata({"/Title": pdf_title})
    writer.write(pdf_output)
  Return: PDF path if successful, or error details.
```

Wait for the subagent to complete. Report its output (replacements made, banner values, PDF path).

Tell the user:

```
vF formatted and exported to PDF: [PDF filename]

Master deck retains live Macabacus links for future refreshes.
Do not edit the vF directly — make changes in the master, re-run Steps 8a–8d.
```

---

## Step 9: Verify PDF

The deck-formatter subagent in Step 8d produced the PDF. Open it for review:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pdf"
```

If the PDF does not exist (formatter failed), fall back to manual export:

```
PDF export fallback:
1. In PowerPoint, open the vF file and go to File → Export → Create PDF/XPS.
   Save to: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pdf

2. Then run this to set the PDF title metadata:
```

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 -c "
import pypdf, sys
pdf_path = sys.argv[1]
pdf_title = sys.argv[2]
writer = pypdf.PdfWriter(clone_from=pdf_path)
writer.add_metadata({'/Title': pdf_title})
writer.write(pdf_path)
print(f'PDF title set: {pdf_title}')
" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pdf" \
  "[COMPANY_NAME] Intro Deck (YYYY.MM.DD)"
```

Tell the user:

```
PDF opened. Quick review:

1. Scroll through every page — confirm no [placeholder] tokens remain
2. Check banner values are formatted correctly ($X.Xk or $X.XXMM)
3. Confirm dollar amounts match the approved model values

Type "done" when the PDF looks good.
```

Wait for "done" before continuing to Step 10.

---

## Step 10: Generate Cheat Sheets

Run the cheat sheet generator for this company:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
cd "$WS" && python3 ".claude/scripts/cheatsheet_gen.py" --company "[COMPANY_NAME]"
```

This produces a single combined PDF in `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/`:
- `[COMPANY_NAME] Cheat Sheet.pdf` — company profile, meeting intelligence, and campaign breakdowns

If the script fails (missing packages or no research data), tell the user:

```
Cheat sheet generation failed: [error].
You can run it manually later: python3 .claude/scripts/cheatsheet_gen.py --company "[COMPANY_NAME]"
```

Do not stop the workflow if this step fails — continue to Step 11.

---

## Step 11: Update Session State

Write a new session state file at `$WS/.claude/data/session_state_[YYYY-MM-DD].md` (today's date). Include:
- Company name
- Client root
- Current phase: Phase 4 complete
- Phase 1, 2, 3, 4 marked complete; Phase 5 pending
- Master deck path: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx` (retains live Macabacus links)
- vF deck path: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx` (delivery copy, links broken)
- PDF path: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pdf`
- Cheat sheet path: `[COMPANY_NAME] Cheat Sheet.pdf`
- Next action: "Run /deck-qa"

---

## Step 12: Hand Off

Tell the user:

```
Deck formatting complete for [COMPANY NAME].

Working deck:  [COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx  (master, retains live Macabacus links)
vF (delivery): [COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx  (static delivery copy)
PDF:           [COMPANY_NAME] Intro Deck (YYYY.MM.DD).pdf
Cheat sheet:   [COMPANY_NAME] Cheat Sheet.pdf

Session state saved. Next: run /deck-qa for final quality check before delivery.
```
