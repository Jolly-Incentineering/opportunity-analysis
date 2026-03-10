# Plugin Efficiency Refactor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce mistakes (single source of truth per phase, no drift) and reduce runtime (fewer tokens, fewer gates, cached state, Figma prompt generation, auto-QA before vF).

**Architecture:** Extract shared content to a preamble file all skills reference. Make deck-start a thin orchestrator that invokes phase skills via Skill tool (not summarizing them). Restructure deck-format to run qa_check.py before creating the vF. Add a Figma prompt generation step that reads a screenshot and outputs campaign text + points. Cache template config in session state.

**Tech Stack:** Claude Code plugin system (SKILL.md, plugin.json), Python scripts (deck_engine.py, qa_check.py)

---

## File Map

### New files
- `skills/shared-preamble.md` - Hard rules, bash preamble, executive audience rule (referenced by all skills)
- `skills/deck-figma/SKILL.md` - New skill: screenshot input, campaign text + points output

### Modified files
- `skills/deck-start/SKILL.md` - Gut phases 2-5, replace with Skill tool invocations
- `skills/deck-format/SKILL.md` - Add auto-QA gate before vF creation, add Figma prompt step
- `skills/deck-qa/SKILL.md` - Deduplicate checks already run in deck-format, focus on final verification
- `skills/deck-research/SKILL.md` - Remove hard rules block, reference shared-preamble
- `skills/deck-model/SKILL.md` - Remove hard rules block, reference shared-preamble, consolidate 4 review gates into 1
- `skills/deck-continue/SKILL.md` - Remove hard rules block, reference shared-preamble
- `skills/deck-new-template/SKILL.md` - Remove hard rules block, reference shared-preamble
- `skills/deck-setup/SKILL.md` - Remove hard rules block, reference shared-preamble
- `skills/deck-help/SKILL.md` - Add /deck-figma to command list

### No changes needed
- `scripts/deck_engine.py` - Already has format-all action
- `scripts/qa_check.py` - Already runs all checks via single CLI call
- `scripts/ws_env.sh` - Already handles preamble sourcing
- `.claude-plugin/plugin.json` - No structural changes needed
- `skills/jolly-onboarding/SKILL.md` - No hard rules to extract

---

## Chunk 1: Extract Shared Preamble

### Task 1: Create shared-preamble.md

**Files:**
- Create: `skills/shared-preamble.md`

- [ ] **Step 1: Write the shared preamble file**

Create `skills/shared-preamble.md` with all content currently duplicated across 8 skills:

```markdown
# Shared Preamble

All deck workflow skills inherit these rules and conventions. Do not repeat them in individual skills - reference this file instead.

## Hard Rules - NEVER VIOLATE

1. Do NOT generate or invent campaign names. Read them from the template config JSON.
2. Do NOT make tool calls or add steps not listed in the skill's instructions.
3. Do NOT write to formula cells under any circumstances.
4. Do NOT skip gates marked with AskUserQuestion - but do NOT add extra gates.
5. Do NOT open files you are about to write to programmatically. Keep them closed during writes.
6. Do NOT proceed past a failed step - stop and report. Do NOT retry more than once.
7. Keep all client-specific data in the client folder under 4. Reports/. Never write client data to .claude/data/.
8. All Attio, Slack, and other MCP tools are READ-ONLY. Never use create, update, or delete MCP actions.
9. Use HAIKU for research agents unless explicitly told otherwise. (Only applies to skills that dispatch agents: deck-start, deck-research.)

## Bash Preamble

Use at the start of every bash block:

\```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
\```

## Executive Audience Rule

Intro decks are reviewed by C-suite executives (CEO, CFO, COO). Never include internal process language in any text written to the deck:
- References to calls, meetings, or conversations ("as discussed on our call", "per our meeting", "as mentioned")
- References to internal research steps ("our analysis found", "based on our review")
- References to data sourcing ("according to SEC filings", "per Glassdoor")
- Hedging language ("we believe", "we think", "it appears")
- Any language that reveals the deck was built by an automated process or external team

All campaign descriptions, commentary, and insights must read as confident, client-facing strategic recommendations - not internal working notes.

## Session State Loader

Standard pattern for loading session state at the start of any phase skill:

\```python
python3 -c "
import json, glob, os
ws = os.environ.get('JOLLY_WORKSPACE', '.')
files = sorted(glob.glob(f'{ws}/.claude/data/session_state_*.json'))
if not files: raise SystemExit('No session state found')
data = json.load(open(files[-1], encoding='utf-8'))
for k, v in data.items():
    if isinstance(v, dict):
        print(f'{k}:', json.dumps(v))
    else:
        print(f'{k}:', v)
"
\```

## Company Slug

Derive from company name: lowercase, spaces to underscores, remove special characters. Compute once, reuse throughout the skill.
```

