---
name: deck-setup
description: Run once per workspace to detect or create the client folder root and write workspace_config.json.
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

---

You are performing one-time workspace setup for the Jolly deck workflow. This skill runs once. If it has already been run, report the existing config and stop.

Set the workspace root:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
```

---

## Step 1: Check for Existing Config

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
cat "$WS/.claude/data/workspace_config.json" 2>/dev/null
```

If the file exists and is valid JSON with a `client_root` key, tell the user:

```
Workspace already configured.
  clients:   [client_root]/
  templates: [templates_root or "Templates (default)"]/
  tools:     [tools_root or "Tools (default)"]/
  gong:      [gong_integration or "none"]
  setup_date: [setup_date from file]

To change any setting, edit .claude/data/workspace_config.json directly.
Run /deck-start [Company] to begin.
```

Then stop. Do not re-run setup or overwrite the config.

---

## Step 2: Scan for Candidate Client Collection Folders

If no config exists, scan the workspace root for candidate folders. Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
find "$WS" -maxdepth 1 -type d | sort
```

From the output, exclude the following system folders (exact name matches):
- `.claude`
- `Tools`
- `Templates`
- `docs`
- `jolly-deck-plugin`
- `.git`
- Any folder whose name starts with `.`

The remaining folders are candidates. For each candidate, check whether any of its immediate subfolders match the standard client folder structure by looking for at least one subfolder that contains all of: `1. Model`, `2. Presentations`, `3. Company Resources`, `4. Reports`, `5. Call Transcripts`.

Run this check for each candidate:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
# For each candidate [FOLDER], check:
find "$WS/[FOLDER]" -maxdepth 2 -type d | sort
```

A candidate "has standard structure" if at least one of its direct subfolders contains all 5 required subdirectories. A candidate is "present but unstructured" if it exists but none of its subfolders have that pattern.

---

## Step 3: Decision Logic

Apply exactly one of the following three cases. Do not ask the user for input in cases 1 and 2.

**Case 1 -- Existing folder with correct structure:**
If exactly one candidate has the standard structure, tell the user:

```
Found existing client folder at [FOLDER_NAME]/ with standard structure. Using it.
```

Set `client_root` = that folder name (relative, e.g. "Garnett Station"). Set `structure_choice` = "existing".

Do not create any new folders.

**Case 2 -- Existing folder(s) with wrong or missing structure:**
If candidates exist but none have the standard structure, tell the user:

```
Found [FOLDER_NAME(s)] but subfolders are not structured as standard client folders.
Using standard Clients/ setup instead.
```

Create the folder:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
mkdir -p "$WS/Clients"
```

Set `client_root` = "Clients". Set `structure_choice` = "new_folder".

**Case 3 -- No existing client folders:**
If no candidates were found at all, tell the user:

```
No existing client folders found. Creating standard Clients/ folder.
```

Create the folder:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
mkdir -p "$WS/Clients"
```

Set `client_root` = "Clients". Set `structure_choice` = "new_folder".

**If multiple candidates have standard structure:** present them to the user as a numbered list and ask which one to use. Wait for the user's reply before proceeding.

---

## Step 4: Detect Templates Folder

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
find "$WS/Templates" -maxdepth 1 -type d 2>/dev/null | head -1
find "$WS" -maxdepth 2 -name "*.pptx" 2>/dev/null | head -3
```

Apply this logic silently (no user prompt):
1. If `$WS/Templates/` exists → `templates_root = "Templates"`
2. Else if any top-level folder at `$WS` contains `.pptx` files → `templates_root` = that folder name
3. Else → `templates_root = "Templates"`, create it:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
mkdir -p "$WS/Templates"
```

Do not tell the user. Continue to Step 5.

---

## Step 5: Detect Tools Folder

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
find "$WS/Tools" -maxdepth 1 -type d 2>/dev/null | head -1
```

Apply silently:
- If `$WS/Tools/` exists → `tools_root = "Tools"`
- Else → `tools_root = "Tools"` (no folder creation needed — tools are optional)

Do not tell the user. Continue to Step 5.5.

---

## Step 5.5: Configure Gong Integration

Ask the user:

```
Gong Integration

  [1] Rube — call data via rube.app (recommended)
  [2] Manual — transcripts already in 5. Call Transcripts/
  [3] Skip — not set up yet

→ 1, 2, or 3
```

Wait for the user's reply.

- If **1 (Rube)**: Tell the user:

  ```
  To connect Gong, you'll create a recipe on Rube that pulls call data for any
  company you research.

  Here's how:

    1. Go to rube.app and sign in.
    2. Click "New Recipe".
    3. Name it: gong_company_search
    4. In the description box, paste this:

       "Retrieves Gong calls for a specific Salesforce account and extracts
       comprehensive structured insights using multi-pass AI analysis. Returns
       maximum detail (metrics, pain points, tech stack, campaign signals,
       champions) with validation and retry logic to ensure nothing is missed."

    5. Add the Gong app as the integration.
    6. Set up these inputs:
         client_name     — Text (the company name to search for)
         days_back       — Number (default: 180)
         max_calls       — Number (default: 10)
         strict_salesforce_match  — "true" or "false" (default: "true")
         include_full_transcript  — "true" or "false" (default: "false")

    7. The recipe should run 6 extraction passes on each call:
         Pass 1 (HIGH reasoning): Revenue, employees, turnover, costs, growth rates
         Pass 2 (MEDIUM): Pain points and operational challenges
         Pass 3 (LOW): Tech stack — HRIS, ERP, POS, scheduling systems
         Pass 4 (MEDIUM): Campaign signals — behaviors to incentivize
         Pass 5 (LOW): 10 key quotes with speaker context
         Pass 6 (MEDIUM): Champions — decision-makers and internal advocates

    8. Save the recipe. Make sure it is named exactly: gong_company_search

    Once created, Claude will call this recipe automatically every time you run
    research on an existing client.

  Type "done" when your recipe is ready, or "skip" to set this up later.
  ```

  Wait for "done" or "skip".
  - If "done": set `gong_integration = "rube"`, `gong_webhook_url = null`
  - If "skip": set `gong_integration = "none"`, `gong_webhook_url = null`

- If **2 (Manual)**: set `gong_integration = "manual"`, `gong_webhook_url = null`
- If **3 (Skip)**: set `gong_integration = "none"`, `gong_webhook_url = null`

Continue to Step 6.

---

## Step 6: Write workspace_config.json

Write the config file:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
mkdir -p "$WS/.claude/data"
```

