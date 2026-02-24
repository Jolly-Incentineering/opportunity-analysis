---
name: deck-format
description: Format the PowerPoint intro deck -- populate text, update banners, apply brand colors, and export PDF.
---

HARD RULES — NEVER VIOLATE:
1. Do NOT generate or invent campaign names. Read them from the template config JSON.
2. Do NOT make tool calls not listed in these instructions.
3. Do NOT write to formula cells under any circumstances.
4. Do NOT skip gates — wait for user confirmation at every gate.
5. Do NOT open files you are about to write to programmatically. Keep them closed during writes.
6. Do NOT add features, steps, or checks not specified here.
7. Do NOT proceed past a failed step — stop and report the failure.
8. If a tool call fails, report the error. Do NOT retry more than once.
9. Keep all client-specific data in the client folder under 4. Reports/. Never write client data to .claude/data/.
10. Use HAIKU for research agents unless explicitly told otherwise.

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
- `context` -- "pre_call" or "post_call"
- `deck_folder` -- path to the Presentations subfolder
- `deck_filename` -- the working deck filename
- `vf_deck_filename` -- the vF delivery copy filename
- `pdf_filename` -- the PDF filename
- `phase_3_complete` -- whether Phase 3 (deck-model) has been marked complete
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
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research_output_[company_slug].json"
```

Tell the user:

```
Resuming from [session date] -- company: [Company Name], vertical: [Vertical].
Starting Phase 4: Deck formatting.

Deck file: [deck filename]
```

Phase 4 scope:
```
  WILL DO: Banner fill, text replacement, brand assets, Macabacus refresh, vF copy, link break, PDF export
  WILL NOT: Custom UI design, app mockups, visual redesign
  MANUAL: Macabacus refresh (~1 min), brand frames (optional), link break (~30 sec)
  PDF: Manual export via PowerPoint UI (~15 sec)
```

---

## Step 2: Ensure Files Are Closed

```
PHASE 4 FILE MANAGEMENT:
1. Close ALL Excel and PowerPoint files now — I need them closed for automated steps.
2. I'll tell you when to open each file and when to close it.
3. Each file opens exactly once.
```

Sequence: Automated banner scan + write (files closed) → open master + model → brand + refresh → close master → vF copy (auto) → open vF → break links → close vF → open PDF

Tell the user: "Confirm all Excel and PowerPoint files are closed, then type 'ready'."

Wait for "ready" before continuing.

---

## Step 3: Detect and Populate Banner Slides

Scan the deck for slides containing banner placeholder shapes. A shape is a banner if its text content matches any of these patterns (case-insensitive):
- `$[ ]`
- `[ ] quantified`
- `$[EBITDA]`
- `quantified Jolly`

For each banner shape found, report its slide number and current text.

Map each banner to the corresponding campaign EBITDA uplift value from `campaign_details` in the research output JSON at `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research_output_[company_slug].json`. Read `campaign_details.[campaign_name].ebitda_uplift_base` for each campaign. Do NOT try to extract values from the Excel model at runtime (file locking issues). Apply dollar formatting:
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

## Step 3a: Open Files for Manual Review

Banner writes are complete. Now open both files for the manual steps that follow:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[deck_filename]"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
```

Tell the user: "Both files opened. Do not edit the deck yet -- I will walk you through each section."

---

## Step 3.5: Context Branch

Check the `context` from session state:

**IF `context == "pre_call"`:**

Tell the user:

```
Pre-call deck — Macabacus pulls all numbers from the model automatically.
Quick deck template works for all contexts. Streamlined workflow.

Next steps:
  1. Brand Assets review
  2. Final Visual Review
  3. Macabacus refresh + vF copy + link break + PDF export
```

Continue to Step 6 (Brand Assets).

**IF `context == "post_call"`:**

Continue to Step 4 normally (full flow including campaign slides).

---

## Step 4: Populate Text Placeholders

Scan all slides for text placeholders that contain template tokens (e.g., `[Company Name]`, `[Revenue]`, `[Unit Count]`, `[Year]`, `[Vertical]`).

For each placeholder found, map it to the correct value from `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research_output_[company_slug].json`. Apply dollar formatting where applicable.

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
```

---

## Step 6: Brand Assets -- Manual Step Checklist

```
Brand asset checklist -- complete each step, then type "done":

