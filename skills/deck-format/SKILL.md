---
name: deck-format
description: Format the PowerPoint intro deck -- populate text, update banners, apply brand colors, and export PDF.
disable-model-invocation: true
---

Read and follow all rules in skills/shared-preamble.md before proceeding.

---

The Executive Audience Rule (see shared-preamble.md) applies to ALL text written in Steps 4C, 4D, 4E, and 4G.

---

You are executing the `deck-format` phase of the Jolly intro deck workflow. Follow every step exactly as written. Do not skip steps. Only stop at gates marked with AskUserQuestion - do not add extra confirmation prompts.

Set workspace root using the bash preamble from shared-preamble.md.

If `workspace_config.json` does not exist, tell the user: "Workspace is not configured. Run /deck-setup first." Then stop.

---

## Step 1: Load Session State and Research Output

Load the most recent session state file:

Load session state using the standard loader from shared-preamble.md.

Extract all printed fields. If `phase_3_status != 'complete'`, tell the user:

```
Phase 3 is not complete. Run /deck-model first, then return to /deck-format.
```

Then stop.

Derive `company_slug` from company name: lowercase, spaces replaced with underscores, remove special characters.

Read the research output:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research_output_[company_slug].json"
```

Tell the user:

```
Resuming from [session_date] -- company: [Company Name], vertical: [Vertical].
Starting Phase 4: Deck formatting.

Gates this phase:
  □ Placeholder writes approved (C/D/E/G items)
  □ Pre-vF QA passed
  □ Macabacus refresh complete
  □ vF links broken
  □ vF saved + PDF exported

Deck file: [deck filename]
```

After each gate is confirmed, echo "[Gate name] ✓" in your reply before proceeding.

Phase 4 scope:
```
  WILL DO: Banner fill, text replacement, systems of record, Figma app text, pre-vF QA, Macabacus refresh, vF copy, link break, PDF export
  WILL NOT: Custom UI design, visual redesign
  MANUAL (3 stops): Macabacus refresh (~1 min), link break (~30 sec), PDF export (~15 sec)
```

---

## Step 2: Ensure Files Are Closed

Tell the user:

```
Close all Excel and PowerPoint files — I need them closed for automated steps.
I'll tell you when to open each file.
```

Pause 3 seconds, then proceed. Do not ask for confirmation.

---

## Step 3: Scan Banner Slides (Read-Only)

Scan the deck for slides containing banner placeholder shapes. A shape is a banner if its text contains any bracket-placeholder pattern — i.e. any text matching the regex `\[.*?\]` (square brackets with any content, including empty). Common examples:
- `$[ ]`, `[ ]`, `$[EBITDA]`, `[ ] quantified`, `quantified Jolly`
- Any other `[...]` token that hasn't been replaced with a real value

For each banner shape found, report its slide number and current text.

**Do NOT fill banners here.** Banner values will be written in Step 8d on the vF copy (after Macabacus refresh, vF copy, and link break). This step is scan-only so we know what the formatter will need to fix.

Tell the user:

```
BANNER SCAN -- [COMPANY NAME]

Slide [N] | "[current text]" (placeholder — will be filled on vF)
...

Banners will be populated in the vF formatting step (Step 8d).
```

---

## Step 3a: Open Files for Manual Review

Banner scan is complete. Now open both files for the manual steps that follow:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[deck_filename]"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
```

Tell the user: "Both files opened. Do not edit the deck yet -- I will walk you through each section."

---

## Step 3b: Context Branch

Check the `context` from session state:

**IF `context == "pre_call"`:**

Tell the user:

```
Pre-call deck — Macabacus pulls all numbers from the model automatically.
Quick deck template works for all contexts. Streamlined workflow.

Next steps:
  1. Brand Assets review
  2. Final Visual Review
  3. Macabacus refresh + vF copy + link break + PDF export
```

Continue to Step 6 (Brand Assets).

**IF `context == "post_call"`:**

Continue to Step 4 normally (full flow including campaign slides).

---

## Step 4: Full Placeholder Audit

Run a comprehensive scan of ALL slides for any text matching the bracket pattern `\[.*?\]` (including empty `[ ]`). Also flag raw dollar amounts (`$X,XXX` or larger without k/MM formatting) and narrative text that references a different vertical than this company's.

Read campaign details and banner values from:
```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research_output_[company_slug].json"
```

Categorize every finding into one of 5 buckets:

