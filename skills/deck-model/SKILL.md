---
name: deck-model
description: Populate the Excel intro model with researched values -- assumptions, campaign inputs, and sensitivities.
disable-model-invocation: true
---

HARD RULES — NEVER VIOLATE:
1. Do NOT generate or invent campaign names. Read them from the template config JSON.
2. Do NOT make tool calls or add steps not listed in these instructions.
3. Do NOT write to formula cells under any circumstances.
4. Do NOT skip gates marked with AskUserQuestion — but do NOT add extra gates. Only stop for key decisions.
5. Do NOT open files you are about to write to programmatically. Keep them closed during writes.
6. Do NOT proceed past a failed step — stop and report. Do NOT retry more than once.
7. Keep all client-specific data in the client folder under 4. Reports/. Never write client data to .claude/data/.
8. All Attio, Slack, and other MCP tools are READ-ONLY. Never use create, update, or delete MCP actions.

---

### Executive Audience Rule

Campaign descriptions written to `campaign_details` in the research
output JSON will appear verbatim on client-facing slides. Never include:
- References to calls, meetings, or conversations
- References to internal research steps or data sourcing
- Hedging language ("we believe", "we think", "it appears")
- Any language revealing the deck was built by an automated process

Write every description as a confident, client-facing strategic
recommendation. The reader is a C-suite executive seeing this material
for the first time with no prior context.

---

You are executing the `deck-model` phase of the Jolly intro deck workflow. Follow every step exactly as written. Do not skip steps. Do not write to any Excel cell without explicit user approval.

**Model:** Use Haiku for standard Excel population tasks. If the model structure is unusually complex, row/column mappings are ambiguous, or campaign logic requires intricate validation, pause and tell the user you need to handle this with Sonnet to ensure accuracy. Do not attempt complex Excel logic with Haiku.

Set workspace root and client root:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
```

If `workspace_config.json` does not exist, tell the user: "Workspace is not configured. Run /deck-setup first." Then stop.

---

## Step 1: Load Session State and Research Output

Load the most recent session state file:

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
print('session_date:', data['session_date'])
print('phase_2_status:', data['phase_checklist']['phase_2_research'])
print('campaigns_selected:', json.dumps(data['campaigns_selected']))
print('template_paths:', json.dumps(data['template_paths']))
"
```

Extract `company_name`, `client_root`, `vertical`, `branch`, `session_date`, `phase_2_status`, `campaigns_selected`, and model file path from `template_paths`.

If `phase_2_status` is not `complete`, tell the user:

```
Phase 2 is not complete. Run /deck-research first, then return to /deck-model.
```

Then stop.

Derive `company_slug` from company name: lowercase, spaces replaced with underscores, remove special characters.

Read the research output file:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research_output_[company_slug].json"
```

If the file does not exist, tell the user: "Research output not found. Run /deck-research first." Then stop.

Tell the user:

```
Resuming from [session_date] -- company: [Company Name], branch: [A or B], vertical: [Vertical].
Starting Phase 3: Model population.

Gates this phase:
  □ Model file closed
  □ Dry-run plan approved
  □ Model review passed (inputs, campaigns, ROPS, summary)
  □ Model saved

Model file: [model filename]
Campaigns approved: [N]
```

After each gate is confirmed, echo "[Gate name] ✓" in your reply before proceeding.

---

## Step 2: Ensure Model File is Closed

Tell the user:

```
Close the model file if it's open — I need it closed to write values programmatically.
All writes happen in a single batch in Step 5. You'll open it for review in Step 7.
```

Pause 3 seconds, then proceed. Do not ask for confirmation.

---

## Step 3: Build the Dry-Run Plan

Read the template config from the client's Reports folder:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/template_config.json"
```

Use the template config's `labels` dict for row → cell address mapping. Use the config's `campaigns` dict for campaign names. Do NOT scan row labels at runtime — the config already has this mapping.

Compute all values to write before touching the file. Use the merged field map from `research_output_[company_slug].json`.

Apply rounding standards to all computed values:

| Field | Round To |
|-------|----------|
| Revenue | Nearest $500K or $1M |
| Store / facility count | Exact integer |
| Orders / units per day | Nearest 50 or 100 |
| Employees | Nearest 50 or 100 |
| Menu prices / upsell costs | Nearest $0.25 or $0.50 |
| Contribution margins | Nearest 1% or 5% |
| Turnover rate | Nearest 5% |
| Hiring cost | Nearest $100 or $500 |
| EBITDA per hour | Nearest $0.25 or $0.50 |
| Incentive costs | Clean numbers ($0.10, $0.25, $0.50) |
| Reduction / gain % | Nearest 2.5% or 5% |

**Hiring cost cap:** Read `vertical_standards.hiring_cost_cap` from `template_config.json`. If defined, never exceed that value. If null or missing, no cap applies.

