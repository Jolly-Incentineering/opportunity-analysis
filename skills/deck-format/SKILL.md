---
name: deck-format
description: Format the PowerPoint intro deck -- populate text, update banners, apply brand colors, and export PDF.
---

You are executing the `deck-format` phase of the Jolly intro deck workflow. Follow every step exactly as written. Do not skip steps. Do not modify the deck without explicit user approval at each gate.

Set workspace root and client root:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
```

If `workspace_config.json` does not exist, tell the user: "Workspace is not configured. Run /deck-setup first." Then stop.

---

## Step 1: Load Session State and Research Output

Scan for the most recent session state file:

```bash
WS="${JOLLY_WORKSPACE:-.}"
ls "$WS/.claude/data/session_state_"*.md 2>/dev/null | sort | tail -1
```

Read the most recent file. Extract:
- `company_name`
- `client_root` (use this to override CLIENT_ROOT if present)
- `vertical`
- `branch`
- `phase_3_complete` -- whether Phase 3 (deck-model) has been marked complete
- Deck file path (from template paths)
- Model file path (from template paths)

If Phase 3 is not marked complete, tell the user:

```
Phase 3 is not complete. Run /deck-model first, then return to /deck-format.
```

Then stop.

Derive `company_slug` from company name: lowercase, spaces replaced with underscores, remove special characters.

Read the research output:

```bash
WS="${JOLLY_WORKSPACE:-.}"
cat "$WS/.claude/data/research_output_[company_slug].json"
```

Tell the user:

```
Resuming from [session date] -- company: [Company Name], vertical: [Vertical].
Starting Phase 4: Deck formatting.

Deck file: [deck filename]
```

---

## Step 2: Open Files

Open both the deck and the model (model is read-only reference):

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/2. Presentations/[deck filename]"
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/1. Model/[model filename]"
```

Tell the user: "Both files opened. Do not edit the deck yet -- I will walk you through each section."

---

## Step 3: Detect and Populate Banner Slides

Scan the deck for slides containing banner placeholder shapes. A shape is a banner if its text content matches any of these patterns (case-insensitive):
- `$[ ]`
- `[ ] quantified`
- `$[EBITDA]`
- `quantified Jolly`

For each banner shape found, report its slide number and current text.

Map each banner to the corresponding campaign output value from the model population data in `research_output_[company_slug].json`. Apply dollar formatting:
- Under $1M: `$XXXk` (lowercase k, no space, e.g. `$516k`)
- $1M and above: `$X.XXMM` (uppercase MM, no space, e.g. `$1.96MM`)

Present the banner replacement plan to the user before writing anything:

```
BANNER REPLACEMENT PLAN -- [COMPANY NAME]

Slide [N] | Shape: "[current text]" -> "$[value]" ([source campaign])
Slide [N] | Shape: "[current text]" -> "$[value]" ([source campaign])
...

Type "approve banners" to apply, or tell me what to change:
```

Wait for "approve banners" before writing. If the user requests changes, update and re-present.

Use `figma_editor.py` or `deck_format.py` to write banner values:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 "$WS/.claude/scripts/deck_format.py" \
  --company "[COMPANY_NAME]" \
  --step banners
```

---

## Step 5: Populate Text Placeholders

Scan all slides for text placeholders that contain template tokens (e.g., `[Company Name]`, `[Revenue]`, `[Unit Count]`, `[Year]`, `[Vertical]`).

For each placeholder found, map it to the correct value from `research_output_[company_slug].json`. Apply dollar formatting where applicable.

Present the text replacement plan to the user:

```
TEXT REPLACEMENT PLAN -- [COMPANY NAME]

Slide [N] | "[Company Name]" -> "[COMPANY_NAME]"
Slide [N] | "[Revenue]" -> "$X.XXMM"
Slide [N] | "[Unit Count]" -> "XXX locations"
...

Type "approve text" to apply, or tell me what to change:
```

Wait for "approve text" before writing.

---

## Step 6: Campaign Slides -- Manual Step Checklist

Campaign slide population requires the user to do manual formatting steps in the open deck. Walk through each step and wait for "done" before presenting the next.

```
Campaign slide checklist -- complete each step in the open deck, then type "done":

