---
name: deck-auto-optimized
description: "OPTIMIZED: Run the full intro deck workflow automatically for a company with fast path for cold prospects. Saves progress after every phase and resumes if interrupted. Usage: /deck-auto [Company Name]."
---

## OPTIMIZATION NOTES

This is an **optimized version** of the deck-auto skill designed to hit the 10-15 minute target for "Without Commentary" (cold prospect) decks.

**Key Changes from Original:**

1. **Phase 1.5: Explicit Deck-Type Gate** - Ask user and store deck type in session state before proceeding
2. **Phase 2: Conditional Research Agent Dispatch** - For "Without Commentary", dispatch ONLY ws-public (skip ws-attio-gong, ws-m365, ws-slack)
3. **Phase 3: Template Defaults Path** - For "Without Commentary", use vertical template defaults instead of custom computation; skip ROPS/accretion validation
4. **Phase 4: Streamlined Formatting** - For "Without Commentary", skip Figma step and reduce manual gates
5. **Phase 5: Reduced QA Checks** - For "Without Commentary", run 6 focused checks instead of 11

**Expected Timeline:**
- Without Commentary: 10-15 minutes (from ~20-25 min)
- With Commentary: 20-25 minutes (unchanged)

---

You are the `deck-auto-optimized` orchestrator for the Jolly intro deck workflow. Your job is to run all five phases of the workflow end-to-end for a single company, pausing only at required human gates, and saving state after every phase so work can be resumed across sessions.

The company name is the argument the user passed to `/deck-auto`. Substitute [COMPANY_NAME] throughout with that exact value.

Set workspace root and client root at the start of every bash block:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
```

Derive `company_slug` from [COMPANY_NAME]: lowercase, spaces replaced with underscores, remove all special characters. Compute this once and reuse it throughout.

---

## Phase 0: Workspace Check

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
cat "$WS/.claude/data/workspace_config.json" 2>/dev/null
```

If the file does not exist or is not valid JSON with a `client_root` key, stop and tell the user:

```
Welcome to the Jolly deck workflow. Before starting, you need to run one-time setup.

Here's what to do:

  1. Run /deck-setup   — finds your client folder and saves your workspace config.
                         Takes a few seconds. Only needed once per machine.

  2. Then run /deck-auto [COMPANY_NAME] again to begin.
```

Do not proceed past Phase 0 until workspace_config.json is confirmed valid. Once confirmed, read and store `CLIENT_ROOT` from its `client_root` field.

---

## Phase 0B: Session State Check and Plan Announcement

Scan for existing session state files:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
ls "$WS/.claude/data/session_state_"*.md 2>/dev/null | sort
```

For each file found, read it and check whether the `company` field matches [COMPANY_NAME] (case-insensitive).

**If a matching session state file exists:**

Read the phase checklist from it. Determine which phases are complete, which is in progress, and which are pending. Tell the user:

```
Resuming [COMPANY_NAME] from [session date].
Last completed phase: Phase [N] -- [phase name].
Next action: [next action from state file].

Phase status:
  Phase 0: Workspace check     -- complete
  Phase 1: Start               -- [complete / pending]
  Phase 2: Research            -- [complete / in progress / pending]
  Phase 3: Model               -- [complete / in progress / pending]
  Phase 4: Format              -- [complete / in progress / pending]
  Phase 5: QA                  -- [complete / in progress / pending]

Type "go" to continue from Phase [N+1], or "stop [N]" to jump directly to a specific phase:
```

Wait for the user to type "go" or "stop [N]" before proceeding. If the user types "stop [N]", skip directly to that phase. If the user types "go", skip all complete phases and start the next pending one. If a phase is marked "in progress", restart it from its beginning.

**If no matching session state file exists:**

Tell the user:

```
No existing session found for [COMPANY_NAME]. Starting from Phase 1.

First, I'll ask you which deck type you need:
  • Without Commentary (before a call) — ~10-15 minutes, numbers only
  • With Commentary (after a call) — ~20-25 minutes, includes narrative

Then I'll run these phases:
  Phase 1: Start               -- folder structure, templates, deck type selection
  Phase 2: Research            -- parallel research agents, merge, campaign selection
  Phase 3: Model               -- dry-run plan, Excel population
  Phase 4: Format              -- Macabacus refresh, text replacement, brand formatting
  Phase 5: QA                  -- 6-13 checks depending on deck type

Human gates (will pause for your input):
  - Phase 1: template selection, deck type selection
  - End of Phase 2: campaign confirmation
  - Start of Phase 3: dry-run approval
  - Phase 4: manual steps (reduced for cold decks)
  - Phase 5: any FAIL checks

