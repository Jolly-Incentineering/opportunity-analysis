---
name: deck-new-template
description: Create a new vertical template (Excel model + PowerPoint deck + JSON config) by adapting an existing template.
---

HARD RULES - NEVER VIOLATE:
1. Do NOT generate or invent campaign names. Ask the user for campaign names.
2. Do NOT make tool calls not listed in these instructions.
3. Do NOT write to formula cells under any circumstances.
4. Do NOT skip gates - wait for user confirmation at every gate.
5. Do NOT open files you are about to write to programmatically. Keep them closed during writes.
6. Do NOT add features, steps, or checks not specified here.
7. Do NOT proceed past a failed step - stop and report the failure.
8. If a tool call fails, report the error. Do NOT retry more than once.
9. Keep all client-specific data in the client folder under 4. Reports/. Never write client data to .claude/data/.
10. Use HAIKU for research agents unless explicitly told otherwise.

---

You are creating a new vertical template for the Jolly intro deck workflow. This skill produces three outputs: an Excel model template, a PowerPoint deck template, and a JSON config file. All three are required for the vertical to work with the plugin.

This skill can be invoked directly via `/deck-new-template [VERTICAL_NAME]` or triggered from `/deck-start` when no matching template exists.

Set workspace root:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
TEMPLATES_ROOT=$(python3 -c "import json; c=json.load(open('$WS/.claude/data/workspace_config.json')); print(c.get('templates_root', 'Templates'))" 2>/dev/null || echo "Templates")
```

---

## Step 1: Gather Vertical Information

Ask the user:

```
New vertical template: [VERTICAL_NAME]

I need a few things to build this template. Answer each question:

1. What industry does this vertical serve?
   (e.g., "Food supply chain logistics", "SaaS / tech services", "Healthcare staffing")

2. What are the campaign names? List 3-8 campaigns that make sense for this vertical.
   Each campaign should be an incentivizable employee behavior.
   Example (QSR): Beverage Upsell, Food Upsell, Employee Referrals, Employee Timeliness
   Example (Retail): Member Sign-Ups, Employee Referrals, Timeliness & Attendance, Inventory Accuracy, Employee Retention

3. What company basics are relevant? Default is:
   - Company Name, Annual Revenue, Unit/Location Count, Employee Count
   Add any vertical-specific fields (e.g., "Units Produced Per Day", "Working Days Per Year", "Members Per Store").

4. What are the key economics inputs per campaign?
   For each campaign, what 2-4 assumption rows drive the ROPS calculation?
   Example (Upsell): Sales Uplift %, Contribution Margin %
   Example (Referrals): Turnover Rate, Referral Success Rate, Traditional Hiring Cost
   Example (Timeliness): Hours Lost to Tardiness %, Campaign Reduction %, EBITDA per Hour Saved

5. Which existing template is closest to what you need?
```

Then list all available templates:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
TEMPLATES_ROOT=$(python3 -c "import json; c=json.load(open('$WS/.claude/data/workspace_config.json')); print(c.get('templates_root', 'Templates'))" 2>/dev/null || echo "Templates")
find "$WS/$TEMPLATES_ROOT" -type f -name "*.xlsx" | sort
```

```
   Available base templates:
   1. QSR (8 campaigns: upsell, referrals, timeliness, retention, compliance)
   2. Manufacturing (10 campaigns: returns, efficiency, referrals, timeliness, defects, retention, cross-training, safety, suggestions, downtime)
   3. Retail (5 campaigns: sign-ups, referrals, timeliness, inventory, retention)
   4. Other -- I'll start from scratch

   Reply with the number of the closest match, plus your answers to questions 1-4.
```

Wait for the user's full reply. Record:
- `vertical_name` (from argument or user input)
- `vertical_slug` (lowercase, underscores, no special chars)
- `industry_description`
- `campaign_names` (list)
- `company_basics` (list of field names)
- `campaign_economics` (dict: campaign name -> list of assumption row labels)
- `base_template` (which existing template to adapt)

---

## Step 2: Gather Vertical Standards

Ask the user:

```
Vertical standards for [VERTICAL_NAME]:

These values control guardrails and validation. Defaults shown in brackets.

1. Hours per employee per year?  [2080 for office/manufacturing, 1820 for hourly/retail]
2. Hiring cost cap?              [null = no cap, or a dollar amount like 3500]
3. Incentive cost range?         [low, high] per event (e.g., [0.25, 0.50] for QSR, [0.01, 0.10] for manufacturing)
4. Customer/product return rate range?  [low%, high%] (e.g., [5, 15] for consumer, [0.1, 0.5] for B2B)
5. TRIR divisor?                 [null for most, 100 for manufacturing safety]

Reply with values, or "defaults" to use [2080, null, [0.25, 1.00], [1, 10], null].
```

Wait for reply. Record all values.

---

