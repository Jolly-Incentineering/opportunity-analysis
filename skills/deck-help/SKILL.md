---
name: deck-help
description: Show a quick-reference guide for the Opportunity Analysis plugin — all commands, what each one does, and where to start.
---

Print the following help text exactly. Do not add, remove, or summarize anything.

```
╔══════════════════════════════════════════════════════════════════════════════╗
║           JOLLY OPPORTUNITY ANALYSIS PLUGIN — QUICK REFERENCE               ║
╚══════════════════════════════════════════════════════════════════════════════╝

COMMANDS
────────────────────────────────────────────────────────────────────────────────

  /deck-help
    Show this reference guide.

  /deck-setup
    One-time workspace setup. Run this once on each new machine before anything
    else. Detects your client folder, templates, and Gong integration, then saves
    the config to .claude/data/workspace_config.json.

  /deck-auto [Company Name]
    ★ RECOMMENDED — runs the full workflow automatically.
    Give it a company name and Claude handles research, model population, deck
    formatting, and QA. Pauses only when it needs your input or when there is a
    manual step only you can do in PowerPoint. Progress is saved — if you stop
    mid-workflow, run the same command again and it picks up where it left off.

    Example: /deck-auto Firebirds

  /deck-start [Company Name]
    Step 1 of the manual workflow. Creates the client folder structure, copies
    the right template files, opens them, and starts downloading brand assets in
    the background. Run /deck-research next.

  /deck-research
    Step 2. Pulls everything Claude can find about the company — CRM records,
    Gong transcripts, emails, Slack messages, and public data. Proposes a
    campaign list for your approval before moving on.

  /deck-model
    Step 3. Shows you every value it plans to enter into the Excel model (with
    source for each number) and waits for your approval before writing anything.

  /deck-format
    Step 4. Populates the PowerPoint with values, brand assets, and logos. Walks
    you through any manual steps in PowerPoint one at a time. Exports PDF when done.

  /deck-qa
    Step 5. Runs 11 quality checks across the model and presentation. Flags
    anything that needs fixing before delivery.

CONTEXT
────────────────────────────────────────────────────────────────────────────────

  Pre-call
    Use before a call has happened. Includes Slack + Public research only.
    No Attio/Gong transcripts. Fast turnaround (~8–12 minutes).

  Post-call
    Use after a call has happened. Includes full Attio/Gong research with
    transcripts, plus Slack and Public data. Comprehensive (~14–20 minutes).

  At the start of every deck, Claude asks which context applies.

TYPICAL WORKFLOW
────────────────────────────────────────────────────────────────────────────────

  First time on a new machine:
    1. /deck-setup

  Every new Opportunity Analysis:
    2. /deck-auto [Company Name]   ← does everything below automatically

  Or step-by-step:
    2. /deck-start [Company Name]
    3. /deck-research
    4. /deck-model
    5. /deck-format
    6. /deck-qa

WHAT CLAUDE DOES vs. WHAT YOU DO
────────────────────────────────────────────────────────────────────────────────

  Claude handles:    Research, model population, text replacement, asset placement,
                     QA checks, PDF export, progress tracking.

  You handle:        Template selection, campaign list approval, model value review,
                     three manual PowerPoint steps (Claude walks you through each).

GATES — PLACES WHERE CLAUDE PAUSES AND WAITS FOR YOUR INPUT
────────────────────────────────────────────────────────────────────────────────

  1. Template selection      Pick the template that matches the client's industry
  2. Campaign list           Add/remove campaigns, then type "confirm"
  3. Model fill plan         Review every value + source, then type "approve"
  4. PowerPoint manual steps Complete each step, then type "done"

WORKSPACE STRUCTURE
────────────────────────────────────────────────────────────────────────────────

  Your Jolly folder (JOLLY_WORKSPACE) should contain:

    Templates/             ← intro deck templates grouped by vertical
    Clients/               ← one subfolder per company
      └── Company Name/
            ├── 1. Model/
            ├── 2. Presentations/
            │     └── 1. [Company] Intro Deck with Commentary (YYYY.MM.DD)/
            ├── 3. Company Resources/
            │     ├── 1. Logos/
            │     └── 2. Swag/
            ├── 4. Reports/
            │     ├── 1. Call Summaries/
            │     ├── 2. Public Filings/
            │     └── 3. Slack/
            └── 5. Call Transcripts/
    Tools/                 ← scripts (setup.bat, cheatsheet_gen.py)
    .claude/data/          ← workspace config and session state files

TROUBLESHOOTING
────────────────────────────────────────────────────────────────────────────────

  "Workspace not configured"
    → Run /deck-setup first.

  "A session already exists for this company"
    → Run /deck-auto [Company] to resume, or ask ops to delete the session
      file in .claude/data/ if you want to start over.

  "Templates folder not found"
    → Check that JOLLY_WORKSPACE is set as a System environment variable and
      that you restarted Claude Code after setting it.

  "Python not found" or package errors
    → Run Tools/setup.bat (double-click it in File Explorer) to install all
      required packages.

  Research taking too long
    → Normal: research runs 4 agents simultaneously and takes 3-5 minutes.
      If nothing happens after 10 minutes, something went wrong — ask Nishant.

  Updating the plugin
    → /plugin update opportunity-analysis

  Full setup guide
    → See #7 in the Incentineering section of Notion.

────────────────────────────────────────────────────────────────────────────────
```
