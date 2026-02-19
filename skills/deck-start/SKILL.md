---
name: deck-start
description: Initialize a new intro deck engagement -- verify folder, copy templates, add to Notion pipeline, detect branch, and launch asset gathering.
---

You are initializing a new intro deck engagement for **[COMPANY_NAME]** (replace with the argument the user passed to `/deck-start`). Work through each step below in order. Stop and surface blockers to the user before proceeding past any gate.

Set the workspace root and read the client root from workspace config:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
```

If `workspace_config.json` does not exist, tell the user:

```
Workspace is not configured. Run /deck-setup first, then re-run /deck-start [COMPANY_NAME].
```

Then stop.

Use `$WS/$CLIENT_ROOT` as the prefix for all client folder paths below.

---

## Step 1: Check for Existing Session State

Run:

```bash
WS="${JOLLY_WORKSPACE:-.}"
ls "$WS/.claude/data/"session_state_*.md 2>/dev/null
```

For each file found, read it and check whether the `company` field equals [COMPANY_NAME] (case-insensitive).

If a session state file for this company exists, tell the user:

```
A session for [COMPANY_NAME] already exists (session_state_[DATE].md).
Last phase: [phase from file]. Next action: [next action from file].

If you want to restart from scratch, delete that file first and re-run /deck-start.
If you want to continue, run /deck-research instead.
```

Then stop. Do not proceed.

---

## Step 2: Verify Client Folder Structure

Run:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]" -type d -maxdepth 4 2>/dev/null
```

The following folders must all exist:
- `$CLIENT_ROOT/[COMPANY_NAME]/1. Model/`
- `$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/`
- `$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Logos/`
- `$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Swag/`
- `$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/`
- `$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts/`

If any folder is missing, tell the user exactly what to create:

```
Client folder is missing or incomplete. Please create the following structure before continuing:

[CLIENT_ROOT]/[COMPANY_NAME]/
  1. Model/
  2. Presentations/
  3. Company Resources/
      Logos/
      Swag/
  4. Reports/
  5. Call Transcripts/

Create these folders, then re-run /deck-start [COMPANY_NAME].
```

Then stop. Do not proceed.

---

## Step 3: Show Templates and Ask for Vertical + Variant

Run:

```bash
WS="${JOLLY_WORKSPACE:-.}"
find "$WS/Templates" -type f \( -name "*.xlsx" -o -name "*.pptx" \) | sort
```

From the output, build a numbered list of available template pairs grouped by vertical. Each pair is one `.xlsx` and one `.pptx` with matching names. Present only template pairs (both files exist). Show the vertical folder name and the template display name.

Example format:

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
Also confirm the Notion vertical label (e.g., QSR, Manufacturing, Automotive, Other).
```

Wait for the user's reply. Record the chosen template number, the vertical label, and the full paths to both files.

---

## Step 4: Copy Templates to Client Folder

Using today's date in YYYY.MM.DD format, copy the chosen template files:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
cp "[full source .xlsx path]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model YYYY.MM.DD.xlsx"
cp "[full source .pptx path]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck YYYY.MM.DD.pptx"
```

Then open both files:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model YYYY.MM.DD.xlsx"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck YYYY.MM.DD.pptx"
```

Tell the user: "Templates copied and opened. Model: [filename]. Deck: [filename]."

Record both destination paths -- they will be written to session state.

---

## Step 5: Add to Notion Pipeline

Use `mcp__plugin_Notion_notion__notion-search` to search for an existing page with the title equal to [COMPANY_NAME] in database `4afe3d50-864d-8388-9b82-8119f374c573`.

If a matching page already exists, tell the user: "Notion entry for [COMPANY_NAME] already exists -- skipping." and continue to Step 6.

If no match is found, create a new page using `mcp__plugin_Notion_notion__notion-create-pages` with:
- Parent database: `4afe3d50-864d-8388-9b82-8119f374c573`
- Title (task name): [COMPANY_NAME] -- company name only, no prefix
- Due date: today's date + 4 days
- Vertical: the label confirmed in Step 3
- Internal checkbox: unchecked (false)

Tell the user: "Added [COMPANY_NAME] to Notion pipeline. Due: [due date]. Vertical: [vertical]."

---

## Step 6: Detect Branch (Run All 3 Checks Simultaneously)

Run all three checks at the same time (do not wait for one before starting the others):

**Check A -- Gong insights file:**

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts" -name "gong_insights_*.json" 2>/dev/null
```

For any file found, check if its date (extracted from the filename `gong_insights_YYYY-MM-DD.json`) is within the last 30 days. A file counts as "has data" only if it is 30 days old or newer.

**Check B -- Attio CRM:**
Call `mcp__claude_ai_Attio__search-records` with query [COMPANY_NAME]. Result counts as "has data" if any records are returned.

**Check C -- Slack channel:**
Derive a slug from [COMPANY_NAME]: lowercase, spaces replaced with hyphens, remove special characters. Call `mcp__claude_ai_Slack__slack_search_channels` with that slug. Result counts as "has data" if any channels are returned.

Branch decision:
- If ANY of the three checks has data: **Branch A (existing relationship)**
- If ALL three checks are empty: **Branch B (cold prospect)**

Record which checks had data -- this becomes the branch reason.

---

## Step 7: Launch Asset Gatherer as Background Subagent

Launch a background subagent using the Task tool with subagent_type `asset-gatherer`. Pass the following prompt, substituting [COMPANY_NAME] and [CLIENT_ROOT]:

```
Gather assets for [COMPANY_NAME]. Follow the asset-gatherer spec at .claude/agents/asset-gatherer.md.
Client folder: [CLIENT_ROOT]/[COMPANY_NAME]/3. Company Resources/
Skip banner step entirely -- do not ask for or mention a banner.
```

Do not wait for the subagent to finish. Continue immediately to Step 8.

---

## Step 8: Write Session State

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
```

Write a session state file to `$WS/.claude/data/session_state_YYYY-MM-DD.md` (use today's date). Contents:

```markdown
# Session State: [COMPANY_NAME]
Date: YYYY-MM-DD

## Company
[COMPANY_NAME]

## Client Root
[CLIENT_ROOT]

## Branch
[A or B] -- [reason: which checks had data, or "all checks empty"]

## Vertical
[vertical label from Step 3]

## Template Paths
- Model: [CLIENT_ROOT]/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model YYYY.MM.DD.xlsx
- Deck: [CLIENT_ROOT]/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck YYYY.MM.DD.pptx

## Phase Checklist
- Phase 1: Initialization -- complete
- Phase 2: Research -- pending
- Phase 3: Model Population -- pending
- Phase 4: Deck Formatting -- pending
- Phase 5: QA and Delivery -- pending

## Next Action
Run /deck-research
```

---

## Step 9: Report to User

Tell the user:

```
[COMPANY_NAME] initialized.

Branch: [A - Existing Relationship / B - Cold Prospect]
Reason: [which of Gong / Attio / Slack had data, or "no prior data found"]

Assets: gathering in background (logos, swag, Figma frames).

Next step: run /deck-research
```

Do not add anything beyond this summary.
