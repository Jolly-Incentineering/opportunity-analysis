---
name: deck-research
description: Run research workstreams via 4 parallel agents, merge results, and select campaigns for an in-progress intro deck.
---

You are executing the `deck-research` phase of the Jolly intro deck workflow. Follow every step exactly as written. Do not skip steps. Do not proceed past a gate without explicit user confirmation.

Set workspace root and client root:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
```

If `workspace_config.json` does not exist, tell the user: "Workspace is not configured. Run /deck-setup first." Then stop.

---

## Step 1: Load Session State

Scan for the most recent session state file:

```bash
WS="${JOLLY_WORKSPACE:-.}"
ls "$WS/.claude/data/session_state_"*.md 2>/dev/null | sort | tail -1
```

Read the most recent file. Extract:
- `company_name` -- the company being worked on
- `client_root` -- from the session state (use this to override CLIENT_ROOT if present)
- `branch` -- "A" (existing client with call data) or "B" (prospect, no call data)
- `vertical` -- industry vertical (QSR, manufacturing, etc.)
- `phase_1_complete` -- whether Phase 1 (deck-start) has been marked complete

If Phase 1 is not marked complete, tell the user:

```
Phase 1 is not complete. Run /deck-start [Company] first, then return to /deck-research.
```

Then stop. Do not continue.

If Phase 1 is complete, tell the user:

```
Resuming from [session date] -- company: [Company Name], branch: [A or B], vertical: [Vertical].
Starting Phase 2: Research workstreams.
```

Derive `company_slug` from company name: lowercase, spaces replaced with underscores, remove special characters.

---

## Step 2: Check and Ensure Gong Recipe Exists (Branch A only)

Skip this step entirely if branch is B.

Call `RUBE_FIND_RECIPE` with `name: "gong_company_search"`.

If the recipe is NOT found, create it immediately using `RUBE_CREATE_UPDATE_RECIPE` with the following definition:

- Recipe name: `gong_company_search`
- Description: "Search Gong calls by date range and retrieve transcripts for matched calls."
- Steps:
  - Pass 1: Call `GONG_RETRIEVE_FILTERED_CALL_DETAILS` with parameters:
    - `filter__fromDateTime`: `"{{from_date}}T00:00:00Z"`
    - `filter__toDateTime`: `"{{to_date}}T23:59:59Z"`
    - `contentSelector__exposedFields__content__brief`: `true`
    - `contentSelector__exposedFields__parties`: `true`
    - `contentSelector__context`: `"Extended"`
    - `contentSelector__contextTiming`: `["Now", "TimeOfCall"]`
  - Pass 2: Call `GONG_GET_CALL_TRANSCRIPT` with parameters:
    - `filter.callIds`: `["{{matched_call_ids}}"]`

Confirm the recipe exists before proceeding.

---

## Step 3: Dispatch 4 Research Agents in Parallel

Dispatch all 4 agents simultaneously using the Task tool. Do not wait for any one agent to finish before dispatching the others. All 4 Task calls must be issued in a single message.

Each agent is fully self-contained. Each reads what it needs, does its work, and writes a JSON output file. The main skill does not do any inline research -- only dispatching and merging.

The output path format for all agents:
- `$WS/$CLIENT_ROOT/[COMPANY_NAME]/reports/research/ws_[workstream]_[company_slug].json`

---

### Agent 1: ws-attio-gong

**Output file:** `$WS/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research/ws_attio_gong_[company_slug].json`

Pass this prompt to the agent (substitute actual values):

```
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
- Write the transcript to: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/reports/transcripts/[YYYY-MM-DD]_[Call Title].md

