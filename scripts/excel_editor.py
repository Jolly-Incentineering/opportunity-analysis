"""
Excel Editor
============
CLI for reading and writing Jolly intro model Excel files.

Actions:
    scan-formulas  — list every formula cell address in the workbook
    write-cells    — write values (and optional comments) to named cells
    read-summary   — read key inputs from the Inputs sheet

Usage:
    python excel_editor.py --file model.xlsx --action scan-formulas
    python excel_editor.py --file model.xlsx --action write-cells --cells '[{"sheet":"Inputs","cell":"E6","value":12000000,"comment":"..."}]'
    python excel_editor.py --file model.xlsx --action read-summary
"""
from jolly_utils import load_workbook_safe, save_workbook_safe, add_comment


def main():
    import argparse, json, sys

    parser = argparse.ArgumentParser(description="Excel editor for Jolly intro models")
    parser.add_argument("--file",   required=True, help="Path to Excel model file")
    parser.add_argument("--action", required=True,
                        choices=["scan-formulas", "write-cells", "read-summary"])
    parser.add_argument("--cells", help='JSON array: [{"sheet":"Inputs","cell":"E6","value":...,"comment":"..."}]')
    args = parser.parse_args()

    if args.action == "scan-formulas":
        wb = load_workbook_safe(args.file, data_only=False)
        formula_cells = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in ws.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and cell.value.startswith("="):
                        formula_cells.append(f"{sheet_name}!{cell.coordinate}")
        wb.close()
        print(json.dumps({"formula_cells": formula_cells, "count": len(formula_cells)}))

    elif args.action == "write-cells":
        if not args.cells:
            print("ERROR: --cells required for write-cells action", file=sys.stderr)
            sys.exit(1)
        writes = json.loads(args.cells)
        wb = load_workbook_safe(args.file)
        written = 0
        for w in writes:
            ref   = w["cell"]
            sheet = w.get("sheet", "Inputs")
            ws    = wb[sheet] if sheet in wb.sheetnames else wb["Inputs"]
            current = ws[ref].value
            if isinstance(current, str) and current.startswith("="):
                print(f"SKIPPED {ref}: contains formula", file=sys.stderr)
                continue
            ws[ref] = w["value"]
            if w.get("comment"):
                add_comment(ws, ref, w["comment"])
            written += 1
        save_workbook_safe(wb, args.file)
        wb.close()
        print(json.dumps({"written": written, "total": len(writes)}))

    elif args.action == "read-summary":
        wb = load_workbook_safe(args.file, data_only=True)
        ws = wb["Inputs"]
        result = {
            "company_name":          ws["E5"].value,
            "revenue":               ws["E6"].value,
            "stores_or_facilities":  ws["E7"].value,
            "orders_or_units":       ws["E8"].value,
            "employees":             ws["E9"].value,
            "campaigns_sheet_exists": "Campaigns" in wb.sheetnames,
        }
        wb.close()
        print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
