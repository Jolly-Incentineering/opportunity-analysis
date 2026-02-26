---
name: deck-qa
description: Run final quality checks on the Excel model and PowerPoint deck before client delivery.
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
11. All Attio, Slack, and other MCP tools are READ-ONLY. Never use create, update, or delete MCP actions.

---

You are executing the `deck-qa` phase of the Jolly intro deck workflow. This is the final phase before delivery. Follow every step exactly as written. Do not skip any check. Surface every issue to the user -- do not silently pass a failing check.

Set workspace root and client root:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
```

If `workspace_config.json` does not exist, tell the user: "Workspace is not configured. Run /deck-setup first." Then stop.

---

## Step 1: Load Session State

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
- `deck_folder` -- presentation subfolder path
- `vf_deck_filename` -- the vF deck filename
- `pdf_filename` -- the PDF filename
- `phase_4_complete` -- whether Phase 4 (deck-format) has been marked complete
- Model file path
- Campaigns selected

If Phase 4 is not marked complete, tell the user:

```
Phase 4 is not complete. Run /deck-format first, then return to /deck-qa.
```

Then stop.

Derive `company_slug` from company name: lowercase, spaces replaced with underscores, remove special characters.

Tell the user:

```
Resuming from [session date] -- company: [Company Name], vertical: [Vertical].
Starting Phase 5: QA and delivery.
Context: [Pre-call / Post-call]
```

---

## Step 1.5: Display QA Scope

Display the QA scope table to the user:

**All contexts use the unified Intro Deck template — 11 focused checks run:**
```
  Run:   M1 M2 M3 M4 M5 M6  D2 D3 D4 D5 D6
```

All required checks to ensure the model and presentation are delivery-ready.

---

## Step 2: Run the QA Script

Run the automated QA checklist:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 "$WS/.claude/scripts/qa_check.py" --company "[COMPANY_NAME]"
```

Read the script output. If any check fails, report it to the user with the exact failure message. Do not silently skip failures.

---

## Step 3: Model QA Checks

Ensure the model file is **closed** before running programmatic checks (openpyxl cannot read a file locked by Excel on Windows).

Run these checks programmatically using `excel_editor.py` where possible, otherwise instruct the user to check manually:

**Check M1 -- Formula cell integrity:**

Read the expected formula counts from the template config:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/template_config.json" 2>/dev/null
```

Extract expected formula counts from `formula_counts` in the template config JSON. Compare actual formula cell counts against the config values — do NOT use hardcoded numbers.

If counts do not match:

```
FAIL M1: Formula cell count mismatch in [Sheet].
Expected [N] (from template config), found [N]. A formula may have been overwritten.
Please review [Sheet] before proceeding.
```

**Check M2 -- No empty required assumption cells:**

Scan the Assumptions sheet for any hard-coded input cells in column E of the Inputs sheet that are blank or still contain placeholder text. Report any found.

**Check M3 -- ROPS range:**

For every active campaign, verify ROPS is between 10x and 30x inclusive.
- 1st-party sourced campaigns: note if ROPS is outside range but do not fail -- flag for user awareness.
- Non-1st-party campaigns: FAIL if ROPS is outside range.

Report format:

```
[PASS / FAIL] M3 -- ROPS check
  [Campaign Name]: ROPS = [Nx] -- [pass / FAIL: out of range / note: 1st party, outside range]
```

**Check M4 -- Accretion ceiling:**

Verify Total EBITDA accretion <= 15% of Annual EBITDA.
- 1st-party sourced: flag if exceeded but allow with user confirmation.
- Non-1st-party: FAIL if exceeded.

Report format:

```
[PASS / FAIL] M4 -- Accretion ceiling
  Total accretion: $[X.XMM] = [X]% of $[X.XMM] annual EBITDA
  [Within ceiling / EXCEEDS ceiling -- requires user approval]
```

**Check M5 -- Hiring cost cap:**

Read `vertical_standards.hiring_cost_cap` from `template_config.json`. If the value is null or the key is missing, skip this check (report N/A).

If a cap exists, verify no hiring cost cell exceeds that value.

```
[PASS / FAIL / N/A] M5 -- Hiring cost cap
  [Pass / FAIL: [cell] shows $[X], exceeds $[cap] cap / N/A: no cap defined for this vertical]
