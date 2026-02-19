---
name: deck-model
description: Populate the Excel intro model with researched values -- assumptions, campaign inputs, and sensitivities.
---

You are executing the `deck-model` phase of the Jolly intro deck workflow. Follow every step exactly as written. Do not skip steps. Do not write to any Excel cell without explicit user approval.

Set workspace root and client root:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
```

If `workspace_config.json` does not exist, tell the user: "Workspace is not configured. Run /deck-setup first." Then stop.

---

## Step 1: Load Session State and Research Output

Scan for the most recent session state file:

```bash
WS="${JOLLY_WORKSPACE:-.}"
ls "$WS/.claude/data/session_state_"*.md 2>/dev/null | sort | tail -1
```

Read the most recent file. Extract:
- `company_name`
- `client_root` (use this to override CLIENT_ROOT if present)
- `vertical` -- "QSR" or "Manufacturing" (determines formula counts)
- `branch`
- `phase_2_complete` -- whether Phase 2 (deck-research) has been marked complete
- `campaigns_selected` -- the confirmed campaign list from deck-research
- Model file path (from template paths)

If Phase 2 is not marked complete, tell the user:

```
Phase 2 is not complete. Run /deck-research first, then return to /deck-model.
```

Then stop.

Derive `company_slug` from company name: lowercase, spaces replaced with underscores, remove special characters.

Read the research output file:

```bash
WS="${JOLLY_WORKSPACE:-.}"
cat "$WS/.claude/data/research_output_[company_slug].json"
```

If the file does not exist, tell the user: "Research output not found. Run /deck-research first." Then stop.

Tell the user:

```
Resuming from [session date] -- company: [Company Name], branch: [A or B], vertical: [Vertical].
Starting Phase 3: Model population.

Model file: [model filename]
Campaigns approved: [N]
```

---

## Step 2: Open the Model File

Open the model file:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
```

Tell the user: "Model opened. Do not edit it yet -- I will tell you exactly what to enter and where."

---

## Step 3: Build the Dry-Run Plan

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

**Hiring cost cap (QSR only):** Never exceed $3,500.

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
- Cell address
- Value (rounded)
- Source (from research_output)
- Source tier
- Comment text (see comment format below)

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

**Formula lock list -- never write to these cells:**

QSR model:
- All cells in the Campaigns sheet that are part of the 153 campaign formula cells
- All cells in the Sensitivities sheet that are part of the 86 sensitivity formula cells

Manufacturing model:
- All cells in the Campaigns sheet that are part of the 366 campaign formula cells
- All cells in the Campaigns sheet that are part of the 205 sensitivity formula cells

If a value needs to go into a formula cell, flag it to the user and ask for guidance. Do not overwrite formulas.

---

## Step 4: Present Dry-Run Plan and Wait for Approval

Present the complete plan as a table before writing anything. Format:

```
DRY-RUN PLAN -- [COMPANY NAME]
[N] cells to write across [N] sheets

Sheet: Assumptions
  Cell A1  | Annual Revenue         | $X.XXMM    | Source: Gong (1st party) | Comment: included
  Cell A2  | Unit Count             | XXX        | Source: SEC 10-K (2nd)   | Comment: included
  ...

Sheet: Campaigns
  Cell B5  | [Campaign Name] Adoption Rate | X%  | Source: benchmark (2nd)  | Comment: included
  ...

ROPS CHECK:
  [Campaign Name]: ROPS = [Nx] -- [pass / adjusted]
  ...

ACCRETION CHECK:
  Total EBITDA accretion: $X.XXMM ([X]% of $X.XXMM annual EBITDA) -- [within ceiling / flag]

FORMULA CELLS SKIPPED (do not overwrite):
  [List any formula cells that were identified and skipped]

Type "approve" to write all cells, or tell me what to change:
```

Wait for the user to type "approve" before writing anything. If the user requests changes, update the plan and re-present. Repeat until "approve" is received.

---

## Step 5: Write to Excel

After "approve" is received, write all planned values to the Excel file using `excel_editor.py`:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 "$WS/.claude/agents/excel_editor.py" \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]" \
  --cells "[JSON of cell writes]"
```

For each cell written, add the comment using the comment format defined in Step 3. Comment dimensions: width=420, height=220, font size 8.

After writing, tell the user: "Wrote [N] cells to [model filename]. Verifying..."

---

## Step 6: Verify Writes

Read back each cell that was written and confirm the value matches what was planned. Report any discrepancies.

Run a formula integrity check: confirm that the formula cell counts are unchanged.

QSR: Campaigns sheet should still have 153 formula cells. Sensitivities sheet should have 86.
Manufacturing: Campaigns sheet should still have 366 formula cells. Sensitivities sheet should have 205.

If any formula cell count has changed, alert the user immediately:

```
WARNING: Formula cell count changed in [Sheet] -- expected [N], found [N].
This may indicate a formula was overwritten. Please check [sheet] before proceeding.
```

---

## Step 7: Manual Review Checklist

Present a checklist of manual steps the user must complete in Excel before the model is considered final. Wait for the user to type "done" after each item before presenting the next.

Checklist:

```
Manual review checklist -- complete each step in the open model, then type "done":

1. Scroll through the Assumptions sheet. Confirm all yellow cells have values. Any still showing placeholders?
   > [wait for "done"]

2. Check the Campaigns sheet. Confirm all selected campaigns ([list]) are activated (toggle = ON). Any toggled off that should be on?
   > [wait for "done"]

3. Check ROPS column. Confirm all active campaigns show ROPS between 10x and 30x. Any outside range?
   > [wait for "done"]

4. Check the Summary slide inputs tab (if present). Confirm company name, revenue, and unit count are correct.
   > [wait for "done"]

5. Save the model (Ctrl+S).
   > [wait for "done"]
```

If the user reports an issue at any step, address it before marking that step done and moving to the next.

---

## Step 8: Update Research Output and Session State

Update `research_output_[company_slug].json` -- populate the `model_population` field:

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
  }
}
```

Write a new session state file at `$WS/.claude/data/session_state_[YYYY-MM-DD].md` (today's date). Include:
- Company name
- Client root
- Current phase: Phase 3 complete
- Phase 1, 2, 3 marked complete; Phase 4, 5 pending
- Model filename and cell count
- ROPS and accretion results summary
- Next action: "Run /deck-format"

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
