---
name: deck-research
description: Run research workstreams via 3 parallel agents, merge results, and select campaigns for an in-progress intro deck.
---

HARD RULES — NEVER VIOLATE:
1. Do NOT generate or invent campaign names. Read them from the template config JSON.
2. Do NOT make tool calls not listed in these instructions.
3. Do NOT write to formula cells under any circumstances.
4. Do NOT skip gates — wait for user confirmation at every gate.
5. Do NOT open files you are about to write to programmatically. Keep them closed during writes.
6. Do NOT add features, steps, or checks not specified here.
7. Do NOT proceed past a failed step — stop and report the failure.
8. If a tool call fails, report the error. Do NOT retry more than once.
9. Keep all client-specific data in the client folder under 4. Reports/. Never write client data to .claude/data/.
10. Use HAIKU for research agents unless explicitly told otherwise.

---

You are executing the `deck-research` phase of the Jolly intro deck workflow. Follow every step exactly as written. Do not skip steps. Do not proceed past a gate without explicit user confirmation.

Set workspace root and client root:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
```

If `workspace_config.json` does not exist, tell the user: "Workspace is not configured. Run /deck-setup first." Then stop.

---

## Step 1: Load Session State

Scan for the most recent session state file:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
ls "$WS/.claude/data/session_state_"*.md 2>/dev/null | sort | tail -1
```

Read the most recent file. Extract:
- `company_name` -- the company being worked on
- `client_root` -- from the session state (use this to override CLIENT_ROOT if present)
- `context` -- "pre_call" or "post_call"
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

## Step 2: Check Research Path Based on Context

**Pre-call context:** Skip to Step 3b (Public + Slack only). Do not run the Attio/Gong research agent at all.

**Post-call context:** Continue to Step 2a (below) to prepare Gong integration for Branch A.

---

## Step 2a: Prepare Gong Integration (Branch A + Post-Call Only)

Skip this step entirely if branch is B OR context is pre_call.

Read `gong_integration` from workspace config:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 -c "import json; c=json.load(open('$WS/.claude/data/workspace_config.json')); print(c.get('gong_integration','none'))"
```

**If `gong_integration = "rube"`:**

Call `RUBE_FIND_RECIPE` with `name: "gong_company_search"`.

If the recipe is NOT found, create it using `RUBE_CREATE_UPDATE_RECIPE`:

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

Confirm the recipe exists before proceeding to Step 3.

**If `gong_integration = "zapier"`:**

Read `gong_webhook_url` from workspace config. Tell the user:

```
Gong: triggering Zapier webhook for [COMPANY_NAME]...
```

Trigger the webhook:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
WEBHOOK_URL=$(python3 -c "import json; c=json.load(open('$WS/.claude/data/workspace_config.json')); print(c.get('gong_webhook_url',''))")
curl -s -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "{\"company\": \"[COMPANY_NAME]\", \"from_date\": \"[180 days ago YYYY-MM-DD]\", \"to_date\": \"[today YYYY-MM-DD]\"}"
```

Then tell the user:

```
Gong webhook triggered. Waiting up to 3 minutes for transcript file to appear...
```

Poll every 15 seconds (up to 12 attempts) for a new `gong_insights_*.json` file in `$WS/$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts/`. If found, continue. If not found after 3 minutes, note "Gong: no transcript file received — continuing without call data" and proceed to Step 3.

**If `gong_integration = "manual"` or `"none"`:**

