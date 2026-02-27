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

  /deck-auto [Company Name]
    ★ START HERE — runs the full workflow automatically.
    Give it a company name and Claude handles research, model population, deck
    formatting, and QA. Pauses only when it needs your input or when there is a
    manual step only you can do in PowerPoint.

    Example: /deck-auto Firebirds

  /deck-continue
    ★ RESUME — picks up where you left off.
    Reads your saved progress, shows which phases are done, and continues from
    the next pending phase. No arguments needed.

  /deck-help
    Show this reference guide.

  /deck-setup
    One-time workspace setup. Run once on each new machine before anything else.

  /deck-new-template [Vertical Name]
    Create a new vertical template (campaigns, model, deck, config).

  ADVANCED — Individual Phase Commands
  · · · · · · · · · · · · · · · · · · · · · · · · · · · · · · · · · · · · · ·
  These run a single phase. You don't need them — /deck-auto and /deck-continue
  handle everything. Use only if you want to re-run or debug a specific step.

    /deck-start [Company Name]    Phase 1: Create folders, copy templates
    /deck-research                Phase 2: Research + campaign selection
    /deck-model                   Phase 3: Populate Excel model
    /deck-format                  Phase 4: Populate deck, export PDF
    /deck-qa                      Phase 5: Quality checks

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
    2. /deck-auto [Company Name]   ← starts the workflow

  Interrupted or returning later:
    3. /deck-continue              ← resumes from where you left off

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
            │     └── 1. [Company] Intro Deck (YYYY.MM.DD)/
            ├── 3. Company Resources/
            │     ├── 1. Logos/
            │     └── 2. Swag/
            ├── 4. Reports/
            │     ├── 1. Call Summaries/
            │     ├── 2. Public Filings/
            │     └── 3. Slack/
            └── 5. Call Transcripts/
    Tools/                 ← scripts (setup.bat)
    .claude/data/          ← workspace config and session state files

TROUBLESHOOTING
────────────────────────────────────────────────────────────────────────────────

  "Workspace not configured"
    → Run /deck-setup first.

  "A session already exists for this company"
    → Run /deck-continue to resume, or delete the session file in
      .claude/data/ if you want to start over.

  "Templates folder not found"
    → Check that JOLLY_WORKSPACE is set as a System environment variable and
      that you restarted Claude Code after setting it.

  "Python not found" or package errors
    → Run: pip install openpyxl python-pptx requests
      Or re-run /jolly-onboarding to install packages step by step.

  Research taking too long
    → Normal: research runs 3 agents simultaneously and takes 3-5 minutes.
      If nothing happens after 10 minutes, something went wrong — ask Nishant.

  Updating the plugin
    → /plugin update opportunity-analysis

  Full setup guide
    → See #7 in the Incentineering section of Notion.

────────────────────────────────────────────────────────────────────────────────
```