- [ ] **Step 2: Commit**

```bash
git add skills/shared-preamble.md
git commit -m "feat: extract shared preamble for all deck workflow skills"
```

### Task 2: Strip duplicated content from all phase skills

**Files:**
- Modify: `skills/deck-research/SKILL.md` (lines 7-16)
- Modify: `skills/deck-model/SKILL.md` (lines 7-15)
- Modify: `skills/deck-format/SKILL.md` (lines 7-38)
- Modify: `skills/deck-qa/SKILL.md` (lines 7-15)
- Modify: `skills/deck-continue/SKILL.md` (lines 7-15)
- Modify: `skills/deck-new-template/SKILL.md` (lines 7-15)
- Modify: `skills/deck-setup/SKILL.md` (lines 7-15)

- [ ] **Step 1: Replace hard rules block in each skill**

In each of the 7 skills listed above, replace the "HARD RULES" block (and "Executive Audience Rule" block where present) with a single reference line:

```
Read and follow all rules in skills/shared-preamble.md before proceeding.
```

For deck-format, also remove the Executive Audience Rule section (lines 19-38) since it's now in the shared preamble. Replace with:

```
The Executive Audience Rule (see shared-preamble.md) applies to ALL text written in Steps 4C, 4D, 4E, and 4G.
```

- [ ] **Step 2: Replace duplicated session state loader blocks**

In deck-format (Step 1), deck-qa (Step 1), deck-model (Step 1), and deck-research (Step 1): replace the inline Python session state loader with a reference:

```
Load session state using the standard loader from shared-preamble.md.
```

Keep the field extraction and validation logic that's unique to each skill (e.g., "If phase_3_status != 'complete', stop").

- [ ] **Step 3: Replace duplicated bash preamble blocks**

In each skill, replace the first occurrence of the workspace setup block with:

```
Set workspace root using the bash preamble from shared-preamble.md.
```

