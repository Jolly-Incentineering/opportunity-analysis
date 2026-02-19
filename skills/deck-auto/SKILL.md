---
name: deck-auto
description: Run the full intro deck workflow automatically for a company. Saves progress after every phase and resumes if interrupted. Usage: /deck-auto [Company Name].
---

You are the `deck-auto` orchestrator for the Jolly intro deck workflow. Your job is to run all five phases of the workflow end-to-end for a single company, pausing only at required human gates, and saving state after every phase so work can be resumed across sessions.

The company name is the argument the user passed to `/deck-auto`. Substitute [COMPANY_NAME] throughout with that exact value.

Set workspace root and client root at the start of every bash block:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
```

Derive `company_slug` from [COMPANY_NAME]: lowercase, spaces replaced with underscores, remove all special characters. Compute this once and reuse it throughout.

---

## Phase 0: Workspace Check

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
cat "$WS/.claude/data/workspace_config.json" 2>/dev/null
```

If the file does not exist or is not valid JSON with a `client_root` key, stop and tell the user:

```
Welcome to the Jolly deck workflow. Before starting, you need to run one-time setup.

Here's what to do:

  1. Run /deck-setup   — finds your client folder and saves your workspace config.
                         Takes a few seconds. Only needed once per machine.

  2. Then run /deck-auto [COMPANY_NAME] again to begin.
```

Do not proceed past Phase 0 until workspace_config.json is confirmed valid. Once confirmed, read and store `CLIENT_ROOT` from its `client_root` field.

---

## Phase 0B: Session State Check and Plan Announcement

Scan for existing session state files:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
ls "$WS/.claude/data/session_state_"*.md 2>/dev/null | sort
```

For each file found, read it and check whether the `company` field matches [COMPANY_NAME] (case-insensitive).

**If a matching session state file exists:**

Read the phase checklist from it. Determine which phases are complete, which is in progress, and which are pending. Tell the user:

```
Resuming [COMPANY_NAME] from [session date].
Last completed phase: Phase [N] -- [phase name].
Next action: [next action from state file].

Phase status:
  Phase 0: Workspace check     -- complete
  Phase 1: Start               -- [complete / pending]
  Phase 2: Research            -- [complete / in progress / pending]
  Phase 3: Model               -- [complete / in progress / pending]
  Phase 4: Format              -- [complete / in progress / pending]
  Phase 5: QA                  -- [complete / in progress / pending]

Type "go" to continue from Phase [N+1], or "stop [N]" to jump directly to a specific phase:
```

Wait for the user to type "go" or "stop [N]" before proceeding. If the user types "stop [N]", skip directly to that phase. If the user types "go", skip all complete phases and start the next pending one. If a phase is marked "in progress", restart it from its beginning.

**If no matching session state file exists:**

Tell the user:

```
No existing session found for [COMPANY_NAME]. Starting from Phase 1.

Phases to run:
  Phase 1: Start               -- initialize folder, templates, branch detection
  Phase 2: Research            -- 4 parallel research agents, merge, campaign selection
  Phase 3: Model               -- dry-run plan, Excel population, formula verification
  Phase 4: Format              -- Macabacus refresh, Figma paste, link-break, deck_format.py
  Phase 5: QA                  -- 13 checks (M1-M6 model, D1-D7 deck), open final files

Human gates (will pause for your input):
  - End of Phase 2: campaign selection confirmation
  - Start of Phase 3 writes: dry-run approval
  - Phase 4: Macabacus refresh, Figma paste, link-break (one at a time)
  - Phase 5: any FAIL checks before re-running

Type "go" to begin, or "stop [N]" to jump to a specific phase:
```

Wait for "go" or "stop [N]" before proceeding.

---

## Phase 1: Start

Tell the user: "Phase 1: Start -- running."

### 1.1 Ensure Client Folder Structure

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]" -type d -maxdepth 4 2>/dev/null
```

Check whether the following folders all exist:
- `$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/`
- `$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/`
- `$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Logos/`
- `$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Swag/`
- `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/`
- `$WS/$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts/`

If any are missing, create them silently:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Logos"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Swag"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts"
```

Do not tell the user which folders were created. Do not stop or ask for input. Continue to 1.2.

### 1.2 Show Templates and Ask for Template

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
find "$WS/Templates" -type f \( -name "*.xlsx" -o -name "*.pptx" \) | sort
```

From the output, build a numbered list of available template pairs grouped by vertical. Present only pairs where both the `.xlsx` and `.pptx` exist with matching names. Example format:

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

Wait for the user's reply. Record: chosen template number, derive vertical from the chosen template's folder name, and full paths to both template files.

### 1.3 Copy Templates to Client Folder

Using today's date in YYYY.MM.DD format, copy the chosen templates:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
cp "[full source .xlsx path]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx"
cp "[full source .pptx path]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx"
```

Then open both files:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx"
```

Update document title metadata on both files to match the filename (without extension):

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 - \
  "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" \
  "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx" \
  "[COMPANY_NAME] Intro Model (YYYY.MM.DD)" \
  "[COMPANY_NAME] Intro Deck (YYYY.MM.DD)" <<'EOF'
import sys
from openpyxl import load_workbook
from pptx import Presentation
wb = load_workbook(sys.argv[1]); wb.properties.title = sys.argv[3]; wb.save(sys.argv[1])
prs = Presentation(sys.argv[2]); prs.core_properties.title = sys.argv[4]; prs.save(sys.argv[2])
EOF
```

Record both destination paths. They will be written to session state.

### 1.4 Detect Branch (3 Parallel Checks)

Run all three checks simultaneously -- do not wait for one before starting the others:

**Check A -- Gong insights file:**

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts" -name "gong_insights_*.json" 2>/dev/null
```

