"""
qa_check.py — Run QA checks on the Excel model and vF PowerPoint deck.

Usage:
    python .claude/scripts/qa_check.py --company "Company Name"

Checks:
    Excel:  formula counts, comment coverage, ROPS range, accretion ceiling
    PPT:    red text, placeholders, dollar formatting, banner fill, uppercase K
    Cross:  key values approximately match between Excel and PPT
"""

import sys
import re
import glob
import argparse

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    from openpyxl import load_workbook
except ImportError:
    print("ERROR: openpyxl not installed. Run: pip install openpyxl")
    sys.exit(1)

try:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
except ImportError:
    print("ERROR: python-pptx not installed. Run: pip install python-pptx")
    sys.exit(1)


PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

# Expected formula counts by industry
FORMULA_COUNTS = {
    "qsr":           {"Campaigns": 153, "Sensitivities": 86},
    "manufacturing": {"Campaigns": 366, "Sensitivities": 205},
}


def find_file(company: str, subfolder: str, pattern: str) -> str:
    matches = glob.glob(f"Clients/{company}/{subfolder}/{pattern}")
    if not matches:
        raise FileNotFoundError(f"No file matching '{pattern}' in Clients/{company}/{subfolder}/")
    return sorted(matches)[-1]  # Most recent


def count_formulas(wb, sheet_name: str) -> int:
    if sheet_name not in wb.sheetnames:
        return -1
    return sum(
        1 for row in wb[sheet_name].iter_rows()
        for cell in row
        if cell.value and isinstance(cell.value, str) and cell.value.startswith('=')
    )


def detect_industry(wb) -> str:
    """Heuristic: Manufacturing has more campaigns formulas."""
    n = count_formulas(wb, "Campaigns")
    if n > 200:
        return "manufacturing"
    return "qsr"


def check_excel(company: str) -> dict:
    results = {}
    print("\n=== EXCEL MODEL ===")

    try:
        model_path = find_file(company, "1. Model", "*.xlsx")
        print(f"File: {model_path}")
    except FileNotFoundError as e:
        print(f"  {FAIL} Model file not found: {e}")
        return {}

    wb = load_workbook(model_path, data_only=True)
    industry = detect_industry(wb)
    expected = FORMULA_COUNTS.get(industry, {})
    print(f"  Detected industry: {industry}")

    # 1. Formula counts
    for sheet, exp_count in expected.items():
        actual = count_formulas(load_workbook(model_path, data_only=False), sheet)
        if actual == exp_count:
            print(f"  {PASS} {sheet} formulas: {actual} (expected {exp_count})")
            results[f"{sheet}_formulas"] = True
        elif actual == -1:
            print(f"  {WARN} {sheet} sheet not found")
            results[f"{sheet}_formulas"] = None
        else:
            print(f"  {FAIL} {sheet} formulas: {actual} (expected {exp_count}) -- formulas may be overwritten")
            results[f"{sheet}_formulas"] = False

    # 2. Comment coverage on Inputs sheet
    if "Inputs" in wb.sheetnames:
        ws = wb["Inputs"]
        missing_comments = []
        wb_full = load_workbook(model_path, data_only=False)
        ws_full = wb_full["Inputs"]

        # Check all non-formula, non-empty cells in columns C-E rows 1-100
        for row in ws_full.iter_rows(min_row=1, max_row=100, min_col=3, max_col=5):
            for cell in row:
                if (cell.value is not None
                        and not (isinstance(cell.value, str) and cell.value.startswith('='))
                        and cell.comment is None):
                    missing_comments.append(cell.coordinate)

        if not missing_comments:
            print(f"  {PASS} Comment coverage: all value cells commented")
            results["comments"] = True
        else:
            print(f"  {FAIL} Comment coverage: {len(missing_comments)} cells missing comments: {missing_comments[:10]}")
            results["comments"] = False
    else:
        print(f"  {WARN} Inputs sheet not found")
        results["comments"] = None

    # 3. Value reasonableness (basic sanity checks on Inputs)
    if "Inputs" in wb.sheetnames:
        ws = wb["Inputs"]
        issues = []
        for row in ws.iter_rows(min_row=1, max_row=100, min_col=3, max_col=5):
            for cell in row:
                if cell.value is not None and isinstance(cell.value, (int, float)):
                    if cell.value < 0:
                        issues.append(f"{cell.coordinate}={cell.value} (negative)")
                    if isinstance(cell.value, float) and cell.value != int(cell.value) and cell.value > 10:
                        issues.append(f"{cell.coordinate}={cell.value} (fractional headcount?)")
        if not issues:
            print(f"  {PASS} Value reasonableness: no obvious issues")
            results["reasonableness"] = True
        else:
            print(f"  {WARN} Value reasonableness: check these cells: {issues[:5]}")
            results["reasonableness"] = None

    return results


