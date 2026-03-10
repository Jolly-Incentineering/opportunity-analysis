---
name: deck-qa
description: Run final quality checks on the Excel model and PowerPoint deck before client delivery.
---

HARD RULES - NEVER VIOLATE:
1. Do NOT generate or invent campaign names. Read them from the template config JSON.
2. Do NOT make tool calls or add steps not listed in these instructions.
3. Do NOT write to formula cells under any circumstances.
4. Do NOT skip gates - wait for user confirmation at every gate.
5. Do NOT open files you are about to write to programmatically. Keep them closed during writes.
6. Do NOT proceed past a failed step - stop and report. Do NOT retry more than once.
7. Keep all client-specific data in the client folder under 4. Reports/. Never write client data to .claude/data/.
8. All Attio, Slack, and other MCP tools are READ-ONLY. Never use create, update, or delete MCP actions.

---

You are executing the `deck-qa` phase of the Jolly intro deck workflow. This is the final phase before delivery. Follow every step exactly as written. Do not skip any check. Surface every issue to the user - do not silently pass a failing check.

Set workspace root and client root:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
```

If `workspace_config.json` does not exist, tell the user: "Workspace is not configured. Run /deck-setup first." Then stop.

---

## Step 1: Load Session State

Read the most recent session state file:

```python
python3 -c "
import json, glob, os
ws = os.environ.get('JOLLY_WORKSPACE', '.')
files = sorted(glob.glob(f'{ws}/.claude/data/session_state_*.json'))
if not files: raise SystemExit('No session state found')
data = json.load(open(files[-1], encoding='utf-8'))
print('company_name:', data['company_name'])
print('client_root:', data['client_root'])
print('vertical:', data['vertical'])
print('branch:', data['branch'])
print('context:', data['context'])
print('session_date:', data['session_date'])
print('phase_4_status:', data['phase_checklist']['phase_4_deck_formatting'])
print('campaigns_selected:', json.dumps(data['campaigns_selected']))
print('template_paths:', json.dumps(data['template_paths']))
"
```

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

## Step 2: Run Automated QA (all programmatic checks)

Ensure both Excel model and vF deck are **closed** before running (openpyxl/python-pptx cannot read files locked by Office on Windows).

Tell the user:

```
Close Excel and PowerPoint if open -- I need both files closed for automated checks.
```

Pause 3 seconds, then run the full automated checklist:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 "$WS/.claude/scripts/qa_check.py" --company "[COMPANY_NAME]"
```

This single script runs all programmatic checks:
- **M1-M6:** Formula integrity, empty cells, ROPS range, accretion ceiling, hiring cost cap, comment coverage
- **D1-D2:** Placeholders, dollar formatting, uppercase K, stray $0
- **D2b:** Macabacus range blanks
- **D2c:** Raw integers in narrative
- **D4:** Red text (live Macabacus links)
- **D7:** Executive audience rule violations
- **Cross-validation:** Excel vs PPT value matches

Read the script output. Report every failure and warning to the user with exact details. Do not silently skip.

---

## Step 3: Manual Verification

Automated checks are complete. Now open both files for the user to verify the items that require human judgment:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[vf_deck_filename]"
```

Tell the user: "Both files opened for manual verification."

Present one combined checklist for user confirmation:

```
MANUAL CHECKS (automated checks already passed/flagged above):

Model:
  M1-M6 results look correct when viewed in Excel?

Deck:
  D3  Banner values match the model (spot-check 2-3 numbers)
  D4  Campaign list matches approved: [list from session state]
  D5  Company logo on title slide, no placeholder images
  D6  PDF at [deck_folder]/[pdf_filename] matches the vF deck
```

Use AskUserQuestion with 2 questions:
1. "Model checks (M1-M6) - results look correct in Excel?" - Options: ["All good", "Found issues"]
2. "Deck checks D3-D6 - banners match, campaigns correct, logo placed, PDF matches?" - Options: ["All pass", "Found issues"]

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
