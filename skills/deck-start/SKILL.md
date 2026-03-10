---
name: deck-start
description: Run the full intro deck workflow for a company. Saves progress after every phase and resumes if interrupted. Usage: /deck-start [Company Name].
disable-model-invocation: true
---

Read and follow all rules in skills/shared-preamble.md before proceeding.

---

You are the `deck-start` orchestrator for the Jolly intro deck workflow. Run all five phases end-to-end for a single company, pausing only at required human gates, saving state after every phase.

The company name is the argument passed to `/deck-start`. Substitute [COMPANY_NAME] throughout.

**Bash preamble** — use at the start of every bash block:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
```

Derive `company_slug`: lowercase, spaces → underscores, remove special characters. Compute once, reuse.

---

## Phase 0: Workspace Check

Read `$WS/.claude/data/workspace_config.json`. If missing or invalid, tell the user:

```
Welcome to the Jolly deck workflow. Before starting, you need to run one-time setup.

Here's what to do:

  1. Run /deck-setup   - finds your client folder and saves your workspace config.
                         Takes a few seconds. Only needed once per machine.

  2. Then run /deck-start [COMPANY_NAME] again to begin.
```

Then stop.

### Library Check

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

- If **MISSING_REQUIRED**: tell the user "Missing required packages: [list]. Run Tools/setup.bat (Windows) or: pip install openpyxl python-pptx requests. Then re-run /deck-start [COMPANY_NAME]." Then stop.
- If **MISSING_OPTIONAL**: tell the user "Note: optional packages not installed: [list]. SEC filing lookups and PDF metadata editing will be skipped. To enable: pip install [list]." Then continue.
- If **OK**: continue silently.

---

## Phase 0B: Session State Check

Scan `$WS/.claude/data/session_state_*.json` for a file matching [COMPANY_NAME].

**If found:** Show phase status. Ask "go" to continue or "stop [N]" to jump. Wait.

**If not found:**

```
No existing session for [COMPANY_NAME]. Starting from Phase 1.

Context

  [1] Pre-call — no call yet
      Slack + Public data only (~8-12 min)

  [2] Post-call — after a call or internal notes
      Full Attio + Slack + Public (~14-20 min)

→ 1 or 2
```

Use AskUserQuestion:
- Question: "What context is this deck for?"
- Options: ["Pre-call — no call yet", "Post-call — after a call or internal notes"]

Store as `context`. Then show phase plan and gate checklist, then use AskUserQuestion:
- Question: "Ready to start?"
- Options: ["Go", "Stop — I need to check something first"]

Tell the user:

```
Gates this run:
  Phase 0:  □ Context selected
  Phase 1:  □ Template selected
  Phase 2:  □ Conflicts/gaps resolved  □ Campaigns confirmed
  Phase 3:  □ Model closed  □ Dry-run approved  □ Model review passed  □ Model saved
  Phase 4:  □ Placeholders written  □ Campaign slides  □ Logo  □ Macabacus  □ Links broken  □ Visual review  □ PDF exported  □ PDF reviewed
  Phase 5:  □ Model QA confirmed  □ Deck QA confirmed  □ Delivery ready
```

After each gate is confirmed, echo "[Gate name] ✓" in your reply before proceeding.

---

## Phase 1: Start

Tell the user: "Phase 1: Start — running."

### 1.1 Ensure Client Folder Structure

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]"/{1." Model","2. Presentations","3. Company Resources/1. Logos","3. Company Resources/2. Swag","4. Reports/1. Call Summaries","4. Reports/2. Public Filings","4. Reports/3. Slack","5. Call Transcripts"}
```

### 1.2 Template Selection

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
find "$WS/$TEMPLATES_ROOT" -type f \( -name "*.xlsx" -o -name "*.pptx" \) | sort
```

Build a numbered list of available template pairs grouped by vertical (one template per vertical). Each pair is one `.xlsx` and one `.pptx` with matching names. Present only template pairs (both files exist). Show the vertical folder name and the template display name.

Example format:

```
Template for [COMPANY_NAME]

  QSR
    [1] QSR Intro Template

  Retail
    [2] Retail Intro Template

-> Number, or "new" to create a template for a different vertical
```

If the user types "new", run `/deck-new-template` and return after the template is created.

Wait for the user's choice. Record the chosen template number, derive the vertical from the chosen template's folder name, and record the full paths to both files.

### 1.3 Copy Templates

Using today's date in YYYY.MM.DD format, create a subfolder under Presentations and copy the template files:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)"
cp "[full source .xlsx path]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx"
cp "[full source .pptx path]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx"
python3 "$WS/.claude/scripts/deck_engine.py" set-title \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" \
  --title "[COMPANY_NAME] Intro Model (YYYY.MM.DD)"
python3 "$WS/.claude/scripts/deck_engine.py" set-title \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx" \
  --title "[COMPANY_NAME] Intro Deck (YYYY.MM.DD)"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" &
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx"
```

Tell the user: "Templates copied and opened. Model: [filename]. Deck: [filename]."

Record the presentation subfolder path and deck filename - they will be written to session state as `deck_folder`, `deck_filename`, `vf_deck_filename`, and `pdf_filename`.

