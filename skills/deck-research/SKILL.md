---
name: deck-research
description: Run research workstreams via 3 parallel agents, merge results, and select campaigns for an in-progress intro deck.
disable-model-invocation: true
---

Read and follow all rules in skills/shared-preamble.md before proceeding.

---

You are executing the `deck-research` phase of the Jolly intro deck workflow. Follow every step exactly as written. Do not skip steps. Only stop for gates marked with AskUserQuestion.

Set workspace root and client root:

Set workspace root using the bash preamble from shared-preamble.md.

If `workspace_config.json` does not exist, tell the user: "Workspace is not configured. Run /deck-setup first." Then stop.

---

## Step 1: Load Session State

Read and extract fields from the session state JSON:

Load session state using the standard loader from shared-preamble.md.

Extract from the output:
- `company_name` -- the company being worked on
- `client_root` -- from the session state (use this to override CLIENT_ROOT if present)
- `context` -- "pre_call" or "post_call"
- `branch` -- "A" (existing client with call data) or "B" (prospect, no call data)
- `vertical` -- industry vertical (QSR, manufacturing, etc.)
- `phase_1_status` -- whether Phase 1 (deck-start) has been marked complete
- `template_paths` -- paths to master/vF templates
- `campaigns_selected` -- any previously selected campaigns
- `session_date` -- from `data['session_date']` in the JSON

If `phase_1_status != 'complete'`, tell the user:

```
Phase 1 is not complete. Run /deck-start [Company] first, then return to /deck-research.
```

Then stop. Do not continue.

If `phase_1_status` is `'complete'`, tell the user:

```
Resuming from [session_date] -- company: [Company Name], branch: [A or B], vertical: [Vertical].
Starting Phase 2: Research workstreams.
```

Derive `company_slug` from company name: lowercase, spaces replaced with underscores, remove special characters.

Tell the user:

```
Gates this phase:
  □ Data conflicts / gaps resolved
  □ Campaign selection confirmed
```

After each gate is confirmed, echo "[Gate name] ✓" in your reply before proceeding.

---

## Step 2: Check Research Path Based on Context

**Pre-call context:** Skip to Step 3a (Public + Slack only). Do not dispatch the Attio agent.

**Post-call context:** Continue to Step 3b (all 3 agents including Attio with call recordings).

---

## Step 3: Dispatch Research Agents Based on Context

### Step 3a: Pre-Call Path (2 Agents)

Dispatch only the **Slack** and **Public** agents simultaneously using the Task tool with `model: "haiku"`. Do not dispatch the Attio agent.

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
- Agent 1 (attio) → `4. Reports/1. Call Summaries/`
- Agent 2 (slack) → `4. Reports/3. Slack/`
- Agent 3 (public) → `4. Reports/2. Public Filings/`
- Merged output   → `4. Reports/` (directly in Reports, not in a subfolder)

---

### Agent 1: ws-attio

**Output file:** `$WS/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/1. Call Summaries/ws_attio_[company_slug].json`

Pass this prompt to the agent (substitute actual values):