A file counts as "has data" only if its date (from filename `gong_insights_YYYY-MM-DD.json`) is within the last 30 days.

**Check B -- Attio CRM:**

Call `mcp__claude_ai_Attio__search-records` with query [COMPANY_NAME]. Result counts as "has data" if any records are returned.

**Check C -- Slack channel:**

Derive a channel slug: [COMPANY_NAME] lowercase, spaces replaced with hyphens, special characters removed. Call `mcp__claude_ai_Slack__slack_search_channels` with that slug. Result counts as "has data" if any channels are returned.

Branch decision:
- If ANY check has data: **Branch A (existing relationship)**
- If ALL checks are empty: **Branch B (cold prospect)**

Record which checks had data -- this is the branch reason.

### 1.6 Launch Asset Gatherer as Background Subagent

Launch a background subagent using the Task tool. Pass this prompt (substitute actual values):

```
Gather assets for [COMPANY_NAME]. Follow the asset-gatherer spec at .claude/agents/asset-gatherer.md.
Client folder: [CLIENT_ROOT]/[COMPANY_NAME]/3. Company Resources/
Skip banner step entirely -- do not ask for or mention a banner.
```

Do not wait for the subagent. Continue immediately.

### 1.7 Save State After Phase 1

Write `$WS/.claude/data/session_state_YYYY-MM-DD.md` (use today's date):

```markdown
# Session State: [COMPANY_NAME]
Date: YYYY-MM-DD
Mode: auto

## Company
[COMPANY_NAME]

## Client Root
[CLIENT_ROOT]

## Branch
[A or B] -- [reason: which checks had data, or "all checks empty"]

## Vertical
[vertical label]

## Template Paths
- Model: [CLIENT_ROOT]/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx
- Deck: [CLIENT_ROOT]/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx

## Phase Checklist
- Phase 0: Workspace check -- complete
- Phase 1: Start -- complete
- Phase 2: Research -- pending
- Phase 3: Model -- pending
- Phase 4: Format -- pending
- Phase 5: QA -- pending

## Approved Campaigns
(none yet)

## Last Completed Step
Phase 1: Start complete

## Next Action
Phase 2: Research
```

Tell the user: "Phase 1 complete. Moving to Phase 2: Research..."

Then immediately continue to Phase 2 without waiting for any user input.

---

## Phase 2: Research

Tell the user: "Phase 2: Research -- running."

### 2.1 Check and Ensure Gong Recipe Exists (Branch A Only)

Skip this step entirely if branch is B.

Call `mcp__rube__RUBE_FIND_RECIPE` with `name: "gong_company_search"`.

If the recipe is NOT found, create it using `mcp__rube__RUBE_CREATE_UPDATE_RECIPE` with:
- Recipe name: `gong_company_search`
- Description: "Search Gong calls by date range and retrieve transcripts for matched calls."
- Steps:
  - Pass 1: Call `GONG_RETRIEVE_FILTERED_CALL_DETAILS` with:
    - `filter__fromDateTime`: `"{{from_date}}T00:00:00Z"`
    - `filter__toDateTime`: `"{{to_date}}T23:59:59Z"`
    - `contentSelector__exposedFields__content__brief`: `true`
    - `contentSelector__exposedFields__parties`: `true`
    - `contentSelector__context`: `"Extended"`
    - `contentSelector__contextTiming`: `["Now", "TimeOfCall"]`
  - Pass 2: Call `GONG_GET_CALL_TRANSCRIPT` with:
    - `filter.callIds`: `["{{matched_call_ids}}"]`

Confirm the recipe exists before proceeding to 2.2.

### 2.2 Dispatch 4 Research Agents in Parallel

Dispatch all 4 agents simultaneously using the Task tool. Issue all 4 Task calls in a single message. Do not wait for any one agent before dispatching the others. Compute today's date and 180 days ago before dispatching -- pass them as literal date strings in each prompt.

Use `model: "haiku"` and `extended_thinking: true` for all 4 agents. Each agent prompt should begin with the reasoning preamble defined below.

Target: all 4 agents complete within 5 minutes total. Each agent should make only the tool calls listed -- do not expand scope.

Output path for all agents: `$WS/.claude/data/ws_[workstream]_[company_slug].json`

---

**Agent 1: ws-attio-gong**

Output file: `$WS/.claude/data/ws_attio_gong_[company_slug].json`

Pass this prompt (substitute all bracketed values), using `model: "haiku"`:

```
Before taking any action, reason through the full plan: what data sources are available for this company, what each tool call is likely to return, and what the most efficient sequence of calls is. Only then begin executing. Do not make a tool call without first reasoning about whether it is necessary and what you expect it to return.

You are the ws-attio-gong research agent for the Jolly deck workflow.

Company: [COMPANY_NAME]
Company slug: [company_slug]
Branch: [A or B]
Vertical: [vertical]
Workspace root (WS): [WS]
Client root (CLIENT_ROOT): [CLIENT_ROOT]
Today's date: [YYYY-MM-DD]
180 days ago: [YYYY-MM-DD]

Your job: run Attio + Gong research and write a clean JSON output.

--- ATTIO (Branch A only -- if Branch B, skip all Attio calls and set all Attio fields to empty) ---

Fire all 4 Attio calls in parallel:
1. mcp__claude_ai_Attio__search-records -- query: [COMPANY_NAME]
2. mcp__claude_ai_Attio__get-records-by-ids -- for any record IDs returned in call 1
3. mcp__claude_ai_Attio__semantic-search-notes -- query: [COMPANY_NAME]
4. mcp__claude_ai_Attio__search-emails-by-metadata -- query: [COMPANY_NAME]

Extract from results: revenue mentions, headcount mentions, location counts, pain points, pricing signals, any campaigns mentioned.

--- GONG (Branch A only -- if Branch B, skip and set all Gong fields to empty) ---

Run RUBE recipe "gong_company_search" (it already exists -- do not recreate it):
- from_date: [180 days ago YYYY-MM-DD]
- to_date: [today YYYY-MM-DD]

From Pass 1 results, identify matched call IDs. Take the 6 most recent. Fire GONG_GET_CALL_TRANSCRIPT for each matched call ID in parallel (up to 6 simultaneous calls).

For each transcript retrieved:
- Extract: call date, call title, participants, key topics, verbatim quotes relevant to revenue, headcount, locations, turnover, pricing, and pain points.
- Write the transcript to: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/5. Call Transcripts/[YYYY-MM-DD]_[Call Title].md

After all transcripts are saved, write a consolidated insights file to:
[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/5. Call Transcripts/gong_insights_[today YYYY-MM-DD].json

The gong_insights JSON schema:
{
  "company": "[COMPANY_NAME]",
  "generated_date": "[YYYY-MM-DD]",
  "call_count": 0,
  "calls": [
    {
      "call_id": "",
      "date": "",
      "title": "",
      "participants": [],
      "topics": [],
      "quotes": []
    }
  ],
  "aggregate_insights": {
    "revenue_mentions": [],
    "headcount_mentions": [],
    "location_mentions": [],
    "pain_points": [],
    "campaigns_mentioned": []
  }
}

--- OUTPUT ---

Write your output to: [WS]/.claude/data/ws_attio_gong_[company_slug].json

Schema:
{
  "workstream": "attio_gong",
  "company": "[COMPANY_NAME]",
  "findings": {
    "attio_records_count": 0,
    "attio_notes_count": 0,
    "attio_emails_count": 0,
    "gong_calls_found": 0,
    "gong_calls_transcribed": 0,
    "revenue": null,
    "revenue_source": "",
    "unit_count": null,
    "unit_count_source": "",
    "employee_count": null,
    "employee_count_source": "",
    "pain_points": [],
    "campaigns_mentioned": [],
    "verbatim_quotes": [],
    "other_data_points": {}
  },
  "source_summary": {
    "attio_used": false,
    "gong_used": false,
    "transcript_files_written": [],
    "gong_insights_file_written": ""
  }
}

Populate all fields from your research. If branch is B, set attio_used and gong_used to false and leave findings empty. Write the file. Do not output a long summary -- just confirm the file path written.
```

---

**Agent 2: ws-m365**

Output file: `$WS/.claude/data/ws_m365_[company_slug].json`

Pass this prompt (substitute all bracketed values), using `model: "haiku"`:

```
Before taking any action, reason through the full plan: what data sources are available for this company, what each tool call is likely to return, and what the most efficient sequence of calls is. Only then begin executing. Do not make a tool call without first reasoning about whether it is necessary and what you expect it to return.

You are the ws-m365 research agent for the Jolly deck workflow.

Company: [COMPANY_NAME]
Company slug: [company_slug]
Branch: [A or B]
Workspace root (WS): [WS]
Today's date: [YYYY-MM-DD]
180 days ago: [YYYY-MM-DD]

Your job: run Microsoft 365 research (Outlook + SharePoint) and write a clean JSON output.

If Branch B, skip all M365 calls and write an empty findings output.

Fire both calls in parallel:
1. mcp__claude_ai_Microsoft_365__outlook_email_search: query="[COMPANY_NAME]", afterDateTime=[180 days ago ISO 8601], limit=20
2. mcp__claude_ai_Microsoft_365__sharepoint_search: query="[COMPANY_NAME]", limit=10

After results return, read the full email body only for emails whose subject line contains any of these keywords (case-insensitive): revenue, headcount, locations, turnover, pricing, contract, or $.

Use mcp__claude_ai_Microsoft_365__read_resource to fetch full body for qualifying emails.

If the Microsoft 365 integration is not available or returns an auth error, skip all calls silently and set m365_available to false in output.

Extract from results: revenue figures, headcount, location counts, pricing signals, any campaign mentions.

Write output to: [WS]/.claude/data/ws_m365_[company_slug].json

Schema:
{
  "workstream": "m365",
  "company": "[COMPANY_NAME]",
  "findings": {
    "emails_found": 0,
    "emails_read_full": 0,
    "sharepoint_results": 0,
    "revenue": null,
    "revenue_source": "",
    "unit_count": null,
    "unit_count_source": "",
    "employee_count": null,
    "employee_count_source": "",
    "pain_points": [],
    "campaigns_mentioned": [],
    "other_data_points": {}
  },
  "source_summary": {
    "m365_available": true,
    "outlook_used": false,
    "sharepoint_used": false,
    "skip_reason": ""
  }
}

Write the file. Do not output a long summary -- just confirm the file path written.
```

---

**Agent 3: ws-slack**

Output file: `$WS/.claude/data/ws_slack_[company_slug].json`

Pass this prompt (substitute all bracketed values), using `model: "haiku"`:

```
Before taking any action, reason through the full plan: what data sources are available for this company, what each tool call is likely to return, and what the most efficient sequence of calls is. Only then begin executing. Do not make a tool call without first reasoning about whether it is necessary and what you expect it to return.

You are the ws-slack research agent for the Jolly deck workflow.

Company: [COMPANY_NAME]
Company slug: [company_slug]
Branch: [A or B]
Workspace root (WS): [WS]

Your job: run Slack research and write a clean JSON output.

If Branch B, skip all Slack calls and write an empty findings output.

Fire both keyword searches in parallel:
1. mcp__claude_ai_Slack__slack_search_public_and_private: query="[COMPANY_NAME] revenue"
2. mcp__claude_ai_Slack__slack_search_public_and_private: query="[COMPANY_NAME] locations headcount turnover"

If either search returns zero useful results (no messages with data points), then and only then read the channel directly:
- mcp__claude_ai_Slack__slack_read_channel: limit=50, for the most relevant channel found

Do not read the channel if keyword searches return useful results.

Extract from results: revenue figures, headcount, location counts, pricing signals, pain points, campaign mentions.

Write output to: [WS]/.claude/data/ws_slack_[company_slug].json

Schema:
{
  "workstream": "slack",
  "company": "[COMPANY_NAME]",
  "findings": {
    "messages_found": 0,
    "channel_read": false,
    "revenue": null,
    "revenue_source": "",
    "unit_count": null,
    "unit_count_source": "",
    "employee_count": null,
    "employee_count_source": "",
    "pain_points": [],
    "campaigns_mentioned": [],
    "other_data_points": {}
  },
  "source_summary": {
    "slack_available": true,
    "keyword_searches_run": 2,
    "channel_fallback_used": false,
    "skip_reason": ""
  }
}

Write the file. Do not output a long summary -- just confirm the file path written.
```

---

**Agent 4: ws-public**

Output file: `$WS/.claude/data/ws_public_[company_slug].json`

Pass this prompt (substitute all bracketed values), using `model: "haiku"`:

```
Before taking any action, reason through the full plan: what data sources are available for this company, what each tool call is likely to return, and what the most efficient sequence of calls is. Only then begin executing. Do not make a tool call without first reasoning about whether it is necessary and what you expect it to return.

You are the ws-public research agent for the Jolly deck workflow.

Company: [COMPANY_NAME]
Company slug: [company_slug]
Vertical: [vertical]
Workspace root (WS): [WS]
Today's date: [YYYY-MM-DD]

Your job: run SEC filings, vertical benchmarks, and web research. Write a clean JSON output.

--- SEC FILINGS ---

Determine whether [COMPANY_NAME] is publicly traded (use your knowledge or do one WebSearch).

If public:
  Run: python "[WS]/.claude/scripts/sec_filings.py" --ticker [TICKER] --output "[WS]/.claude/data/sec_[TICKER].json"
  After the script completes, read the output JSON.
  For annual revenue, use only the 10-K value. Do not use 10-Q values for annual revenue.
  Then perform one targeted WebFetch of the most recent filing_url from the output JSON.
  Navigate to the MD&A section to extract unit count and employee count (not XBRL-tagged).

If private: note "private company -- no SEC filings" and set sec_used to false.

--- VERTICAL BENCHMARKS ---

Read: [WS]/.claude/data/vertical_benchmarks.json

Check the last_updated date. If less than 90 days old AND the company vertical is present, use cached data.
If older than 90 days OR vertical is missing, set benchmarks_stale to true but still extract whatever is available.

Extract relevant benchmarks for vertical: [vertical].

--- WEB ESTIMATES (cap at 4 total operations) ---

Use up to 4 web operations total. Prioritize filling gaps not covered by SEC or benchmarks.

Operation 1: Use Playwright to navigate to https://www.linkedin.com/company/[company-slug]/about/ and take a snapshot to extract headcount range. If LinkedIn presents a login wall or returns no data, fall back to WebSearch: "[COMPANY_NAME] number of employees [current year]". This fallback counts as 1 operation.

Use remaining slots (up to 3 more) to fill whichever of these fields are still missing:
- Location / unit count
- Annual revenue
- Menu prices or average ticket (QSR) / hourly rates (manufacturing)

Use WebSearch or WebFetch for each. Stop at 4 total operations.

Write output to: [WS]/.claude/data/ws_public_[company_slug].json

Schema:
{
  "workstream": "public",
  "company": "[COMPANY_NAME]",
  "findings": {
    "revenue": null,
    "revenue_source": "",
    "revenue_year": null,
    "unit_count": null,
    "unit_count_source": "",
    "employee_count": null,
    "employee_count_source": "",
    "menu_price_or_avg_ticket": null,
    "menu_price_source": "",
    "comp_benchmarks": {},
    "other_data_points": {}
  },
  "source_summary": {
    "sec_used": false,
    "sec_ticker": "",
    "sec_output_file": "",
    "benchmarks_used": false,
    "benchmarks_stale": false,
    "web_operations_used": 0,
    "linkedin_used": false
  }
}

Write the file. Do not output a long summary -- just confirm the file path written.
```

### 2.3 Wait for All 4 Agents

Do not proceed until all 4 Task calls have returned. Once all agents report completion, read all 4 output files:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
cat "$WS/.claude/data/ws_attio_gong_[company_slug].json"
cat "$WS/.claude/data/ws_m365_[company_slug].json"
cat "$WS/.claude/data/ws_slack_[company_slug].json"
cat "$WS/.claude/data/ws_public_[company_slug].json"
```

If any file is missing or invalid JSON, note it as a failed workstream and continue with the remaining data.

### 2.4 WS-Merge

Consolidate all data from the 4 output files. Apply source priority (highest to lowest):

1. Gong transcript (1st party)
2. Attio note (1st party)
3. Microsoft 365 Outlook / SharePoint (1st party)
4. Slack (1st party)
5. SEC filing (2nd party)
6. Comp benchmark (2nd party)
7. Online estimate (3rd party)

For each field, use the highest-priority source that has a value. Record source name and tier alongside each value.

**Conflict flagging:** If two sources for the same field diverge by more than 15%, flag it explicitly with both values and sources. Do not silently pick one.

**Gap flagging:** If a required field has no value after all workstreams, flag it as a gap. Required fields: annual revenue, unit/location count, employee count, and at least one menu price or average ticket value.

Present the merged field map:

```
MERGED FIELD MAP -- [COMPANY NAME]

Field                  | Value        | Source              | Tier
-----------------------|--------------|---------------------|------
Annual Revenue         | $XXX.XMM     | Gong (2025-11-14)   | 1st party
Unit Count             | XXX          | SEC 10-K (2024)     | 2nd party
Employee Count         | ~X,XXX       | LinkedIn estimate   | 3rd party
...

CONFLICTS:
- [Field]: Source A says [X], Source B says [Y] -- delta [Z%]. Please confirm which to use.

GAPS:
- [Field]: No data found across all workstreams. Please provide a value or confirm [benchmark default].
```

Wait for the user to resolve any conflicts and gaps before proceeding. If there are none, continue immediately.

### 2.5 GATE: Campaign Selection

Present campaign recommendations and wait for the user to type "confirm". Do not proceed until "confirm" is received.

**Branch A format:**

```
CAMPAIGN RECOMMENDATIONS for [COMPANY NAME]
Based on [N] Gong calls + [list other sources used]

RECOMMENDED (include in model + summary slide):
1. [Campaign Name] -- HIGH priority
   Evidence: "[exact verbatim quote]" (Gong, [YYYY-MM-DD])
   Client interest: Explicit

2. [Campaign Name] -- HIGH priority
   Evidence: "[paraphrase or quote]" ([source], [date])
   Client interest: [Explicit / Implied]

STANDARD (include in model, exclude from summary slide):
3. [Campaign Name] -- [reason for standard classification]

EXCLUDE:
- [Campaign Name] -- [reason for exclusion]

Type "confirm" to proceed with this campaign list, or tell me what to change:
```

**Branch B format:**

```
CAMPAIGN SELECTION for [COMPANY NAME]
No call data -- showing full standard template for [Vertical].

All [N] campaigns included (prospect deck -- illustrative):
1. [Campaign Name]
2. [Campaign Name]
...

Type "confirm" to proceed with all campaigns, or remove any you do not want:
```

If the user requests changes, apply them and re-present. Repeat until "confirm" is received.

### 2.6 Save Research Output and Update State

Write `$WS/.claude/data/research_output_[company_slug].json`:

```json
{
  "company_name": "",
  "industry": "",
  "branch": "",
  "research_date": "",
  "source_summary": {
    "gong_calls_found": 0,
    "gong_calls_transcribed": 0,
    "attio_records": 0,
    "attio_notes": 0,
    "m365_emails": 0,
    "slack_messages": 0,
    "sec_filings": false,
    "comp_benchmarks_used": false,
    "web_operations_used": 0
  },
  "slack_insights": [],
  "attio_insights": {},
  "gong_insights": {},
  "company_basics": {
    "annual_revenue": null,
    "annual_revenue_source": "",
    "annual_revenue_tier": "",
    "unit_count": null,
    "unit_count_source": "",
    "unit_count_tier": "",
    "employee_count": null,
    "employee_count_source": "",
    "employee_count_tier": ""
  },
  "campaign_inputs": {},
  "campaigns_selected": [],
  "comps_benchmarks": {},
  "model_population": {}
}
```

Populate all fields from merged data. Leave `model_population` as an empty object.

Update session state file (`$WS/.claude/data/session_state_YYYY-MM-DD.md`). Write a new file with today's date. Include:
- All fields from Phase 1 state
- Phase 2 marked complete
- Approved campaigns list (verbatim)
- Source breakdown summary
- Key decisions made (conflicts resolved, gaps filled, campaigns excluded)
- Next action: Phase 3: Model

Tell the user: "Phase 2 complete. Moving to Phase 3: Model..."

Then immediately continue to Phase 3 without waiting for user input.

---

## Phase 3: Model

Tell the user: "Phase 3: Model -- running."

### 3.1 Load Research Output

Read:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
cat "$WS/.claude/data/research_output_[company_slug].json"
```

Extract: `company_basics`, `campaigns_selected`, `campaign_inputs`, `comps_benchmarks`, `model_population` (should be empty at this stage), and branch.

Also read the model file path from the current session state file.

### 3.2 Open the Model File

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
```

Tell the user: "Model opened. Do not edit it yet -- I will show you the full plan before writing anything."

### 3.3 Map Row Labels to Row Numbers

Use `excel_editor.py` to scan the Assumptions and Campaigns sheets for row labels. Never hardcode row numbers -- always resolve them from the actual file at runtime:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 "$WS/.claude/agents/excel_editor.py" \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]" \
  --action scan-labels
```

Build a label-to-cell map from the output. This map is required before computing values.

### 3.4 Build Formula Lock List

Use `excel_editor.py` to identify all formula cells in the Campaigns and Sensitivities sheets:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 "$WS/.claude/agents/excel_editor.py" \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]" \
  --action scan-formulas
