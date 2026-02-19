# jolly-deck

Claude Code plugin for the Jolly intro deck workflow. Six slash commands take a company from zero to a formatted, QA'd deck package.

---

## Install

```bash
/plugin install nishant-jolly/jolly-deck --scope user
```

Requires GitHub access to the private repo.

---

## One-Time Setup (per person)

### 1. Set your workspace path

Add to your shell profile (`.bashrc`, `.zshrc`) or Windows environment variables:

```bash
export JOLLY_WORKSPACE="/path/to/Jolly - Documents"
```

Example for OneDrive:
```bash
export JOLLY_WORKSPACE="/c/Users/YourName/OneDrive - Default Directory/Jolly - Documents"
```

Or add it to `.claude/.env` at the workspace root:
```
JOLLY_WORKSPACE=C:/Users/YourName/OneDrive - Default Directory/Jolly - Documents
```

### 2. Run workspace setup (once per machine)

```
/deck-setup
```

This scans your workspace, detects or creates the client folder structure, and saves a config. You only do this once — all subsequent commands read from it.

---

## Commands

Run these in order for each new company.

### `/deck-setup`
One-time workspace configuration. Detects existing client folder structure — if it matches the standard layout, uses it as-is. If not, creates a new `Clients/` folder with the standard structure. Saves your choice to `.claude/data/workspace_config.json` and skips automatically on future runs.

### `/deck-start [Company Name]`
Initializes a new deck engagement. Checks for existing session state, lists available templates, copies the right one to the client folder, adds the company to the Notion pipeline, detects whether a prior sales call has happened (Branch A) or this is a cold prospect (Branch B), and launches asset gathering in the background.

```
/deck-start Firebirds
```

### `/deck-research`
Runs all research workstreams in parallel using dedicated agents — one each for Attio/Gong, Microsoft 365, Slack, and public data (SEC filings, web, LinkedIn). Each agent writes a structured JSON to `.claude/data/` and exits, keeping the main context clean. After all agents complete, results are merged and you approve the campaign list before any Excel work begins.

### `/deck-model`
Reads the approved campaign list from session state, maps the actual Excel file by row label (never by hardcoded row number — handles all template variants), runs a dry-run showing every value and ROPS before writing, waits for your approval, then writes values and comments to the model. Verifies formula counts after writing.

### `/deck-format`
Walks you through the three manual steps (Macabacus refresh, Figma paste, break links) one at a time with clear instructions, waiting for confirmation at each step. After you confirm links are broken, runs the formatter automatically and performs a QA scan for unformatted values, unfilled placeholders, and cross-slide inconsistencies.

### `/deck-qa`
Runs the PE diligence audit, reports any critical or high issues, and opens the final files for review.

---

## Workflow Summary

```
/deck-setup          (once per machine)

/deck-start Acme     starts the engagement, launches assets in background
/deck-research       parallel agents research + campaign gate
/deck-model          dry run + Excel population
/deck-format         manual steps + formatting + QA
/deck-qa             final audit + open files
```

Total time: ~30-45 minutes per deck.

---

## Folder Structure

The plugin works with this client folder layout (created automatically if it does not exist):

```
[client_root]/[Company Name]/
  1. Model/              Excel model (.xlsx)
  2. Presentations/      PowerPoint deck (.pptx) and vF copy
  3. Company Resources/
      Logos/             Brand logos (PNG, SVG, brand_info.json)
      Swag/              Branded merchandise mockups
  4. Reports/            PDFs and audit reports
  5. Call Transcripts/   Gong insights JSON and call transcript .md files
```

`client_root` is set during `/deck-setup` and stored in `.claude/data/workspace_config.json`.

---

## Requirements

- Claude Code with the superpowers plugin installed (`/plugin install superpowers@mbenhamd --scope user`)
- MCP integrations connected in Claude.ai Settings: Slack, Attio, Linear, Notion, Microsoft 365
- Python packages: `openpyxl`, `python-pptx`, `requests`, `edgartools`
- `JOLLY_WORKSPACE` environment variable pointing to the shared workspace root

---

## Updating

When the plugin is updated, run:

```bash
/plugin update jolly-deck
```

---

## Support

Contact the ops team or open an issue in the repo.
