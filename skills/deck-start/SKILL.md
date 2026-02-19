---
name: deck-start
description: Initialize a new intro deck engagement -- verify folder, copy templates, detect branch, and launch asset gathering.
---

You are initializing a new intro deck engagement for **[COMPANY_NAME]** (replace with the argument the user passed to `/deck-start`). Work through each step below in order. Stop and surface blockers to the user before proceeding past any gate.

---

## Onboarding Check (run before everything else)

Run:

```bash
WS="${JOLLY_WORKSPACE:-.}"
cat "$WS/.claude/data/workspace_config.json" 2>/dev/null
```

If the file does **not** exist, this is a first-time user. Tell them:

```
Welcome to the Jolly deck workflow. Before starting, you need to run one-time setup.

Here's what to do:

  1. Run /deck-setup   — finds your client folder and saves your workspace config.
                         Takes a few seconds. Only needed once per machine.

  2. Then run /deck-start [COMPANY_NAME] again to begin.
```

Then stop. Do not proceed with the rest of this skill.

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

## Step 2: Ensure Client Folder Structure

Run:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]" -type d -maxdepth 4 2>/dev/null
```

Check whether the following folders all exist:
- `$CLIENT_ROOT/[COMPANY_NAME]/1. Model/`
- `$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/`
- `$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Logos/`
- `$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Swag/`
- `$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/`
- `$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts/`

If any are missing, create them silently:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Logos"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Swag"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts"
```

Do not tell the user which folders were created. Do not stop or ask for input. Continue to Step 3.

---

## Step 3: Show Templates and Ask for Template

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
```

Wait for the user's reply. Record the chosen template number, derive the vertical from the chosen template's folder name, and record the full paths to both files.

---

## Step 4: Copy Templates to Client Folder

Using today's date in YYYY.MM.DD format, copy the chosen template files:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
cp "[full source .xlsx path]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx"
cp "[full source .pptx path]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx"
```

Update the document title metadata on both files to match the filename (without extension):

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 - <<'EOF'
import sys
from openpyxl import load_workbook
from pptx import Presentation

model_path = f"{sys.argv[1]}"
deck_path = f"{sys.argv[2]}"
model_title = f"{sys.argv[3]}"
deck_title = f"{sys.argv[4]}"

wb = load_workbook(model_path)
wb.properties.title = model_title
wb.save(model_path)

prs = Presentation(deck_path)
prs.core_properties.title = deck_title
prs.save(deck_path)
EOF
python3 - \
  "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" \
  "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx" \
  "[COMPANY_NAME] Intro Model (YYYY.MM.DD)" \
  "[COMPANY_NAME] Intro Deck (YYYY.MM.DD)"
```

Then open both files:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx"
```

Tell the user: "Templates copied and opened. Model: [filename]. Deck: [filename]."

Record both destination paths -- they will be written to session state.

---

## Step 5: Detect Branch (Run All 3 Checks Simultaneously)

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

## Step 6: Launch Asset Gatherer as Background Subagent

Launch a background subagent using the Task tool with subagent_type `asset-gatherer`. Pass the following prompt, substituting [COMPANY_NAME] and [CLIENT_ROOT]:

```
Gather assets for [COMPANY_NAME]. Follow the asset-gatherer spec at .claude/agents/asset-gatherer.md.
Client folder: [CLIENT_ROOT]/[COMPANY_NAME]/3. Company Resources/
Skip banner step entirely -- do not ask for or mention a banner.
```

Do not wait for the subagent to finish. Continue immediately to Step 8.

---

## Step 7: Write Session State

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
- Model: [CLIENT_ROOT]/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx
- Deck: [CLIENT_ROOT]/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx

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

## Step 8: Report to User

Tell the user:

```
[COMPANY_NAME] initialized.

Branch: [A - Existing Relationship / B - Cold Prospect]
Reason: [which of Gong / Attio / Slack had data, or "no prior data found"]

Assets: gathering in background (logos, swag, Figma frames).

Next step: run /deck-research
```

Do not add anything beyond this summary.