```

Store the list of formula cell addresses. Do not write to any cell on this list under any circumstances.

### 3.5 Compute All Values and Apply Rounding

Compute all values to write before touching the file. Apply rounding standards:

| Field | Round To |
|-------|----------|
| Revenue | Nearest $500K or $1M |
| Store / facility count | Exact integer |
| Orders / units per day | Nearest 50 or 100 |
| Employees | Nearest 50 or 100 |
| Menu prices / upsell costs | Nearest $0.25 or $0.50 |
| Contribution margins | Nearest 1% or 5% |
| Turnover rate | Nearest 5% |
| Hiring cost | Nearest $100 or $500 |
| EBITDA per hour | Nearest $0.25 or $0.50 |
| Incentive costs | Clean numbers ($0.10, $0.25, $0.50) |
| Reduction / gain % | Nearest 2.5% or 5% |

**Hiring cost cap (QSR only):** Never exceed $3,500.

**ROPS check for each campaign:**
- Formula: ROPS = Savings / Incentive Cost
- Target: 10x <= ROPS <= 30x
- If outside range: adjust incentive cost first; if still out of range, adjust assumptions
- 1st-party sourced assumptions can bypass ROPS checks -- note in the plan

**Accretion ceiling check (run after all campaigns are computed):**
- Target: Total EBITDA accretion <= 15% of Annual EBITDA
- If exceeded: remove the campaign with the lowest ROPS first
- 1st-party assumptions can exceed the ceiling with user approval -- flag and ask

For each cell to write, prepare:
- Sheet name
- Cell address (from label map)
- Value (rounded)
- Source (from research_output)
- Source tier
- Comment text (see format below)

**Comment format for every hard-coded cell:**

```
SOURCE: [tier] ([source name])
[URL or "N/A"]