**SCENARIO SENSITIVITY RULE (MANDATORY):**

When building Base / Upside / Downside scenarios for any campaign:

1. **SINGLE INDEPENDENT VARIABLE**
   Only the Target % (compliance rate, adoption rate, achievement rate, etc.) may vary across scenarios. Every other row — events, current %, savings per event, costs, employee counts — must be identical in all three columns, set to the Base value.

2. **CONSISTENT SPREAD**
   - Base → Upside: +5 percentage points
   - Base → Downside: -5 percentage points
   - Exception: if the Base target % is ≤ 15%, use ±2pp to avoid unrealistic swings.

3. **VALIDATION CHECK (shown in dry-run plan before any write)**
   For each campaign, confirm that ONLY ONE row differs between Base, Upside, and Downside columns. If more than one row differs, fix it before presenting the dry-run plan.

   Correct example:
   ```
     Total Events:    480,000 / 480,000 / 480,000   ✓ constant
     Current %:           75% /     75% /     75%   ✓ constant
     Target %:            85% /     90% /     80%   ✓ only this varies
     Savings/Event:       $50 /     $50 /     $50   ✓ constant
   ```

   Wrong (do not produce this):
   ```
     Target %:            85% /     90% /     80%
     Savings/Event:       $50 /     $60 /     $40   ✗ VIOLATION — two rows vary
   ```

   Include the per-campaign validation result as a column in the dry-run output.

**ROPS check for each campaign:**
- Formula: ROPS = Savings / Incentive Cost
- Target: 10x <= ROPS <= 30x
- If ROPS is outside range: adjust incentive cost first; if still out of range, adjust assumptions
- 1st-party sourced assumptions can bypass ROPS checks -- note this in the plan

**Accretion ceiling check (run after all campaigns are computed):**
- Target: Total EBITDA accretion <= 15% of Annual EBITDA
- If exceeded: remove the campaign with the lowest ROPS first
- 1st-party assumptions can exceed ceiling with user approval -- flag and ask

For each cell to be written, prepare:
- Sheet name
- Cell address (columns C/D/E for values)
- Value (rounded)
- Source (from research_output)
- Source tier
- Comment text (see comment format below)
- Column H note (see notes column format below)

**Comment format for every hard-coded cell:**

```
SOURCE: [tier] ([source name])
[URL or "N/A"]

VALUE: [the value]

ADJUSTMENTS: [what changed and why, or "None - used as researched."]

METHODOLOGY: [how derived]

RATIONALE: [why chosen]

CONFIDENCE: High / Medium / Low

DATE: [Month Year]
```

Comment dimensions: width=420px, height=220px, font size 8.

**Column H — Notes/Source column (MANDATORY for every row that receives a value):**

For every row where a value is written to columns C/D/E, also write a condensed source note to column H of the same row. This gives reviewers a quick at-a-glance reference without hovering over cell comments.

Format: `[Source tier]: [source name] ([date or "est."])`

Examples:
- `1st party: Attio call (Jan 2026)`
- `2nd party: SEC 10-K FY2024`
- `3rd party: industry benchmark (est.)`
- `Calculated: $12M rev / 450 stores / 365 / $8.50 AOV`
- `Adjusted: capped at $3,500 per vertical standard`

Keep each note to one line (~60 chars max). If a value has multiple sources, use the primary one. The full detail lives in the cell comment — column H is the summary.

Column H cells are NOT formula cells, so they are safe to write. Include them in the dry-run plan and in the `--cells` JSON passed to `excel_editor.py`.

**Formula lock list -- never write to these cells:**

Scan formulas at runtime to build the lock list (the template config has formula counts but not individual cell addresses):

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
python3 "$WS/.claude/agents/excel_editor.py" \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]" \
  --action scan-formulas
```

Store the list of formula cell addresses. Do not write to any cell on this list under any circumstances. If a value needs to go into a formula cell, flag it to the user and ask for guidance.

---

## Step 4: Present Dry-Run Plan and Wait for Approval

Present the complete plan as a table before writing anything. Format:

```
DRY-RUN PLAN -- [COMPANY NAME]
[N] cells to write across [N] sheets

Sheet: Assumptions
  Cell E6  | Annual Revenue         | $X.XMM     | H: "1st party: Attio call (Jan 2026)"  | Comment: included
  Cell E7  | Unit Count             | XXX        | H: "2nd party: SEC 10-K FY2024"       | Comment: included
  ...

Sheet: Campaigns
  Cell C55 | [Campaign Name] Adoption Rate | X%  | H: "3rd party: industry benchmark"    | Comment: included
  ...

ROPS CHECK:
  [Campaign Name]: ROPS = [Nx] -- [pass / adjusted]
  ...