1. Navigate to the Campaign Summary slide. Confirm the approved campaigns ([list]) are shown and in the correct order.
   > [wait for "done"]

2. For each RECOMMENDED campaign (highlighted evidence from Gong/Attio):
   Add the verbatim quote or evidence callout to the speaker notes or evidence text box on that slide.
   > [wait for "done"]

3. For any campaigns in the EXCLUDE list, confirm their slides are hidden or removed from the deck.
   > [wait for "done"]

4. Check all campaign slide headlines. Replace any remaining "[Campaign Name]" tokens with the actual campaign name.
   > [wait for "done"]
```

---

## Step 7: Brand Assets -- Manual Step Checklist

```
Brand asset checklist -- complete each step, then type "done":

1. Navigate to the title slide. Confirm the company logo is placed correctly. If not, find the logo at:
   [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/3. Company Resources/Logos/
   and insert it.
   > [wait for "done"]

2. Check the color scheme. If the template colors do not match [COMPANY_NAME]'s brand colors (check brand_info.json in the Logos folder), update the theme colors manually.
   > [wait for "done"]

3. If swag images are available at [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/3. Company Resources/Swag/, insert the most relevant one on the swag/merchandise slide (if present).
   > [wait for "done"]

4. Open Figma and export the branded frames for [COMPANY_NAME]:
   - Open the Jolly Figma template file
   - Find the [COMPANY_NAME] brand frames (title slide background, section headers, etc.)
   - Export them as PNG or copy-paste directly into the appropriate slides in the open deck
   - Resize and position each frame to match the template layout
   - Save the deck (Ctrl+S)
   Type "skip" if no Figma frames are needed.
   > [wait for "done" or "skip"]
```

---

## Step 8: Final Visual Review -- Manual Step Checklist

```
Final visual review -- complete each step, then type "done":

1. Run Slide Show from the beginning (F5). Check that no template tokens ([...]) remain on any slide.
   > [wait for "done"]

2. Check all dollar values in the deck. Confirm formatting: under $1M = $XXXk, $1M+ = $X.XXMM.
   > [wait for "done"]

3. Check that ROPS values are not shown on prospect slides (Branch B). ROPS is internal only.
   > [wait for "done"]

4. Save the deck (Ctrl+S).
   > [wait for "done"]
```

---

## Step 9: Export PDF

Export the deck to PDF:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
python3 "$WS/.claude/scripts/deck_format.py" \
  --company "[COMPANY_NAME]" \
  --step export-pdf
```

If the script fails, tell the user: "Automated PDF export failed. Please export manually: File > Export > Create PDF/XPS. Save to: [WS]/[CLIENT_ROOT]/[COMPANY_NAME]/4. Reports/[COMPANY_NAME] Intro Deck [YYYY.MM.DD].pdf"

After the PDF is created, open it:

```bash
WS="${JOLLY_WORKSPACE:-.}"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
start "" "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/[COMPANY_NAME] Intro Deck [YYYY.MM.DD].pdf"
```

---

## Step 10: Cheat Sheet (Skipped)

The cheat sheet generation script is under development as of 2026-02-18. Skip this step and note it for the user.

Tell the user: "Cheat sheet generation skipped -- script under development. Will be available in a future update."

---

## Step 11: Update Session State

Write a new session state file at `$WS/.claude/data/session_state_[YYYY-MM-DD].md` (today's date). Include:
- Company name
- Client root
- Current phase: Phase 4 complete
- Phase 1, 2, 3, 4 marked complete; Phase 5 pending
- Deck filename and PDF path
- Next action: "Run /deck-qa"

---

## Step 12: Hand Off

Tell the user:

```
Deck formatting complete for [COMPANY NAME].

Deck file: [deck filename]
PDF exported: [PDF filename]
Cheat sheet: skipped (script under development)

Session state saved. Next: run /deck-qa for final quality check before delivery.
```
