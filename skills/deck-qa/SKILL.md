---
name: deck-qa
description: Run final quality checks on the Excel model and PowerPoint deck before client delivery.
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
- `phase_4_complete` -- whether Phase 4 (deck-format) has been marked complete
- Model file path
- Deck file path
- PDF path
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
```

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

Open the model file:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
```

Run these checks programmatically using `excel_editor.py` where possible, otherwise instruct the user to check manually:

**Check M1 -- Formula cell integrity:**

Confirm formula cell counts match the template:
- QSR: Campaigns sheet = 153 formula cells, Sensitivities sheet = 86 formula cells
- Manufacturing: Campaigns sheet = 366 formula cells, Sensitivities sheet = 205 formula cells

If counts do not match:

```
FAIL M1: Formula cell count mismatch in [Sheet].
Expected [N], found [N]. A formula may have been overwritten.
Please review [Sheet] before proceeding.
```

**Check M2 -- No empty required assumption cells:**

Scan the Assumptions sheet for any hard-coded input cells that are blank or still contain placeholder text. Report any found.

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
  Total accretion: $[X.XXMM] = [X]% of $[X.XXMM] annual EBITDA
  [Within ceiling / EXCEEDS ceiling -- requires user approval]
```

**Check M5 -- Hiring cost cap (QSR only):**

If vertical is QSR, verify no hiring cost cell exceeds $3,500.

```
[PASS / FAIL / N/A] M5 -- Hiring cost cap (QSR only)
  [Pass / FAIL: [cell] shows $[X], exceeds $3,500 cap]
```

**Check M6 -- Comment coverage:**

Spot-check 10 hard-coded cells across the Assumptions and Campaigns sheets. Verify each has a comment with all required fields: SOURCE, VALUE, ADJUSTMENTS, METHODOLOGY, RATIONALE, CONFIDENCE, DATE.

Report any cells missing comments or missing required fields.

---

## Step 4: Deck QA Checks

Open the deck file:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[deck filename]"
```

Walk through each deck check. Instruct the user to check manually in the open file, and wait for "done" after each item.

**Check D1 -- No template tokens remaining:**

```
Check D1: Search the deck for any remaining template tokens.
In PowerPoint, press Ctrl+F and search for "[". Report any matches found.
Type "done" when complete (or report any tokens found):
```

**Check D2 -- Dollar formatting:**

```
Check D2: Scroll through all slides with dollar values.
Confirm: under $1M shows as $XXXk (lowercase k), $1M+ shows as $X.XXMM (uppercase MM).
Report any incorrectly formatted values.
Type "done":
```

**Check D2b -- Unfilled Macabacus range blanks:**

```
Check D2b: Search the deck for unfilled Macabacus range links.
In PowerPoint, press Ctrl+F and search for "  to  " (two spaces, "to", two spaces).
Also search for "ranges from" to find any "ranges from [blank] to [blank]" patterns.
These appear where Macabacus linked a range value that was never populated.
Report any matches found -- each one needs a manual value entered.
Type "done" if no matches:
```

**Check D2c -- Raw integers in narrative text:**

```
Check D2c: Scroll through all commentary and body text on campaign slides.
Look for bare integers >= 1,000 (e.g., 234,000 / 374,400 / 93,600) that appear
without a $ prefix and are not in a table or formula row.
These are numbers that should be contextually reviewed -- confirm they are
intentionally presented as counts (not dollar amounts that need $MM formatting).
Report any that look incorrect.
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

**Check D6 -- ROPS not visible to client (Branch B):**

If branch is B (prospect deck), run this check. If branch is A, skip.

```
Check D6 (Branch B only): Confirm ROPS values are not shown on any visible slide.
ROPS is internal only and must not appear in the client-facing deck.
Type "done":
```

**Check D7 -- PDF matches deck:**

```
Check D7: Open the PDF at: [PDF path]
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
  D6  ROPS hidden (B only):    [PASS / FAIL / N/A]
  D7  PDF matches deck:        [PASS / FAIL]

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

Write a new session state file at `$WS/.claude/data/session_state_[YYYY-MM-DD].md` (today's date). Include:
- Company name
- Client root
- Current phase: Phase 5 complete
- All phases marked complete
- QA results summary (pass/fail for each check)
- Delivery-ready files:
  - Model: [model filename]
  - Deck: [deck filename]
  - PDF: [PDF filename]
- Next action: "Deliver to client"

---

## Step 8: Hand Off

Tell the user:

```
QA complete for [COMPANY NAME].

Delivery-ready files:
  Model: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/1. Model/[model filename]
  Deck:  [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/2. Presentations/[deck filename]
  PDF:   [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/[PDF filename]

QA result: [PASS / PASS with notes / FAIL -- resolved]

All phases complete. The engagement for [COMPANY_NAME] is ready for delivery.
```

Do not add anything beyond this summary.
