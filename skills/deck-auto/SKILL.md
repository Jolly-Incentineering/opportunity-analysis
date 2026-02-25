---
name: deck-auto
description: Run the full intro deck workflow automatically for a company. Saves progress after every phase and resumes if interrupted. Usage: /deck-auto [Company Name].
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

You are the `deck-auto` orchestrator for the Jolly intro deck workflow. Run all five phases end-to-end for a single company, pausing only at required human gates, saving state after every phase.

The company name is the argument passed to `/deck-auto`. Substitute [COMPANY_NAME] throughout.

**Bash preamble** — use at the start of every bash block:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
```

Derive `company_slug`: lowercase, spaces → underscores, remove special characters. Compute once, reuse.

---

## Phase 0: Workspace Check

Read `$WS/.claude/data/workspace_config.json`. If missing or invalid, tell the user to run `/deck-setup` first and stop.

---

## Phase 0B: Session State Check

Scan `$WS/.claude/data/session_state_*.md` for a file matching [COMPANY_NAME].

**If found:** Show phase status. Ask "go" to continue or "stop [N]" to jump. Wait.

**If not found:**

```
No existing session for [COMPANY_NAME]. Starting from Phase 1.

Context

  [1] Pre-call — no call yet
      Slack + Public data only (~8-12 min)

  [2] Post-call — after a call or internal notes
      Full Attio + Gong + Slack + Public (~14-20 min)

→ 1 or 2
```

Wait for context selection. Store as `context`. Then show phase plan and wait for "go".

---

## Phase 1: Start

Tell the user: "Phase 1: Start — running."

### 1.1 Ensure Client Folder Structure

```bash
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/1. Logos"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/2. Swag"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/1. Call Summaries"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/2. Public Filings"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/3. Slack"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/5. Call Transcripts"
```

### 1.2 Template Selection

List available template pairs from `$WS/$TEMPLATES_ROOT` grouped by vertical (one template per vertical). Wait for user's choice. Record vertical and paths.

### 1.3 Copy Templates

```bash
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)"
cp "[source .xlsx]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx"
cp "[source .pptx]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx"
```

Update document title metadata on both files. Open both files.

Naming:
- Deck subfolder: `1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)/`
- Deck: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx`
- vF: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx`
- PDF: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pdf`

### 1.4 Scan Template and Load Config

```bash
python3 "$WS/.claude/agents/template_scanner.py" \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" \
  --configs-dir "$WS/.claude/agents/templates/" --threshold 0.85
```

If match ≥85%: copy matched config to `$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/template_config.json`.
If no match: create new config with `--create`, save to both templates dir and client folder.

Extract campaign names, formula counts, cell addresses from config.

### 1.5 Detect Branch (3 Parallel Checks)

Run simultaneously:
- **Check A:** `gong_insights_*.json` in `5. Call Transcripts/` (≤30 days old)
- **Check B:** Attio CRM — prefer REST API (`POST https://api.attio.com/v2/objects/companies/records/query` with `Authorization: Bearer $ATTIO_API_KEY`) if ATTIO_API_KEY is available in env or .env file. Fallback: `mcp__claude_ai_Attio__search-records` query [COMPANY_NAME]
- **Check C:** `mcp__claude_ai_Slack__slack_search_channels` with slug

Branch A (existing) if ANY has data. Branch B (prospect) if ALL empty.

### 1.6 Launch Asset Gatherer

Background Task tool subagent for logos/swag. Do not wait.

### 1.7 Save State

Write `session_state_YYYY-MM-DD.md`: Phase 1 complete, context, branch, vertical, template paths, template config path.

Tell user: "Phase 1 complete. Moving to Phase 2: Research..."

---

## Phase 2: Research

Tell the user: "Phase 2: Research — running."

### 2.1 Gong Recipe (Branch A + Post-Call Only)

If Branch A and post-call and gong_integration = "rube": ensure recipe exists via Rube.

### 2.2 Dispatch Research Agents

Dispatch **3 agents** simultaneously using `model: "haiku"`:

**Pre-call path:** Slack + Public only (2 agents).
**Post-call path:** Attio/Gong + Slack + Public (3 agents).

Output paths:
- Agent 1 (attio-gong): `4. Reports/1. Call Summaries/ws_attio_gong_[slug].json`
- Agent 2 (slack): `4. Reports/3. Slack/ws_slack_[slug].json`
- Agent 3 (public): `4. Reports/2. Public Filings/ws_public_[slug].json`

Use same agent prompts as in deck-research skill.

### 2.3 Wait and Read Results

Wait for all agents. Read output files. Note failed workstreams.

### 2.4 WS-Merge

Source priority: Gong > Attio > Slack > SEC > Benchmark > Web estimate.
Flag conflicts (>15% delta). Flag gaps. Present merged field map. Wait for resolution.

### 2.5 GATE: Campaign Selection

Read campaign names from `template_config.json`. Do NOT generate names.

**Branch A:** Rank by evidence. Present RECOMMENDED / STANDARD / EXCLUDE.
**Branch B:** Show all template campaigns.

Wait for "confirm".

### 2.6 Save Research Output

Write `research_output_[slug].json` to `$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/` (directly, not subfolder).
Update session state: Phase 2 complete, approved campaigns.

Tell user: "Phase 2 complete. Moving to Phase 3: Model..."

---

## Phase 3: Model

Tell the user: "Phase 3: Model — running."

### 3.1 Ensure Model is Closed

Tell user to close the model file. Wait for "ready".

### 3.2 Load Template Config

Read `template_config.json` from `4. Reports/`. Use `labels` for cell mapping, `campaigns` for names.