Type "go" to begin, or "stop [N]" to jump to a specific phase:
```

Wait for "go" or "stop [N]" before proceeding.

---

## Phase 1: Start

Tell the user: "Phase 1: Start -- running."

### 1.1 Ensure Client Folder Structure

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]" -type d -maxdepth 4 2>/dev/null
```

Check whether the following folders all exist:
- `$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/`
- `$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/`
- `$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Logos/`
- `$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Swag/`
- `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/`
- `$WS/$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts/`

If any are missing, create them silently:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Logos"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Swag"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts"
```

Do not tell the user which folders were created. Do not stop or ask for input. Continue to 1.2.

### 1.2 Show Templates and Ask for Template

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
TEMPLATES_ROOT=$(python3 -c "import json; c=json.load(open('$WS/.claude/data/workspace_config.json')); print(c.get('templates_root', 'Templates'))" 2>/dev/null || echo "Templates")
find "$WS/$TEMPLATES_ROOT" -type f \( -name "*.xlsx" -o -name "*.pptx" \) | sort
```

From the output, build a numbered list of available template pairs grouped by vertical. Present only pairs where both the `.xlsx` and `.pptx` exist with matching names. Example format:

```
Available templates:

  QSR
    1. QSR Intro Template

  Manufacturing
    2. Custom Manufacturer Intro Template
    3. Food & Beverage Manufacturer Intro Template
    4. Furniture Manufacturer Intro Template
    5. Manufacturing Intro Template (General)

  Automotive Services
    6. Automotive Services Intro Template

Which template should I use for [COMPANY_NAME]? Reply with the number.
```

Wait for the user's reply. Record: chosen template number, derive vertical from the chosen template's folder name, and full paths to both template files.

### 1.3 Copy Templates to Client Folder

Using today's date in YYYY.MM.DD format, copy the chosen templates:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
cp "[full source .xlsx path]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx"
cp "[full source .pptx path]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx"
```

Then open both files:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx"
```

Update document title metadata on both files to match the filename (without extension):

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 - \
  "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" \
  "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx" \
  "[COMPANY_NAME] Intro Model (YYYY.MM.DD)" \
  "[COMPANY_NAME] Intro Deck (YYYY.MM.DD)" <<'EOF'
import sys
from openpyxl import load_workbook
from pptx import Presentation
wb = load_workbook(sys.argv[1]); wb.properties.title = sys.argv[3]; wb.save(sys.argv[1])
prs = Presentation(sys.argv[2]); prs.core_properties.title = sys.argv[4]; prs.save(sys.argv[2])
EOF
```

Record both destination paths. They will be written to session state.

### 1.4 Detect Branch (3 Parallel Checks)

Run all three checks simultaneously - do not wait for one before starting the others:

**Check A - Gong insights file:**

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts" -name "gong_insights_*.json" 2>/dev/null
```

A file counts as "has data" only if its date (from filename `gong_insights_YYYY-MM-DD.json`) is within the last 30 days.

**Check B - Attio CRM:**

Call `mcp__claude_ai_Attio__search-records` with query [COMPANY_NAME]. Result counts as "has data" if any records are returned.

**Check C - Slack channel:**

Derive a channel slug: [COMPANY_NAME] lowercase, spaces replaced with hyphens, special characters removed. Call `mcp__claude_ai_Slack__slack_search_channels` with that slug. Result counts as "has data" if any channels are returned.

Branch decision:
- If ANY check has data: **Branch A (existing relationship)**
- If ALL checks are empty: **Branch B (cold prospect)**

Record which checks had data - this is the branch reason.

### 1.5 GATE: Deck Type Selection (NEW - OPTIMIZATION)

**Ask the user to confirm the deck type.** This is critical for routing through the optimized fast path.

Tell the user:

```
Which deck type do you need for [COMPANY_NAME]?

  1. Without Commentary (before a call) — numbers only, ~10-15 minutes
  2. With Commentary (after a call) — includes narrative, ~20-25 minutes

Reply with 1 or 2:
```

Wait for the user to type "1" or "2". Record the choice:
- **Deck type 1 = "Without Commentary" = FAST PATH**
- **Deck type 2 = "With Commentary" = STANDARD PATH**

### 1.6 Launch Asset Gatherer as Background Subagent

Launch a background subagent using the Task tool. Pass this prompt (substitute actual values):