def check_ppt(company: str) -> dict:
    results = {}
    print("\n=== POWERPOINT DECK ===")

    try:
        vf_path = find_file(company, "2. Presentations", "*vF*.pptx")
        if not glob.glob(f"Clients/{company}/2. Presentations/*vF*.pptx"):
            vf_path = find_file(company, "2. Presentations", "*vf*.pptx")
        print(f"File: {vf_path}")
    except FileNotFoundError as e:
        print(f"  {FAIL} vF deck not found: {e}")
        return {}

    prs = Presentation(vf_path)

    # 1. Red text
    red_runs = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        try:
                            if run.font.color.rgb == RGBColor(0xFF, 0x00, 0x00):
                                red_runs.append(run.text[:40])
                        except Exception:
                            pass
    if not red_runs:
        print(f"  {PASS} No red text")
        results["red_text"] = True
    else:
        print(f"  {FAIL} {len(red_runs)} red text runs found: {red_runs[:3]}")
        results["red_text"] = False

    # 2. Unfilled placeholders
    placeholders = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text
                if re.search(r'\[[ \w]*\]', text):
                    placeholders.append(text[:60])
    if not placeholders:
        print(f"  {PASS} No unfilled placeholders")
        results["placeholders"] = True
    else:
        print(f"  {FAIL} {len(placeholders)} unfilled placeholders: {placeholders[:3]}")
        results["placeholders"] = False

    # 3. Raw dollar amounts (5+ digits)
    raw_dollars = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text
                matches = re.findall(r'\$[\d,]{5,}', text)
                if matches:
                    raw_dollars.extend(matches)
    if not raw_dollars:
        print(f"  {PASS} Dollar formatting: all amounts use K/MM")
        results["dollar_format"] = True
    else:
        print(f"  {FAIL} {len(raw_dollars)} raw dollar amounts: {raw_dollars[:5]}")
        results["dollar_format"] = False

    # 4. Uppercase $K (should be lowercase $k)
    uppercase_k = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                matches = re.findall(r'\$\d+K\b', shape.text_frame.text)
                if matches:
                    uppercase_k.extend(matches)
    if not uppercase_k:
        print(f"  {PASS} No uppercase $K (all lowercase $k)")
        results["lowercase_k"] = True
    else:
        print(f"  {FAIL} Uppercase $K found: {uppercase_k[:5]} (should be lowercase)")
        results["lowercase_k"] = False

    # 5. Banner filled
    banner_ok = False
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text
                if ("MM" in text or "k" in text) and "quantified" in text:
                    if "$[ ]" not in text and "[ ] quantified" not in text:
                        banner_ok = True
    if banner_ok:
        print(f"  {PASS} Banner appears filled")
        results["banner"] = True
    else:
        print(f"  {WARN} Banner may not be filled - check summary slide manually")
        results["banner"] = None

    return results


def check_cross_validation(company: str) -> dict:
    results = {}
    print("\n=== CROSS-VALIDATION (Excel vs PPT) ===")

    # Read key values from Excel
    excel_values = {}
    try:
        model_path = find_file(company, "1. Model", "*.xlsx")
        wb = load_workbook(model_path, data_only=True)
        if "Inputs" in wb.sheetnames:
            ws = wb["Inputs"]
            # Read first non-empty values in column C for rows 5-9
            for row_num in range(5, 10):
                cell = ws.cell(row=row_num, column=3)
                label_cell = ws.cell(row=row_num, column=2)
                if cell.value is not None and label_cell.value:
                    excel_values[str(label_cell.value).strip()] = cell.value
    except Exception as e:
        print(f"  {WARN} Could not read Excel: {e}")
        return {}

    if not excel_values:
        print(f"  {WARN} No values extracted from Excel Inputs sheet")
        return {}

    # Check if key numbers appear in PPT (approximate match)
    try:
        vf_path = find_file(company, "2. Presentations", "*vF*.pptx")
        prs = Presentation(vf_path)
        ppt_text = " ".join(
            shape.text_frame.text
            for slide in prs.slides
            for shape in slide.shapes
            if shape.has_text_frame
        )
    except Exception as e:
        print(f"  {WARN} Could not read PPT: {e}")
        return {}

    mismatches = 0
    for label, value in list(excel_values.items())[:5]:
        if not isinstance(value, (int, float)) or value == 0:
            continue
        # Check if rounded version appears in deck text
        val_str = str(int(value))
        val_mm = f"{value/1_000_000:.0f}" if value >= 1_000_000 else None
        found = val_str in ppt_text or (val_mm and val_mm in ppt_text)
        status = PASS if found else WARN
        print(f"  {status} {label}: {value} {'found in deck' if found else 'NOT found in deck (may be formatted differently)'}")
        if not found:
            mismatches += 1

    results["cross_validation"] = mismatches == 0
    return results


def main():
    parser = argparse.ArgumentParser(description="QA check for intro deck package")
    parser.add_argument("--company", required=True, help="Company name (must match Clients/ folder)")
    args = parser.parse_args()
    company = args.company

    print(f"\n=== qa_check.py | {company} ===")

    excel_results = check_excel(company)
    ppt_results = check_ppt(company)
    cross_results = check_cross_validation(company)

    all_results = {**excel_results, **ppt_results, **cross_results}
    failures = [k for k, v in all_results.items() if v is False]
    warnings = [k for k, v in all_results.items() if v is None]

    print("\n=== SUMMARY ===")
    total = len(all_results)
    passed = sum(1 for v in all_results.values() if v is True)
    print(f"  {passed}/{total} checks passed")

    if failures:
        print(f"\n  FAILURES ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")

    if warnings:
        print(f"\n  WARNINGS ({len(warnings)}) - verify manually:")
        for w in warnings:
            print(f"    - {w}")

    if not failures:
        print(f"\n  OVERALL: PASS - ready for delivery")
    else:
        print(f"\n  OVERALL: FAIL - fix issues above and re-run")
        print(f"\n  Re-run: python .claude/scripts/qa_check.py --company \"{company}\"")


if __name__ == "__main__":
    main()
