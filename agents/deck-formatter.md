---
name: deck-formatter
description: Format the vF intro deck — dollar formatting and banner fill. Run after Macabacus links are broken on the vF file.
model: sonnet
---

You are formatting the vF intro deck for **[COMPANY_NAME]**. Working directory: `C:\Users\Nishant\OneDrive - Default Directory\Jolly - Documents`

## Step 1: Find the Files

```python
import glob
vf_files = glob.glob(f"Clients/[COMPANY_NAME]/2. Presentations/*vF*.pptx")
model_files = glob.glob(f"Clients/[COMPANY_NAME]/1. Model/*.xlsx")
```

If no vF file found, stop and tell the user.

## Step 2: Inspect the Summary Slide

Use python-pptx to open the vF deck. Find the slide that contains "Campaign Summary" in any shape. Print ALL shapes on that slide — for each shape print: shape name, shape type, and the full text. This is essential before making any edits.

```python
from pptx import Presentation
prs = Presentation(vf_path)  # use os.path.abspath()

for slide in prs.slides:
    for shape in slide.shapes:
        if shape.has_text_frame and "Campaign Summary" in shape.text_frame.text:
            print("=== SUMMARY SLIDE ===")
            for s in slide.shapes:
                if s.has_text_frame:
                    print(f"  Name: {s.name!r} | Text: {s.text_frame.text[:120]!r}")
            break
```

From this output, identify:
- The banner shape (the sentence containing EBITDA and campaign count)
- How many campaign boxes are on the slide (look for shapes that represent individual campaigns)
- The exact placeholder text in the banner (e.g. `$[ ]`, `[ ] quantified`, or already-filled bad values)

## Step 3: Read Model Totals

Open the Sensitivities sheet from the Excel model. Find:
- **Campaign count**: count rows where column B starts with "Campaign" — these are the campaign header rows
- **Base EBITDA**: find the row where column B is "Base" in the Totals section (rows ~13-15), then find the large positive value in that row (columns C-F)

```python
from openpyxl import load_workbook
wb = load_workbook(model_path, data_only=True)
ws = wb["Sensitivities"]
for row in ws.iter_rows(values_only=True):
    print(row)  # inspect first to understand structure
```

## Step 4: Dollar Formatting (Non-Summary Slides)

On every slide EXCEPT the summary slide, replace any raw dollar amounts (5+ digit numbers like $1234567) with formatted versions:
- $1M+: `$X.XMM` (1 decimal, uppercase MM, no space) — e.g. `$21.6MM`
- $1K–$999K: `$XXXk` (lowercase k, no space) — e.g. `$516k`

Use regex: `\$[\d,]{5,}(?:\.\d+)?` to find candidates.

**Do not touch the summary slide** — it is handled in Step 5.

## Step 5: Fill the Banner

Using what you found in Step 2:
- Replace the EBITDA placeholder with the base EBITDA formatted as `$X.X` (no MM suffix — the template already has it, or format without suffix)
- Replace the campaign count placeholder with the count of campaigns ON THE SLIDE (from Step 2 shape inspection, not from the model)

Handle both original placeholders (`$[ ]`, `[ ] quantified`) and previously-bad fills (`$[EBITDA]`, wrong numbers) using regex where needed.

## Step 6: Save and Export PDF

```python
prs.save(vf_path)
```

Derive the PDF path from the vF pptx path: same folder (`2. Presentations/`), same filename stem (keep the ` - vF` suffix), extension `.pdf`.

```python
abs_pdf = os.path.splitext(abs_pptx)[0] + ".pdf"
# e.g. "...2. Presentations/Coca-Cola United Intro Deck (2026.02.19) - vF.pdf"
```

Export PDF via PowerShell temp .ps1 file (NOT -Command, to avoid bash $ escaping):

```python
import tempfile, subprocess, os

ps_script = (
    f'$ppt = New-Object -ComObject PowerPoint.Application\n'
    f'$pres = $ppt.Presentations.Open("{abs_pptx}")\n'
    f'$pres.SaveAs("{abs_pdf}", 32)\n'
    f'$pres.Close()\n'
    f'$ppt.Quit()\n'
)
with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8') as f:
    f.write(ps_script)
    ps1_path = f.name

subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps1_path], ...)
os.unlink(ps1_path)
```

Verify the PDF exists after export.

## Step 7: Open and Report

```bash
start "" "[vF pptx path]"
start "" "[vF pdf path]"   # same folder as pptx, same stem + .pdf
```

Report:
- How many dollar replacements made
- What the banner now says (full text)
- Campaign count used
- EBITDA value used
- PDF confirmed created: yes/no

## Standards

| Amount | Format |
|--------|--------|
| $1M+ (non-summary) | `$X.XMM` |
| $1K–$999K (non-summary) | `$XXXk` |
| Summary banner EBITDA | `$X.X` (no suffix) |

- Always use `os.path.abspath()` on file paths before opening with python-pptx
- Always add `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` at top of any Python
- Do not leave temp files in client folders
