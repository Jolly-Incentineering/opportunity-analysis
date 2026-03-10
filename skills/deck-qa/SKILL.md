---
name: deck-qa
description: Run final quality checks on the Excel model and PowerPoint deck before client delivery.
disable-model-invocation: true
---

Read and follow all rules in skills/shared-preamble.md before proceeding.

---

You are executing the `deck-qa` phase of the Jolly intro deck workflow. This is the final phase before delivery. Follow every step exactly as written. Do not skip any check. Surface every issue to the user - do not silently pass a failing check.

Set workspace root and client root:

Set workspace root using the bash preamble from shared-preamble.md.

If `workspace_config.json` does not exist, tell the user: "Workspace is not configured. Run /deck-setup first." Then stop.

---

## Step 1: Load Session State

Read the most recent session state file:

Load session state using the standard loader from shared-preamble.md.

If `phase_4_status != 'complete'`, tell the user:

```
Phase 4 is not complete. Run /deck-format first, then return to /deck-qa.
```

Then stop.

Derive `company_slug` from company name: lowercase, spaces replaced with underscores, remove special characters.

Tell the user:

```
Resuming from [session_date] -- company: [Company Name], vertical: [Vertical].
Starting Phase 5: QA and delivery.
Context: [Pre-call / Post-call]
```

---

## Step 2: Run Final Verification

Automated deck checks already passed on the master during deck-format (Step 6). This final pass verifies the vF copy and cross-validates against the model.

Tell the user:

```
Close Excel and PowerPoint if open - I need both files closed for final checks.
```

Pause 3 seconds, then run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 "$WS/.claude/scripts/qa_check.py" --company "[COMPANY_NAME]"
```

Focus on these results:
- **Must pass (vF-specific):** D1 (no tokens), D2 (dollar formatting), D3 (banners filled), D4 (no red text/links broken)
- **Must pass (cross-validation):** Banner values match model, campaign list matches approved
- **Must pass (deliverables):** D6 (PDF matches deck)
- **Report all:** M1-M6 results (should already pass from Phase 3, flag if regression)

Read the script output. Report every failure and warning to the user with exact details. Do not silently skip.

---

## Step 3: Manual Verification

Open both files for the user to verify items requiring human judgment:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[vf_deck_filename]"
```

Tell the user: "Both files opened for manual verification."

Present one combined checklist:

```
FINAL MANUAL CHECKS:
  - Banner values match model (spot-check 2-3 numbers)
  - Campaign list matches approved: [list from session state]
  - Company logo on title slide, no placeholder images
  - PDF at [deck_folder]/[pdf_filename] matches the vF deck
  - Model M1-M6 results look correct in Excel
```

Use AskUserQuestion:
- Question: "Final manual checks - all items above check out?"
- Options: ["All pass", "Found issues"]

If issues found, walk the user through fixes and re-check the specific items.

---

## Step 4: Resolve Failures

If any automated or manual check failed:

1. List all failures with specific fix instructions
2. For programmatic failures: tell user exactly what to change
3. For deck issues requiring master edit: remind them to edit master -> Macabacus refresh -> recreate vF (Steps 7a-7d of deck-format)
4. After fixes, re-run the specific checks:
   - For model fixes: re-run `qa_check.py` after closing the file
   - For deck fixes: re-run `qa_check.py` after closing the file

Do not proceed until all failures are resolved.

---

## Step 5: Summarize QA Results

After all checks pass, present the summary:

```
QA SUMMARY -- [COMPANY NAME]
[Date]

MODEL CHECKS:
  M1 Formula integrity:    [PASS / FAIL]
  M2 No empty cells:       [PASS / FAIL]
  M3 ROPS range:           [PASS / FAIL / WARN]
  M4 Accretion ceiling:    [PASS / FAIL / WARN]
  M5 Hiring cost cap:      [PASS / FAIL / N/A]
  M6 Comment coverage:     [PASS / FAIL]

DECK CHECKS:
  D1  No template tokens:      [PASS / FAIL]
  D2  Dollar formatting:       [PASS / FAIL]
  D2b Macabacus range blanks:  [PASS / FAIL]
  D2c Raw integers in text:    [PASS / FAIL]
  D3  Banner values:           [PASS / FAIL]
  D4  Red text / links broken: [PASS / FAIL]
  D5  Logo/brand + campaigns:  [PASS / FAIL]
  D6  PDF matches deck:        [PASS / FAIL]
  D7  Executive audience:      [PASS / FAIL]

Overall: [PASS -- ready for delivery / FAIL -- [N] issues require attention]
```

---

## Step 6: Delete Lock Files

Clean up Office lock files before delivery:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]" -name "~$*" -delete 2>/dev/null
```

Report how many lock files were removed.

---

## Step 7: Update Session State

Run:

```python
python3 -c "
import json, glob, os
from datetime import date
ws = os.environ.get('JOLLY_WORKSPACE', '.')
files = sorted(glob.glob(f'{ws}/.claude/data/session_state_*.json'))
if not files: raise SystemExit('No session state found - cannot update')
path = files[-1]
data = json.load(open(path, encoding='utf-8'))
data['phase_checklist']['phase_5_qa_delivery'] = 'complete'
data['next_action'] = 'Deliver to client'
data['last_updated'] = date.today().isoformat()
data['metadata']['qa_results'] = '[QA results summary string]'
with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
print('Updated:', path)
"
```

Where `[QA results summary string]` is Claude's runtime substitution of the actual pass/fail results.

---

## Step 8: Hand Off

Tell the user:

```
QA complete for [COMPANY NAME].

Delivery-ready files:
  Model:       [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/1. Model/[model filename]
  vF (deck):   [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/2. Presentations/[vF deck filename]
  PDF:         [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/[deck_folder]/[pdf_filename]

QA result: [PASS / PASS with notes / FAIL -- resolved]

All phases complete. The engagement for [COMPANY_NAME] is ready for delivery.
```

Do not add anything beyond this summary.