After all transcripts are saved, write a consolidated insights file to:
[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research/gong_insights_[today YYYY-MM-DD].json

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

Create output directories before writing (run immediately, before any research):
  mkdir -p [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research
  mkdir -p [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/reports/transcripts

Save findings immediately after each source completes -- do not wait until all sources are done.

Write your output to: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research/ws_attio_gong_[company_slug].json

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

### Agent 2: ws-m365

**Output file:** `$WS/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research/ws_m365_[company_slug].json`

Pass this prompt to the agent (substitute actual values):

```
You are the ws-m365 research agent for the Jolly deck workflow.

Company: [COMPANY_NAME]
Company slug: [company_slug]
Branch: [A or B]
Workspace root (WS): [WS]
Client root (CLIENT_ROOT): [CLIENT_ROOT]
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

Create output directory before writing: mkdir -p [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research
Save findings immediately after each source completes -- do not wait until all sources are done.
Write output to: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research/ws_m365_[company_slug].json

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

### Agent 3: ws-slack

**Output file:** `$WS/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research/ws_slack_[company_slug].json`

Pass this prompt to the agent (substitute actual values):

```
You are the ws-slack research agent for the Jolly deck workflow.

Company: [COMPANY_NAME]
Company slug: [company_slug]
Branch: [A or B]
Workspace root (WS): [WS]
Client root (CLIENT_ROOT): [CLIENT_ROOT]

Your job: run Slack research and write a clean JSON output.

If Branch B, skip all Slack calls and write an empty findings output.

Fire both keyword searches in parallel:
1. mcp__claude_ai_Slack__slack_search_public_and_private: query="[COMPANY_NAME] revenue"
2. mcp__claude_ai_Slack__slack_search_public_and_private: query="[COMPANY_NAME] locations headcount turnover"

If either search returns zero useful results (no messages with data points), then and only then read the channel directly:
- mcp__claude_ai_Slack__slack_read_channel: limit=50, for the most relevant channel found

Do not read the channel if keyword searches return useful results.

Extract from results: revenue figures, headcount, location counts, pricing signals, pain points, campaign mentions.

Create output directory before writing: mkdir -p [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research
Save findings immediately after each source completes -- do not wait until all sources are done.
Write output to: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research/ws_slack_[company_slug].json

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

### Agent 4: ws-public

**Output file:** `$WS/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research/ws_public_[company_slug].json`

Pass this prompt to the agent (substitute actual values):

```
You are the ws-public research agent for the Jolly deck workflow.

Company: [COMPANY_NAME]
Company slug: [company_slug]
Vertical: [vertical]
Workspace root (WS): [WS]
Client root (CLIENT_ROOT): [CLIENT_ROOT]
Today's date: [YYYY-MM-DD]

Your job: run SEC filings, vertical benchmarks, and web research. Write a clean JSON output.

--- SEC FILINGS ---

Determine whether [COMPANY_NAME] is publicly traded (use your knowledge or do one WebSearch).

If public:
  Step 1 -- Run the filings script:
    python "[WS]/.claude/scripts/sec_filings.py" --ticker [TICKER] --output "[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research/sec_[TICKER].json"
  After the script completes, read the output JSON.
  For annual revenue, use only the 10-K value. Do not use 10-Q values for annual revenue.

  Step 2 -- Download the last 4 filing documents (10-K and 10-Q):
    Create the filings directory: mkdir -p "[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research/filings"

    Using the EDGAR REST API (no auth required):
    a) Resolve CIK: GET https://efts.sec.gov/LATEST/search-index?q=%22[TICKER]%22&dateRange=custom&startdt=2020-01-01&enddt=[TODAY]&forms=10-K,10-Q
       Or use: GET https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=[COMPANY_NAME]&type=10-K&dateb=&owner=include&count=4&search_text=&output=atom
       Or resolve via: GET https://data.sec.gov/submissions/CIK{zero-padded-10-digit-CIK}.json

    b) From the submissions JSON, extract the last 4 filings of type 10-K or 10-Q (most recent first, regardless of mix).

    c) For each of the 4 filings, fetch the filing index page:
       GET https://www.sec.gov/Archives/edgar/data/{CIK}/{accession-number-no-dashes}/{accession-number}-index.htm
       Find the primary document (htm or htm.gz). Prefer the full 10-K/10-Q document over exhibits.

    d) Download each primary document and save to:
       "[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research/filings/[YYYY-MM-DD]_[FORM_TYPE]_[TICKER].[ext]"
       Example: 2024-09-30_10-K_MCD.htm

    e) After downloading, WebFetch the most recent 10-K's MD&A section to extract unit count and employee count (not XBRL-tagged). This counts as one of your web operations.

  Record all downloaded file paths in sec_filing_files in the output schema.

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

Create output directory before writing: mkdir -p [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research
Save findings immediately after each source completes -- do not wait until all sources are done.
Write output to: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/reports/research/ws_public_[company_slug].json

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
    "sec_filing_files": [],
    "benchmarks_used": false,
    "benchmarks_stale": false,
    "web_operations_used": 0,
    "linkedin_used": false
  }
}

Write the file. Do not output a long summary -- just confirm the file path written.
```

---

## Step 4: Wait for All 4 Agents to Complete

Do not proceed until all 4 Task calls have returned. Once all agents have completed, read all 4 output files:

```bash
WS="${JOLLY_WORKSPACE:-.}"
RESEARCH="$WS/$CLIENT_ROOT/[COMPANY_NAME]/reports/research"
cat "$RESEARCH/ws_attio_gong_[company_slug].json"
cat "$RESEARCH/ws_m365_[company_slug].json"
cat "$RESEARCH/ws_slack_[company_slug].json"
cat "$RESEARCH/ws_public_[company_slug].json"
```

If any file is missing or invalid JSON, note it as a failed workstream and continue with the remaining data.

---

## Step 5: WS-Merge

Consolidate all data from the 4 agent output files into a single field map. Apply the following source priority order (highest to lowest):

1. Gong transcript (1st party)
2. Attio note (1st party)
3. Microsoft 365 Outlook / SharePoint (1st party)
4. Slack (1st party)
5. SEC filing (2nd party)
6. Comp benchmark (2nd party)
7. Online estimate (3rd party)

For each field, use the highest-priority source that has a value. Record the source name and tier alongside each value.

**Conflict flagging:** If two sources for the same field diverge by more than 15%, flag it explicitly with both values and sources. Do not silently pick one.

**Gap flagging:** If a required field has no value from any source after all workstreams, flag it as a gap. Required fields are: annual revenue, unit / location count, employee count, and at least one menu price or average ticket value.

Present the merged field map to the user before the campaign gate. Format:

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

Wait for the user to resolve any conflicts and gaps before proceeding to the campaign gate. If there are none, proceed immediately.

---

## Step 6: Campaign Selection Gate

Present campaign recommendations and wait for explicit user confirmation. Do not proceed to any Excel or model work until the user types "confirm".

**Branch A format:**

```
CAMPAIGN RECOMMENDATIONS for [COMPANY NAME]
Based on [N] Gong calls + [list other sources used]

RECOMMENDED (include in model + summary slide):
1. [Campaign Name] -- HIGH priority
   Evidence: "[exact verbatim quote]" (Gong, [YYYY-MM-DD])
   Client interest: Explicit

2. [Campaign Name] -- HIGH priority
   Evidence: "[exact verbatim quote or paraphrase]" ([source], [date])
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

**Revision loop:** If the user requests changes, apply them and re-present the full campaign list. Repeat until the user types "confirm". Only proceed after "confirm" is received.

---

## Step 7: Save Research Outputs

After user confirmation, write the research JSON.

Create the output directory if it does not exist:

```bash
WS="${JOLLY_WORKSPACE:-.}"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/reports/research"
# Write to: "$WS/$CLIENT_ROOT/[COMPANY_NAME]/reports/research/research_output_[company_slug].json"
```

The JSON must conform to this schema:

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

Populate all fields from the merged data. Leave `model_population` as an empty object.

Then update the session state file. Write a new file at `$WS/.claude/data/session_state_[YYYY-MM-DD].md` (today's date). Include:
- Company name
- Client root
- Current phase: Phase 2 complete
- Task status table with Phase 1 and Phase 2 marked complete, Phase 3 pending
- Approved campaign list (verbatim from user confirmation)
- Next action: "Run /deck-model"
- Key decisions made during this session (source conflicts resolved, gaps filled, campaigns excluded)

---

## Step 8: Hand Off

Tell the user:

```
Research complete for [COMPANY NAME].

Source breakdown:
- Gong: [N] calls found, [N] transcribed
- Attio: [N] records, [N] notes
- Microsoft 365: [N] emails read (or: skipped)
- Slack: [N] messages
- SEC filings: [used / not applicable]
- Comp benchmarks: [used / stale -- flag for refresh]
- Web operations: [N of 4 used]

Approved campaigns ([N] total):
1. [Campaign Name]
2. [Campaign Name]
...

Research file saved to: [CLIENT_ROOT]/[COMPANY_NAME]/reports/research/research_output_[company_slug].json
Session state saved. Next: run /deck-model to populate the Excel model.
```