Check whether a recent `gong_insights_*.json` file already exists:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; c=json.load(open('$WS/.claude/data/workspace_config.json')); print(c['client_root'])" 2>/dev/null || echo "Clients")
find "$WS/$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts" -name "gong_insights_*.json" 2>/dev/null
```

If a file exists and is ≤30 days old, note "Gong: using existing transcript file." Proceed to Step 3.
If no file exists, note "Gong: no transcript file found — continuing without call data." Proceed to Step 3.

---

## Step 3: Dispatch Research Agents Based on Context

### Step 3a: Pre-Call Path (2 Agents)

Dispatch only the **Slack** and **Public** agents simultaneously using the Task tool with `model: "haiku"`. Do not dispatch the Attio/Gong agent.

Each agent is fully self-contained. Each reads what it needs, does its work, and writes a JSON output file.

**Model selection:** All research agents use **Haiku** by default for speed. If an agent encounters a complex ask (e.g., intricate data structure, ambiguous campaign logic), it should explicitly tell you it needs more processing power and recommend a manual Sonnet review instead of attempting the task with Haiku.

Agents write to their own named subfolders under `4. Reports/`:
- Agent 2 (slack)      → `4. Reports/3. Slack/`
- Agent 3 (public)     → `4. Reports/2. Public Filings/`
- Merged output        → `4. Reports/` (directly in Reports, not in a subfolder)

### Step 3b: Post-Call Path (3 Agents)

Dispatch all 3 agents simultaneously using the Task tool with `model: "haiku"`. Do not wait for any one agent to finish before dispatching the others. All 3 Task calls must be issued in a single message.

Each agent is fully self-contained. Each reads what it needs, does its work, and writes a JSON output file.

**Model selection:** All research agents use **Haiku** by default for speed. If an agent encounters a complex ask (e.g., intricate data structure, ambiguous campaign logic), it should explicitly tell you it needs more processing power and recommend a manual Sonnet review instead of attempting the task with Haiku.

Each agent writes to its own named subfolder under `4. Reports/`:
- Agent 1 (attio-gong) → `4. Reports/1. Call Summaries/`
- Agent 2 (slack)      → `4. Reports/3. Slack/`
- Agent 3 (public)     → `4. Reports/2. Public Filings/`
- Merged output        → `4. Reports/` (directly in Reports, not in a subfolder)

---

### Agent 1: ws-attio-gong

**Output file:** `$WS/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/1. Call Summaries/ws_attio_gong_[company_slug].json`

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

**Preferred method: Attio REST API (faster, more reliable).** Check for ATTIO_API_KEY in the environment or .env file. If the key is available, use the REST API. If not, fall back to the MCP tools.

**Option A — Attio REST API (preferred):**

Load the API key:
```bash
ATTIO_API_KEY=$(python3 -c "
import os
key = os.environ.get('ATTIO_API_KEY', '')
if not key:
    try:
        for line in open('.env'):
            if line.startswith('ATTIO_API_KEY='):
                key = line.split('=',1)[1].strip()
                break
    except FileNotFoundError:
        pass
print(key)
")
```

If ATTIO_API_KEY is non-empty, fire these 4 API calls in parallel using curl with header `Authorization: Bearer $ATTIO_API_KEY`:

1. POST https://api.attio.com/v2/objects/companies/records/query — body: `{"filter":{"name":{"$contains":"[COMPANY_NAME]"}}}` — to search company records
2. POST https://api.attio.com/v2/notes/query — body: `{"filter":{"parent_object":"companies","parent_record_id":"[record_id from call 1]"}}` — to get notes (run after call 1 returns)
3. POST https://api.attio.com/v2/objects/companies/records/query with full field expansion — to get record details by ID (run after call 1 returns)
4. POST https://api.attio.com/v2/emails/query — body: `{"filter":{"parent_object":"companies","parent_record_id":"[record_id from call 1]"}}` — to search emails (run after call 1 returns)

**Option B — MCP fallback (if no API key):**

Fire all 4 Attio MCP calls in parallel:
1. mcp__claude_ai_Attio__search-records -- query: [COMPANY_NAME]
2. mcp__claude_ai_Attio__get-records-by-ids -- for any record IDs returned in call 1
3. mcp__claude_ai_Attio__semantic-search-notes -- query: [COMPANY_NAME]
4. mcp__claude_ai_Attio__search-emails-by-metadata -- query: [COMPANY_NAME]

Extract from results: revenue mentions, headcount mentions, location counts, pain points, pricing signals, any campaigns mentioned.

--- GONG (Branch A only -- if Branch B, skip and set all Gong fields to empty) ---

First, read gong_integration from workspace config:
  python3 -c "import json; c=json.load(open('[WS]/.claude/data/workspace_config.json')); print(c.get('gong_integration','none'))"

IF gong_integration = "rube":
  Run RUBE recipe "gong_company_search" (it already exists -- do not recreate it):
  - from_date: [180 days ago YYYY-MM-DD]
  - to_date: [today YYYY-MM-DD]
  From Pass 1 results, identify matched call IDs. Take the 6 most recent. Fire GONG_GET_CALL_TRANSCRIPT for each matched call ID in parallel (up to 6 simultaneous calls).
  For each transcript retrieved:
  - Extract: call date, call title, participants, key topics, verbatim quotes relevant to revenue, headcount, locations, turnover, pricing, and pain points.
  - Write the transcript to: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/5. Call Transcripts/[YYYY-MM-DD]_[Call Title].md
  After all transcripts are saved, write a consolidated insights file.

IF gong_integration = "zapier":
  The main skill already triggered the Zapier webhook and waited for the file.
  Check for an existing gong_insights_*.json in [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/5. Call Transcripts/.
  If found, read it and use the data in your output. Set gong_used = true.
  If not found, set gong_used = false and continue.

IF gong_integration = "manual" or "none":
  Check for an existing gong_insights_*.json in [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/5. Call Transcripts/.
  If found and ≤30 days old, read it and use the data. Set gong_used = true.
  If not found, set gong_used = false and continue with empty Gong data.

After all transcripts are saved (or if no Gong data), write a consolidated insights file to:
[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/1. Call Summaries/gong_insights_[today YYYY-MM-DD].json

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

Create output directory before writing (run immediately, before any research):
  mkdir -p "[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/1. Call Summaries"

Save findings immediately after each source completes -- do not wait until all sources are done.

Write your output to: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/1. Call Summaries/ws_attio_gong_[company_slug].json

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

### Agent 2: ws-slack

**Output file:** `$WS/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/3. Slack/ws_slack_[company_slug].json`


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

Create output directory before writing: mkdir -p "[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/3. Slack"
Save findings immediately after each source completes -- do not wait until all sources are done.
Write output to: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/3. Slack/ws_slack_[company_slug].json

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

### Agent 3: ws-public

**Output file:** `$WS/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/2. Public Filings/ws_public_[company_slug].json`

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
    python "[WS]/.claude/scripts/sec_filings.py" --ticker [TICKER] --output "[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/2. Public Filings/sec_[TICKER].json"
  After the script completes, read the output JSON.
  For annual revenue, use only the 10-K value. Do not use 10-Q values for annual revenue.

  Step 2 -- Download the last 4 filing documents (10-K and 10-Q):
    Create the filings directory: mkdir -p "[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/2. Public Filings/Filings"

    Using the EDGAR REST API (no auth required):
    a) Resolve CIK: GET https://efts.sec.gov/LATEST/search-index?q=%22[TICKER]%22&dateRange=custom&startdt=2020-01-01&enddt=[TODAY]&forms=10-K,10-Q
       Or use: GET https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=[COMPANY_NAME]&type=10-K&dateb=&owner=include&count=4&search_text=&output=atom
       Or resolve via: GET https://data.sec.gov/submissions/CIK{zero-padded-10-digit-CIK}.json

    b) From the submissions JSON, extract the last 4 filings of type 10-K or 10-Q (most recent first, regardless of mix).

    c) For each of the 4 filings, fetch the filing index page:
       GET https://www.sec.gov/Archives/edgar/data/{CIK}/{accession-number-no-dashes}/{accession-number}-index.htm
       Find the primary document (htm or htm.gz). Prefer the full 10-K/10-Q document over exhibits.

    d) Download each primary document and save to:
       "[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/2. Public Filings/Filings/[YYYY-MM-DD]_[FORM_TYPE]_[TICKER].[ext]"
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

Create output directory before writing: mkdir -p "[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/2. Public Filings"
Save findings immediately after each source completes -- do not wait until all sources are done.
Write output to: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/2. Public Filings/ws_public_[company_slug].json

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

## Step 4: Wait for All 3 Agents to Complete

Do not proceed until all 3 Task calls have returned. Once all agents have completed, read all 3 output files:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/1. Call Summaries/ws_attio_gong_[company_slug].json"
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/3. Slack/ws_slack_[company_slug].json"
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/2. Public Filings/ws_public_[company_slug].json"
```

If any file is missing or invalid JSON, note it as a failed workstream and continue with the remaining data.

---

## Step 5: WS-Merge

Consolidate all data from the 4 agent output files into a single field map. Apply the following source priority order (highest to lowest):

1. Gong transcript (1st party)
2. Attio note (1st party)
3. Slack (1st party)
4. SEC filing (2nd party)
5. Comp benchmark (2nd party)
6. Online estimate (3rd party)

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

Read campaign names from the template config saved by deck-start:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/template_config.json"
```

Extract the campaign names from the `campaigns` dict in the config. Do NOT generate or invent campaign names — use ONLY the names from the template config.

Present campaign recommendations and wait for explicit user confirmation. Do not proceed to any Excel or model work until the user types "confirm".

**Branch A format:**

```
CAMPAIGN RECOMMENDATIONS for [COMPANY NAME]
Based on [N] Gong calls + [list other sources used]
Template campaigns (from config): [list all campaign names from template_config.json]

RECOMMENDED (include in model + summary slide):
1. [Campaign Name from config] -- HIGH priority
   Evidence: "[exact verbatim quote]" (Gong, [YYYY-MM-DD])
   Client interest: Explicit

2. [Campaign Name from config] -- HIGH priority
   Evidence: "[exact verbatim quote or paraphrase]" ([source], [date])
   Client interest: [Explicit / Implied]

STANDARD (include in model, exclude from summary slide):
3. [Campaign Name from config] -- [reason for standard classification]

EXCLUDE:
- [Campaign Name from config] -- [reason for exclusion]

Type "confirm" to proceed with this campaign list, or tell me what to change:
```

**Branch B format:**

```
CAMPAIGN SELECTION for [COMPANY NAME]
No call data -- showing full standard template for [Vertical].
Template campaigns (from config): [list all campaign names]

All [N] campaigns included (prospect deck -- illustrative):
1. [Campaign Name from config]
2. [Campaign Name from config]
...

Type "confirm" to proceed with all campaigns, or remove any you do not want:
```

**Revision loop:** If the user requests changes, apply them and re-present the full campaign list. Repeat until the user types "confirm". Only proceed after "confirm" is received.

---

## Step 7: Save Research Outputs

After user confirmation, write the research JSON.

Write the merged output directly to the Reports folder (no subfolder):

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
# Write to: "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research_output_[company_slug].json"
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
- Slack: [N] messages
- SEC filings: [used / not applicable]
- Comp benchmarks: [used / stale -- flag for refresh]
- Web operations: [N of 4 used]

Approved campaigns ([N] total):
1. [Campaign Name]
2. [Campaign Name]
...

Research file saved to: [CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/research_output_[company_slug].json
Session state saved. Next: run /deck-model to populate the Excel model.
```
