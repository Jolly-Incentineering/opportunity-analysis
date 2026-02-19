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
client_root: [client_root value from file]
setup_date: [setup_date from file]

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

## Step 4: Write workspace_config.json

Write the config file:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
mkdir -p "$WS/.claude/data"
```

Write to `$WS/.claude/data/workspace_config.json` with the following content (substitute actual values):

```json
{
  "client_root": "[relative path decided in Step 3]",
  "setup_date": "[today YYYY-MM-DD]",
  "structure_choice": "[existing | new_folder]"
}
```

---

## Step 5: Report to User

Tell the user:

```
Setup complete.
client_root: [client_root]
structure_choice: [existing | new_folder]

Run /deck-start [Company] to begin a new engagement.
```

Do not add anything beyond this summary.