VALUE: [the value]

ADJUSTMENTS: [what changed and why, or "None - used as researched."]

METHODOLOGY: [how derived]

RATIONALE: [why chosen]

CONFIDENCE: High / Medium / Low

DATE: [Month Year]
```

Comment dimensions: width=420px, height=220px, font size 8.

### 3.6 GATE: Dry-Run Approval

Present the complete plan before writing anything:

```
DRY-RUN PLAN -- [COMPANY NAME]
[N] cells to write across [N] sheets

Sheet: Assumptions
  [Cell]  | [Field Name]                   | [Value]    | Source: [source (tier)] | Comment: included
  ...

Sheet: Campaigns
  [Cell]  | [Campaign Name] [Field]        | [Value]    | Source: [source (tier)] | Comment: included
  ...

ROPS CHECK:
  [Campaign Name]: ROPS = [Nx] -- [pass / adjusted: [what changed]]
  ...

ACCRETION CHECK:
  Total EBITDA accretion: $[X.XXMM] ([X]% of $[X.XXMM] annual EBITDA) -- [within ceiling / EXCEEDS -- flag]

FORMULA CELLS SKIPPED (do not overwrite):
  [List any formula cells identified and skipped]

Type "approve" to write all cells, or tell me what to change:
```

Wait for "approve". If the user requests changes, update the plan and re-present. Repeat until "approve" is received.

### 3.7 Write to Excel

After "approve" is received, write all planned values using `excel_editor.py`:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 "$WS/.claude/agents/excel_editor.py" \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]" \
  --cells "[JSON of cell writes]"
```

