---
name: deck-start
description: Initialize a new intro deck engagement -- verify folder, copy templates, detect branch, and launch asset gathering.
---

HARD RULES — NEVER VIOLATE:
1. Do NOT generate or invent campaign names. Read them from the template config JSON.
2. Do NOT make tool calls or add steps not listed in these instructions.
3. Do NOT write to formula cells under any circumstances.
4. Do NOT skip gates — wait for user confirmation at every gate.
5. Do NOT open files you are about to write to programmatically. Keep them closed during writes.
6. Do NOT proceed past a failed step — stop and report. Do NOT retry more than once.
7. Keep all client-specific data in the client folder under 4. Reports/. Never write client data to .claude/data/.
8. All Attio, Slack, and other MCP tools are READ-ONLY. Never use create, update, or delete MCP actions.
9. Use HAIKU for research agents unless explicitly told otherwise.

---

You are initializing a new intro deck engagement for **[COMPANY_NAME]** (replace with the argument the user passed to `/deck-start`). Work through each step below in order. Stop and surface blockers to the user before proceeding past any gate.

---

## Onboarding Check (run before everything else)

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
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

## Library Check

Run:

```bash
python3 -c "
import importlib, sys
required = ['openpyxl', 'pptx', 'requests']
optional = ['edgar', 'pypdf']
missing_req, missing_opt = [], []
for pkg, label in [(r, r) for r in required] + [(o, o) for o in optional]:
    found = importlib.util.find_spec(pkg) is not None
    if not found:
        (missing_opt if pkg in optional else missing_req).append(pkg)
if missing_req:
    print('MISSING_REQUIRED:' + ','.join(missing_req))
if missing_opt:
    print('MISSING_OPTIONAL:' + ','.join(missing_opt))
if not missing_req and not missing_opt:
    print('OK')
"
```

- If **MISSING_REQUIRED** packages are listed, tell the user:

```
Missing required packages: [list].
Run Tools/setup.bat (Windows) or: pip install openpyxl python-pptx requests
Then re-run /deck-start [COMPANY_NAME].
```

Then stop.

- If **MISSING_OPTIONAL** packages are listed, tell the user (one line, then continue):

```
Note: optional packages not installed: [list]. SEC filing lookups and PDF metadata editing will be skipped.
To enable: pip install [list]
```

- If **OK**, continue silently.

---

Set the workspace root and read the client root from workspace config:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
```

If `workspace_config.json` does not exist, tell the user:

```
Workspace is not configured. Run /deck-setup first, then re-run /deck-start [COMPANY_NAME].
```

Then stop.

Use `$WS/$CLIENT_ROOT` as the prefix for all client folder paths below.

---

## Gate Checklist

After the workspace check passes, tell the user:

```
Gates this run:
  □ Context (pre-call / post-call)
  □ Template selected
```

After each gate is confirmed, echo "[Gate name] ✓" in your reply before proceeding.

---

## Step 1: Check for Existing Session State

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
ls "$WS/.claude/data/"session_state_*.md 2>/dev/null
```

For each file found, read it and check whether the `company` field equals [COMPANY_NAME] (case-insensitive).

If a session state file for this company exists, tell the user:

```
A session for [COMPANY_NAME] already exists (session_state_[company_slug]_[DATE].md).
Last phase: [phase from file]. Next action: [next action from file].

If you want to restart from scratch, delete that file first and re-run /deck-start.
If you want to continue, run /deck-research instead.
```

Then stop. Do not proceed.

---

## Step 2: Ensure Client Folder Structure

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]" -type d -maxdepth 4 2>/dev/null
```

Check whether the following folders all exist:
- `$CLIENT_ROOT/[COMPANY_NAME]/1. Model/`
- `$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/`
- `$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/1. Logos/`
- `$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/2. Swag/`
- `$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/1. Call Summaries/`
- `$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/2. Public Filings/`
- `$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/3. Slack/`
- `$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts/`

If any are missing, create them silently:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/1. Logos"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/2. Swag"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/1. Call Summaries"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/2. Public Filings"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/3. Slack"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts"
```