```
You are the ws-attio research agent for the Jolly deck workflow.

Company: [COMPANY_NAME]
Company slug: [company_slug]
Branch: [A or B]
Vertical: [vertical]
Workspace root (WS): [WS]
Client root (CLIENT_ROOT): [CLIENT_ROOT]
Today's date: [YYYY-MM-DD]
180 days ago: [YYYY-MM-DD]

Your job: run Attio CRM + call recording research and write a clean JSON output.

TIMEOUT: If any single Attio MCP call takes longer than 60 seconds, abandon that call and continue with whatever data you have. Do not let a slow API block the entire workstream.

--- ATTIO CRM (Branch A only -- if Branch B, skip all Attio calls and set all Attio fields to empty) ---

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

Extract from results: revenue mentions, headcount mentions, location counts, pain points, pricing signals, any campaigns mentioned. Record the company record ID for the call recording step below.

Also extract **systems of record** - any named software platforms, tools, or data systems the company uses (e.g., Salesforce, Workday, ADP, Toast, UKG, Oracle). Look for mentions in call transcripts, notes, and emails of HR systems, POS systems, payroll providers, CRM platforms, scheduling tools, etc. Record the system name and its domain (e.g., "salesforce.com") when identifiable.

Also determine the **client industry vertical** from the data (e.g., "QSR", "Healthcare", "Manufacturing", "Retail", "Hospitality", "Logistics", "Grocery", "Rideshare"). Use explicit mentions in Attio records, call transcripts, notes, or emails. If the industry is obvious from the company name or description (e.g., a hospital system), infer it. Record this as the `industry` field in the research output. If uncertain, leave it empty.

--- ATTIO CALL RECORDINGS (Branch A only -- if Branch B, skip) ---

After CRM data is collected, search for call recordings associated with the company.

Use mcp__claude_ai_Attio__search-call-recordings-by-metadata:
  - Filter by the company record ID found above
  - Date range: [180 days ago] to [today]

For each recording found (take the 6 most recent by date):
  - Call mcp__claude_ai_Attio__get-call-recording to get the full transcript
  - Extract: call date, call title, participants, key topics, verbatim quotes relevant to revenue, headcount, locations, turnover, pricing, and pain points
  - Write the transcript to: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/5. Call Transcripts/[YYYY-MM-DD]_[Call Title].md

After all transcripts are saved, write a consolidated insights file to:
[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/1. Call Summaries/attio_call_insights_[today YYYY-MM-DD].json

The call insights JSON schema:
{
  "company": "[COMPANY_NAME]",
  "generated_date": "[YYYY-MM-DD]",
  "call_count": 0,
  "calls": [
    {
      "recording_id": "",
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

Write your output to: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/1. Call Summaries/ws_attio_[company_slug].json

Schema:
{
  "workstream": "attio",
  "company": "[COMPANY_NAME]",
  "findings": {
    "attio_records_count": 0,
    "attio_notes_count": 0,
    "attio_emails_count": 0,
    "call_recordings_found": 0,
    "call_recordings_transcribed": 0,
    "revenue": null,
    "revenue_source": "",
    "unit_count": null,
    "unit_count_source": "",
    "employee_count": null,
    "employee_count_source": "",
    "pain_points": [],
    "campaigns_mentioned": [],
    "verbatim_quotes": [],
    "systems_of_record": [],
    "other_data_points": {}
  },
  "source_summary": {
    "attio_used": false,
    "calls_used": false,
    "transcript_files_written": [],
    "call_insights_file_written": ""
  }
}

Each entry in systems_of_record should be: {"name": "Salesforce", "domain": "salesforce.com", "source": "Attio call 2025-11-14"}. Only include systems explicitly named - do not guess. If no systems are found, leave the array empty.

Populate all fields from your research. If branch is B, set attio_used and calls_used to false and leave findings empty. Write the file. Do not output a long summary -- just confirm the file path written.
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

CRITICAL RULE: Only extract data that is DIRECTLY ABOUT [COMPANY_NAME] itself.
- If a message mentions [COMPANY_NAME] in the context of another company (e.g., "[COMPANY_NAME] is acquiring OtherCo" — the revenue figure in that message likely belongs to OtherCo, not [COMPANY_NAME]), DISCARD that data point.
- For each data point you extract, verify the subject of the sentence is [COMPANY_NAME]. If the data describes a different company, do not include it.
- When in doubt, discard the data point rather than risk attributing another company's data to [COMPANY_NAME].

If Branch B, skip all Slack calls and write an empty findings output.

--- SEARCH (max 2 Slack API calls) ---

Fire both keyword searches in parallel:
1. mcp__claude_ai_Slack__slack_search_public_and_private: query="[COMPANY_NAME] revenue OR locations OR headcount"
2. mcp__claude_ai_Slack__slack_search_public_and_private: query="[COMPANY_NAME] turnover OR pricing OR campaign"

For each result, check: is this message ABOUT [COMPANY_NAME], or does it just mention the name in passing? Only extract data from messages where [COMPANY_NAME] is the subject.

--- CHANNEL FALLBACK (only if both searches return zero usable results) ---

If and only if BOTH searches returned zero data points about [COMPANY_NAME]:
- mcp__claude_ai_Slack__slack_read_channel: limit=20, for the most relevant channel found
- Do NOT use channel fallback if keyword searches returned any usable data.

--- OUTPUT ---

Create output directory before writing: mkdir -p "[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/3. Slack"
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
    "other_data_points": {},
    "discarded_other_company": []
  },
  "source_summary": {
    "slack_available": true,
    "keyword_searches_run": 2,
    "channel_fallback_used": false,
    "skip_reason": ""
  }
}

If you discarded data that belonged to a different company, log it in discarded_other_company with the company name and reason (e.g., "Revenue $2B mentioned in context of US Merchants, not [COMPANY_NAME]").

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
    python "[WS]/.claude/scripts/sec_filings.py" --ticker [TICKER] --include-text --save-pdf \
      --output "[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/2. Public Filings/sec_[TICKER].json"
  After the script completes, read the output JSON.
  For annual revenue, use only the 10-K value. Do not use 10-Q values for annual revenue.

  Step 2 -- Extract unit count and employee count from the 10-K text:
    The JSON output contains filing_text.business and filing_text.mda from the most recent
    10-K (extracted by edgartools — no raw HTTP calls needed).

    Scan filing_text.business for unit count: patterns like "X,XXX locations",
    "X restaurants", "X company-operated stores", "X facilities".
    Scan filing_text.business and filing_text.mda for employee count: patterns like
    "approximately X,XXX employees", "X full-time employees", "X team members".

    If filing_text is absent or contains an error key (e.g. private company, parse failure),
    fall back to a WebSearch for unit and employee count — this counts as 1 web operation.

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
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/1. Call Summaries/ws_attio_[company_slug].json"
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/3. Slack/ws_slack_[company_slug].json"
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/2. Public Filings/ws_public_[company_slug].json"
```