For each cell written, include the comment using the format defined in Step 3.5. Comment dimensions: width=420, height=220, font size 8.

Tell the user: "Wrote [N] cells to [model filename]. Verifying..."

### 3.8 Verify Formula Counts

Read back each written cell and confirm the value matches the plan. Report any discrepancies.

Confirm formula cell counts are unchanged:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 "$WS/.claude/agents/excel_editor.py" \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]" \
  --action scan-formulas
```

QSR: Campaigns sheet = 153 formula cells, Sensitivities sheet = 86 formula cells.
Manufacturing: Campaigns sheet = 366 formula cells, Sensitivities sheet = 205 formula cells.

If any count has changed, alert the user immediately and do not proceed until they confirm:

```
WARNING: Formula cell count changed in [Sheet] -- expected [N], found [N].
This may indicate a formula was overwritten. Please check [sheet] before proceeding.
```

### 3.9 Manual Review Checklist

Walk through these 5 checks one at a time. Wait for "done" after each before presenting the next:

```
Manual review -- complete each step in the open model, then type "done":

1. Scroll through the Assumptions sheet. Confirm all yellow cells have values. Any still showing placeholders?

2. Check the Campaigns sheet. Confirm all selected campaigns ([list]) are activated (toggle = ON).

3. Check ROPS column. Confirm all active campaigns show ROPS between 10x and 30x.