## Step 3: Create the Template Folder

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
TEMPLATES_ROOT=$(python3 -c "import json; c=json.load(open('$WS/.claude/data/workspace_config.json')); print(c.get('templates_root', 'Templates'))" 2>/dev/null || echo "Templates")
mkdir -p "$WS/$TEMPLATES_ROOT/[Vertical Name]"
```

---

## Step 4: Copy and Adapt the Excel Model

Copy the base template:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
TEMPLATES_ROOT=$(python3 -c "import json; c=json.load(open('$WS/.claude/data/workspace_config.json')); print(c.get('templates_root', 'Templates'))" 2>/dev/null || echo "Templates")
cp "[base template .xlsx path]" "$WS/$TEMPLATES_ROOT/[Vertical Name]/[Vertical Name] Intro Template.xlsx"
```

Now modify the Excel template using openpyxl. The model must have exactly this structure:

**Inputs sheet (required):**
- Row 2: "Inputs" header
- Row 4: "COMPANY BASICS" section header
- Rows 5+: Company basics fields (Company Name, Annual Revenue, etc.)
- Row after basics: "CAMPAIGN SETTINGS" section header
- Campaign setting rows: one row per campaign, columns C/D/E for ON/OFF toggles or descriptions
- Row after settings: "SCENARIO ASSUMPTIONS" section header
- For each campaign: header row + 2-4 assumption rows, each with columns C (Base), D (Upside), E (Downside)

**Campaigns sheet (required):**
- Formula-driven sheet that calculates savings, costs, and ROPS per campaign
- Do NOT modify formulas - only structure (add/remove campaign blocks as needed)
- Each campaign block: ~15-20 rows of formulas referencing the Inputs sheet

**Sensitivities sheet (required):**
- Summary of all campaigns with Base/Upside/Downside totals
- Formula-driven - do NOT modify formulas

Present the modification plan to the user before making any changes:

```
EXCEL TEMPLATE PLAN for [VERTICAL NAME]

Base: [base template name]

COMPANY BASICS (Inputs sheet):
  Row 5: Company Name
  Row 6: [field 2]
  Row 7: [field 3]
  ...

CAMPAIGNS ([N] total):
  Campaign 1: [name] -- assumptions: [list]
  Campaign 2: [name] -- assumptions: [list]
  ...

CHANGES FROM BASE:
  - [Renamed/Added/Removed] field X
  - [Renamed/Added/Removed] campaign Y
  - ...

Type "approve" to create the template, or tell me what to change:
```

Wait for "approve".

After approval, make the modifications:
- Rename campaign labels in column B to match the new campaign names
- Rename company basics labels to match the new field names
- Rename scenario assumption headers and row labels
- Update any campaign-specific economics labels
- Do NOT touch formula cells - only text labels and section headers
- Set all assumption values to 0 or reasonable defaults for the vertical

After writing, close the file.

---

## Step 5: Copy and Adapt the PowerPoint Deck

Copy the base template deck:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
TEMPLATES_ROOT=$(python3 -c "import json; c=json.load(open('$WS/.claude/data/workspace_config.json')); print(c.get('templates_root', 'Templates'))" 2>/dev/null || echo "Templates")
cp "[base template .pptx path]" "$WS/$TEMPLATES_ROOT/[Vertical Name]/[Vertical Name] Intro Template.pptx"
```

The PowerPoint template contains Macabacus-linked slides. Campaign slide titles and summary slide campaign names need to match the Excel model.

Using python-pptx, scan for campaign name references on each slide and rename them:

```python
from pptx import Presentation
import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pptx_path = os.path.abspath("[path to new .pptx]")
prs = Presentation(pptx_path)

# Map old campaign names to new campaign names
rename_map = {
    "[Old Campaign 1 Name]": "[New Campaign 1 Name]",
    "[Old Campaign 2 Name]": "[New Campaign 2 Name]",
    # ... one entry per campaign
}

changes = []
for slide_num, slide in enumerate(prs.slides, 1):
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                for old_name, new_name in rename_map.items():
                    if old_name in run.text:
                        run.text = run.text.replace(old_name, new_name)
                        changes.append(f"Slide {slide_num}: '{old_name}' -> '{new_name}'")

prs.save(pptx_path)
```

Report what was changed. If no Macabacus links exist (plain template), note that the user will need to add them manually.

Tell the user:

```
PowerPoint template created. Campaign names updated on [N] slides.

NOTE: Macabacus links from the base template are preserved but point to the old model.
After opening the new model + deck pair, you will need to:
  1. Open both files in PowerPoint + Excel
  2. Macabacus ribbon -> Refresh Links -> point to the new model
  3. Save the deck