If any file is missing or invalid JSON, note it as a failed workstream and continue with the remaining data.

---

## Step 5: WS-Merge

Consolidate all data from the 4 agent output files into a single field map. Apply the following source priority order (highest to lowest):

1. Attio call recording (1st party)
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
Annual Revenue         | $XXX.XMM     | Attio call (2025-11-14) | 1st party
Unit Count             | XXX          | SEC 10-K (2024)     | 2nd party
Employee Count         | ~X,XXX       | LinkedIn estimate   | 3rd party
...

CONFLICTS:
- [Field]: Source A says [X], Source B says [Y] -- delta [Z%]. Please confirm which to use.

GAPS:
- [Field]: No data found across all workstreams. Please provide a value or confirm [benchmark default].
```

If there are conflicts or gaps, use AskUserQuestion:
- Question: "Resolve conflicts and gaps above before proceeding?"
- Options: ["All resolved — proceed to campaigns", "I need to provide values"]

If "I need to provide values", wait for the user's input then re-merge. If no conflicts or gaps, proceed immediately.

---

## Step 5a: Systems of Record Logo Fetch

Check the ws-attio output for `systems_of_record`. If the array is non-empty and contains named systems with domains, download logos for each using the Brandfetch downloader. If the array is empty, skip this step entirely.

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
BRANDFETCH_API_KEY=$(grep BRANDFETCH_API_KEY "$WS/.claude/.env" 2>/dev/null | cut -d '=' -f2)
SOR_LOGOS="$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/3. Systems of Record"
mkdir -p "$SOR_LOGOS"
```

For each system with a known domain, run:
```bash
python "$WS/Tools/brandfetch_downloader.py" \
  --api-key "$BRANDFETCH_API_KEY" --brand "[domain]" --output "$SOR_LOGOS"
```