4. Check the Summary slide inputs tab (if present). Confirm company name, revenue, and unit count are correct.

5. Save the model (Ctrl+S).
```

If the user reports an issue at any step, address it before marking that step done.

### 3.10 Save State After Phase 3

Update `research_output_[company_slug].json` -- populate `model_population`:

```json
{
  "model_population": {
    "cells_written": 0,
    "sheets_modified": [],
    "rops_results": {},
    "accretion_result": {
      "total_accretion": null,
      "annual_ebitda": null,
      "accretion_pct": null,
      "within_ceiling": true
    },
    "formula_cells_preserved": true,
    "model_file": "[model filename]",
    "population_date": "[YYYY-MM-DD]"
  }
}
```

Write new session state file (`$WS/.claude/data/session_state_YYYY-MM-DD.md`) with Phase 3 marked complete:
- Phase 1, 2, 3: complete
- Phase 4, 5: pending
- ROPS and accretion results
- Next action: Phase 4: Format

Tell the user: "Phase 3 complete. Moving to Phase 4: Format..."

Then immediately continue to Phase 4 without waiting for user input.

---

## Phase 4: Format

Tell the user: "Phase 4: Format -- running."

### 4.1 Check Asset Gatherer Output

Run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Logos" -type f 2>/dev/null
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/Swag" -type f 2>/dev/null
```