Do not tell the user which folders were created. Do not stop or ask for input. Continue to Step 3.

---

## Step 3: Ask if Pre-Call or Post-Call

Ask the user:

Use AskUserQuestion:
- Question: "What context is this deck for?"
- Options: ["Pre-call — no call yet (Slack + Public, ~8-12 min)", "Post-call — after a call or internal notes (Full Attio + Gong + Slack + Public, ~14-20 min)"]

Store `context = "pre_call"` or `"post_call"` based on their choice. This will inform the research phase but will not change the template or workflow.

---

## Step 4: Show Templates and Ask for Template

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
find "$WS/$TEMPLATES_ROOT" -type f \( -name "*.xlsx" -o -name "*.pptx" \) | sort
```

From the output, build a numbered list of available template pairs grouped by vertical. There is one template per vertical (no Commentary variants).

Each pair is one `.xlsx` and one `.pptx` with matching names. Present only template pairs (both files exist). Show the vertical folder name and the template display name.

Example format:

```
Template for [COMPANY_NAME]

  QSR
    [1] QSR Intro Template

  Retail
    [2] Retail Intro Template

→ Number, or "new" to create a template for a different vertical
```

If the user types "new", run `/deck-new-template` and return to this skill after the template is created. The new template will appear in the list above.

Wait for the user's reply. Record the chosen template number, derive the vertical from the chosen template's folder name, and record the full paths to both files.

---

## Step 5: Copy Templates to Client Folder

Using today's date in YYYY.MM.DD format, create a subfolder under Presentations and copy the template files:

Create the Presentations subfolder with numbering:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)"
```

Copy the files:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
cp "[full source .xlsx path]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx"
cp "[full source .pptx path]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx"
```

Update the document title metadata on both files to match the filename (without extension):

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
python3 "$WS/.claude/scripts/deck_engine.py" set-title \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" \
  --title "[COMPANY_NAME] Intro Model (YYYY.MM.DD)"
python3 "$WS/.claude/scripts/deck_engine.py" set-title \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx" \
  --title "[COMPANY_NAME] Intro Deck (YYYY.MM.DD)"
```

Then open both files:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx"
```

Tell the user: "Templates copied and opened. Model: [filename]. Deck: [filename]."

Record the presentation subfolder path and deck filename -- they will be written to session state as `deck_folder`, `deck_filename`, `vf_deck_filename`, and `pdf_filename`.

Naming conventions:
- Deck subfolder: `1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)/`
- Deck filename: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx`
- vF filename: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx`
- PDF filename: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pdf`

---

## Step 6: Scan Template and Load Config

Run `template_scanner.py` on the copied model file to identify the template type and extract cell mappings:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
python3 "$WS/.claude/agents/template_scanner.py" \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" \
  --configs-dir "$WS/.claude/agents/templates/" \
  --threshold 0.85
```

**If a match is found (≥85% similarity):**
- Check whether the Excel template has been modified since the config was last updated:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
python3 -c "
import json, os, datetime
cfg = json.load(open('$WS/.claude/agents/templates/[matched_config].json'))
last = datetime.date.fromisoformat(cfg.get('last_updated','2000-01-01'))
tmpl = datetime.date.fromtimestamp(os.path.getmtime('$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx'))
print('STALE' if tmpl > last else 'FRESH')
"
```

- If **STALE**: the template has changed since the config was last built. Re-scan and update:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 "$WS/.claude/agents/template_scanner.py" \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" \
  --create \
  --output "$WS/.claude/agents/templates/[matched_config].json"
```

Tell the user: "Template newer than config — re-scanned [matched_config].json." Then continue.

- If **FRESH**: no action needed, continue.

- Load the config JSON, extract: campaign names, cell addresses, formula counts, labels dict
- Save the config to the client folder:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
cp "$WS/.claude/agents/templates/[matched_config].json" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/template_config.json"
```

**If no match is found:**
- Run the scanner in create mode to generate a new config:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
python3 "$WS/.claude/agents/template_scanner.py" \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" \
  --create \
  --output "$WS/.claude/agents/templates/[company_slug]_custom.json"