ACCRETION CHECK:
  Total EBITDA accretion: $X.XMM ([X]% of $X.XMM annual EBITDA) -- [within ceiling / flag]

FORMULA CELLS SKIPPED (do not overwrite):
  [List any formula cells that were identified and skipped]

```

Use AskUserQuestion:
- Question: "Approve the dry-run plan? All cells above will be written to the model."
- Options: ["Approve — write all cells", "I need to make changes first"]

If changes requested, update the plan and re-present. Repeat until approved.

---

## Step 5: Write to Excel

After "approve" is received, write all planned values to the Excel file using `excel_editor.py`:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
python3 "$WS/.claude/agents/excel_editor.py" \
  --action write-cells \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]" \
  --cells "[JSON of cell writes]"
```

For each cell written, add the comment using the comment format defined in Step 3. Comment dimensions: width=420, height=220, font size 8.

After writing, tell the user: "Wrote [N] cells to [model filename]. Verifying..."

If the company name contains an apostrophe (e.g., "Scooter's"), read back cell E5 and verify the apostrophe was preserved correctly. Openpyxl may interpret a leading `'` as a text prefix. If the value is wrong, re-write E5 with the correct name.

---

## Step 6: Verify Writes

Read back each cell that was written and confirm the value matches what was planned. Report any discrepancies.

Run a formula integrity check: confirm that the formula cell counts are unchanged. Read expected counts from `template_config.json` (do NOT use hardcoded numbers):

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
python3 -c "import json; c=json.load(open('$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/template_config.json')); print(json.dumps(c.get('formula_counts', {})))"
```

Compare actual formula cell counts against the values from template_config.json.

If any formula cell count has changed, alert the user immediately:

```
WARNING: Formula cell count changed in [Sheet] -- expected [N] (from template config), found [N].
This may indicate a formula was overwritten. Please check [sheet] before proceeding.
```

---

## Step 7: Open Model for Review and Manual Review Checklist

Open the model file now that all writes are complete:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
```

Tell the user to do a quick spot-check while saving:

```
Model opened. Quick spot-check while you save:
  - Inputs sheet col E: all cells filled?
  - ROPS column: all active campaigns 10x-30x?
  - Company name, revenue, unit count correct?

Save the model (Ctrl+S) when you're satisfied.
```

Use AskUserQuestion:
- Question: "Model saved?"
- Options: ["Saved — looks good", "Found issues"]

If issues found, help the user resolve before continuing.

---

## Step 8: Update Research Output and Session State

Update `research_output_[company_slug].json` -- populate the `model_population` field AND add `campaign_details`:

```json
{
  "model_population": {
    "cells_written": 0,
    "sheets_modified": [],
    "rops_results": {},
    "accretion_result": {
      "total_accretion": null,
      "annual_ebitda": null,
      "accretion_pct": null,
      "within_ceiling": true
    },
    "formula_cells_preserved": true,
    "model_file": "[model filename]",
    "population_date": "[YYYY-MM-DD]"
  },
  "campaign_details": {
    "[Campaign Name]": {
      "rops_base": null,
      "rops_upside": null,
      "incentive_cost_base": null,
      "ebitda_uplift_base": null,
      "description": ""
    }
  }
}
```

For each campaign, populate `campaign_details` with the values from the model population. These values are needed by deck-format for banner values — deck-format reads them from this JSON instead of extracting from Excel at runtime (avoids file locking issues).

Update the session state JSON:

```python
python3 -c "
import json, glob, os
from datetime import date
ws = os.environ.get('JOLLY_WORKSPACE', '.')
files = sorted(glob.glob(f'{ws}/.claude/data/session_state_*.json'))
if not files: raise SystemExit('No session state found — cannot update')
path = files[-1]
data = json.load(open(path, encoding='utf-8'))
data['phase_checklist']['phase_3_model_population'] = 'complete'
data['next_action'] = '/deck-format'
data['last_updated'] = date.today().isoformat()
data['metadata']['cells_written'] = [N]
data['metadata']['rops_results'] = '[summary]'
data['metadata']['accretion_pct'] = [pct]
with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
print('Updated:', path)
"
```

Where `[N]`, `'[summary]'`, and `[pct]` are substituted at runtime with the actual cells written count, a ROPS results summary string, and the accretion percentage float.

---

## Step 9: Hand Off

Tell the user:

```
Model population complete for [COMPANY NAME].

Cells written: [N]
Sheets modified: [list]
ROPS: all campaigns [pass / [N] adjusted]
Accretion: [X]% of annual EBITDA ([within ceiling / flagged])
Formula integrity: [preserved / WARNING -- see above]

Model file: [model filename]

Session state saved. Next: run /deck-format to format the PowerPoint deck.
```