Naming conventions:
- Deck subfolder: `1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)/`
- Deck filename: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx`
- vF filename: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx`
- PDF filename: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pdf`

### 1.4 Scan Template and Load Config

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
python3 "$WS/.claude/agents/template_scanner.py" \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" \
  --configs-dir "$WS/.claude/agents/templates/" --threshold 0.85
```

**If a match is found (>=85% similarity):**

Check whether the Excel template has been modified since the config was last updated:

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

- If **STALE**: re-scan and update the config:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 "$WS/.claude/agents/template_scanner.py" \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" \
  --create \
  --output "$WS/.claude/agents/templates/[matched_config].json"
```

Tell the user: "Template newer than config - re-scanned [matched_config].json." Then continue.

- If **FRESH**: no action needed, continue.

Copy the config to the client folder:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
cp "$WS/.claude/agents/templates/[matched_config].json" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/template_config.json"
```

**If no match is found:**

Create a new config:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
python3 "$WS/.claude/agents/template_scanner.py" \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" \
  --create \
  --output "$WS/.claude/agents/templates/[company_slug]_custom.json"
cp "$WS/.claude/agents/templates/[company_slug]_custom.json" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/template_config.json"
```

Extract from config: campaign names (from `campaigns` dict), formula counts (from `formula_counts` dict), cell addresses (from `labels` dict), template type name.

Tell the user: "Template scanned. Config: [template type]. Campaigns: [list names]. Config saved to 4. Reports/template_config.json."

### 1.5 Detect Branch (Attio Check)

Check Attio for existing company records or notes. Preferred: use the Attio REST API if ATTIO_API_KEY is available (check environment and .env file). If the key exists, run:

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

Branch decision:
- If Attio has records OR notes for the company: **Branch A (existing relationship)**
- If Attio returns no records: **Branch B (cold prospect)**

Record `branch_reason` as "Attio records found" or "no Attio records".

### 1.6 Launch Asset Gatherer

Launch a background subagent using the Task tool with subagent_type `asset-gatherer`. Pass the following prompt, substituting [COMPANY_NAME] and [CLIENT_ROOT]:

```
Gather assets for [COMPANY_NAME]. Follow the asset-gatherer spec at .claude/agents/asset-gatherer.md.
Client folder: [CLIENT_ROOT]/[COMPANY_NAME]/3. Company Resources/
Skip banner step entirely -- do not ask for or mention a banner.
```

Do not wait for the subagent to finish. Continue immediately.

### 1.7 Save State

Write `session_state_[company_slug]_YYYY-MM-DD.json` to `$WS/.claude/data/`:

```python
python3 -c "
import json, os
from datetime import date
ws = os.environ.get('JOLLY_WORKSPACE', '.')
slug = '[company_slug]'
today = date.today().isoformat()
data = {
    'company_name': '[COMPANY_NAME]',
    'company_slug': slug,
    'client_root': '[CLIENT_ROOT]',
    'context': '[pre_call or post_call]',
    'branch': '[A or B]',
    'branch_reason': '[reason]',
    'vertical': '[vertical]',
    'session_date': today,
    'last_updated': today,
    'template_paths': {
        'model': '[model path]',
        'deck_folder': '[deck folder path]',
        'deck_filename': '[deck filename]',
        'vf_filename': '[vF filename]',
        'pdf_filename': '[pdf filename]',
        'template_config': '[template config path]'
    },
    'phase_checklist': {
        'phase_1_initialization': 'complete',
        'phase_2_research': 'pending',
        'phase_3_model_population': 'pending',
        'phase_4_deck_formatting': 'pending',
        'phase_5_qa_delivery': 'pending'
    },
    'next_action': 'phase_2',
    'campaigns_selected': [],
    'template_config_cache': json.load(open('[template config path]', encoding='utf-8')),
    'metadata': {}
}
out = f'{ws}/.claude/data/session_state_{slug}_{today}.json'
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'w') as f: json.dump(data, f, indent=2)
print('Saved:', out)
"
```

Tell user: "Phase 1 complete. Moving to Phase 2: Research..."

---

## Phase 2: Research

Tell the user: "Phase 2: Research - running."

Invoke the `/deck-research` skill. Follow it completely. When it finishes and session state shows phase_2 complete, continue.

---

## Phase 3: Model

Tell the user: "Phase 3: Model - running."

Invoke the `/deck-model` skill. Follow it completely. When it finishes and session state shows phase_3 complete, continue.

---

## Phase 4: Format

Tell the user: "Phase 4: Format - running."

Invoke the `/deck-format` skill. Follow it completely. When it finishes and session state shows phase_4 complete, continue.

---

## Phase 5: QA

Tell the user: "Phase 5: QA - running."

Invoke the `/deck-qa` skill. Follow it completely. When it finishes, present the final summary below.

---

## Final Summary

Read session state and research output to populate:

```
[COMPANY_NAME] deck complete.

Campaigns: [list each with ROPS]
Accretion: [X]% of EBITDA

Files:
  PPT:   [full path to vF.pptx]
  Model: [full path to model .xlsx]
  PDF:   [full path to .pdf]

QA: [PASS / PASS with notes]
All phases complete. Ready for delivery.
```

Do not add anything beyond this summary.