1. Navigate to the title slide. Confirm the company logo is placed correctly. If not, find the logo at:
   [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/3. Company Resources/1. Logos/
   and insert it.
   > [wait for "done"]

2. Check the color scheme. If the template colors do not match [COMPANY_NAME]'s brand colors (check brand_info.json in the 1. Logos/ folder), update the theme colors manually.
   > [wait for "done"]

3. If swag images are available at [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/3. Company Resources/2. Swag/, insert the most relevant one on the swag/merchandise slide (if present).
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

## Step 8a: Refresh Macabacus on Master -- Manual Step

Refresh all live Macabacus links in the master deck so values are current before creating the delivery copy.

Tell the user:

```
Macabacus refresh — complete these steps in the master deck, then type "ready":

1. Click the Macabacus tab in the PowerPoint ribbon
2. Click Refresh All (or Refresh)
3. Wait for all slides to update — values should pull in from the populated model
4. Confirm the key banner numbers look correct at a glance
5. Save the master deck (Ctrl+S)
6. Close the master deck

The master will keep its live Macabacus links. Do NOT break links here.
The master must be saved and closed before the vF copy is created.
```

Wait for "ready" before continuing.

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
deck_folder = sys.argv[4]  # relative path from CLIENT_ROOT/company
deck_filename = sys.argv[5]
vf_filename = sys.argv[6]

src  = Path(ws) / client_root / company / deck_folder / deck_filename
dest = Path(ws) / client_root / company / deck_folder / vf_filename

shutil.copy2(src, dest)

prs = Presentation(dest)
prs.core_properties.title = vf_filename.replace('.pptx', '')
prs.save(dest)

print(f"vF copy created: {dest}")
EOF
python3 - "$WS" "$CLIENT_ROOT" "[COMPANY_NAME]" "[deck_folder]" "[deck_filename]" "[vf_deck_filename]"
```

Record the vF file path:
- vF file: `$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[vf_deck_filename]`

Tell the user:

```
vF copy created: [vf_deck_filename]
The master deck retains all live Macabacus links — do not modify it.
```

---

## Step 8c: Break Links in vF -- Manual Step

The delivery copy (vF) must have all Macabacus links converted to static values. Break links in the vF only — never in the master.

Tell the user:

```
Break Macabacus links in the vF — complete these steps, then type "ready":

1. Open the vF file in PowerPoint:
   [deck_folder]/[vf_deck_filename]
2. Click the Macabacus tab in the PowerPoint ribbon
3. Click Break Links → confirm the dialog
4. Spot-check 2-3 key banner slides — values should be identical to the master
5. Save the vF (Ctrl+S)
6. Close the vF

Do NOT break links in the master deck. The master always retains live links.
```

Wait for "ready" before continuing.

---

## Step 8d: Run Deck Formatter -- Automated

Launch the deck-formatter subagent to scan for any remaining unfilled placeholders, apply dollar formatting, and export to PDF. Banners were already filled in Step 3 and carried over to the vF via the copy in Step 8b — the formatter is a cleanup pass and PDF export, not a primary fill.

Record the paths:
- vF file: `$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx`
- PDF output: `$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pdf`

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

  Scan for any remaining unfilled placeholders (text matching patterns like $[ ], [ ] quantified,
  [Company Name], [Revenue], etc.) and fill them from model and research data. If none are found,
  skip silently.

  Apply dollar formatting to all numeric values:
  - Under $1M: $X.Xk — one decimal place, drop the decimal only if it is exactly zero
    (e.g. $2,400 → $2.4k, $2,000 → $2k, $516,000 → $516k)
  - $1M and above: $X.XXMM (e.g. $1,960,000 → $1.96MM)

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
vF formatted. Cleanup pass complete.

Master deck retains live Macabacus links for future refreshes.
Do not edit the vF directly — make changes in the master, re-run Steps 8a–8d.
```

---

## Step 7: Final Visual Review -- Manual Step Checklist

Walk through each item in the open vF deck and wait for "done" before presenting the next.

```
Final visual review -- complete each step in the vF deck, then type "done":

1. Run Slide Show from the beginning (F5). Check that no template tokens ([...]) remain on any slide.
   > [wait for "done"]

2. Check all dollar values in the deck. Confirm formatting: under $1M = $X.Xk (one decimal, drop if zero), $1M+ = $X.XXMM.
   > [wait for "done"]

3. Check that ROPS values are not shown on prospect slides (Branch B). ROPS is internal only.
   > [wait for "done"]

4. Save the vF deck (Ctrl+S).
   > [wait for "done"]
```

---

## Step 9: Export PDF -- Manual Step

Tell the user:

```
Export PDF manually:
1. Open the vF in PowerPoint: [deck_folder]/[vf_deck_filename]
2. File → Export → Create PDF/XPS
3. Save to: [deck_folder]/[pdf_filename]
Takes ~15 seconds.

After exporting, type "done".
```

Wait for "done". Then set the PDF title metadata:

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
" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[pdf_filename]" \
  "[COMPANY_NAME] Intro Deck (YYYY.MM.DD)"
```

Open the PDF for verification:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[pdf_filename]"
```

Tell the user:

```
PDF opened. Confirm the export is clean:

1. Correct number of pages (matches slide count)
2. No blank or corrupted slides
3. Banner values are readable and not cut off

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

This produces a single combined PDF in `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/Cheat Sheets/`:
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
- Cheat sheet path: `4. Reports/Cheat Sheets/[COMPANY_NAME] Cheat Sheet.pdf`
- Next action: "Run /deck-qa"

---

## Step 12: Hand Off

Tell the user:

```
Deck formatting complete for [COMPANY NAME].

Working deck:  [COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx  (master, retains live Macabacus links)
vF (delivery): [COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx  (static delivery copy)
PDF:           [COMPANY_NAME] Intro Deck (YYYY.MM.DD).pdf
Cheat sheet:   4. Reports/Cheat Sheets/[COMPANY_NAME] Cheat Sheet.pdf

Session state saved. Next: run /deck-qa for final quality check before delivery.
```