Write to `$WS/.claude/data/workspace_config.json` with the following content (substitute actual values):

```json
{
  "client_root": "[relative path decided in Step 3]",
  "templates_root": "[templates_root from Step 4]",
  "tools_root": "[tools_root from Step 5]",
  "gong_integration": "[rube | zapier | manual | none]",
  "gong_webhook_url": "[URL or null]",
  "setup_date": "[today YYYY-MM-DD]",
  "structure_choice": "[existing | new_folder]",
  "plugin_dir": "[path to plugin install directory]",
  "scripts_version": "3.0.0"
}
```

---

## Step 6.5: Install Plugin Resources

The plugin bundles all scripts, agents, templates, and tools. Copy them into the workspace so all skills can find them.

Locate the plugin install directory by traversing up from this SKILL.md file to the plugin root (the directory containing `.claude-plugin/plugin.json`).

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
PLUGIN_DIR="[path to plugin root directory]"

# Copy scripts
mkdir -p "$WS/.claude/scripts"
mkdir -p "$WS/.claude/agents"
mkdir -p "$WS/.claude/agents/templates"
mkdir -p "$WS/.claude/data"

cp "$PLUGIN_DIR/scripts/"*.py "$WS/.claude/scripts/" 2>/dev/null
cp "$PLUGIN_DIR/scripts/ws_env.sh" "$WS/.claude/scripts/ws_env.sh" 2>/dev/null
cp "$PLUGIN_DIR/scripts/excel_editor.py" "$WS/.claude/agents/excel_editor.py" 2>/dev/null
cp "$PLUGIN_DIR/scripts/template_scanner.py" "$WS/.claude/agents/template_scanner.py" 2>/dev/null
cp "$PLUGIN_DIR/scripts/jolly_utils.py" "$WS/.claude/agents/jolly_utils.py" 2>/dev/null

# Copy agent specs
cp "$PLUGIN_DIR/agents/"*.md "$WS/.claude/agents/" 2>/dev/null

# Copy template configs
cp "$PLUGIN_DIR/data/templates/"*.json "$WS/.claude/agents/templates/" 2>/dev/null
cp "$PLUGIN_DIR/data/templates/README.md" "$WS/.claude/agents/templates/" 2>/dev/null

# Copy vertical benchmarks
cp "$PLUGIN_DIR/data/vertical_benchmarks.json" "$WS/.claude/data/" 2>/dev/null

# Copy tools
mkdir -p "$WS/Tools/Goody Scraper"
cp "$PLUGIN_DIR/tools/brandfetch_downloader.py" "$WS/Tools/" 2>/dev/null
cp "$PLUGIN_DIR/tools/goody_scraper.py" "$WS/Tools/Goody Scraper/" 2>/dev/null
cp "$PLUGIN_DIR/tools/setup.bat" "$WS/Tools/" 2>/dev/null
```

Confirm the copies succeeded by checking that key files exist:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
ls "$WS/.claude/agents/excel_editor.py" "$WS/.claude/agents/template_scanner.py" "$WS/.claude/agents/templates/qsr_standard.json" "$WS/.claude/data/vertical_benchmarks.json" 2>/dev/null
```

If any key file is missing, report it to the user but continue setup.

---

## Step 7: Report to User

Tell the user:

```
Setup complete.

Workspace layout detected:
  clients:   [client_root]/
  templates: [templates_root]/
  tools:     [tools_root]/
  gong:      [gong_integration]

These paths are saved to .claude/data/workspace_config.json. If your folders
are named differently, edit that file to match.

Template configs available for: QSR, Retail. New templates will be auto-scanned.
Scripts version: 3.0.0 (bundled with plugin).

Expected workspace structure:
  [WORKSPACE ROOT]/
  ├── [templates_root]/           ← Intro deck and model templates (grouped by vertical)
  │     └── QSR/
  │           ├── QSR Intro Template.pptx
  │           └── QSR Intro Template.xlsx
  ├── [client_root]/              ← One subfolder per company
  │     └── Acme Corp/
  │           ├── 1. Model/
  │           ├── 2. Presentations/
  │           ├── 3. Company Resources/
  │           │     ├── 1. Logos/
  │           │     └── 2. Swag/
  │           ├── 4. Reports/
  │           │     ├── 1. Call Summaries/
  │           │     ├── 2. Public Filings/
  │           │     └── 3. Slack/
  │           └── 5. Call Transcripts/
  ├── [tools_root]/               ← Optional: scripts, cheatsheet_gen.py, etc.
  └── .claude/
        ├── agents/
        │     └── templates/      ← Template configs (auto-matched during deck-start)
        ├── data/
        │     └── workspace_config.json
        └── scripts/

Run /deck-start [Company] to begin a new engagement.
```

Do not add anything beyond this summary.