**A. MACABACUS-LINKED (skip — filled on refresh in Step 7a)**
Any text run with red font color (RGB `FF0000`) is a live Macabacus link. Also skip company name, revenue, store count, employee count, and other values linked from the Excel model. Do NOT propose replacing these.

**B. BANNER PLACEHOLDERS (deferred — filled by deck_engine.py in Step 7d)**
Banner shapes containing `$[ ]`, `[ ]`, or `$[...]MM` patterns. These are filled programmatically from `research_output` after Macabacus refresh + link break. Show the proposed fill values now so the user can verify, but do NOT write them here.

**C. CAMPAIGN DESCRIPTION PLACEHOLDERS (write in this step)**
Slides with `Suggested Jolly Campaign: [ ]` or empty campaign description text boxes. Map each to the matching campaign from the approved list in `research_output`. For each, write two bullets:
- **Bullet 1 - Campaign mechanism:** Campaign name + 1 sentence selling the value to a CEO/CFO (what it rewards, how it drives EBITDA). Write as a pitch, not a label.
- **Bullet 2 - Company-specific impact:** 1 sentence with hard numbers from research_output showing why this matters at THIS company's scale (e.g., turnover rate, dollar figures, utilization %). End with the key metric (EBITDA uplift + ROPS).

**Apply the Executive Audience Rule** to every bullet. No references to calls, research steps, data sources, hedging, or automation. Present numbers as confident facts.

**D. NARRATIVE TEXT TO REWRITE (write in this step)**
Any paragraph that references the wrong vertical (e.g., QSR language like "beverages and food offerings" for a distribution company). Propose a rewrite using the correct vertical language and the company's actual business context from research. **Apply the Executive Audience Rule** - no internal process language, hedging, or source references.

**E. SIMPLE TOKEN REPLACEMENTS (write in this step)**
Non-linked tokens like `[Year]`, `[Vertical]`, or other template fill-ins. Map to correct values.

**F. RAW DOLLAR AMOUNTS (deferred — reformatted by deck_engine.py in Step 7d)**
Dollar values like `$760,000` that need `$760k` or `$1.5MM` formatting. Show them so the user knows they will be fixed, but do NOT reformat here.

**G. "YOU CAN REWARD ANY TRACKABLE DATA" SLIDE (write in this step)**
Find the slide titled "You Can Reward Any Trackable Data" (or similar). Check `research_output.systems_of_record` for named systems with logos. Also read `system_slot_defaults` from the template config JSON (in `data/templates/`) matched during deck-start.

The slide has placeholder slots for system categories. Fill them using this priority:
1. **Logo match:** If a system in `systems_of_record` has `logo_found: true`, replace the slot with the system's logo from `3. Company Resources/3. Systems of Record/`. Insert as a picture shape sized to fit the existing layout.
2. **Text match:** If a system was found but its logo failed (`logo_found: false`), replace the slot text with the actual system name (e.g., "Workday", "Toast").
3. **Industry default:** If no system was found for a slot, use the label from `system_slot_defaults` in the template config (ranked by importance). These are industry-appropriate fallback labels (e.g., "EHR" for healthcare instead of "POS").
4. **No config fallback:** If no template config or `system_slot_defaults` is available, keep the existing generic labels on the slide as-is.

Fill up to 5 slots. Match found systems to the most relevant slot by category before falling back to defaults for remaining slots.

Present the full audit to the user:

