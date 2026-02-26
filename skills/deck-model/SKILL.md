---
name: deck-model
description: Populate the Excel intro model with researched values -- assumptions, campaign inputs, and sensitivities.
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

You are executing the `deck-model` phase of the Jolly intro deck workflow. Follow every step exactly as written. Do not skip steps. Do not write to any Excel cell without explicit user approval.

**Model:** Use Haiku for standard Excel population tasks. If the model structure is unusually complex, row/column mappings are ambiguous, or campaign logic requires intricate validation, pause and tell the user you need to handle this with Sonnet to ensure accuracy. Do not attempt complex Excel logic with Haiku.

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
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research_output_[company_slug].json"
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

## Step 2: Ensure Model File is Closed

Tell the user:

```
Close the model file if it's open. I need it closed to write values programmatically.
All writes will happen in a single batch in Step 5. You can open and review the model after writes complete in Step 7.

Type "ready" when the model file is closed.
```

Wait for "ready" before proceeding.

---

## Step 3: Build the Dry-Run Plan

Read the template config from the client's Reports folder:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
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

Scan formulas at runtime to build the lock list (the template config has formula counts but not individual cell addresses):

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
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
  Cell A1  | Annual Revenue         | $X.XMM     | Source: Gong (1st party) | Comment: included
  Cell A2  | Unit Count             | XXX        | Source: SEC 10-K (2nd)   | Comment: included
  ...

Sheet: Campaigns
  Cell B5  | [Campaign Name] Adoption Rate | X%  | Source: benchmark (2nd)  | Comment: included
  ...

ROPS CHECK:
  [Campaign Name]: ROPS = [Nx] -- [pass / adjusted]
  ...

ACCRETION CHECK:
  Total EBITDA accretion: $X.XMM ([X]% of $X.XMM annual EBITDA) -- [within ceiling / flag]

FORMULA CELLS SKIPPED (do not overwrite):
  [List any formula cells that were identified and skipped]

→ "approve" to write all cells, or tell me what to adjust
```

Wait for the user to type "approve" before writing anything. If the user requests changes, update the plan and re-present. Repeat until "approve" is received.

---

## Step 5: Write to Excel

After "approve" is received, write all planned values to the Excel file using `excel_editor.py`:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 "$WS/.claude/agents/excel_editor.py" \
  --action write-cells \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]" \
  --cells "[JSON of cell writes]"
```

For each cell written, add the comment using the comment format defined in Step 3. Comment dimensions: width=420, height=220, font size 8.

After writing, tell the user: "Wrote [N] cells to [model filename]. Verifying..."

---

## Step 6: Verify Writes

Read back each cell that was written and confirm the value matches what was planned. Report any discrepancies.

Run a formula integrity check: confirm that the formula cell counts are unchanged. Read expected counts from `template_config.json` (do NOT use hardcoded numbers):

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
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
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
```

Present a checklist of manual steps the user must complete in Excel before the model is considered final. Wait for the user to type "done" after each item before presenting the next.

Checklist:

```
Manual review checklist -- complete each step in the open model, then type "done":

1. Scroll through the Inputs sheet. Confirm all hard-coded input cells in column E have values. Any still showing placeholders?
   > [wait for "done"]

2. Check the Campaigns sheet. Confirm all selected campaigns ([list]) have non-zero values in their assumption rows.
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

Write a new session state file at `$WS/.claude/data/session_state_[company_slug]_[YYYY-MM-DD].md` (today's date). Include:
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
