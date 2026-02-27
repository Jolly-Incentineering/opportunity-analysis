---
name: deck-format
description: Format the PowerPoint intro deck -- populate text, update banners, apply brand colors, and export PDF.
---

HARD RULES — NEVER VIOLATE:
1. Do NOT generate or invent campaign names. Read them from the template config JSON.
2. Do NOT make tool calls or add steps not listed in these instructions.
3. Do NOT write to formula cells under any circumstances.
4. Do NOT skip gates — wait for user confirmation at every gate.
5. Do NOT open files you are about to write to programmatically. Keep them closed during writes.
6. Do NOT proceed past a failed step — stop and report. Do NOT retry more than once.
7. Keep all client-specific data in the client folder under 4. Reports/. Never write client data to .claude/data/.
8. All Attio, Slack, and other MCP tools are READ-ONLY. Never use create, update, or delete MCP actions.

---

You are executing the `deck-format` phase of the Jolly intro deck workflow. Follow every step exactly as written. Do not skip steps. Do not modify the deck without explicit user approval at each gate.

Set workspace root and client root:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
```

If `workspace_config.json` does not exist, tell the user: "Workspace is not configured. Run /deck-setup first." Then stop.

---

## Step 1: Load Session State and Research Output

Scan for the most recent session state file:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
ls "$WS/.claude/data/session_state_"*.md 2>/dev/null | sort | tail -1
```

Read the most recent file. Extract:
- `company_name`
- `client_root` (use this to override CLIENT_ROOT if present)
- `vertical`
- `branch`
- `context` -- "pre_call" or "post_call"
- `deck_folder` -- path to the Presentations subfolder
- `deck_filename` -- the working deck filename
- `vf_deck_filename` -- the vF delivery copy filename
- `pdf_filename` -- the PDF filename
- `phase_3_complete` -- whether Phase 3 (deck-model) has been marked complete
- Model file path (from template paths)

If Phase 3 is not marked complete, tell the user:

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
Resuming from [session date] -- company: [Company Name], vertical: [Vertical].
Starting Phase 4: Deck formatting.

Gates this phase:
  □ Placeholder writes approved (C/D/E items)
  □ Campaign slides checked
  □ Logo placed
  □ Macabacus refresh complete
  □ vF links broken
  □ Final visual review passed
  □ PDF exported
  □ PDF reviewed

Deck file: [deck filename]
```

After each gate is confirmed, echo "[Gate name] ✓" in your reply before proceeding.

Phase 4 scope:
```
  WILL DO: Banner fill, text replacement, brand assets, Macabacus refresh, vF copy, link break, PDF export
  WILL NOT: Custom UI design, app mockups, visual redesign
  MANUAL: Macabacus refresh (~1 min), brand frames (optional), link break (~30 sec)
  PDF: Manual export via PowerPoint UI (~15 sec)
```

---

## Step 2: Ensure Files Are Closed

```
PHASE 4 FILE MANAGEMENT:
1. Close ALL Excel and PowerPoint files now — I need them closed for automated steps.
2. I'll tell you when to open each file and when to close it.
3. Each file opens exactly once.
```

Sequence: Automated banner scan + write (files closed) → open master + model → brand + refresh → close master → vF copy (auto) → open vF → break links → close vF → open PDF

Use AskUserQuestion:
- Question: "Are all Excel and PowerPoint files closed?"
- Options: ["Yes, all closed", "Not yet — give me a moment"]

If "Not yet", wait for the user and re-ask. Proceed only after confirmation.

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
Slides with `Suggested Jolly Campaign: [ ]` or empty campaign description text boxes. Map each to the matching campaign from the approved list in `research_output`. For each:
- Campaign name
- 1-2 sentence description tailored to THIS company's vertical and context
- Key metric (e.g., "$1.5MM EBITDA uplift, 18x ROPS")

**D. NARRATIVE TEXT TO REWRITE (write in this step)**
Any paragraph that references the wrong vertical (e.g., QSR language like "beverages and food offerings" for a distribution company). Propose a rewrite using the correct vertical language and the company's actual business context from research.

**E. SIMPLE TOKEN REPLACEMENTS (write in this step)**
Non-linked tokens like `[Year]`, `[Vertical]`, or other template fill-ins. Map to correct values.

**F. RAW DOLLAR AMOUNTS (deferred — reformatted by deck_engine.py in Step 7d)**
Dollar values like `$760,000` that need `$760k` or `$1.5MM` formatting. Show them so the user knows they will be fixed, but do NOT reformat here.

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

C. CAMPAIGN DESCRIPTIONS (will write now):
  Slide [N] | "Suggested Jolly Campaign: [ ]" -> "Visit Order Amounts — Increase average order
              value through targeted visit incentives. $1,480K EBITDA uplift, 22x ROPS."
  Slide [N] | "Suggested Jolly Campaign: [ ]" -> "On-Time Training — Drive completion rates
              for mandatory training modules. $1,160K EBITDA uplift, 19x ROPS."
  Slide [N] | "Suggested Jolly Campaign: [ ]" -> "Employee Referrals — Reduce hiring costs
              through referral bonuses. $1,013K EBITDA uplift, 15x ROPS."
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

SUMMARY: [N] items to write now (C + D + E) | [N] deferred to Step 7d (B + F) | [N] skipped (A)

SUMMARY: [N] items to write now (C + D + E) | [N] deferred to Step 7d (B + F) | [N] skipped (A)
```

Use AskUserQuestion:
- Question: "Approve writing C/D/E placeholder items to the deck?"
- Options: ["Approve — write all", "I need to make changes first"]