```
PLACEHOLDER AUDIT -- [COMPANY NAME]

A. MACABACUS-LINKED (auto-filled on refresh, skipping):
  Slide [N] | "[Company Name]" -- live link
  Slide [N] | "$[Revenue]" -- live link
  ...

B. BANNERS (filled in Step 7d):
  Slide [N] | "[ ]" -> "$5.3MM"         (Grand Total EBITDA)
  Slide [N] | "[ ]" -> "6 quantified"   (campaign count)
  Slide [N] | "$[ ]MM of EBITDA..." -> "$5.3MM of EBITDA...6 quantified"
  ...

C. CAMPAIGN DESCRIPTIONS (will write now — two bullets each):
  Slide [N] | "Suggested Jolly Campaign: [ ]" ->
    - "Visit Order Amounts — Reward crew for upselling higher-value orders, driving incremental revenue per visit."
    - "With 880 stores averaging $12.50 tickets, a 3% uplift recovers $1,480k EBITDA. 22x ROPS."
  Slide [N] | "Suggested Jolly Campaign: [ ]" ->
    - "On-Time Training — Incentivize completion of mandatory training modules, reducing compliance gaps."
    - "At 22% annual turnover and 14,000 employees, faster onboarding saves $1,160k EBITDA. 19x ROPS."
  ...

D. NARRATIVE REWRITES (will write now):
  Slide [N] | Current: "visiting on slow days fills seats" (QSR language)
             -> Proposed: "[company-specific distribution language]"
  Slide [N] | Current: "beverages and food offerings" (QSR language)
             -> Proposed: "[correct vertical language]"
  ...

E. TOKEN REPLACEMENTS (will write now):
  Slide [N] | "[Year]" -> "2026"
  ...

F. RAW DOLLARS (reformatted in Step 7d):
  Slide [N] | "$760,000" -> "$760k" (auto)
  Slide [N] | "$1,500,000" -> "$1.5MM" (auto)
  ...

G. SYSTEMS OF RECORD (will write now):
  Slide [N] | "You Can Reward Any Trackable Data"
    Template config: [config name] | Industry defaults: [slot1], [slot2], [slot3], [slot4], [slot5]
    Systems found: Salesforce (logo), Workday (logo), ADP (text only)
    Slot 1: Salesforce logo (found) | Slot 2: Workday logo (found) | Slot 3: ADP text (found) | Slot 4: [default label] | Slot 5: [default label]
  [OR]
    No systems identified - using industry defaults from template config: [slot1], [slot2], [slot3], [slot4], [slot5]
  [OR]
    No systems identified, no template config - keeping generic labels.

SUMMARY: [N] items to write now (C + D + E + G) | [N] deferred to Step 7d (B + F) | [N] skipped (A)
```

Use AskUserQuestion:
- Question: "Approve writing C/D/E/G placeholder items to the deck?"
- Options: ["Approve — write all", "I need to make changes first"]

If changes requested, update the plan and re-present. Only write items in categories C, D, E, and G after approval. Categories A, B, and F are handled later in the workflow.

---

## Step 5: Brand Assets

Tell the user to handle campaign slides and logo while the deck is open:

```
While the deck is open, check:
  - Campaign Summary slide: approved campaigns in correct order
  - Excluded campaigns: hidden or removed
  - Title slide: company logo placed (logos at [CLIENT_ROOT]/[COMPANY_NAME]/3. Company Resources/1. Logos/)
```

Do not gate on this - QA (D4/D5) will catch any misses. Proceed immediately.

---

## Step 5a: Figma App Screen Text (Optional)

If the deck includes app mockup screens in Figma, offer to generate the text now while campaign data is fresh.

Tell the user:

```
If you have Figma app screens to fill (inbox feed, campaign details, rewards summary):
  - Paste a screenshot of the Figma layout and I'll generate campaign text + points.
  - Or type "skip" to continue without Figma text.
```

Use AskUserQuestion:
- Question: "Generate Figma app screen text?"
- Options: ["Yes - let me paste a screenshot", "Skip - no Figma screens needed"]

If "Yes": invoke the `/deck-figma` skill. When the user is done generating text for all screens, continue to Step 6.

If "Skip": continue to Step 6.

---

## Step 6: Pre-vF Quality Check (Automated)

Before creating the vF, run automated QA on the master deck to catch issues early. The user should close the master deck for this check.

Tell the user:

```
Running pre-vF quality check on the master deck.
Close the master deck (Ctrl+S first), then tell me when it's closed.
```

Use AskUserQuestion:
- Question: "Master deck saved and closed?"
- Options: ["Closed", "Give me a moment"]

Then run:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 "$WS/.claude/scripts/qa_check.py" --company "[COMPANY_NAME]"
```

Only report deck-related results (D1, D2, D2b, D2c, D7). Ignore model checks here since the model was already verified in Phase 3.

**If any deck checks FAIL:**

```
PRE-VF CHECK FAILED:
  [list each failure with slide number and description]

Fix these in the master deck before proceeding.
After fixing, save, close, and tell me to re-run the check.
```

Loop: re-run qa_check.py after each fix round until all deck checks pass.

**If all deck checks PASS:**

```
Pre-vF check passed. Master deck is clean - proceeding to Macabacus refresh.
```

Continue to Step 7a.

---

## Step 7a: Refresh Macabacus on Master -- Manual Step

Refresh all live Macabacus links in the master deck so values are current before creating the delivery copy.

Tell the user:

```
Macabacus refresh — complete these steps in the master deck:

1. Click the Macabacus tab in the PowerPoint ribbon
2. Click Refresh All (or Refresh)
3. Wait for all slides to update — values should pull in from the populated model
4. Confirm the key banner numbers look correct at a glance
5. Save the master deck (Ctrl+S)
6. Close the master deck

The master will keep its live Macabacus links. Do NOT break links here.
The master must be saved and closed before the vF copy is created.
```

Use AskUserQuestion:
- Question: "Macabacus refresh complete? (Refreshed, checked values, saved, and closed master)"
- Options: ["Ready — master saved and closed", "Need help with Macabacus"]

If "Need help", troubleshoot before continuing.

---

## Step 7b: Create vF Copy -- Automated

Tell the user: "Creating vF delivery copy from refreshed master..."

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
python3 "$WS/.claude/scripts/deck_engine.py" copy-vf \
  --src "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[deck_filename]" \
  --dest "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[vf_deck_filename]"
```

Record the vF file path:
- vF file: `$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[vf_deck_filename]`

Tell the user:

```
vF copy created: [vf_deck_filename]
The master deck retains all live Macabacus links — do not modify it.
```

---

## Step 7c: Break Links in vF -- Manual Step

The delivery copy (vF) must have all Macabacus links converted to static values. Break links in the vF only — never in the master.

Open the vF for the user:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[vf_deck_filename]"
```

Tell the user:

```
Break Macabacus links in the vF — complete these steps:

1. Click the Macabacus tab in the PowerPoint ribbon
2. Click Break Links → confirm the dialog
3. Spot-check 2-3 slides with Macabacus-linked values — numbers should match the master
   (Banner placeholders like $[ ] are expected — they will be filled in the next step)
4. Save the vF (Ctrl+S)
5. Close the vF

Do NOT break links in the master deck. The master always retains live links.
```

Use AskUserQuestion:
- Question: "Links broken in vF? (Broke links, spot-checked values, saved, and closed vF)"
- Options: ["Ready — vF saved and closed", "Values don't match — need help"]

If values don't match, troubleshoot before continuing.

---

## Step 7d: Format vF Deck -- Automated

Fill banners and reformat dollars on the vF for delivery. This is the primary banner fill — banners were intentionally left as placeholders on the master so Macabacus refresh and link break happen first. The vF must be closed for this step.

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
VF="$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[vf_deck_filename]"
RESEARCH="$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research_output_[company_slug].json"

# Single pass: fill banners + reformat dollars + verify placeholders
python3 "$WS/.claude/scripts/deck_engine.py" format-all --file "$VF" --research "$RESEARCH"
```

The output JSON includes `remaining_placeholders`. If any are listed, report them to the user before continuing.

Tell the user:

```
vF formatted — banners filled, dollars reformatted.

Master deck retains live Macabacus links for future refreshes.
Do not edit the vF directly — make changes in the master, re-run Steps 7a–7d.
```

---

## Step 8: Save vF and Export PDF

Tell the user:

```
Save the vF (Ctrl+S), then export PDF:
  File → Export → Create PDF/XPS → save to [deck_folder]/[pdf_filename]

QA will catch any remaining tokens, formatting issues, or mismatches.
```

Use AskUserQuestion:
- Question: "vF saved and PDF exported?"
- Options: ["Done", "Need help"]

If "Need help", troubleshoot before continuing. Then set the PDF title and open both files:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
python3 "$WS/.claude/scripts/deck_engine.py" set-pdf-title \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[pdf_filename]" \
  --from-pptx "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[vf_deck_filename]"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[pdf_filename]"
```

---

## Step 10: Update Session State

Run:

```python
python3 -c "
import json, glob, os
from datetime import date
ws = os.environ.get('JOLLY_WORKSPACE', '.')
files = sorted(glob.glob(f'{ws}/.claude/data/session_state_*.json'))
if not files: raise SystemExit('No session state found — cannot update')
path = files[-1]
data = json.load(open(path, encoding='utf-8'))
data['phase_checklist']['phase_4_deck_formatting'] = 'complete'
data['next_action'] = '/deck-qa'
data['last_updated'] = date.today().isoformat()
with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
print('Updated:', path)
"
```

---

## Step 12: Hand Off

Tell the user:

```
Deck formatting complete for [COMPANY NAME].

Working deck:  [COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx  (master, retains live Macabacus links)
vF (delivery): [COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx  (static delivery copy)
PDF:           [COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pdf

Session state saved. Next: run /deck-qa for final quality check before delivery.
```