Keep subsequent bash blocks that use `$WS` and `$CLIENT_ROOT` as-is (they're short and contextual).

- [ ] **Step 4: Commit**

```bash
git add skills/deck-research/SKILL.md skills/deck-model/SKILL.md skills/deck-format/SKILL.md skills/deck-qa/SKILL.md skills/deck-continue/SKILL.md skills/deck-new-template/SKILL.md skills/deck-setup/SKILL.md
git commit -m "refactor: replace duplicated hard rules and preambles with shared-preamble reference"
```

---

## Chunk 2: Thin Orchestrator deck-start

### Task 3: Rewrite deck-start as thin orchestrator

**Files:**
- Modify: `skills/deck-start/SKILL.md`

The current deck-start is 665 lines because it contains full instructions for all 5 phases. Phases 2-5 duplicate (in summary form) what the standalone phase skills already specify in full detail. This causes drift - the summaries get out of sync with the real skills.

**New structure:** deck-start keeps Phase 0 (workspace check, library check, session state check, context selection, gate checklist) and Phase 1 (folder creation, template selection, template copy, config scan, Attio branch detect, asset gatherer, save state) as-is. Phases 2-5 become single-line Skill invocations.

- [ ] **Step 1: Delete Phase 2-5 content from deck-start**

Remove everything from `## Phase 2: Research` through `## Final Summary` (roughly lines 379-665). Replace with:

```markdown
## Phase 2: Research

Tell the user: "Phase 2: Research - running."

Invoke the `/deck-research` skill. Follow it completely. When it finishes and session state shows phase_2 complete, continue.

---

## Phase 3: Model

Tell the user: "Phase 3: Model - running."

Invoke the `/deck-model` skill. Follow it completely. When it finishes and session state shows phase_3 complete, continue.

---

## Phase 4: Format

Tell the user: "Phase 4: Format - running."

Invoke the `/deck-format` skill. Follow it completely. When it finishes and session state shows phase_4 complete, continue.

---

## Phase 5: QA

Tell the user: "Phase 5: QA - running."

Invoke the `/deck-qa` skill. Follow it completely. When it finishes, present the final summary below.

---

## Final Summary

Read session state and research output to populate:

\```
[COMPANY_NAME] deck complete.

Campaigns: [list each with ROPS]
Accretion: [X]% of EBITDA

Files:
  PPT:   [full path to vF.pptx]
  Model: [full path to model .xlsx]
  PDF:   [full path to .pdf]

QA: [PASS / PASS with notes]
All phases complete. Ready for delivery.
\```

Do not add anything beyond this summary.
```

- [ ] **Step 2: Also strip the hard rules block from deck-start**

Replace lines 7-17 (hard rules) with:

```
Read and follow all rules in skills/shared-preamble.md before proceeding.
```

- [ ] **Step 3: Verify deck-start is now ~330 lines**

The file should contain: frontmatter (5) + preamble reference (3) + Phase 0 setup (~80) + Phase 0B session check (~45) + Phase 1 full detail (~200) + Phase 2-5 delegations (~40) + final summary (~20) = ~393 lines max.

- [ ] **Step 4: Commit**

```bash
git add skills/deck-start/SKILL.md
git commit -m "refactor: deck-start delegates phases 2-5 to phase skills (single source of truth)"
```

---

## Chunk 3: Cache Template Config in Session State

### Task 4: Write template config into session state during Phase 1

**Files:**
- Modify: `skills/deck-start/SKILL.md` (Phase 1, Step 1.7 save state)

- [ ] **Step 1: Add template_config to session state JSON**

In the session state write block (Step 1.7), add a new field that caches the template config:

After the existing `template_paths` dict, add:

```python
    # Cache template config so downstream phases don't re-read the file
    'template_config_cache': json.load(open('[template config path]', encoding='utf-8')),
```

This means `campaigns`, `formula_counts`, `labels`, and `template_type` are all available from session state in phases 2-5 without re-reading template_config.json.

- [ ] **Step 2: Update deck-model to read from session state cache**

In deck-model Step 2 (Load Template Config), replace the explicit file read with:

```
Read `template_config_cache` from session state (cached during Phase 1). If missing (legacy session), fall back to reading `4. Reports/template_config.json`.
```

- [ ] **Step 3: Update deck-format to read from session state cache**

Same pattern in deck-format Step 1 - read template config from session state cache, fall back to file read.

- [ ] **Step 4: Commit**

```bash
git add skills/deck-start/SKILL.md skills/deck-model/SKILL.md skills/deck-format/SKILL.md
git commit -m "perf: cache template config in session state, eliminate redundant file reads"
```

---

## Chunk 4: Restructure deck-format (Auto-QA Before vF)

### Task 5: Add pre-vF QA gate to deck-format

**Files:**
- Modify: `skills/deck-format/SKILL.md`

Currently the flow is: write placeholders -> Macabacus refresh -> vF copy -> break links -> format vF -> export PDF -> then run /deck-qa separately. The problem: if QA finds issues after vF creation, the user has to redo the entire vF cycle (edit master, refresh, copy, break links again).

**New flow:** After writing placeholders to the master (Step 4) and before Macabacus refresh (Step 7a), run an automated pre-vF QA pass on the master deck. Catch issues early so the user fixes them in the master before creating the vF.

- [ ] **Step 1: Add Step 5b (Pre-vF QA) after Step 5 (Brand Assets)**

Insert after the current Step 5, before Step 7a:

```markdown
## Step 6: Pre-vF Quality Check (Automated)

Before creating the vF, run automated QA on the master deck to catch issues early. The user should close the master deck for this check.

Tell the user:

\```
Running pre-vF quality check on the master deck.
Close the master deck (Ctrl+S first), then tell me when it's closed.
\```

Use AskUserQuestion:
- Question: "Master deck saved and closed?"
- Options: ["Closed", "Give me a moment"]

Then run:

\```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 "$WS/.claude/scripts/qa_check.py" --company "[COMPANY_NAME]" --deck-only
\```

If qa_check.py does not support `--deck-only`, run the full check and only report deck-related results (D1, D2, D2b, D2c, D7). Ignore model checks here since the model was already verified in Phase 3.

**If any deck checks FAIL:**

\```
PRE-VF CHECK FAILED:
  [list each failure with slide number and description]

Fix these in the master deck before proceeding.
After fixing, save, close, and tell me to re-run the check.
\```

Loop: re-run qa_check.py after each fix round until all deck checks pass.

**If all deck checks PASS:**

\```
Pre-vF check passed. Master deck is clean - proceeding to Macabacus refresh.
\```

Continue to Step 7a.
```

- [ ] **Step 2: Update the gate checklist at the top of deck-format**

Add `Pre-vF QA passed` to the gates list:

```
Gates this phase:
  [] Placeholder writes approved (C/D/E/G items)
  [] Pre-vF QA passed
  [] Macabacus refresh complete
  [] vF links broken
  [] vF saved + PDF exported
```

- [ ] **Step 3: Commit**

```bash
git add skills/deck-format/SKILL.md
git commit -m "feat: add pre-vF automated QA gate to catch issues before vF creation"
```

### Task 6: Simplify deck-qa to focus on final verification

**Files:**
- Modify: `skills/deck-qa/SKILL.md`

Since deck-format now runs automated QA before vF creation, deck-qa becomes a final verification pass focused on:
1. vF-specific checks (banners filled, links broken, dollar formatting on vF)
2. Cross-validation (model vs deck values match)
3. PDF matches vF
4. Manual spot-checks

- [ ] **Step 1: Update deck-qa Step 2 description**

Change the framing from "run all checks" to "final verification":

```markdown
## Step 2: Run Final Verification

Automated deck checks already passed on the master in deck-format. This final pass verifies the vF copy and cross-validates against the model.

Tell the user:

\```
Close Excel and PowerPoint if open - I need both files closed for final checks.
\```

Pause 3 seconds, then run:

\```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 "$WS/.claude/scripts/qa_check.py" --company "[COMPANY_NAME]"
\```

Focus on these results:
- **Must pass (vF-specific):** D1 (no tokens), D2 (dollar formatting), D3 (banners filled), D4 (no red text/links broken)
- **Must pass (cross-validation):** Banner values match model, campaign list matches approved
- **Must pass (deliverables):** D6 (PDF matches deck)
- **Report all:** M1-M6 results (should already pass from Phase 3, flag if regression)
```

- [ ] **Step 2: Consolidate manual checks into single gate**

Replace the current 2 AskUserQuestion calls in Step 3 with a single combined checklist:

```markdown
Use AskUserQuestion:
- Question: "Final manual checks - model values correct in Excel, banners match model, campaigns correct, logo placed, PDF matches vF?"
- Options: ["All pass", "Found issues"]
```

- [ ] **Step 3: Commit**

```bash
git add skills/deck-qa/SKILL.md
git commit -m "refactor: deck-qa focuses on vF verification (master QA now runs in deck-format)"
```

---

## Chunk 5: Figma Prompt Generation

### Task 7: Create deck-figma skill

**Files:**
- Create: `skills/deck-figma/SKILL.md`

This skill takes a screenshot of Figma screens as input and generates campaign-specific text and points values that the user can paste into Figma. It does NOT write to Figma - it gives the user ready-to-paste text.

- [ ] **Step 1: Write the deck-figma skill**

Create `skills/deck-figma/SKILL.md`:

```markdown
---
name: deck-figma
description: Generate campaign text and points for Figma app screens. Takes a screenshot as input, outputs ready-to-paste text. Usage: /deck-figma [Company Name] then paste or drag a screenshot.
disable-model-invocation: true
---

Read and follow all rules in skills/shared-preamble.md before proceeding.

---

You are generating text content for Figma app mockup screens. The user will provide a screenshot of the Figma layout and you will output campaign-specific text and points values they can paste in.

Set workspace root using the bash preamble from shared-preamble.md.

---

## Step 1: Load Session State and Research Output

Load session state using the standard loader from shared-preamble.md.

Extract: company_name, client_root, campaigns_selected, vertical.

If no session state exists, tell the user: "No active session found. Run /deck-start [Company] first." Then stop.

Read research output:

\```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research_output_[company_slug].json"
\```

Extract from research output:
- `campaign_details` - each campaign's name, description, rops_base, incentive_cost_base, ebitda_uplift_base
- `company_profile` - company name, vertical, revenue, unit count

---

## Step 2: Receive Screenshot

Tell the user:

\```
Ready to generate Figma text for [COMPANY_NAME].

Paste or drag a screenshot of the Figma screens you need text for.
I'll identify each screen type and generate the right content.
\```

Wait for the user to provide a screenshot. Use the Read tool to view the image.

---

## Step 3: Identify Screen Types

Analyze the screenshot to identify which app screen types are shown. Common screen types in Jolly app mockups:

- **Inbox/Feed screen** - push notification cards showing campaign rewards
- **Campaign detail screen** - full campaign description with reward amount and rules
- **Rewards summary screen** - list of active campaigns with points totals
- **Leaderboard screen** - ranking display with names and points
- **Achievement/badge screen** - milestone rewards with icons
- **Home/dashboard screen** - overview with total points and active campaigns

For each screen identified, note:
- Screen type
- Number of text fields visible (titles, subtitles, body text, point values)
- Layout structure (cards, list items, headers)

---

## Step 4: Generate Text for Each Screen

For each screen type identified, generate text using the campaign data from research_output.

### Points Calculation

Standard conversion: **200 points per $1 of incentive cost**.

For each campaign, compute:
- Points value = `incentive_cost_base * 200` (round to nearest 50)
- Sort campaigns by points value descending for feed/inbox displays

### Inbox/Feed Cards

For each campaign, generate a notification card:

\```
TITLE: [Campaign Name]
SUBTITLE: Earn [X] pts
BODY: [1 sentence - what to do to earn the reward, written as an action prompt]
POINTS BADGE: [X] pts
\```

Example:
\```
TITLE: Visit Order Amounts
SUBTITLE: Earn 2,400 pts
BODY: Ring up orders over $15 to earn bonus points this week.
POINTS BADGE: 2,400 pts
\```

### Campaign Detail Screen

\```
HEADER: [Campaign Name]
POINTS: [X] points
DESCRIPTION: [2-3 sentences explaining the campaign mechanic and reward. Written for the employee, not the executive. Simple, direct language.]
HOW TO EARN: [1-2 bullet points with specific trackable actions]
REWARD: [Points amount] points ([dollar equivalent at 200:$1])
\```

### Rewards Summary

For each campaign in the approved list:
\```
[Campaign Name]          [X] pts
\```

Total at bottom:
\```
Total Available          [sum] pts
\```

### Leaderboard

Generate 5-8 sample names with realistic point spreads:
\```
1. [Name]    [highest pts]
2. [Name]    [slightly less]
...
\```

Use common first names appropriate to the vertical and region.

---

## Step 5: Present Output

Present all generated text in a structured, copy-paste-friendly format:

\```
FIGMA TEXT - [COMPANY NAME]
Generated from [N] approved campaigns

====================================
SCREEN: [Screen Type]
====================================

[Card/field 1]
---
[Card/field 2]
---
...

====================================
SCREEN: [Screen Type 2]
====================================
...

POINTS SUMMARY:
  [Campaign 1]: [X] pts ($[Y] incentive)
  [Campaign 2]: [X] pts ($[Y] incentive)
  ...
  Total: [sum] pts ($[sum] incentive)
\```

Tell the user:

\```
Text generated for [N] screens. Copy each section into the matching Figma frame.

If you have more screens to fill, paste another screenshot.
If the text needs adjustments (tone, length, specific wording), tell me what to change.
\```

Do not update session state. This skill is stateless - it reads research data and outputs text.
```

- [ ] **Step 2: Commit**

```bash
git add skills/deck-figma/SKILL.md
git commit -m "feat: add /deck-figma skill for generating campaign text and points for Figma screens"
```

### Task 8: Add Figma step to deck-format workflow

**Files:**
- Modify: `skills/deck-format/SKILL.md`

- [ ] **Step 1: Add Step 5a (Figma Prompts) after Step 5 (Brand Assets)**

Insert after the current Step 5, before the new Step 6 (Pre-vF QA):

```markdown
## Step 5a: Figma App Screen Text (Optional)

If the deck includes app mockup screens in Figma, offer to generate the text now while campaign data is fresh.

Tell the user:

\```
If you have Figma app screens to fill (inbox feed, campaign details, rewards summary):
  - Paste a screenshot of the Figma layout and I'll generate campaign text + points.
  - Or type "skip" to continue without Figma text.
\```

Use AskUserQuestion:
- Question: "Generate Figma app screen text?"
- Options: ["Yes - let me paste a screenshot", "Skip - no Figma screens needed"]

If "Yes": invoke the `/deck-figma` skill. When the user is done generating text for all screens, continue to Step 6.

If "Skip": continue to Step 6.
```

- [ ] **Step 2: Update the WILL DO scope block**

Update the scope declaration at the top of deck-format:

```
  WILL DO: Banner fill, text replacement, systems of record, Figma app text, pre-vF QA, Macabacus refresh, vF copy, link break, PDF export
  WILL NOT: Custom UI design, visual redesign
  MANUAL (3 stops): Macabacus refresh (~1 min), link break (~30 sec), PDF export (~15 sec)
```

- [ ] **Step 3: Commit**

```bash
git add skills/deck-format/SKILL.md
git commit -m "feat: add optional Figma prompt generation step to deck-format"
```

### Task 9: Update deck-help with /deck-figma

**Files:**
- Modify: `skills/deck-help/SKILL.md`

- [ ] **Step 1: Add /deck-figma to the commands list**

Add after the /deck-new-template entry:

```
  /deck-figma [Company Name]
    Generate campaign text and points for Figma app screens.
    Paste a screenshot of the Figma layout - Claude outputs ready-to-paste text
    with campaign names, descriptions, and point values (200 pts/$1).
```

- [ ] **Step 2: Commit**

```bash
git add skills/deck-help/SKILL.md
git commit -m "docs: add /deck-figma to help reference"
```

---

## Chunk 6: Consolidate Gates and Bash Blocks

### Task 10: Consolidate Phase 1 bash blocks in deck-start

**Files:**
- Modify: `skills/deck-start/SKILL.md`

- [ ] **Step 1: Merge 8 mkdir commands into single bash block**

Replace the 8 separate `mkdir -p` lines (Step 1.1) with a single combined block:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
mkdir -p "$WS/$CLIENT_ROOT/[COMPANY_NAME]"/{1." Model","2. Presentations","3. Company Resources/1. Logos","3. Company Resources/2. Swag","4. Reports/1. Call Summaries","4. Reports/2. Public Filings","4. Reports/3. Slack","5. Call Transcripts"}
```

- [ ] **Step 2: Merge copy + set-title + open into fewer blocks**

Combine the copy (Step 1.3), set-title, and open commands into 2 blocks instead of 4:

Block 1 - copy and set titles:
```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
cp "[source .xlsx]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx"
cp "[source .pptx]" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx"
python3 "$WS/.claude/scripts/deck_engine.py" set-title \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" \
  --title "[COMPANY_NAME] Intro Model (YYYY.MM.DD)"
python3 "$WS/.claude/scripts/deck_engine.py" set-title \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx" \
  --title "[COMPANY_NAME] Intro Deck (YYYY.MM.DD)"
```

Block 2 - open both files:
```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[COMPANY_NAME] Intro Model (YYYY.MM.DD).xlsx" &
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/1. [COMPANY_NAME] Intro Deck (YYYY.MM.DD)/[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx"
```

- [ ] **Step 3: Commit**

```bash
git add skills/deck-start/SKILL.md
git commit -m "perf: consolidate sequential bash blocks in deck-start Phase 1"
```

### Task 11: Consolidate Phase 3 review gates in deck-model

**Files:**
- Modify: `skills/deck-model/SKILL.md`

- [ ] **Step 1: Replace 4 separate AskUserQuestion calls with single checklist**

Find the 4 individual review questions (Step 7/3.8 area) and replace with:

```markdown
### Model Review

Open the model. Present a single review checklist:

\```
MODEL REVIEW CHECKLIST:
  1. Inputs sheet - all column E cells filled?
  2. Campaigns - all selected campaigns have non-zero values?
  3. ROPS - all in 10x-30x range?
  4. Summary inputs - company name, revenue, unit count correct?
\```

Use AskUserQuestion:
- Question: "Model review - all 4 items above check out?"
- Options: ["All correct - save and continue", "Found issues - need to fix"]

If issues found, ask which item(s) failed and resolve. Then re-present the checklist.
After confirmed, ask user to save (Ctrl+S).
```

- [ ] **Step 2: Commit**

```bash
git add skills/deck-model/SKILL.md
git commit -m "perf: consolidate 4 model review gates into single checklist"
```

---

## Post-Implementation

After all tasks complete:

1. Verify skill line counts are reduced:
   - deck-start: ~665 -> ~330 lines (50% reduction)
   - deck-format: ~491 -> ~530 lines (slight increase from new steps, but less duplication)
   - deck-qa: ~245 -> ~200 lines (simplified)
   - All other skills: ~8-15 lines shorter each (removed hard rules)

2. Verify no remaining hard rules blocks (except in shared-preamble.md):
   ```bash
   grep -r "HARD RULES" skills/ --include="*.md" | grep -v shared-preamble
   ```
   Expected: no results.

3. Test the flow: `/deck-start [Company]` should invoke each phase skill in sequence without summarizing their content.