```

**Check M6 -- Comment coverage:**

Spot-check 10 hard-coded cells across the Assumptions and Campaigns sheets. Verify each has a comment with all required fields: SOURCE, VALUE, ADJUSTMENTS, METHODOLOGY, RATIONALE, CONFIDENCE, DATE.

Report any cells missing comments or missing required fields.

---

## Step 3b: Open Model for Manual Review

All programmatic model checks (M1–M6) are complete. Now open the model so the user can verify results visually:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
```

Tell the user: "Model opened. Review the M1–M6 results above. Type 'done' when satisfied, or report any issues."

Wait for "done" before continuing.

---

## Step 4: Deck QA Checks

Ensure the vF file is **closed** before running programmatic checks (python-pptx cannot read a file locked by PowerPoint on Windows).

The vF file is the delivery copy with static values (Macabacus links broken). Do NOT open the master deck for QA — the master has live Macabacus links and is not for delivery.

Run the programmatic checks (D2b, D2c) first while the file is closed, then open for manual checks.

**Check D2b -- Macabacus range blanks (programmatic, file closed):**

Run programmatically against the vF:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 - <<'EOF'
import sys
from pptx import Presentation

vf_path = sys.argv[1]
prs = Presentation(vf_path)
found = []
for slide_num, slide in enumerate(prs.slides, 1):
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for para in shape.text_frame.paragraphs:
            text = "".join(run.text for run in para.runs)
            if "  to  " in text:
                found.append((slide_num, shape.name, text.strip()))

if found:
    print(f"FAIL D2b: {len(found)} Macabacus range blank(s) found.")
    for slide_num, shape_name, text in found:
        print(f"  Slide {slide_num} | Shape \"{shape_name}\": \"{text}\"")
    print("Fix: refresh Macabacus on the master deck, recreate the vF (Steps 8a-8d), and re-run deck-qa.")
else:
    print("PASS D2b")
EOF
python3 - "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[vF deck filename]"
```

**Check D2c -- Raw integers in narrative text:**

Always run this check. Scan all narrative text for raw integers that should be spelled out.

Run programmatically against the vF:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 - <<'EOF'
import sys, re
from pptx import Presentation

vf_path = sys.argv[1]
prs = Presentation(vf_path)

INTEGER_RE = re.compile(r'(?<!\$)\b(\d{1,3}(?:,\d{3})+)\b')
YEAR_RE    = re.compile(r'\b20[0-9]{2}\b')

found = []
for slide_num, slide in enumerate(prs.slides, 1):
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for para in shape.text_frame.paragraphs:
            text = "".join(run.text for run in para.runs)
            scrubbed = YEAR_RE.sub('', text)
            for m in INTEGER_RE.finditer(scrubbed):
                val = int(m.group(1).replace(',', ''))
                if val >= 1000:
                    found.append((slide_num, shape.name, text.strip()))
                    break  # one flag per paragraph is enough

if found:
    print(f"FAIL D2c: {len(found)} raw integer(s) found in narrative text.")
    for slide_num, shape_name, text in found:
        print(f"  Slide {slide_num} | Shape \"{shape_name}\": \"{text[:120]}\"")
    print("Review each: confirm it is intentionally a count, not a dollar amount needing $MM formatting.")
else:
    print("PASS D2c")
EOF
python3 - "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[vF deck filename]"
```

### Step 4b: Open vF for Manual Review

Programmatic checks (D2b, D2c) are complete. Now open the vF so the user can perform the manual checks:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[vf_deck_filename]"
```

Tell the user: "vF opened. Walking through manual checks now."

Walk through each remaining deck check. Instruct the user to check manually in the open file, and wait for "done" after each item.

**Check D1 -- No template tokens remaining:**

Scan all slides for any remaining template tokens (e.g., `[Company Name]`, `[Revenue]`).

```
Check D1: Search the deck for any remaining template tokens.
In PowerPoint, press Ctrl+F and search for "[". Report any matches found.
Type "done" when complete (or report any tokens found):
```

**Check D2 -- Dollar formatting:**

```
Check D2: Scroll through all slides with dollar values.
Confirm: under $1M shows as $XXXk (integer, no decimal — e.g. $516k, $2k),
         $1M+ shows as $X.XMM (1 decimal, uppercase MM, e.g. $2.0MM).