If changes requested, update the plan and re-present. Only write items in categories C, D, and E after approval. Categories A, B, and F are handled later in the workflow.

---

## Step 5: Campaign Slides -- Manual Step Checklist

Campaign slide population requires the user to do manual formatting steps in the open deck.

Present the instructions, then use AskUserQuestion with 3 questions:
1. "Campaign Summary slide — approved campaigns ([list]) shown in correct order?" — Options: ["Done", "Needs adjustment"]
2. "Evidence callouts added to speaker notes for RECOMMENDED campaigns?" — Options: ["Done", "Not applicable"]
3. "EXCLUDED campaign slides hidden or removed?" — Options: ["Done", "Not applicable"]

If any answer is "Needs adjustment", help the user resolve before continuing.

---

## Step 6: Brand Assets and Inbox Feed

### Step 6a: Logo Check

Tell the user to check the title slide for the company logo. If missing, it should be at:
`[WS]/[CLIENT_ROOT]/[COMPANY_NAME]/3. Company Resources/1. Logos/`

Use AskUserQuestion:
- Question: "Company logo placed correctly on the title slide?"
- Options: ["Done — logo looks good", "No logo found — need help"]

If "No logo found", help the user locate or download the logo before continuing.

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

# 1. Fill banners from research data
python3 "$WS/.claude/scripts/deck_engine.py" fill-banners --file "$VF" --research "$RESEARCH"

# 2. Reformat raw dollar amounts
python3 "$WS/.claude/scripts/deck_engine.py" format-dollars --file "$VF"

# 3. Verify no placeholders remain
python3 "$WS/.claude/scripts/deck_engine.py" find-placeholders --file "$VF"
```

If find-placeholders returns any results, report them to the user before continuing.

Tell the user:

```
vF formatted — banners filled, dollars reformatted.

Master deck retains live Macabacus links for future refreshes.
Do not edit the vF directly — make changes in the master, re-run Steps 7a–7d.
```

---

## Step 8: Final Visual Review -- Manual Step Checklist

Tell the user to review the open vF deck, then use AskUserQuestion with 3 questions:
1. "Slide show check (F5) — any template tokens [...] remaining?" — Options: ["All clear", "Found tokens — need fix"]
2. "Dollar formatting correct? ($X.XMM for $1M+, $XXXk for $1K–$999K)" — Options: ["Looks good", "Found formatting issues"]
3. "vF deck saved (Ctrl+S)?" — Options: ["Saved", "Not yet"]

If any issues found, help the user resolve before continuing.

---

## Step 9: Export PDF -- Manual Step

Tell the user:

```
Export PDF manually:
1. Open the vF in PowerPoint: [deck_folder]/[vf_deck_filename]
2. File → Export → Create PDF/XPS
3. Save to: [deck_folder]/[pdf_filename]
Takes ~15 seconds.
```

Use AskUserQuestion:
- Question: "PDF exported to the correct location?"
- Options: ["Done — PDF exported", "Need help exporting"]

If "Need help", troubleshoot before continuing. Then set the PDF title and open it:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
python3 "$WS/.claude/scripts/deck_engine.py" set-pdf-title \
  --file "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[pdf_filename]" \
  --from-pptx "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[vf_deck_filename]"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/[deck_folder]/[pdf_filename]"
```

Tell the user to review the PDF, then use AskUserQuestion:
- Question: "PDF review — pages correct, no blank slides, banner values readable?"
- Options: ["Looks good — proceed", "Found issues — need to re-export"]

If issues found, help the user fix and re-export before continuing to Step 10.

---

## Step 10: Generate Cheat Sheets

Run the cheat sheet generator for this company:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
cd "$WS" && python3 ".claude/scripts/cheatsheet_gen.py" --company "[COMPANY_NAME]"
```

This produces a single combined PDF in `$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/Cheat Sheets/`:
- `[COMPANY_NAME] Cheat Sheet.pdf` — company profile, meeting intelligence, and campaign breakdowns

If the script fails (missing packages or no research data), tell the user:

```
Cheat sheet generation failed: [error].
Install renderer: pip install weasyprint
Or run manually: python3 .claude/scripts/cheatsheet_gen.py --company "[COMPANY_NAME]"
```

Do not stop the workflow if this step fails — continue to Step 11.

---

## Step 11: Update Session State

Write a new session state file at `$WS/.claude/data/session_state_[company_slug]_[YYYY-MM-DD].md` (today's date). Include:
- Company name
- Client root
- Current phase: Phase 4 complete
- Phase 1, 2, 3, 4 marked complete; Phase 5 pending
- Master deck path: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx` (retains live Macabacus links)
- vF deck path: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx` (delivery copy, links broken)
- PDF path: `[COMPANY_NAME] Intro Deck (YYYY.MM.DD).pdf`
- Cheat sheet path: `4. Reports/Cheat Sheets/[COMPANY_NAME] Cheat Sheet.pdf`
- Next action: "Run /deck-qa"

---

## Step 12: Hand Off

Tell the user:

```
Deck formatting complete for [COMPANY NAME].

Working deck:  [COMPANY_NAME] Intro Deck (YYYY.MM.DD).pptx  (master, retains live Macabacus links)
vF (delivery): [COMPANY_NAME] Intro Deck (YYYY.MM.DD) - vF.pptx  (static delivery copy)
PDF:           [COMPANY_NAME] Intro Deck (YYYY.MM.DD).pdf
Cheat sheet:   4. Reports/Cheat Sheets/[COMPANY_NAME] Cheat Sheet.pdf

Session state saved. Next: run /deck-qa for final quality check before delivery.
```