If logos are missing, tell the user: "Logo files not found. Asset gatherer may still be running or may have failed. Continuing -- logos can be inserted manually in the brand step." Continue regardless.

### 4.2 Open Source Deck

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx"
```

### 4.4 GATE Manual Step 1: Macabacus Refresh

Tell the user:

```
Manual step 1 of 3 -- Macabacus refresh.

In the open deck ([COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx):
1. Click the Macabacus tab in the PowerPoint ribbon.
2. Click "Refresh Linked Data" (or equivalent Macabacus sync command).
3. Wait for the refresh to complete and all linked values to update.
4. Save the file (Ctrl+S).

Type "done" when complete:
```

Wait for "done" before proceeding.

### 4.5 GATE Manual Step 2: Figma Brand Frames

Tell the user:

```
Manual step 2 of 3 -- Figma brand frames.

Open Figma and export the branded frames for [COMPANY_NAME]:
  1. Open the Jolly Figma template file.
  2. Find the [COMPANY_NAME] brand frames (title background, section headers, etc.).
  3. Export as PNG or copy-paste directly into the appropriate slides in the open deck.
  4. Resize and position each frame to match the template layout.
  5. Save the file (Ctrl+S).

Type "done" when complete, or "skip" if no Figma frames are needed:
```

Wait for "done" or "skip" before proceeding.

### 4.6 Create vF Copy

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
cp "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx" \
   "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck vF.pptx"
```

Then open the vF copy:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck vF.pptx"
```

### 4.7 GATE Manual Step 3: Link-Break on vF

Tell the user:

```
Manual step 3 of 3 -- link-break on vF copy.

In the newly opened vF deck ([COMPANY_NAME] Intro Deck vF.pptx):
1. Click the Macabacus tab.
2. Find the "Break Links" or "Disconnect" command (removes live Macabacus/Excel links so the deck is self-contained).
3. Confirm the break when prompted.
4. Save the file (Ctrl+S).

Type "done" when complete:
```

Wait for "done" before proceeding.

### 4.8 Run deck_format.py

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 "$WS/.claude/scripts/deck_format.py" --company "[COMPANY_NAME]"
```

Capture the output. If the script fails, report the error to the user and ask whether to continue or investigate.

### 4.9 Scan for QA Issues

After deck_format.py completes, scan the vF deck for:
- Unformatted dollar values (not matching `$XXXk` or `$X.XXMM` pattern)
- Unfilled placeholders (text matching `[...]` pattern)
- Cross-slide inconsistencies (company name variations, revenue figure mismatches across slides)

Report findings with slide numbers:

```
DECK SCAN RESULTS -- [COMPANY NAME]

Unformatted dollar values:
  Slide [N]: "[current text]" -- should be "$[formatted]"
  ...

Unfilled placeholders:
  Slide [N]: "[placeholder text]"
  ...

Cross-slide inconsistencies:
  [description]
  ...

[No issues found / [N] issues listed above]
```

If issues are found, tell the user to fix them in the open deck and wait for "fixed" before proceeding. After "fixed", re-scan to confirm.

### 4.10 Save State After Phase 4

Write new session state file (`$WS/.claude/data/session_state_YYYY-MM-DD.md`) with Phase 4 marked complete:
- Phase 1, 2, 3, 4: complete
- Phase 5: pending
- vF deck filename
- Next action: Phase 5: QA

Tell the user: "Phase 4 complete. Moving to Phase 5: QA..."

Then immediately continue to Phase 5 without waiting for user input.

---

## Phase 5: QA

Tell the user: "Phase 5: QA -- running."

### 5.1 Run the QA Script

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 "$WS/.claude/scripts/qa_check.py" --company "[COMPANY_NAME]"
```

Read the script output. Report all failures -- do not silently skip any.

### 5.2 Model QA Checks

Open the model:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
```

Run the following checks using `excel_editor.py` where possible, or instruct the user to check manually:

**Check M1 -- Formula cell integrity:**

Confirm formula cell counts match the template. QSR: Campaigns = 153, Sensitivities = 86. Manufacturing: Campaigns = 366, Sensitivities = 205.

If counts do not match:
```
FAIL M1: Formula cell count mismatch in [Sheet].
Expected [N], found [N]. A formula may have been overwritten.
```

**Check M2 -- No empty required assumption cells:**

Scan Assumptions sheet for blank or placeholder hard-coded input cells. Report any found.

**Check M3 -- ROPS range:**

For every active campaign, verify ROPS is between 10x and 30x inclusive. 1st-party sourced campaigns: flag if outside range but do not fail. Non-1st-party: FAIL if outside range.

**Check M4 -- Accretion ceiling:**

Verify Total EBITDA accretion <= 15% of Annual EBITDA. 1st-party sourced: flag and allow with user confirmation. Non-1st-party: FAIL if exceeded.

**Check M5 -- Hiring cost cap (QSR only):**

If vertical is QSR, verify no hiring cost cell exceeds $3,500.

**Check M6 -- Comment coverage:**

Spot-check 10 hard-coded cells across Assumptions and Campaigns sheets. Verify each has a comment with all required fields: SOURCE, VALUE, ADJUSTMENTS, METHODOLOGY, RATIONALE, CONFIDENCE, DATE.

### 5.3 Deck QA Checks

Open the vF deck:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck vF.pptx"
```

Walk through each deck check one at a time. Wait for "done" or the user's report after each:

**Check D1 -- No template tokens remaining:**
```
Check D1: In the open deck, press Ctrl+F and search for "[".
Report any matches found (with slide numbers), or type "done" if none:
```

**Check D2 -- Dollar formatting:**
```
Check D2: Scroll through all slides with dollar values.
Confirm: under $1M shows as $XXXk (lowercase k), $1M+ shows as $X.XXMM (uppercase MM).
Report any incorrectly formatted values, or type "done":
```

**Check D3 -- Banner values match model:**
```
Check D3: Find the large dollar callout (banner) shapes.
Confirm each banner value matches what the model shows for that campaign.
Report any mismatches, or type "done":
```

**Check D4 -- Campaign list matches approved list:**
```
Check D4: Check the Campaign Summary slide and individual campaign slides.
Approved campaigns: [list from session state]
Confirm all approved campaigns appear and no excluded campaigns appear.
Type "done":
```

**Check D5 -- Logo and brand assets:**
```
Check D5: Confirm the company logo appears on the title slide.
Confirm no placeholder logo images remain.
Type "done":
```

**Check D6 -- ROPS not visible to client (Branch B only):**

Skip if branch is A.

```
Check D6 (Branch B only): Confirm ROPS values are not shown on any visible slide.
ROPS is internal only and must not appear in the client-facing deck.
Type "done":
```

**Check D7 -- PDF matches deck:**

First, export the PDF:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 "$WS/.claude/scripts/deck_format.py" --company "[COMPANY_NAME]" --step export-pdf
```

If the script fails, tell the user: "Automated PDF export failed. Please export manually: File > Export > Create PDF/XPS. Save to: $WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/[COMPANY_NAME] Intro Deck vF.pdf"

Then open the PDF:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/[COMPANY_NAME] Intro Deck vF.pdf"
```

```
Check D7: Compare the open PDF to the deck.
Confirm: same number of slides, all values visible, no blank slides.
Type "done":
```

### 5.4 Summarize QA Results

Present the full summary:

```
QA SUMMARY -- [COMPANY NAME]
[YYYY-MM-DD]

MODEL CHECKS:
  M1 Formula integrity:    [PASS / FAIL]
  M2 No empty cells:       [PASS / FAIL / [N] cells flagged]
  M3 ROPS range:           [PASS / FAIL / [N] flagged]
  M4 Accretion ceiling:    [PASS / FAIL / [X]%]
  M5 Hiring cost cap:      [PASS / FAIL / N/A]
  M6 Comment coverage:     [PASS / FAIL / [N] missing]

DECK CHECKS:
  D1 No template tokens:   [PASS / FAIL]
  D2 Dollar formatting:    [PASS / FAIL]
  D3 Banner values:        [PASS / FAIL]
  D4 Campaign list:        [PASS / FAIL]
  D5 Logo/brand assets:    [PASS / FAIL]
  D6 ROPS hidden (B only): [PASS / FAIL / N/A]
  D7 PDF matches deck:     [PASS / FAIL]

Overall: [PASS -- ready for delivery / FAIL -- [N] issues require attention]
```

### 5.5 GATE: Resolve Any Failures

If any check is FAIL:

- List all failures clearly
- For each failure, tell the user exactly what to change and wait for them to make the change
- After each fix, re-run the specific check to confirm it now passes
- Do not proceed to final file opening until the user types "fixed" and all re-checks pass

If all checks pass (or user has confirmed all fixes), continue.

### 5.6 Delete Lock Files

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]" -name "~$*" -delete 2>/dev/null
echo "Lock file cleanup complete."
```

### 5.7 Open Final Files

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[COMPANY_NAME] Intro Deck vF.pptx"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/[COMPANY_NAME] Intro Deck vF.pdf"
```

### 5.8 Save Final State

Write new session state file (`$WS/.claude/data/session_state_YYYY-MM-DD.md`) with all phases complete:
- All phases 0-5: complete
- QA results summary (pass/fail per check)
- Delivery-ready file paths
- Next action: Deliver to client

---

## Final Summary

After all phases are complete, tell the user:

```
[COMPANY_NAME] deck complete.

Campaigns: [list each with ROPS, e.g. "Employee Rewards -- 14x ROPS"]
Accretion: [X]% of EBITDA ($[X.XXMM] / $[X.XXMM] annual EBITDA)

Sources:
  Gong:             [N] calls ([N] transcribed)
  Attio:            [N] records, [N] notes
  Microsoft 365:    [N] emails (or: skipped)
  Slack:            [N] messages
  SEC filings:      [used / not applicable]
  Comp benchmarks:  [used / stale]
  Web operations:   [N of 4 used]

Files:
  PPT:   [full path to vF.pptx]
  Model: [full path to model .xlsx]
  PDF:   [full path to vF.pdf]

QA: [PASS / PASS with notes]
All phases complete. The engagement for [COMPANY_NAME] is ready for delivery.
```

Do not add anything beyond this summary.