Report any incorrectly formatted values.
Type "done":
```

**Check D3 -- Banner values match model:**

```
Check D3: Find the banner shapes on slides with large dollar callouts.
Confirm each banner value matches what the model shows for that campaign.
Report any mismatches.
Type "done":
```

**Check D4 -- Campaign list matches approved list:**

```
Check D4: Check the Campaign Summary slide and individual campaign slides.
Approved campaigns: [list from session state]
Confirm all approved campaigns appear, and no excluded campaigns appear.
Type "done":
```

**Check D5 -- Logo and brand assets:**

```
Check D5: Confirm the company logo appears on the title slide and any other slides where expected.
Confirm no placeholder logo images remain.
Type "done":
```

**Check D6 -- PDF matches deck:**

```
Check D6: Open the PDF at: [deck_folder]/[pdf_filename]
Confirm it matches the current state of the deck (same number of slides, all values visible).
Type "done":
```

---

## Step 5: Summarize QA Results

After all checks complete, present a summary:

```
QA SUMMARY -- [COMPANY NAME]
[Date]

MODEL CHECKS:
  M1 Formula integrity:    [PASS / FAIL]
  M2 No empty cells:       [PASS / FAIL / [N] cells flagged]
  M3 ROPS range:           [PASS / FAIL / [N] flagged]
  M4 Accretion ceiling:    [PASS / FAIL / [X]%]
  M5 Hiring cost cap:      [PASS / FAIL / N/A]
  M6 Comment coverage:     [PASS / FAIL / [N] missing]

DECK CHECKS:
  D1  No template tokens:      [PASS / FAIL]
  D2  Dollar formatting:       [PASS / FAIL]
  D2b Macabacus range blanks:  [PASS / FAIL]
  D2c Raw integers in text:    [PASS / FAIL]
  D3  Banner values:           [PASS / FAIL]
  D4  Campaign list:           [PASS / FAIL]
  D5  Logo/brand assets:       [PASS / FAIL]
  D6  PDF matches deck:        [PASS / FAIL]

Overall: [PASS -- ready for delivery / FAIL -- [N] issues require attention]
```

If any check is FAIL, list all failures and do not proceed to handoff until the user confirms each has been resolved.

For each failure, walk the user through the fix:
- Tell them exactly what to change
- Wait for them to make the change
- Re-run the specific check to confirm it now passes

---

## Step 6: Delete Lock Files

Clean up Office lock files before delivery:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]" -name "~$*" -delete 2>/dev/null
```

Report how many lock files were removed.

---

## Step 7: Update Session State

Write a new session state file at `$WS/.claude/data/session_state_[company_slug]_[YYYY-MM-DD].md` (today's date). Include:
- Company name
- Client root
- Current phase: Phase 5 complete
- All phases marked complete
- QA results summary (pass/fail for each check)
- Delivery-ready files:
  - Model: [model filename]
  - vF deck (delivery): [vF deck filename]
  - PDF: [PDF filename]
  - Cheat sheet: 4. Reports/Cheat Sheets/[COMPANY_NAME] Cheat Sheet.pdf
- Next action: "Deliver to client"

---

## Step 8: Hand Off

Tell the user:

```
QA complete for [COMPANY NAME].

Delivery-ready files:
  Model:       [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/1. Model/[model filename]
  vF (deck):   [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/2. Presentations/[vF deck filename]
  PDF:         [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/[deck_folder]/[pdf_filename]
  Cheat sheet: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/Cheat Sheets/[COMPANY_NAME] Cheat Sheet.pdf

QA result: [PASS / PASS with notes / FAIL -- resolved]

All phases complete. The engagement for [COMPANY_NAME] is ready for delivery.
```

Do not add anything beyond this summary.
