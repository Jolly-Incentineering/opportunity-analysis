---
name: deck-setup
description: Run once per workspace to detect or create the client folder root and write workspace_config.json.
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
  setup_date: [setup_date from file]

To change paths, edit .claude/data/workspace_config.json directly.
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

Do not tell the user. Continue to Step 6.

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
  "setup_date": "[today YYYY-MM-DD]",
  "structure_choice": "[existing | new_folder]"
}
```

---

## Step 7: Report to User

Tell the user:

```
Setup complete.

Workspace layout detected:
  clients:   [client_root]/
  templates: [templates_root]/
  tools:     [tools_root]/

These paths are saved to .claude/data/workspace_config.json. If your folders
are named differently, edit that file to match.

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
  │           │     ├── Logos/
  │           │     └── Swag/
  │           ├── 4. Reports/
  │           │     └── research/
  │           └── 5. Call Transcripts/
  ├── [tools_root]/               ← Optional: scripts, cheatsheet_gen.py, etc.
  └── .claude/
        └── data/
              └── workspace_config.json

Run /deck-start [Company] to begin a new engagement.
```

Do not add anything beyond this summary.