Cap at 6 systems max. If Brandfetch fails for a system, skip it - the deck-format step will fall back to text labels.

Record the results in a list for the research output:
```json
"systems_of_record": [
  {"name": "Salesforce", "domain": "salesforce.com", "logo_path": "3. Systems of Record/Salesforce/logo_png.png", "logo_found": true},
  {"name": "Workday", "domain": "workday.com", "logo_path": null, "logo_found": false}
]
```

If no BRANDFETCH_API_KEY is set, skip logo download and keep `logo_found: false` for all systems. The deck-format step will use text labels instead.

---

## Step 6: Campaign Selection Gate

Read campaign names from the template config saved by deck-start:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/template_config.json"
```

Extract the campaign names from the `campaigns` dict in the config. Do NOT generate or invent campaign names — use ONLY the names from the template config.

Present campaign recommendations and wait for explicit user confirmation. Do not proceed to any Excel or model work until the user types "confirm".

**Branch A format:**

```
CAMPAIGN RECOMMENDATIONS for [COMPANY NAME]
Based on [N] Attio call recordings + [list other sources used]
Template campaigns (from config): [list all campaign names from template_config.json]

RECOMMENDED (include in model + summary slide):
1. [Campaign Name from config] -- HIGH priority
   Evidence: "[exact verbatim quote]" (Attio call, [YYYY-MM-DD])
   Client interest: Explicit

2. [Campaign Name from config] -- HIGH priority
   Evidence: "[exact verbatim quote or paraphrase]" ([source], [date])
   Client interest: [Explicit / Implied]

STANDARD (include in model, exclude from summary slide):
3. [Campaign Name from config] -- [reason for standard classification]

EXCLUDE:
- [Campaign Name from config] -- [reason for exclusion]

```

Use AskUserQuestion:
- Question: "Confirm campaign selection?"
- Options: ["Confirm — proceed with these campaigns", "I need to make changes"]

**Branch B (auto-proceed):**

Branch B is always a prospect deck with all campaigns included. No confirmation needed. Display the list and proceed immediately:

```
Campaign Selection — [COMPANY NAME]

  No call data — showing full [Vertical] template.

  [1] [Campaign Name from config]
  [2] [Campaign Name from config]
  ...

  All [N] campaigns included (prospect deck — illustrative). Proceeding to save.
```

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
    "call_recordings_found": 0,
    "call_recordings_transcribed": 0,
    "attio_records": 0,
    "attio_notes": 0,
    "slack_messages": 0,
    "sec_filings": false,
    "comp_benchmarks_used": false,
    "web_operations_used": 0
  },
  "slack_insights": [],
  "attio_insights": {},
  "call_insights": {},
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
  "systems_of_record": [],
  "model_population": {}
}
```

Populate all fields from the merged data. Leave `model_population` as an empty object.

Then update the session state JSON:

```python
python3 -c "
import json, glob, os
from datetime import date
ws = os.environ.get('JOLLY_WORKSPACE', '.')
files = sorted(glob.glob(f'{ws}/.claude/data/session_state_*.json'))
if not files: raise SystemExit('No session state found — cannot update')
path = files[-1]
data = json.load(open(path, encoding='utf-8'))
data['phase_checklist']['phase_2_research'] = 'complete'
data['next_action'] = '/deck-model'
data['campaigns_selected'] = [CAMPAIGN_LIST]
data['last_updated'] = date.today().isoformat()
data['metadata']['key_decisions'] = '[key decisions text]'
with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
print('Updated:', path)
"
```

Replace `[CAMPAIGN_LIST]` with the actual Python list of confirmed campaign names (e.g., `['Campaign A', 'Campaign B']`). Replace `[key decisions text]` with a string summarizing source conflicts resolved, gaps filled, and campaigns excluded.

---

## Step 8: Hand Off

Tell the user:

```
Research complete for [COMPANY NAME].

Source breakdown:
- Attio: [N] records, [N] notes, [N] call recordings transcribed
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