### 3.3 Build Formula Lock List

Scan formulas at runtime with `excel_editor.py --action scan-formulas`. Never write to formula cells.

### 3.4 Compute Values and Dry-Run Plan

Apply rounding standards. ROPS check (10x–30x). Accretion ceiling (≤15% EBITDA). Scenario sensitivity: only Target % varies across Base/Upside/Downside.

### 3.5 GATE: Dry-Run Approval

Present complete plan with cells, values, sources, ROPS, accretion, skipped formulas. Wait for "approve".

### 3.6 Write to Excel

Use `excel_editor.py` in single batch while file is closed. Add comments to every hard-coded cell.

### 3.7 Verify Formula Counts

Compare against `template_config.json` (NOT hardcoded numbers). Alert if counts changed.

### 3.8 Open Model for Review

Open model. Walk through 5-item checklist:
1. Inputs sheet — all column E cells filled
2. Campaigns — all selected campaigns have non-zero assumption values
3. ROPS — all in 10x–30x range
4. Summary inputs — correct company name, revenue, unit count
5. Save (Ctrl+S)

Wait for "done" after each.

### 3.9 Save State

Update `research_output_[slug].json` with `model_population` AND `campaign_details` (rops_base, rops_upside, incentive_cost_base, ebitda_uplift_base, description per campaign).
Session state: Phase 3 complete.

Tell user: "Phase 3 complete. Moving to Phase 4: Format..."

---

## Phase 4: Format

Tell the user: "Phase 4: Format — running."

```
PHASE 4 FILE MANAGEMENT:
1. Close ALL Excel and PowerPoint files now.
2. I'll tell you when to open each file and when to close it.
Scope: Banner fill, text replacement, brand assets, Macabacus refresh, vF copy, link break, PDF export.
Will NOT do: Custom UI design, app mockups, visual redesign.
```

### 4.1 Open Master Deck

Open master deck. Read banner values from `campaign_details` in `research_output_[slug].json` (NOT from Excel).

### 4.2 Banners

Present banner replacement plan. Wait for "approve banners". Write.

### 4.3 Text Placeholders

Scan for template tokens. Present replacement plan. Wait for "approve text". Write.

### 4.4 Campaign Slides (Post-Call Only)

Walk through campaign slide checklist. Wait for "done" after each.

### 4.5 Brand Assets

Checklist: logo (`3. Company Resources/1. Logos/`), colors, swag (`2. Swag/`). Wait for "done"/"skip".

### 4.6 Step 8a: Macabacus Refresh (Manual)

User refreshes in master, saves, closes master. Wait for "ready".

### 4.7 Step 8b: Create vF Copy (Automated)

Copy master to vF filename. Update title metadata.

### 4.8 Step 8c: Break Links (Manual)

User opens vF, breaks Macabacus links, saves, closes. Wait for "ready".

### 4.9 Step 8d: Run Deck Formatter (Automated)

Launch deck-formatter subagent for cleanup pass on vF.

### 4.10 Step 7: Final Visual Review (Manual)

User reviews vF: no tokens, dollar formatting, ROPS hidden (Branch B). Wait for "done".

### 4.11 Step 9: Export PDF (Manual)

```
Export PDF manually:
1. Open vF in PowerPoint
2. File → Export → Create PDF/XPS
3. Save as [pdf_filename]
Type "done" when exported.
```

Set PDF title metadata with pypdf after export.

### 4.12 Cheat Sheets and Save State

Run `cheatsheet_gen.py`. Continue if fails. Session state: Phase 4 complete.

Tell user: "Phase 4 complete. Moving to Phase 5: QA..."

---

## Phase 5: QA

Tell the user: "Phase 5: QA — running."

### 5.1 Run QA Script

```bash
python3 "$WS/.claude/scripts/qa_check.py" --company "[COMPANY_NAME]"
```

### 5.2 Model QA Checks

Open model. Run:
- **M1:** Formula counts from `template_config.json` (NOT hardcoded)
- **M2:** No empty input cells in column E of Inputs sheet
- **M3:** ROPS range (10x–30x)
- **M4:** Accretion ceiling (≤15% EBITDA)
- **M5:** Hiring cost cap $3,500 (QSR only)
- **M6:** Comment coverage (spot-check 10 cells)

### 5.3 Deck QA Checks

Open vF. Walk through:
- **D1:** No template tokens (Ctrl+F "[")
- **D2:** Dollar formatting ($X.Xk / $X.XXMM)
- **D2b:** Macabacus range blanks (programmatic)
- **D2c:** Raw integers in narrative (programmatic)
- **D3:** Banner values match model
- **D4:** Campaign list matches approved
- **D5:** Logo and brand assets
- **D6:** ROPS hidden (Branch B only)
- **D7:** PDF matches deck

### 5.4 Summarize and Resolve

Present QA summary. If FAIL: walk user through fix, re-check. Repeat until all pass.

### 5.5 Cleanup

Delete lock files. Open final files (vF, model, PDF). Save final session state.

---

## Final Summary

```
[COMPANY_NAME] deck complete.

Campaigns: [list each with ROPS]
Accretion: [X]% of EBITDA

Sources:
  Gong:             [N] calls ([N] transcribed)
  Attio:            [N] records, [N] notes
  Slack:            [N] messages
  SEC filings:      [used / not applicable]
  Comp benchmarks:  [used / stale]
  Web operations:   [N of 4 used]

Files:
  PPT:   [full path to vF.pptx]
  Model: [full path to model .xlsx]
  PDF:   [full path to .pdf]

QA: [PASS / PASS with notes]
All phases complete. Ready for delivery.
```

Do not add anything beyond this summary.