cp "$WS/.claude/agents/templates/[company_slug]_custom.json" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/template_config.json"
```

Record the following from the template config for use in later phases:
- Campaign names (from `campaigns` dict)
- Formula counts (from `formula_counts` dict)
- Cell addresses (from `labels` dict)
- Template type name

Tell the user: "Template scanned. Config: [template type]. Campaigns: [list names]. Config saved to 4. Reports/template_config.json."

---

## Step 7: Detect Branch (Run All 3 Checks Simultaneously)

Run all three checks at the same time (do not wait for one before starting the others):

**Check A -- Gong insights file:**

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts" -name "gong_insights_*.json" 2>/dev/null
```

For any file found, check if its date (extracted from the filename `gong_insights_YYYY-MM-DD.json`) is within the last 30 days. A file counts as "has data" only if it is 30 days old or newer.

**Check B -- Attio CRM:**

Preferred: use the Attio REST API if ATTIO_API_KEY is available (check environment and .env file). If the key exists, run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
ATTIO_API_KEY=$(python3 -c "
import os
key = os.environ.get('ATTIO_API_KEY', '')
if not key:
    try:
        for line in open('$WS/.env'):
            if line.startswith('ATTIO_API_KEY='):
                key = line.split('=',1)[1].strip()
                break
    except FileNotFoundError:
        pass
print(key)
")
curl -s -X POST "https://api.attio.com/v2/objects/companies/records/query" \
  -H "Authorization: Bearer $ATTIO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"filter":{"name":{"$contains":"[COMPANY_NAME]"}}}'
```

Fallback: if no API key, call `mcp__claude_ai_Attio__search-records` with query [COMPANY_NAME].

Result counts as "has data" if any records are returned.

**Check C -- Slack channel:**
Derive a slug from [COMPANY_NAME]: lowercase, spaces replaced with hyphens, remove special characters. Call `mcp__claude_ai_Slack__slack_search_channels` with that slug. Result counts as "has data" if any channels are returned.

Branch decision:
- If ANY of the three checks has data: **Branch A (existing relationship)**
- If ALL three checks are empty: **Branch B (cold prospect)**

Record which checks had data -- this becomes the branch reason.

---

## Step 8: Launch Asset Gatherer as Background Subagent

Launch a background subagent using the Task tool with subagent_type `asset-gatherer`. Pass the following prompt, substituting [COMPANY_NAME] and [CLIENT_ROOT]:

```
Gather assets for [COMPANY_NAME]. Follow the asset-gatherer spec at .claude/agents/asset-gatherer.md.
Client folder: [CLIENT_ROOT]/[COMPANY_NAME]/3. Company Resources/
Skip banner step entirely -- do not ask for or mention a banner.
```

Do not wait for the subagent to finish. Continue immediately to Step 9.

---

## Step 9: Write Session State

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
```

Write a session state file to `$WS/.claude/data/session_state_[company_slug]_YYYY-MM-DD.md` (use today's date). Contents:

```markdown
# Session State: [COMPANY_NAME]
Date: YYYY-MM-DD

## Company
[COMPANY_NAME]

## Client Root
[CLIENT_ROOT]

## Context
[pre_call or post_call]

## Branch
[A or B] -- [reason: which checks had data, or "all checks empty"]

## Vertical
[vertical label from Step 4]

## Template Paths
- Model: [CLIENT_ROOT]/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx
- Deck Folder: [CLIENT_ROOT]/[COMPANY_NAME]/2. Presentations/1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)
- Deck File: [COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx
- vF File: [COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx
- PDF File: [COMPANY_NAME] Intro Deck (YYYY.MM.DD).pdf
- Template Config: [CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/template_config.json

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

## Step 10: Report to User

Tell the user:

```
[COMPANY_NAME] initialized.

Context: [pre-call / post-call]
Branch: [A - Existing Relationship / B - Cold Prospect]
Reason: [which of Gong / Attio / Slack had data, or "no prior data found"]

Assets: gathering in background (logos, swag).

Next step: run /deck-research
```

Do not add anything beyond this summary.