This is a one-time step per template.
```

---

## Step 6: Generate the JSON Config

Run the template scanner on the new Excel model:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
TEMPLATES_ROOT=$(python3 -c "import json; c=json.load(open('$WS/.claude/data/workspace_config.json')); print(c.get('templates_root', 'Templates'))" 2>/dev/null || echo "Templates")
python3 "$WS/.claude/agents/template_scanner.py" \
  --file "$WS/$TEMPLATES_ROOT/[Vertical Name]/[Vertical Name] Intro Template.xlsx" \
  --create \
  --output "$WS/.claude/agents/templates/[vertical_slug]_standard.json"
```

After the scanner creates the base config, enhance it by adding:

1. `vertical_standards` block (from Step 2 values)
2. `campaigns` dict with row numbers and assumption_start rows
3. `scenario_definitions` mapping (C=Base, D=Upside, E=Downside)
4. `description` with the vertical name and date
5. `template_type` set to the vertical name
6. `last_updated` set to today's date

Write the enhanced config:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
python3 - <<'PYEOF'
import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

config_path = sys.argv[1]
with open(config_path) as f:
    config = json.load(f)

# Add vertical_standards
config["vertical_standards"] = {
    "hours_per_year": [HOURS],
    "hiring_cost_cap": [CAP_OR_NULL],
    "incentive_range": [[LOW], [HIGH]],
    "return_rate_range": [[LOW], [HIGH]],
    "trir_divisor": [DIVISOR_OR_NULL]
}

# Add campaigns dict
config["campaigns"] = {
    "[Campaign 1 Name]": {
        "row": [ROW],
        "assumptions_start": [ROW],
        "type": "[type]"
    },
    # ... one per campaign
}

config["scenario_definitions"] = {"C": "Base", "D": "Upside", "E": "Downside"}
config["template_type"] = "[Vertical Name]"
config["description"] = "[Vertical Name] Intro Model Template (created [YYYY-MM-DD])"
config["last_updated"] = "[YYYY-MM-DD]"

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f"Config written: {config_path}")
PYEOF
python3 - "$WS/.claude/agents/templates/[vertical_slug]_standard.json"
```

Also copy the config to the plugin's data/templates/ directory if the plugin install directory is known:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
PLUGIN_DIR=$(python3 -c "import json; c=json.load(open('$WS/.claude/data/workspace_config.json')); print(c.get('plugin_dir',''))" 2>/dev/null)
if [ -n "$PLUGIN_DIR" ] && [ -d "$PLUGIN_DIR/data/templates" ]; then
  cp "$WS/.claude/agents/templates/[vertical_slug]_standard.json" "$PLUGIN_DIR/data/templates/"
  echo "Config also copied to plugin directory for distribution."
fi
```

---

## Step 7: Verify the Template Pair

Open both files for user review:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
TEMPLATES_ROOT=$(python3 -c "import json; c=json.load(open('$WS/.claude/data/workspace_config.json')); print(c.get('templates_root', 'Templates'))" 2>/dev/null || echo "Templates")
start "" "$WS/$TEMPLATES_ROOT/[Vertical Name]/[Vertical Name] Intro Template.xlsx"
start "" "$WS/$TEMPLATES_ROOT/[Vertical Name]/[Vertical Name] Intro Template.pptx"
```

Tell the user:

```
Template pair created for [VERTICAL NAME]:

  Model:  Templates/[Vertical Name]/[Vertical Name] Intro Template.xlsx
  Deck:   Templates/[Vertical Name]/[Vertical Name] Intro Template.pptx
  Config: .claude/agents/templates/[vertical_slug]_standard.json

Campaigns ([N]):
  1. [Campaign 1 Name]
  2. [Campaign 2 Name]
  ...

Vertical standards:
  Hours/year:      [value]
  Hiring cap:      [value or "none"]
  Incentive range: $[low] - $[high]
  Return range:    [low]% - [high]%
  TRIR divisor:    [value or "none"]

MANUAL STEPS REQUIRED:
  1. Open both files now
  2. Review the Inputs sheet - confirm all field labels are correct
  3. Review the Campaigns sheet - confirm formulas still calculate correctly
  4. In the deck: Macabacus ribbon -> Refresh Links -> point to the new model
  5. Save both files
  6. Create a "(without Commentary)" version of the deck if needed

After verification, this template will appear in /deck-start's template list
for all future engagements in this vertical.

Type "done" when the template is verified, or tell me what to fix:
```

Wait for "done". If the user reports issues, fix them (relabel cells, adjust config rows, etc.) and re-present.

---

## Step 8: Report

Tell the user:

```
Template for [VERTICAL NAME] is ready.

Files:
  Templates/[Vertical Name]/[Vertical Name] Intro Template.xlsx
  Templates/[Vertical Name]/[Vertical Name] Intro Template.pptx
  .claude/agents/templates/[vertical_slug]_standard.json

This vertical will now appear when you or any teammate runs /deck-start.
The template scanner will auto-match any company using this template to the
[vertical_slug]_standard.json config.

To use it: /deck-start [Company Name] -> select [Vertical Name] from the list.
```
