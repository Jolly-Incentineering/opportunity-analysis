# Excel Template Configs

JSON configuration files that map Excel template structures to field labels.

## Purpose

When `ExcelEditor` populates an Excel model, it uses a config file to find the correct cells for each field. This allows the same population code to work with:
- Standard templates (QSR, Manufacturing, etc.)
- Custom templates (per-client variations)
- Rearranged layouts (same fields, different rows)

## Config Format

```json
{
  "template_type": "QSR|Manufacturing|Automotive|Retail|Custom",
  "description": "Human-readable description",
  "labels": {
    "Field Name": row_number,
    "Company Name": 5,
    "Total Annual Revenue ($)": 6,
    ...
  },
  "scenarios": ["C", "D", "E"],
  "campaign_rows": {
    "Campaign 1": 16,
    "Campaign 2": 17,
    ...
  },
  "notes": ["Important notes about this template"],
  "last_updated": "2026-02-15"
}
```

## Files

| File | Template Type | Use Case |
|------|---------------|----------|
| `qsr_standard.json` | QSR | Standard QSR Intro Model Template |
| `manufacturing_standard.json` | Manufacturing | Standard Manufacturing Intro Template |
| `automotive_standard.json` | Automotive | Automotive Services Intro Template |
| `retail_and_ecommerce_standard.json` | Retail | Standard Retail & E-Commerce Template (REI standard as of 2026-02-23) |
| `[company]_custom.json` | Custom | Client-specific custom template |

## How Templates Are Used

### Finding the Right Config

When `excel-editor` agent populates a company:

1. **Scan template** — Extract labels from Excel
2. **Compare configs** — Find closest match (85%+ similarity)
3. **Use or create**:
   - If match found → use existing config
   - If no match → create new config (e.g., `us_merchants_custom.json`)

### Creating a New Config

```bash
# Manually (if needed):
python -c "
from .claude.agents import TemplateScanner
scanner = TemplateScanner()
scanned = scanner.scan_template('path/to/template.xlsx')
scanner.create_config_from_template(scanned, 'company_name.json')
"
```

### Using a Config

```python
from .claude.agents import ExcelEditor

editor = ExcelEditor()

# Method 1: Specify config file
editor.populate_qsr(
    company_name="US Merchants",
    workbook_path="path/to/model.xlsx",
    assumptions={...},
    config_file=".claude/agents/templates/manufacturing_standard.json"
)

# Method 2: Auto-detect config (excel-editor agent does this)
editor.populate_qsr(
    company_name="US Merchants",
    workbook_path="path/to/model.xlsx",
    assumptions={...},
    config_file=None  # Will scan & auto-detect
)
```

## Label Guidelines

### Column B Labels (Row Identifiers)

Labels in column B should be:
- **Exact matches** with your Excel template (spacing matters)
- **Consistent** across all rows
- **Human-readable** (used for matching)

Examples:
```
✅ "Company Name"
✅ "Total Annual Revenue ($)"
✅ "Beverage Contribution Margin %"

❌ "company name" (case mismatch)
❌ "Total Annual Revenue" (missing unit)
❌ "Revenue" (too vague)
```

### Handling Label Variations

If a template uses slightly different labels (e.g., "Revenue" vs. "Total Revenue"), the scanner uses **fuzzy matching** (80%+ similarity) to find the best match.

If a new config is created for a custom template, it will use the exact labels from that template.

## Updating Configs

If you customize a template (move rows, change labels), you have two options:

### Option 1: Update Existing Config
```json
{
  "template_type": "QSR",
  "labels": {
    "Company Name": 8,  // Changed from row 5
    "Total Annual Revenue ($)": 9,  // Changed from row 6
    ...
  }
}
```

### Option 2: Create New Company-Specific Config
```
qsr_standard.json          → Standard template
my_client_custom.json      → Custom for "My Client"
```

The `excel-editor` agent will auto-detect and use the right one.

## Config Validation

Configs are validated when loaded:
- ✅ `template_type` is one of: QSR, Manufacturing, Automotive, Retail, Custom
- ✅ `labels` is a dict of `{field_name: row_number}`
- ✅ `scenarios` is a list of column letters (e.g., ["C", "D", "E"])
- ✅ All row numbers are positive integers

## Troubleshooting

**Template doesn't match any existing config?**
- New template detected
- `excel-editor` agent will create a config automatically
- Review the created config file to verify labels are correct

**Config has wrong row numbers?**
- Edit the config JSON manually
- Re-run population with updated config

**Labels don't match template?**
- Check for extra spaces, typos, case mismatches
- Update config labels to match exact Excel text

## Reusing Configs Across Companies

If multiple companies use the same template structure, they can share the same config:

```
Companies: US Merchants, Comfort Research
Template: Manufacturing Intro Template.xlsx (same structure)
Config: manufacturing_standard.json (reused)
```

No duplication needed — the system automatically reuses matching configs.