```
Gather assets for [COMPANY_NAME]. Follow the asset-gatherer spec at .claude/agents/asset-gatherer.md.
Client folder: [CLIENT_ROOT]/[COMPANY_NAME]/3. Company Resources/
Skip banner step entirely -- do not ask for or mention a banner.
```

Do not wait for the subagent. Continue immediately.

### 1.7 Save State After Phase 1

Write `$WS/.claude/data/session_state_YYYY-MM-DD.md` (use today's date):

```markdown
# Session State: [COMPANY_NAME]
Date: YYYY-MM-DD
Mode: auto
Deck Type: [1 = Without Commentary / 2 = With Commentary]

## Company
[COMPANY_NAME]

## Client Root
[CLIENT_ROOT]

## Branch
[A or B] -- [reason: which checks had data, or "all checks empty"]

## Deck Type
[1 = Without Commentary (FAST PATH) / 2 = With Commentary (STANDARD PATH)]

## Vertical
[vertical label]

## Template Paths
- Model: [CLIENT_ROOT]/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx
- Deck: [CLIENT_ROOT]/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx

## Phase Checklist
- Phase 0: Workspace check -- complete
- Phase 1: Start -- complete
- Phase 2: Research -- pending
- Phase 3: Model -- pending
- Phase 4: Format -- pending
- Phase 5: QA -- pending

## Approved Campaigns
(none yet)

## Last Completed Step
Phase 1: Start complete

## Next Action
Phase 2: Research
```

Tell the user: "Phase 1 complete. Moving to Phase 2: Research..."

Then immediately continue to Phase 2 without waiting for any user input.

---

## Phase 2: Research (OPTIMIZED)

Tell the user: "Phase 2: Research -- running."

**OPTIMIZATION:** For "Without Commentary" decks (deck_type=1), ONLY dispatch ws-public. Skip ws-attio-gong, ws-m365, ws-slack entirely.

### 2.1 Check and Ensure Gong Recipe Exists (Branch A Only)

Skip this step entirely if branch is B OR if deck type is 1 (Without Commentary).

Call `mcp__rube__RUBE_FIND_RECIPE` with `name: "gong_company_search"`.

If the recipe is NOT found, create it using `mcp__rube__RUBE_CREATE_UPDATE_RECIPE` with:
- Recipe name: `gong_company_search`
- Description: "Search Gong calls by date range and retrieve transcripts for matched calls."
- Steps:
  - Pass 1: Call `GONG_RETRIEVE_FILTERED_CALL_DETAILS` with:
    - `filter__fromDateTime`: `"{{from_date}}T00:00:00Z"`
    - `filter__toDateTime`: `"{{to_date}}T23:59:59Z"`
    - `contentSelector__exposedFields__content__brief`: `true`
    - `contentSelector__exposedFields__parties`: `true`
    - `contentSelector__context`: `"Extended"`
    - `contentSelector__contextTiming`: `["Now", "TimeOfCall"]`
  - Pass 2: Call `GONG_GET_CALL_TRANSCRIPT` with:
    - `filter.callIds`: `["{{matched_call_ids}}"]`

Confirm the recipe exists before proceeding to 2.2.

### 2.2 Dispatch Research Agents (CONDITIONAL - OPTIMIZATION)

**FOR DECK TYPE 1 (Without Commentary):** Dispatch ONLY ws-public.

**FOR DECK TYPE 2 (With Commentary):** Dispatch all 4 agents (ws-attio-gong, ws-m365, ws-slack, ws-public).

Dispatch using the Task tool. Issue all Task calls in a single message. Do not wait for one before starting the others. Compute today's date and 180 days ago before dispatching - pass them as literal date strings in each prompt.

Use `model: "sonnet"` for all agents.

Target completion: all agents complete within 5 minutes total.

Output path for all agents: `$WS/.claude/data/ws_[workstream]_[company_slug].json`

---

### 2.2a Agent: ws-public (REQUIRED FOR ALL DECK TYPES)

Output file: `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research/ws_public_[company_slug].json`

Pass this prompt (substitute all bracketed values), using `model: "sonnet"`:

```
[Use the existing ws-public agent prompt from the original deck-auto SKILL.md, lines 589-674]
```

---

### 2.2b Agent: ws-attio-gong (SKIP IF DECK TYPE 1)

**Only dispatch if deck_type=2 (With Commentary).**

Output file: `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research/ws_attio_gong_[company_slug].json`

Pass the existing ws-attio-gong agent prompt from lines 350-455.

---

### 2.2c Agent: ws-m365 (SKIP IF DECK TYPE 1)

**Only dispatch if deck_type=2 (With Commentary).**

Output file: `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research/ws_m365_[company_slug].json`

Pass the existing ws-m365 agent prompt from lines 459-522.

---

### 2.2d Agent: ws-slack (SKIP IF DECK TYPE 1)

**Only dispatch if deck_type=2 (With Commentary).**

Output file: `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research/ws_slack_[company_slug].json`

Pass the existing ws-slack agent prompt from lines 526-585.

---

### 2.3 Wait for All Dispatched Agents

Do not proceed until all dispatched Task calls have returned. Once all agents report completion, read all output files that were actually dispatched (for deck type 1, this is only ws_public_[company_slug].json):

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
[Read only the files that were dispatched based on deck_type]
```

If any file is missing or invalid JSON, note it as a failed workstream and continue with remaining data.

### 2.4 WS-Merge

Consolidate all data from dispatched output files. Apply source priority (highest to lowest):

1. Gong transcript (1st party) - if available
2. Attio note (1st party) - if available
3. Microsoft 365 Outlook / SharePoint (1st party) - if available
4. Slack (1st party) - if available
5. SEC filing (2nd party)
6. Comp benchmark (2nd party)
7. Online estimate (3rd party)

For each field, use the highest-priority source that has a value. Record source name and tier alongside each value.

**Conflict flagging:** If two sources for the same field diverge by more than 15%, flag it explicitly with both values and sources.

**Gap flagging:** If a required field has no value after all workstreams, flag it as a gap. Required fields: annual revenue, unit/location count, employee count, and at least one menu price or average ticket value.

Present the merged field map. Wait for the user to resolve any conflicts and gaps before proceeding.

### 2.5 GATE: Campaign Selection

For "Without Commentary" decks, present a simplified campaign selection:

```
CAMPAIGN SELECTION for [COMPANY_NAME]
No call data -- showing full standard template for [Vertical].

All [N] campaigns included (prospect deck -- illustrative):
1. [Campaign Name]
2. [Campaign Name]
...

Type "confirm" to proceed with all campaigns, or remove any you do not want:
```

For "With Commentary" decks, present full campaign recommendations based on Gong data (use original format from lines 733-756).

If the user requests changes, apply them and re-present. Repeat until "confirm" is received.

### 2.6 Save Research Output and Update State

First create the directory:

```bash
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research"
```

Write `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research/research_output_[company_slug].json` (use original format from lines 781-821).

Update session state file (`$WS/.claude/data/session_state_YYYY-MM-DD.md`). Write a new file with today's date. Include:
- All fields from Phase 1 state
- Phase 2 marked complete
- Approved campaigns list (verbatim)
- Source breakdown summary
- Key decisions made
- Next action: Phase 3: Model

Tell the user: "Phase 2 complete. Moving to Phase 3: Model..."

Then immediately continue to Phase 3 without waiting for user input.

---

## Phase 3: Model (OPTIMIZED)

Tell the user: "Phase 3: Model -- running."

**OPTIMIZATION:** For "Without Commentary" decks (deck_type=1), use vertical template defaults and skip ROPS/accretion validation.

### 3.1 Load Research Output

Read:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research/research_output_[company_slug].json"
```

Extract: `company_basics`, `campaigns_selected`, `campaign_inputs`, `comps_benchmarks`, `model_population` (should be empty at this stage), and branch.

Also read the model file path from the current session state file.

### 3.2 Open the Model File

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
```

Tell the user: "Model opened. Do not edit it yet -- I will show you the full plan before writing anything."

### 3.3 Branch on Deck Type

**IF DECK TYPE 1 (Without Commentary):**

Tell the user: "Using template defaults for cold prospect deck. Skipping custom value computation."

Jump to Step 3.6 (Template Defaults Path).

**IF DECK TYPE 2 (With Commentary):**

Continue to Step 3.4 (Full computation path).

---

### 3.4 [STANDARD PATH] Map Row Labels to Row Numbers

[Use original steps 3.3-3.10 from deck-auto SKILL.md, lines 864-1075]

---

### 3.6 [FAST PATH FOR DECK TYPE 1] Use Template Defaults

For "Without Commentary" cold decks, populate only the highest-level assumptions (company revenue, unit count, employee count) from research. Do NOT compute campaign values.

Present a simplified plan:

```
TEMPLATE DEFAULT PLAN -- [COMPANY NAME]

Company Basics (from research):
  Annual Revenue: $[X.XXMM] (source: [source])
  Unit Count: [N] (source: [source])
  Employee Count: [N] (source: [source])

All campaigns will use template defaults (illustrative numbers). No custom ROPS or accretion calculations.

Campaigns: [list all approved campaigns]

Type "approve" to proceed:
```

Wait for "approve".

Then write ONLY the company basics to Excel (3-5 cells max), skip campaign values entirely.

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 "$WS/.claude/agents/excel_editor.py" \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]" \
  --cells "[JSON of company basics cells only]"
```

Skip to 3.10 (save state).

---

### 3.10 Save State After Phase 3

Update `research_output_[company_slug].json` -- populate `model_population` (simplified for deck type 1):

```json
{
  "model_population": {
    "cells_written": 3-5,
    "sheets_modified": ["Assumptions"],
    "rops_results": {},
    "accretion_result": null,
    "formula_cells_preserved": true,
    "model_file": "[model filename]",
    "population_date": "[YYYY-MM-DD]",
    "deck_type": 1,
    "used_template_defaults": true
  }
}
```

Write new session state file with Phase 3 marked complete.

Tell the user: "Phase 3 complete. Moving to Phase 4: Format..."

Then immediately continue to Phase 4 without waiting for user input.

---

## Phase 4: Format (OPTIMIZED)

Tell the user: "Phase 4: Format -- running."

**OPTIMIZATION:** For "Without Commentary" decks, skip Figma step. Reduce manual gates.

### 4.1-4.2 Check Assets and Open Deck

[Use original steps 4.1-4.2 from deck-auto, lines 1082-1101]

### 4.3 Branch on Deck Type

**IF DECK TYPE 1 (Without Commentary):**

Tell the user: "Cold prospect deck -- using streamlined formatting (no Figma step)."

Skip to Step 4.8 (run deck_format.py directly, skip manual gates).

**IF DECK TYPE 2 (With Commentary):**

Continue with all manual steps 4.4-4.7.

---

### 4.4-4.7 [STANDARD PATH] Manual Steps (Skip for Deck Type 1)

[Use original steps 4.4-4.7 from deck-auto, lines 1103-1173]

### 4.8 Run deck_format.py

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 "$WS/.claude/scripts/deck_format.py" --company "[COMPANY_NAME]"
```

Capture the output. If the script fails, report the error to the user and ask whether to continue or investigate.

### 4.9-4.10 Scan and Save State

[Use original steps 4.9-4.10 from deck-auto, lines 1184-1223]

---

## Phase 5: QA (OPTIMIZED)

Tell the user: "Phase 5: QA -- running."

**OPTIMIZATION:** For "Without Commentary" decks, run only 6 focused checks instead of 13.

### 5.1 Run the QA Script

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 "$WS/.claude/scripts/qa_check.py" --company "[COMPANY_NAME]"
```

Read the script output. Report all failures.

### 5.2-5.3 Model and Deck QA Checks

**IF DECK TYPE 1 (Without Commentary):**

Run ONLY these 6 checks:

1. **M1 -- Formula cell integrity:** Confirm formula counts unchanged
2. **M2 -- No empty required cells:** Scan assumptions for blanks (company basics only)
3. **D1 -- No template tokens:** Search for "[" in deck
4. **D2 -- Dollar formatting:** Confirm $XXXk / $X.XXMM format
5. **D4 -- Campaign list:** Confirm approved campaigns appear on deck
6. **D5 -- Logo and brand:** Confirm logo on title slide

Skip M3-M6, D3, D6, D7.

**IF DECK TYPE 2 (With Commentary):**

Run all 13 checks from original Phase 5 (lines 1250-1362).

---

### 5.4-5.8 Summarize, Resolve, and Save Final State

[Use original steps 5.4-5.8 from deck-auto, lines 1364-1429]

---

## Final Summary

After all phases are complete, tell the user:

```
[COMPANY_NAME] deck complete.

Deck Type: [Without Commentary (cold prospect) / With Commentary (post-call)]

Campaigns: [list each with ROPS if applicable, e.g. "Employee Rewards -- 14x ROPS"]

[If With Commentary:]
Accretion: [X]% of EBITDA ($[X.XXMM] / $[X.XXMM] annual EBITDA)

[If Without Commentary:]
(Template defaults -- not computed)

Sources:
[List sources used based on deck type and agents dispatched]

Files:
  PPT:   [full path to vF.pptx]
  Model: [full path to model .xlsx]
  PDF:   [full path to vF.pdf]

QA: [PASS / PASS with notes]
All phases complete. The engagement for [COMPANY_NAME] is ready for delivery.
```

Do not add anything beyond this summary.
