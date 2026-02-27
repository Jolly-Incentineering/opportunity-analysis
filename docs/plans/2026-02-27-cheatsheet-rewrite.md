# Cheatsheet Rewrite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite `scripts/cheatsheet_gen.py` from 2,171 lines to ~550 lines — remove runtime Claude API calls, remove vertical config system, source campaign numbers from `campaign_details` in the research JSON, switch PDF renderer to WeasyPrint with Playwright fallback.

**Architecture:** Single script. Data comes entirely from `research_output_[slug].json` written by deck-research + deck-model. Assumptions table is the only thing still read from Excel. Renderer tries WeasyPrint → Playwright → HTML fallback (never hard-fails).

**Tech Stack:** Python 3.10+, weasyprint, openpyxl, playwright (optional fallback)

---

## Context: research_output JSON schema

The script reads `research_output_[slug].json`. Relevant fields:

```json
{
  "company_name": "Acme Corp",
  "industry": "Manufacturing / Food & Beverage",
  "company_basics": {
    "annual_revenue": 1000000000,
    "annual_revenue_source": "10-K",
    "unit_count": 500,
    "unit_count_source": "Website",
    "unit_count_label": "Facilities",
    "employee_count": 10000,
    "employee_count_source": "LinkedIn",
    "geography": { "hq": "Chicago, IL", "states": ["IL","TX"], "state_count": 5, "rank": "#2 in category" },
    "employee_breakdown": { "manufacturing_warehousing": 2500, "sales_distribution_delivery": 5000 }
  },
  "attio_insights": {
    "founded": 1990,
    "categories": ["Food & Beverage"],
    "employee_range": "5,001-10,000",
    "estimated_arr_usd": null,
    "last_interaction": "2026-01-15",
    "strongest_connection_strength": "Strong"
  },
  "gong_insights": {
    "pain_points": ["Turnover costs $4M/yr", "Manual scheduling wastes 8hrs/week/manager"],
    "champions": [{ "name": "Jane Doe", "title": "CFO", "note": "Key champion" }],
    "key_objections": ["Budget tied up until Q3", "Need pilot data first"],
    "tech_stack": { "Scheduling": "HomeBase", "Payroll": "ADP" },
    "verbatim_quotes": ["We're hemorrhaging turnover costs — it's our #1 ops issue"]
  },
  "slack_insights": [
    {
      "deal_stage": "Discovery",
      "primary_contact": "Jane Doe",
      "secondary_contact": "Bob Smith",
      "next_steps": "Send ROI model, schedule follow-up Feb 15"
    }
  ],
  "campaigns_selected": [
    { "name": "Employee Retention", "priority": "high", "evidence": "CFO cited $4M turnover", "client_interest": "Explicit" },
    { "name": "Manager Engagement", "priority": "standard", "evidence": "Ops team pain", "client_interest": "Implied" }
  ],
  "campaign_inputs": {},
  "comps_benchmarks": {
    "vertical": "manufacturing",
    "ebitda_margin_pct": { "low": 0.08, "mid": 0.14, "high": 0.22 },
    "turnover_rate": { "low": 0.20, "mid": 0.35, "high": 0.55 }
  },
  "source_summary": {
    "gong_calls_found": 2,
    "attio_records": 1,
    "slack_messages": 4,
    "sec_filings": false,
    "web_operations_used": 6
  },
  "campaign_details": {
    "Employee Retention": {
      "rops_base": 12.5,
      "rops_upside": 18.0,
      "incentive_cost_base": 240000,
      "ebitda_uplift_base": 3000000,
      "description": "Reduce frontline turnover via recognition campaigns"
    },
    "Manager Engagement": {
      "rops_base": 8.0,
      "rops_upside": 11.0,
      "incentive_cost_base": 120000,
      "ebitda_uplift_base": 960000,
      "description": "Improve retention and productivity of managers"
    }
  },
  "model_population": {
    "total_accretion": 3960000,
    "annual_ebitda": null,
    "accretion_pct": null
  }
}
```

The Excel model is only needed for the **scenario assumptions table** (Inputs sheet, rows below "SCENARIO ASSUMPTIONS" header).

---

## Context: current file layout (what to keep vs. remove)

**Keep (copy as-is):**
- Lines 70–71: `slugify()`
- Lines 92–120: `esc()`, `fmt()`, `fmt_plain()`
- Lines 141–155: `_deep_get()`
- Lines 158–170: `get_workspace_config()`
- Lines 173–205: `find_research_json()`
- Lines 208–221: `find_model()`
- Lines 588–697: `read_model_basics()` — but strip the ROPS/EBITDA reading (lines 674–695), keep only the assumptions section (lines 609–672)

**Remove entirely:**
- Lines 75–89: `_match_model_slug()` — no longer needed
- Lines 127–138: `fmt_bench()` — dead code
- Lines 224–255: `_call_claude_api()`
- Lines 258–306: `_generate_config_with_claude()`
- Lines 309–408: `_generate_config_fallback()`
- Lines 411–456: `load_vertical_config()`
- Lines 459–473: `_compute_total_opportunity()` — rewrite inline in build_campaign_html
- Lines 476–565: `_generate_meeting_intelligence()`
- Lines 568–585: `_fmt_assumption()` — inline into read_model_basics
- Lines 1926–1961: `_build_header_template()`
- Lines 1964–1973: `_extract_body_div()`
- Lines 1976–2000: `build_combined_html()`
- Lines 2049–2103: `PLACEHOLDER_RESEARCH`, `save_templates()`

**Rewrite:**
- CSS block (lines 704–1362): consolidate, ~200 lines
- `build_company_html()` (lines 1374–1708): rewrite without vertical config, ~100 lines
- `build_campaign_html()` (lines 1715–1919): rewrite using `campaign_details`, ~80 lines
- `render_pdf()` (lines 2007–2042): rewrite as fallback chain
- `main()` (lines 2110–2171): rewrite, ~40 lines

**Add new:**
- `_section(icon, title, content)` helper (~5 lines)
- `build_meeting_prep_html()` (~50 lines)
- `render_with_weasyprint()` (~15 lines)
- `render_with_playwright()` (~20 lines)

---

### Task 1: Scaffold new file with imports, constants, and helpers

**Files:**
- Overwrite: `scripts/cheatsheet_gen.py`

**Step 1: Write the new file skeleton**

Replace the entire file with:

```python
"""
cheatsheet_gen.py — Generate company and campaign cheat sheets as a combined PDF.

Usage:
    python .claude/scripts/cheatsheet_gen.py --company "Company Name"

Output:
    Clients/[Company]/4. Reports/Cheat Sheets/[Company] Cheat Sheet.pdf

Requires (one of):
    pip install weasyprint        # primary renderer
    pip install playwright && playwright install chromium  # fallback renderer
"""
from __future__ import annotations

import sys
import json
import glob
import argparse
import os
import re
from pathlib import Path
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Brand colors
# ---------------------------------------------------------------------------

NAVY    = "#123769"
NAVY_LT = "#1a4a8a"
GOLD    = "#E8A838"
GOLD_LT = "#FEF6E4"
BG      = "#F6F8FA"
WHITE   = "#FFFFFF"
GRAY_LT = "#EEF1F5"
GRAY    = "#D1D5DC"
BORDER  = "#DDE2EA"
TEXT    = "#1a1a2e"
MUTED   = "#666D80"
GREEN   = "#1a7a4a"
GREEN_LT= "#e8f6ee"
RED     = "#b03030"
RED_LT  = "#fdeaea"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", s.lower().replace(" ", "_").replace("-", "_"))


def esc(s) -> str:
    return (str(s or "")
            .replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def fmt(v, prefix="$") -> str:
    """Format numeric value. Use prefix='' for plain numbers."""
    if v is None:
        return "N/A"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v) or "N/A"
    if 0 < abs(v) < 1:
        return f"{v * 100:.1f}%"
    if abs(v) >= 1_000_000_000:
        return f"{prefix}{v / 1_000_000_000:.1f}B"
    if abs(v) >= 1_000_000:
        return f"{prefix}{v / 1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"{prefix}{v / 1_000:.1f}K"
    if v == int(v):
        return f"{prefix}{int(v)}"
    return f"{prefix}{v:.2f}" if prefix else str(round(v, 2))


def fmt_plain(v) -> str:
    return fmt(v, prefix="")


def _deep_get(d: dict, path: str, default=None):
    """Traverse nested dict/list via dot-separated path."""
    parts = path.split(".")
    cur = d
    for p in parts:
        if isinstance(cur, dict):
            cur = cur.get(p)
        elif isinstance(cur, list) and p.isdigit():
            idx = int(p)
            cur = cur[idx] if idx < len(cur) else None
        else:
            return default
        if cur is None:
            return default
    return cur


def _section(icon: str, title: str, content: str) -> str:
    """Wrap content in a standard labelled section block."""
    return (
        f'<div class="section">'
        f'<div class="section-label"><span class="s-icon">{icon}</span>{esc(title)}</div>'
        f'{content}'
        f'</div>'
    )
```

**Step 2: Verify syntax**

```bash
cd "$WS" && python3 -c "import scripts.cheatsheet_gen" 2>&1 || python3 .claude/scripts/cheatsheet_gen.py --help 2>&1 | head -5
```

Expected: no import errors (argparse not set up yet — that's fine, just check syntax).

Actually run:
```bash
cd "$WS" && python3 -c "
import sys; sys.path.insert(0, '.')
exec(open('.claude/scripts/cheatsheet_gen.py').read().split('def get_workspace')[0])
print('OK')
"
```
Expected: `OK`

**Step 3: Commit**

```bash
git add .claude/scripts/cheatsheet_gen.py
git commit -m "refactor: scaffold cheatsheet_gen rewrite — imports, colors, helpers"
```

---

### Task 2: Data loaders

**Files:**
- Modify: `scripts/cheatsheet_gen.py` (append after helpers)

**Step 1: Add the three data loader functions**

Append after the `_section()` function:

```python
# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def get_workspace_config() -> dict:
    candidates = [".claude/data/workspace_config.json"]
    jolly_ws = os.environ.get("JOLLY_WORKSPACE", "").strip().strip("\r")
    if jolly_ws:
        candidates.append(os.path.join(jolly_ws, ".claude/data/workspace_config.json"))
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


def find_research_json(company: str, base_path: str = None) -> dict:
    slug = slugify(company)
    if base_path:
        client_glob = f"{base_path}/**/research_output_*.json"
    else:
        cfg = get_workspace_config()
        client_root = cfg.get("client_root", "Clients")
        client_glob = f"{client_root}/{company}/**/research_output_*.json"

    candidates = []
    for m in glob.glob(client_glob, recursive=True):
        try:
            candidates.append((os.path.getmtime(m), m))
        except OSError:
            pass
    for _, path in sorted(candidates, reverse=True):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            print(f"  Research JSON: {path}")
            return data
        except (json.JSONDecodeError, OSError):
            continue
    for p in [
        f".claude/data/research_output_{slug}.json",
        f".claude/data/research_output_{company.lower().replace(' ', '-')}.json",
    ]:
        if os.path.exists(p):
            print(f"  Research JSON (legacy): {p}")
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(f"No research JSON found for '{company}'")


def find_model(company: str, base_path: str = None) -> str:
    if base_path:
        model_glob = f"{base_path}/1. Model/*.xlsx"
        search_path = f"{base_path}/1. Model/"
    else:
        cfg = get_workspace_config()
        client_root = cfg.get("client_root", "Clients")
        model_glob = f"{client_root}/{company}/1. Model/*.xlsx"
        search_path = f"{client_root}/{company}/1. Model/"
    matches = glob.glob(model_glob)
    if not matches:
        raise FileNotFoundError(f"No Excel model in {search_path}")
    return sorted(matches)[-1]


def _fmt_assumption(val) -> str:
    """Format a scenario assumption value for display."""
    if val is None:
        return ""
    if isinstance(val, float):
        if 0 < val < 1:
            return f"{val:.0%}"
        if val >= 1000:
            return f"${val:,.0f}"
        if val >= 100:
            return f"{val:,.0f}"
        if val == int(val):
            return f"{int(val):,}"
        return f"{val:.2f}"
    if isinstance(val, int):
        return f"${val:,}" if val >= 1000 else f"{val:,}"
    return str(val)


def read_model_assumptions(model_path: str) -> dict:
    """Read only the scenario assumptions section from the Excel Inputs sheet.

    Returns dict: { "assumptions__{campaign_slug}": [(label, base, upside, downside), ...] }
    Does NOT read ROPS or EBITDA — those come from research JSON campaign_details.
    """
    if not OPENPYXL_AVAILABLE:
        return {}
    try:
        wb = load_workbook(model_path, data_only=True)
    except PermissionError:
        import shutil, tempfile
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            shutil.copy2(model_path, tmp_path)
            wb = load_workbook(tmp_path, data_only=True)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    if "Inputs" not in wb.sheetnames:
        return {}

    ws = wb["Inputs"]
    all_rows = list(ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True))

    # Find "SCENARIO ASSUMPTIONS" header row
    scenario_start = None
    for i, row in enumerate(all_rows):
        if row[1] and "SCENARIO ASSUMPTIONS" in str(row[1]):
            scenario_start = i + 1
            break
    if scenario_start is None:
        return {}

    result = {}
    current_name = None
    current_rows = []

    for row in all_rows[scenario_start:]:
        label    = row[1] if len(row) > 1 else None
        base_val = row[2] if len(row) > 2 else None
        up_val   = row[3] if len(row) > 3 else None
        dn_val   = row[4] if len(row) > 4 else None
        label_str = str(label).strip() if label else ""

        if not label_str:
            if current_name and current_rows:
                result[f"assumptions__{slugify(current_name)}"] = current_rows
                current_name = None
                current_rows = []
            continue

        if re.match(r"Campaign \d+:", label_str) and base_val is None:
            if current_name and current_rows:
                result[f"assumptions__{slugify(current_name)}"] = current_rows
            current_name = label_str.split(":", 1)[1].strip()
            current_rows = []
        elif base_val is not None:
            current_rows.append((
                label_str,
                _fmt_assumption(base_val),
                _fmt_assumption(up_val),
                _fmt_assumption(dn_val),
            ))

    if current_name and current_rows:
        result[f"assumptions__{slugify(current_name)}"] = current_rows

    return result
```

**Step 2: Verify syntax**

```bash
python3 -c "
import sys; sys.argv=['x','--company','Test']
exec(open('.claude/scripts/cheatsheet_gen.py').read().split('# ---\n# CSS')[0])
print('data loaders OK')
"
```

Expected: `data loaders OK`

**Step 3: Commit**

```bash
git add .claude/scripts/cheatsheet_gen.py
git commit -m "refactor: add data loaders to cheatsheet_gen rewrite"
```

---

### Task 3: CSS block

**Files:**
- Modify: `scripts/cheatsheet_gen.py` (append after data loaders)

**Step 1: Add consolidated CSS**

Append the CSS string. This consolidates 660 lines → ~200 lines by:
- Removing unused `.cover`, `.cover-*`, `.gold-rule` selectors
- Using `.table-base` shared class for all 5 table types
- Merging `.badge`, `.pill`, `.ch`, `.cs` shared color/padding patterns

```python
# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = f"""
@page {{ size: Letter; margin: 0; }}
html, body {{ width: 816px; overflow: hidden; box-sizing: border-box; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
    font-family: -apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    color: {TEXT};
    background: {BG};
    line-height: 1.5;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}}

/* ── Banner (top of each page section) ── */
.banner {{
    background: linear-gradient(135deg, {NAVY} 0%, {NAVY_LT} 100%);
    border-bottom: 3px solid {GOLD};
    padding: 10px 28px 9px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}
.banner-eyebrow {{
    font-size: 6.5px; font-weight: 700; letter-spacing: 1.8px;
    text-transform: uppercase; color: {GOLD}; margin-bottom: 2px;
}}
.banner-title {{
    font-size: 14px; font-weight: 800; color: {WHITE};
    letter-spacing: -0.3px; line-height: 1; margin-bottom: 2px;
}}
.banner-sub {{ font-size: 7.5px; color: rgba(255,255,255,0.5); }}
.banner-page {{ font-size: 7.5px; color: rgba(255,255,255,0.4); }}

/* ── Body ── */
.body {{ padding: 8px 28px 20px; background: {BG}; }}

/* ── Section ── */
.section {{ margin: 10px 0 5px; break-inside: avoid; }}
.section-label + * {{ break-before: avoid; }}
.section-label {{
    font-size: 7.5px; font-weight: 800; letter-spacing: 1.4px;
    text-transform: uppercase; color: {NAVY};
    padding-bottom: 4px; border-bottom: 2px solid {GOLD};
    display: flex; align-items: center; gap: 5px;
}}
.s-icon {{
    width: 14px; height: 14px; background: {GOLD}; border-radius: 3px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 8px; color: {NAVY}; font-weight: 900; flex-shrink: 0;
}}

/* ── KPI strip ── */
.kpi-strip {{ display: flex; gap: 0; margin-top: 6px; }}
.kpi-card {{
    flex: 1; padding: 8px 10px; background: {WHITE};
    border: 1px solid {GRAY_LT}; border-right: none; text-align: center;
}}
.kpi-card:last-child {{ border-right: 1px solid {GRAY_LT}; border-radius: 0 5px 5px 0; }}
.kpi-card:first-child {{ border-radius: 5px 0 0 5px; }}
.kpi-v {{ font-size: 18px; font-weight: 900; color: {NAVY}; letter-spacing: -0.5px; line-height: 1; }}
.kpi-l {{ font-size: 7px; font-weight: 700; color: {MUTED}; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }}
.kpi-src {{ font-size: 6.5px; color: {MUTED}; margin-top: 1px; font-style: italic; }}

/* ── Breakdown grid ── */
.breakdown-grid {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 5px; }}
.bk-cell {{
    background: {WHITE}; border: 1px solid {GRAY_LT}; border-radius: 5px;
    padding: 6px 10px; text-align: center; min-width: 80px;
}}
.bk-v {{ font-size: 14px; font-weight: 800; color: {NAVY}; line-height: 1; }}
.bk-l {{ font-size: 7px; color: {MUTED}; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }}

/* ── Tables (shared base) ── */
.data-table, .bench-table, .tech-table, .assump-table, .objection-table {{
    width: 100%; border-collapse: collapse; margin-top: 5px; font-size: 9px;
}}
.data-table td, .bench-table td, .tech-table td, .assump-table td, .objection-table td {{
    padding: 5px 9px; border-bottom: 1px solid {GRAY_LT}; vertical-align: top;
}}
.data-table tr:last-child td, .bench-table tr:last-child td,
.tech-table tr:last-child td, .assump-table tr:last-child td,
.objection-table tr:last-child td {{ border-bottom: none; }}
.data-table tr:nth-child(even) td, .bench-table tr:nth-child(even) td,
.tech-table tr:nth-child(even) td {{ background: {GRAY_LT}; }}
.data-table td:first-child, .tech-table td:first-child {{ color: {MUTED}; width: 38%; font-weight: 600; }}

/* Table header row */
.assump-hdr th, .objection-table tr:first-child td {{
    background: {NAVY}; color: {WHITE}; font-size: 7.5px;
    font-weight: 700; text-transform: uppercase; padding: 5px 9px;
}}
.bench-table td.mid {{ font-weight: 700; color: {NAVY}; }}
.col-base {{ font-weight: 600; }}
.col-up {{ color: {GREEN}; }}
.col-dn {{ color: {RED}; }}

/* ── Opportunity banner ── */
.opp-banner {{
    display: flex; gap: 0; margin: 6px 0 12px;
    border: 1px solid {GOLD}; border-radius: 7px;
    overflow: hidden; background: {GOLD_LT};
}}
.opp-item {{ flex: 1; padding: 10px 12px 9px; text-align: center; border-right: 1px solid rgba(232,168,56,0.35); }}
.opp-item:last-child {{ border-right: none; }}
.opp-v {{ font-size: 20px; font-weight: 900; color: {NAVY}; letter-spacing: -0.5px; line-height: 1; }}
.opp-l {{ font-size: 7px; font-weight: 700; color: {MUTED}; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 3px; }}

/* ── Bullets / lists ── */
.bullets {{ padding-left: 14px; font-size: 9px; margin-top: 4px; }}
.bullets li {{ margin-bottom: 3px; }}
.numbered-list {{ padding-left: 16px; font-size: 9px; margin-top: 4px; }}
.numbered-list li {{ margin-bottom: 3px; }}

/* ── Quote ── */
.quote {{
    background: {GOLD_LT}; border-left: 3px solid {GOLD};
    border-radius: 0 5px 5px 0; padding: 7px 11px;
    font-size: 9px; font-style: italic; margin-bottom: 5px; color: {TEXT};
}}
.quote-src {{ font-size: 7.5px; color: {MUTED}; margin-top: 3px; font-style: normal; }}

/* ── Pills (research sources) ── */
.pills {{ display: flex; gap: 5px; flex-wrap: wrap; margin-top: 5px; }}
.pill {{
    background: {NAVY}; color: {WHITE}; border-radius: 20px;
    padding: 2px 8px; font-size: 7.5px; font-weight: 700;
    display: inline-flex; align-items: center; gap: 4px;
}}
.pill-zero {{ background: {GRAY}; color: {MUTED}; }}
.pill-val {{ font-weight: 400; opacity: 0.85; }}

/* ── Contacts ── */
.contacts-box {{
    background: {WHITE}; border: 1px solid {GRAY_LT};
    border-radius: 6px; padding: 4px 10px; margin-top: 6px;
}}
.champion-row {{ padding: 5px 0; border-bottom: 1px solid {GRAY_LT}; }}
.champion-row:last-child {{ border-bottom: none; }}
.champ-name {{ font-weight: 700; font-size: 9.5px; }}
.champ-title {{ font-size: 8.5px; color: {MUTED}; }}
.champ-note {{ font-size: 8px; color: {MUTED}; font-style: italic; }}

/* ── Deal context ── */
.deal-box {{
    background: {WHITE}; border: 1px solid {GRAY_LT};
    border-radius: 6px; padding: 7px 12px; margin-top: 5px; font-size: 9px;
}}
.deal-row {{ display: flex; gap: 8px; margin-bottom: 3px; }}
.deal-row:last-child {{ margin-bottom: 0; }}
.deal-label {{ color: {MUTED}; font-weight: 600; min-width: 90px; font-size: 8.5px; }}

/* ── Campaign cards ── */
.campaign {{
    background: {WHITE}; border: 1px solid {GRAY_LT};
    border-radius: 8px; margin-bottom: 10px;
    overflow: hidden; break-inside: avoid;
}}
.c-head {{
    background: {BG}; padding: 8px 12px 7px;
    border-bottom: 1px solid {GRAY_LT};
    display: flex; align-items: flex-start; justify-content: space-between;
}}
.c-head.high {{ background: linear-gradient(135deg, {NAVY} 0%, {NAVY_LT} 100%); }}
.c-head.high .c-title {{ color: {WHITE}; }}
.c-title {{ font-size: 11px; font-weight: 800; color: {NAVY}; letter-spacing: -0.2px; }}
.c-badges {{ display: flex; gap: 4px; align-items: center; flex-shrink: 0; }}
.badge {{
    font-size: 7px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.5px; padding: 2px 7px; border-radius: 20px;
}}
.b-high {{ background: {GOLD}; color: {NAVY}; }}
.b-std {{ background: {GRAY_LT}; color: {MUTED}; }}
.b-interest {{ background: {GREEN_LT}; color: {GREEN}; border: 1px solid {GREEN}; }}
.c-body {{ padding: 10px 12px; }}
.c-stats {{ display: flex; gap: 0; margin-bottom: 8px; }}
.c-stat-item {{
    flex: 1; text-align: center; padding: 6px 8px;
    border-right: 1px solid {GRAY_LT};
    border: 1px solid {GRAY_LT}; border-right: none; background: {BG};
}}
.c-stat-item:first-child {{ border-radius: 5px 0 0 5px; }}
.c-stat-item:last-child {{ border-right: 1px solid {GRAY_LT}; border-radius: 0 5px 5px 0; }}
.c-stat-v {{ font-size: 14px; font-weight: 900; color: {NAVY}; line-height: 1; }}
.c-stat-l {{ font-size: 6.5px; color: {MUTED}; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }}
.evidence {{
    font-size: 8.5px; font-style: italic; color: {MUTED};
    border-left: 2px solid {GOLD}; padding: 3px 8px;
    margin-bottom: 7px; background: {GOLD_LT}; border-radius: 0 3px 3px 0;
}}
.assumptions {{ margin-top: 6px; }}
.assumptions-label {{
    font-size: 7px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; color: {MUTED}; margin-bottom: 3px;
}}

/* ── Page break ── */
.page-break {{ break-after: page; }}

/* ── Footer ── */
.footer {{
    margin-top: 16px; padding-top: 8px;
    border-top: 1px solid {GRAY}; font-size: 7.5px; color: {MUTED};
    display: flex; justify-content: space-between;
}}
"""
```

**Step 2: Verify CSS parses (no syntax errors in f-string)**

```bash
python3 -c "
exec(open('.claude/scripts/cheatsheet_gen.py').read())
print('CSS length:', len(CSS), 'chars — OK')
"
```

Expected: `CSS length: XXXX chars — OK`

**Step 3: Commit**

```bash
git add .claude/scripts/cheatsheet_gen.py
git commit -m "refactor: add consolidated CSS to cheatsheet_gen rewrite"
```

---

### Task 4: Company page HTML builder

**Files:**
- Modify: `scripts/cheatsheet_gen.py` (append after CSS)

**Step 1: Add `build_company_html()`**

Append after the CSS block:

```python
# ---------------------------------------------------------------------------
# Company Cheat Sheet
# ---------------------------------------------------------------------------

def build_company_html(company: str, research: dict) -> str:
    today  = date.today().strftime("%B %d, %Y")
    basics = research.get("company_basics") or {}
    attio  = research.get("attio_insights") or {}
    comps  = research.get("comps_benchmarks") or {}
    sources= research.get("source_summary") or {}

    # ── KPI strip ──
    revenue   = basics.get("annual_revenue")
    units     = basics.get("unit_count")
    employees = basics.get("employee_count")
    unit_label = basics.get("unit_count_label") or "Locations"

    def _src_tag(field):
        s = basics.get(f"{field}_source") or ""
        return f'<div class="kpi-src">{esc(s)}</div>' if s else ""

    kpi_content = f"""<div class="kpi-strip">
  <div class="kpi-card"><div class="kpi-v">{fmt(revenue)}</div><div class="kpi-l">Annual Revenue</div>{_src_tag("annual_revenue")}</div>
  <div class="kpi-card"><div class="kpi-v">{fmt_plain(units)}</div><div class="kpi-l">{esc(unit_label)}</div>{_src_tag("unit_count")}</div>
  <div class="kpi-card"><div class="kpi-v">{fmt_plain(employees)}</div><div class="kpi-l">Employees</div>{_src_tag("employee_count")}</div>
</div>"""
    kpi_html = _section("▲", "Key Metrics", kpi_content)

    # ── Company Profile ──
    geo = basics.get("geography") or {}
    profile_rows = []
    if research.get("industry"):
        profile_rows.append(("Industry", str(research["industry"])))
    if attio.get("founded"):
        profile_rows.append(("Founded", str(attio["founded"])))
    if geo.get("hq"):
        profile_rows.append(("HQ", geo["hq"]))
    if geo.get("rank"):
        profile_rows.append(("Market Position", geo["rank"]))
    if geo.get("states"):
        profile_rows.append(("States", ", ".join(geo["states"])))
    elif geo.get("state_count"):
        profile_rows.append(("States Operated", str(geo["state_count"])))
    for key, label in [
        ("categories",   "Categories"),
        ("employee_range", "Employee Range"),
        ("estimated_arr_usd", "Est. ARR"),
        ("last_interaction", "Last Interaction"),
        ("strongest_connection_strength", "Connection"),
    ]:
        v = attio.get(key)
        if v:
            display = fmt(v) if key == "estimated_arr_usd" else (", ".join(v) if isinstance(v, list) else str(v))
            profile_rows.append((label, display))
    slack_list = research.get("slack_insights") or []
    slack = slack_list[0] if slack_list else {}
    for key, label in [("deal_stage","Deal Stage"),("primary_contact","Primary Contact")]:
        if slack.get(key):
            profile_rows.append((label, str(slack[key])))

    profile_html = ""
    if profile_rows:
        rows_html = "".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in profile_rows)
        profile_html = _section("◈", "Company Profile", f'<table class="data-table">{rows_html}</table>')

    # ── Employee Breakdown ──
    breakdown_html = ""
    bd = basics.get("employee_breakdown") or {}
    if bd:
        cells = "".join(
            f'<div class="bk-cell"><div class="bk-v">{fmt_plain(v)}</div><div class="bk-l">{esc(k.replace("_"," ").title())}</div></div>'
            for k, v in bd.items() if v is not None
        )
        if cells:
            breakdown_html = _section("⊞", "Employee Breakdown", f'<div class="breakdown-grid">{cells}</div>')

    # ── Industry Benchmarks ──
    bench_html = ""
    bench_rows = []
    for key, label in [
        ("ebitda_margin_pct", "EBITDA Margin"),
        ("gross_margin_pct",  "Gross Margin"),
        ("turnover_rate",     "Turnover Rate"),
        ("net_margin_pct",    "Net Margin"),
        ("labor_cost_pct",    "Labor Cost %"),
    ]:
        raw = comps.get(key)
        if raw is None:
            continue
        if isinstance(raw, dict):
            bench_rows.append((label, raw.get("low"), raw.get("mid"), raw.get("high")))
        else:
            bench_rows.append((label, None, raw, None))

    if bench_rows:
        has_range = any(lo is not None or hi is not None for _, lo, _, hi in bench_rows)
        if has_range:
            hdr = '<tr class="assump-hdr"><th>Benchmark</th><th>Low</th><th>Mid</th><th>High</th></tr>'
            rows_html = hdr + "".join(
                f'<tr><td>{esc(lbl)}</td>'
                f'<td>{fmt_plain(lo) if lo is not None else "—"}</td>'
                f'<td class="mid">{fmt_plain(mid) if mid is not None else "—"}</td>'
                f'<td>{fmt_plain(hi) if hi is not None else "—"}</td></tr>'
                for lbl, lo, mid, hi in bench_rows
            )
            bench_html = _section("≈", "Industry Benchmarks", f'<table class="bench-table">{rows_html}</table>')
        else:
            rows_html = "".join(
                f'<tr><td>{esc(lbl)}</td><td>{fmt_plain(mid) if mid is not None else "—"}</td></tr>'
                for lbl, _, mid, _ in bench_rows
            )
            bench_html = _section("≈", "Industry Benchmarks", f'<table class="data-table">{rows_html}</table>')

    # ── Research Sources ──
    pill_data = [
        ("Gong",  sources.get("gong_calls_found") or 0),
        ("Attio", sources.get("attio_records") or 0),
        ("Slack", sources.get("slack_messages") or 0),
        ("SEC",   1 if sources.get("sec_filings") else 0),
        ("Web",   sources.get("web_operations_used") or 0),
    ]
    pills = "".join(
        f'<span class="pill {"pill-zero" if not n else ""}">{esc(label)}'
        f' <span class="pill-val">{n}</span></span>'
        for label, n in pill_data
    )
    source_html = _section("◎", "Research Sources", f'<div class="pills">{pills}</div>')

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div class="banner">
  <div>
    <div class="banner-eyebrow">JOLLY.COM &middot; CONFIDENTIAL</div>
    <div class="banner-title">{esc(company)}</div>
    <div class="banner-sub">Company Cheat Sheet &middot; {today}</div>
  </div>
</div>
<div class="body">
{kpi_html}
{profile_html}
{breakdown_html}
{bench_html}
{source_html}
<div class="footer">
  <span>Jolly.com</span>
  <span>Confidential — Internal Use Only</span>
  <span>{today}</span>
</div>
</div>
</body></html>"""
```

**Step 2: Smoke-test with placeholder data**

```bash
python3 -c "
exec(open('.claude/scripts/cheatsheet_gen.py').read())
r = {
  'industry': 'Manufacturing',
  'company_basics': {'annual_revenue': 1e9, 'annual_revenue_source': '10-K', 'unit_count': 500, 'employee_count': 10000, 'geography': {'hq': 'Chicago, IL', 'states': ['IL','TX'], 'rank': '#2'}, 'employee_breakdown': {'manufacturing': 5000, 'corporate': 5000}},
  'attio_insights': {'founded': 1990, 'employee_range': '5k-10k'},
  'comps_benchmarks': {'ebitda_margin_pct': {'low':0.08,'mid':0.14,'high':0.22}, 'turnover_rate': 0.35},
  'source_summary': {'gong_calls_found': 2, 'attio_records': 1, 'slack_messages': 3},
  'slack_insights': [{'deal_stage': 'Discovery', 'primary_contact': 'Jane Doe'}],
}
html = build_company_html('Test Corp', r)
assert 'Test Corp' in html
assert 'Key Metrics' in html
assert 'Company Profile' in html
assert 'Industry Benchmarks' in html
assert 'Employee Breakdown' in html
assert 'Research Sources' in html
print('company HTML OK — all sections present')
"
```

Expected: `company HTML OK — all sections present`

**Step 3: Commit**

```bash
git add .claude/scripts/cheatsheet_gen.py
git commit -m "refactor: add build_company_html to cheatsheet_gen rewrite"
```

---

### Task 5: Meeting Prep page HTML builder

**Files:**
- Modify: `scripts/cheatsheet_gen.py` (append after `build_company_html`)

**Step 1: Add `build_meeting_prep_html()`**

```python
# ---------------------------------------------------------------------------
# Meeting Prep Page
# ---------------------------------------------------------------------------

def build_meeting_prep_html(company: str, research: dict) -> str:
    """Page 2: Pain points, quotes, deal context, objections, contacts, tech stack.

    All data sourced from research JSON — no API calls.
    """
    today = date.today().strftime("%B %d, %Y")
    gong  = research.get("gong_insights") or {}
    slack_list = research.get("slack_insights") or []
    slack = slack_list[0] if slack_list else {}

    sections = []

    # ── Quick Take (pain points) ──
    pain_points = gong.get("pain_points") or []
    if pain_points:
        items = "".join(f"<li>{esc(str(p))}</li>" for p in pain_points[:6])
        sections.append(_section("!", "Key Pain Points", f'<ul class="bullets">{items}</ul>'))

    # ── Lead With (verbatim quotes) ──
    quotes = gong.get("verbatim_quotes") or []
    call_date   = gong.get("call_date") or ""
    interviewee = gong.get("interviewee") or gong.get("call_title") or ""
    if quotes:
        blocks = ""
        for q in quotes[:3]:
            text = q if isinstance(q, str) else (q.get("text") or q.get("quote") or "")
            src  = q.get("source", "") if isinstance(q, dict) else (f"{interviewee} — {call_date}".strip(" — "))
            if text:
                src_tag = f'<div class="quote-src">{esc(src)}</div>' if src else ""
                blocks += f'<div class="quote">"{esc(text)}"{src_tag}</div>'
        if blocks:
            sections.append(_section("❝", "Lead With", blocks))

    # ── Deal Context (from Slack) ──
    deal_rows = []
    for key, label in [
        ("deal_stage",        "Deal Stage"),
        ("primary_contact",   "Primary Contact"),
        ("secondary_contact", "Secondary Contact"),
        ("next_steps",        "Next Steps"),
    ]:
        if slack.get(key):
            deal_rows.append((label, str(slack[key])))
    if deal_rows:
        rows_html = "".join(
            f'<div class="deal-row"><span class="deal-label">{esc(k)}</span><span>{esc(v)}</span></div>'
            for k, v in deal_rows
        )
        sections.append(_section("◑", "Deal Context", f'<div class="deal-box">{rows_html}</div>'))

    # ── Objections ──
    objections = gong.get("key_objections") or []
    if objections:
        items = "".join(f"<li>{esc(str(o))}</li>" for o in objections)
        sections.append(_section("⚑", "Known Objections", f'<ul class="bullets">{items}</ul>'))

    # ── Key Contacts ──
    champions = gong.get("champions") or []
    if champions:
        rows_html = ""
        for ch in champions:
            if isinstance(ch, dict):
                rows_html += (
                    f'<div class="champion-row">'
                    f'<div class="champ-name">{esc(ch.get("name",""))}</div>'
                    f'<div class="champ-title">{esc(ch.get("title",""))}</div>'
                    f'<div class="champ-note">{esc(ch.get("note",""))}</div>'
                    f'</div>'
                )
        if rows_html:
            sections.append(_section("✦", "Key Contacts", f'<div class="contacts-box">{rows_html}</div>'))

    # ── Tech Stack ──
    tech_stack = gong.get("tech_stack") or {}
    if tech_stack and isinstance(tech_stack, dict):
        rows_html = "".join(
            f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>"
            for k, v in tech_stack.items()
        )
        sections.append(_section("⚙", "Tech Stack", f'<table class="tech-table">{rows_html}</table>'))

    if not sections:
        sections.append('<p style="color:#666;padding:16px 0;font-size:11px;">No meeting prep data — run /deck-research first.</p>')

    body = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div class="banner">
  <div>
    <div class="banner-eyebrow">JOLLY.COM &middot; CONFIDENTIAL</div>
    <div class="banner-title">{esc(company)}</div>
    <div class="banner-sub">Meeting Prep &middot; {today}</div>
  </div>
</div>
<div class="body">
{body}
<div class="footer">
  <span>Jolly.com</span>
  <span>Confidential — Internal Use Only</span>
  <span>{today}</span>
</div>
</div>
</body></html>"""
```

**Step 2: Smoke-test**

```bash
python3 -c "
exec(open('.claude/scripts/cheatsheet_gen.py').read())
r = {
  'gong_insights': {
    'pain_points': ['Turnover is brutal', 'Scheduling chaos'],
    'verbatim_quotes': ['We lose 40pct of frontline staff yearly'],
    'champions': [{'name': 'Jane Doe', 'title': 'CFO', 'note': 'Key sponsor'}],
    'key_objections': ['Budget locked until Q3'],
    'tech_stack': {'Scheduling': 'HomeBase'},
  },
  'slack_insights': [{'deal_stage': 'Discovery', 'next_steps': 'Send ROI model'}],
}
html = build_meeting_prep_html('Test Corp', r)
assert 'Key Pain Points' in html
assert 'Lead With' in html
assert 'Deal Context' in html
assert 'Known Objections' in html
assert 'Key Contacts' in html
assert 'Tech Stack' in html
print('meeting prep HTML OK — all sections present')
"
```

Expected: `meeting prep HTML OK — all sections present`

**Step 3: Commit**

```bash
git add .claude/scripts/cheatsheet_gen.py
git commit -m "refactor: add build_meeting_prep_html to cheatsheet_gen rewrite"
```

---

### Task 6: Campaign page HTML builder

**Files:**
- Modify: `scripts/cheatsheet_gen.py` (append after `build_meeting_prep_html`)

**Step 1: Add `build_campaign_html()`**

```python
# ---------------------------------------------------------------------------
# Campaign Cheat Sheet
# ---------------------------------------------------------------------------

def build_campaign_html(company: str, research: dict, assumptions: dict) -> str:
    """Campaign cards sourced from research JSON campaign_details + campaigns_selected.

    `assumptions` is the dict returned by read_model_assumptions() — keyed by
    "assumptions__{campaign_slug}". Pass {} if Excel model not available.
    """
    today    = date.today().strftime("%B %d, %Y")
    campaigns = research.get("campaigns_selected") or []
    details   = research.get("campaign_details") or {}

    def _get_detail(name: str) -> dict:
        """Look up campaign_details by exact name, then case-insensitive."""
        if name in details:
            return details[name]
        name_lo = name.lower()
        for k, v in details.items():
            if k.lower() == name_lo:
                return v
        return {}

    def _get_assumptions(name: str) -> list:
        slug = slugify(name)
        rows = assumptions.get(f"assumptions__{slug}")
        if rows:
            return rows
        # Fuzzy: try all keys
        for k, v in assumptions.items():
            if k.startswith("assumptions__") and slug[:8] in k:
                return v
        return []

    normalised = []
    for c in campaigns:
        if isinstance(c, str):
            name = c
            d = _get_detail(name)
            normalised.append({
                "name": name,
                "priority": "standard",
                "evidence": "",
                "client_interest": "",
                "rops": d.get("rops_base"),
                "ebitda": d.get("ebitda_uplift_base"),
                "description": d.get("description") or "",
            })
        elif isinstance(c, dict):
            name = c.get("campaign_type") or c.get("name") or ""
            d = _get_detail(name)
            normalised.append({
                "name": name,
                "priority": c.get("priority") or "standard",
                "evidence": c.get("evidence") or c.get("evidence_source") or "",
                "client_interest": c.get("client_interest") or c.get("interest") or "",
                "rops": d.get("rops_base") or c.get("rops"),
                "ebitda": d.get("ebitda_uplift_base") or c.get("ebitda_impact"),
                "description": d.get("description") or "",
            })

    # ── Opportunity banner ──
    total_ebitda = sum(
        c["ebitda"] for c in normalised
        if isinstance(c.get("ebitda"), (int, float)) and c["ebitda"] > 0
    )
    rops_vals = [c["rops"] for c in normalised if isinstance(c.get("rops"), (int, float)) and c["rops"] > 0]
    avg_rops  = sum(rops_vals) / len(rops_vals) if rops_vals else None
    high_count = sum(1 for c in normalised if c["priority"].lower() == "high")

    opp_items = ""
    if total_ebitda:
        opp_items += f'<div class="opp-item"><div class="opp-v">{fmt(total_ebitda)}</div><div class="opp-l">Total EBITDA</div></div>'
    if avg_rops:
        opp_items += f'<div class="opp-item"><div class="opp-v">{avg_rops:.0f}x</div><div class="opp-l">Avg ROPS</div></div>'
    opp_items += f'<div class="opp-item"><div class="opp-v">{high_count}</div><div class="opp-l">High Priority</div></div>'
    opp_items += f'<div class="opp-item"><div class="opp-v">{len(normalised)}</div><div class="opp-l">Campaigns</div></div>'
    opp_banner = f'<div class="opp-banner">{opp_items}</div>' if normalised else ""

    # ── Campaign cards ──
    if not normalised:
        cards_html = '<p style="color:#666;padding:16px 0;font-size:11px;">No campaign data. Run /deck-research first.</p>'
    else:
        cards = []
        for c in normalised:
            name     = c["name"]
            priority = c["priority"].lower()
            is_high  = priority == "high"
            rops     = c["rops"]
            ebitda   = c["ebitda"]
            evidence = c["evidence"] or c["description"]
            interest = c["client_interest"]

            head_cls  = "c-head high" if is_high else "c-head"
            interest_badge = f'<span class="badge b-interest">{esc(str(interest).capitalize())}</span>' if interest else ""
            priority_badge = f'<span class="badge {"b-high" if is_high else "b-std"}">{"High Priority" if is_high else priority.capitalize()}</span>'

            rops_fmt   = f"{rops:.0f}x" if isinstance(rops, (int, float)) else (str(rops) if rops else "—")
            ebitda_fmt = fmt(ebitda) if ebitda else "—"

            stats_html = f"""<div class="c-stats">
  <div class="c-stat-item"><div class="c-stat-v">{esc(rops_fmt)}</div><div class="c-stat-l">ROPS</div></div>
  <div class="c-stat-item"><div class="c-stat-v">{esc(ebitda_fmt)}</div><div class="c-stat-l">Est. EBITDA</div></div>
</div>"""

            ev_block = f'<div class="evidence">"{esc(str(evidence))}"</div>' if evidence else ""

            # Assumptions
            assump_rows = _get_assumptions(name)
            assump_block = ""
            if assump_rows:
                sample = assump_rows[0]
                has_scenarios = len(sample) == 4 and any(r[2] or r[3] for r in assump_rows)
                if has_scenarios:
                    hdr = '<tr class="assump-hdr"><th>Assumption</th><th>Base</th><th>Upside</th><th>Downside</th></tr>'
                    row_cells = "".join(
                        f'<tr><td>{esc(lbl)}</td>'
                        f'<td class="col-base">{esc(b)}</td>'
                        f'<td class="col-up">{esc(u) if u else "—"}</td>'
                        f'<td class="col-dn">{esc(d) if d else "—"}</td></tr>'
                        for lbl, b, u, d in assump_rows
                    )
                    label_txt = "Model Assumptions — Base / Upside / Downside"
                else:
                    row_cells = "".join(
                        f'<tr><td>{esc(lbl)}</td><td class="col-base">{esc(b)}</td></tr>'
                        for lbl, b, *_ in assump_rows
                    )
                    label_txt = "Model Assumptions (Base)"
                tbl = f'<table class="assump-table">{hdr if has_scenarios else ""}{row_cells}</table>'
                assump_block = f'<div class="assumptions"><div class="assumptions-label">{label_txt}</div>{tbl}</div>'

            cards.append(f"""<div class="campaign">
  <div class="{head_cls}">
    <div class="c-title">{esc(name)}</div>
    <div class="c-badges">{interest_badge}{priority_badge}</div>
  </div>
  <div class="c-body">{stats_html}{ev_block}{assump_block}</div>
</div>""")
        cards_html = "\n".join(cards)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div class="banner">
  <div>
    <div class="banner-eyebrow">JOLLY.COM &middot; CONFIDENTIAL</div>
    <div class="banner-title">{esc(company)}</div>
    <div class="banner-sub">Campaign Overview &middot; {today}</div>
  </div>
</div>
<div class="body">
{opp_banner}
{cards_html}
<div class="footer">
  <span>Jolly.com</span>
  <span>Confidential — Internal Use Only</span>
  <span>{today}</span>
</div>
</div>
</body></html>"""
```

**Step 2: Smoke-test**

```bash
python3 -c "
exec(open('.claude/scripts/cheatsheet_gen.py').read())
r = {
  'campaigns_selected': [
    {'name': 'Employee Retention', 'priority': 'high', 'evidence': 'CFO cited 4M turnover', 'client_interest': 'Explicit'},
    {'name': 'Manager Engagement', 'priority': 'standard', 'evidence': 'Ops pain'},
  ],
  'campaign_details': {
    'Employee Retention': {'rops_base': 12.5, 'ebitda_uplift_base': 3000000, 'description': 'Reduce turnover'},
    'Manager Engagement': {'rops_base': 8.0, 'ebitda_uplift_base': 960000},
  },
}
assumptions = {
  'assumptions__employee_retention': [('Turnover Rate', '35%', '40%', '30%'), ('Program Cost', '\$240K', '\$200K', '\$280K')],
}
html = build_campaign_html('Test Corp', r, assumptions)
assert 'Employee Retention' in html
assert '12x' in html or '12.5' in html or 'ROPS' in html
assert 'Total EBITDA' in html
assert 'Assumption' in html
print('campaign HTML OK')
"
```

Expected: `campaign HTML OK`

**Step 3: Commit**

```bash
git add .claude/scripts/cheatsheet_gen.py
git commit -m "refactor: add build_campaign_html to cheatsheet_gen rewrite"
```

---

### Task 7: PDF renderer and main()

**Files:**
- Modify: `scripts/cheatsheet_gen.py` (append at end)

**Step 1: Add renderer + main**

```python
# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------

def render_with_weasyprint(html: str, pdf_path: str) -> bool:
    try:
        weasyprint.HTML(string=html).write_pdf(pdf_path)
        return True
    except Exception as e:
        print(f"  WeasyPrint failed: {e}")
        return False


def render_with_playwright(html: str, pdf_path: str) -> bool:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 816, "height": 1056})
                page.set_content(html, wait_until="networkidle")
                page.pdf(
                    path=pdf_path,
                    format="Letter",
                    print_background=True,
                    margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
                )
            finally:
                browser.close()
        return True
    except Exception as e:
        print(f"  Playwright failed: {e}")
        return False


def render_pdf(html: str, pdf_path: str) -> bool:
    """Try WeasyPrint, then Playwright, then save HTML as fallback."""
    if WEASYPRINT_AVAILABLE:
        print("  Renderer: WeasyPrint")
        if render_with_weasyprint(html, pdf_path):
            return True
    if PLAYWRIGHT_AVAILABLE:
        print("  Renderer: Playwright (fallback)")
        if render_with_playwright(html, pdf_path):
            return True
    # HTML fallback — always succeeds
    html_path = str(pdf_path).replace(".pdf", ".html")
    Path(html_path).write_text(html, encoding="utf-8")
    print(f"  PDF renderer not available. Saved HTML to: {html_path}")
    print(f"  Open in browser and use Ctrl+P → Save as PDF")
    print(f"  To install renderer: pip install weasyprint")
    return False


def _combine_pages(*page_htmls: str) -> str:
    """Combine multiple page HTML documents into a single printable document."""
    # Extract body content from each page and join with page breaks
    bodies = []
    for html in page_htmls:
        # Find <body> ... </body>
        start = html.find("<body>")
        end   = html.rfind("</body>")
        if start != -1 and end != -1:
            bodies.append(html[start + 6:end].strip())

    # Use CSS from first page
    css_start = page_htmls[0].find("<style>")
    css_end   = page_htmls[0].find("</style>") + 8
    css_block = page_htmls[0][css_start:css_end] if css_start != -1 else f"<style>{CSS}</style>"

    combined_body = '\n<div class="page-break"></div>\n'.join(bodies)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">{css_block}</head>
<body>{combined_body}</body></html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate cheat sheets for intro deck")
    parser.add_argument("--company", required=True, help="Company name (must match client folder)")
    parser.add_argument("--client-path", default=None, help="Override client folder path")
    args = parser.parse_args()
    company = args.company

    print(f"\n=== cheatsheet_gen.py | {company} ===\n")

    if not OPENPYXL_AVAILABLE:
        print("WARNING: openpyxl not installed — assumptions table will be empty.")
        print("  Run: pip install openpyxl\n")

    cfg = get_workspace_config()
    client_root = cfg.get("client_root", "Clients")
    client_base = Path(args.client_path) if args.client_path else Path(client_root) / company

    # ── Load research JSON ──
    try:
        research = find_research_json(company, base_path=str(client_base))
        print(f"  Research date: {research.get('research_date', 'unknown')}")
    except FileNotFoundError as e:
        print(f"  WARNING: {e}")
        print("  Generating cheat sheet with empty data — run /deck-research first.")
        research = {
            "company_name": company, "company_basics": {}, "attio_insights": {},
            "gong_insights": {}, "slack_insights": [], "campaigns_selected": [],
            "campaign_details": {}, "comps_benchmarks": {}, "source_summary": {},
        }

    # ── Load assumptions from Excel (optional) ──
    assumptions = {}
    if OPENPYXL_AVAILABLE:
        try:
            model_path = find_model(company, base_path=str(client_base))
            assumptions = read_model_assumptions(model_path)
            print(f"  Model: {Path(model_path).name} ({len(assumptions)} assumption groups)")
        except FileNotFoundError as e:
            print(f"  WARNING: {e} — assumptions table will be empty.")

    # ── Build HTML pages ──
    out_dir = client_base / "4. Reports" / "Cheat Sheets"
    out_dir.mkdir(parents=True, exist_ok=True)

    company_html  = build_company_html(company, research)
    meeting_html  = build_meeting_prep_html(company, research)
    campaign_html = build_campaign_html(company, research, assumptions)

    combined_html = _combine_pages(company_html, meeting_html, campaign_html)

    pdf_path = out_dir / f"{company} Cheat Sheet.pdf"
    print("\nRendering Cheat Sheet...")
    ok = render_pdf(combined_html, str(pdf_path))

    if ok:
        print(f"\n  Saved: {pdf_path}")
        print(f'\n  Open with: start "" "{pdf_path}"')
    print("\nDone.")


if __name__ == "__main__":
    main()
```

**Step 2: Verify the full script parses and --help works**

```bash
python3 .claude/scripts/cheatsheet_gen.py --help
```

Expected output includes `--company` and `--client-path`.

**Step 3: Run end-to-end smoke test with a fake research JSON**

```bash
python3 -c "
import json, tempfile, os, sys
from pathlib import Path

# Create temp workspace
tmp = Path(tempfile.mkdtemp())
company = 'SmokeTest Corp'
base = tmp / company
(base / '4. Reports' / 'Cheat Sheets').mkdir(parents=True)
(base / '4. Reports').mkdir(parents=True, exist_ok=True)

research = {
  'company_name': company, 'research_date': '2026-02-27',
  'industry': 'Manufacturing',
  'company_basics': {'annual_revenue': 1e9, 'unit_count': 500, 'employee_count': 10000,
    'unit_count_label': 'Facilities',
    'geography': {'hq': 'Chicago, IL', 'states': ['IL','TX'], 'rank': '#2'},
    'employee_breakdown': {'manufacturing': 5000, 'corporate': 5000}},
  'attio_insights': {'founded': 1990},
  'gong_insights': {
    'pain_points': ['High turnover', 'Manual processes'],
    'verbatim_quotes': ['Turnover is killing us'],
    'champions': [{'name': 'Jane Doe', 'title': 'CFO', 'note': 'Sponsor'}],
    'key_objections': ['Q3 budget freeze'],
    'tech_stack': {'Scheduling': 'HomeBase'},
  },
  'slack_insights': [{'deal_stage': 'Discovery', 'next_steps': 'Send model'}],
  'campaigns_selected': [
    {'name': 'Employee Retention', 'priority': 'high', 'evidence': 'CFO pain', 'client_interest': 'Explicit'},
  ],
  'campaign_details': {
    'Employee Retention': {'rops_base': 12.5, 'ebitda_uplift_base': 3000000}
  },
  'comps_benchmarks': {'ebitda_margin_pct': {'low':0.08,'mid':0.14,'high':0.22}},
  'source_summary': {'gong_calls_found': 2, 'attio_records': 1, 'slack_messages': 3},
}
(base / '4. Reports' / f'research_output_smoketest_corp.json').write_text(json.dumps(research))

sys.argv = ['cheatsheet_gen.py', '--company', company, '--client-path', str(base)]
exec(open('.claude/scripts/cheatsheet_gen.py').read())
main()
" 2>&1
```

Expected: Script runs, produces either a PDF or `.html` file (depending on whether WeasyPrint is installed). No tracebacks. All three pages render with expected sections.

**Step 4: Commit**

```bash
git add .claude/scripts/cheatsheet_gen.py
git commit -m "refactor: add renderer and main() to cheatsheet_gen rewrite — rewrite complete"
```

---

### Task 8: Update skill references and requirements

**Files:**
- Modify: `skills/deck-format/SKILL.md`
- Modify: `skills/deck-auto/SKILL.md`
- Modify: `requirements.txt` or equivalent

**Step 1: Check current cheatsheet invocation in deck-format**

```bash
grep -n -A5 "cheatsheet" .claude/skills/deck-format/SKILL.md
```

**Step 2: Update deck-format cheatsheet step**

Find the step that runs `cheatsheet_gen.py` (Step 10 in deck-format). Update the failure message to mention WeasyPrint:

```
If the script fails (missing packages or no research data), tell the user:

Cheat sheet generation failed: [error].
Install renderer: pip install weasyprint
Or run manually: python3 .claude/scripts/cheatsheet_gen.py --company "[COMPANY_NAME]"
```

**Step 3: Check requirements file exists**

```bash
ls requirements*.txt 2>/dev/null || echo "no requirements file"
```

If `requirements.txt` exists, add `weasyprint` to it. If not, skip — install instructions are in the script docstring.

**Step 4: Commit**

```bash
git add .claude/skills/deck-format/SKILL.md .claude/skills/deck-auto/SKILL.md
git commit -m "refactor: update skill references for cheatsheet_gen rewrite"
```

---

### Task 9: Bump version to v3.2.0

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `../jolly-marketplace/.claude-plugin/marketplace.json`

**Step 1: Bump plugin.json**

In `.claude-plugin/plugin.json`, update `"version": "3.1.2"` → `"version": "3.2.0"`.

**Step 2: Commit plugin repo**

```bash
git add .claude-plugin/plugin.json
git commit -m "chore: bump version to v3.2.0 — cheatsheet rewrite"
```

**Step 3: Create GitHub release**

```bash
git tag v3.2.0
git push origin main --tags
gh release create v3.2.0 --title "v3.2.0 — Cheatsheet Rewrite" --notes "$(cat <<'EOF'
## What's new

- **Rewrote cheatsheet_gen.py** from 2,171 lines to ~550 lines
- **No runtime API calls** — all data sourced from research_output JSON written by deck-research + deck-model
- **WeasyPrint renderer** with Playwright fallback and HTML-save fallback (never hard-fails)
- **Meeting Prep page** replaces Claude-generated Meeting Intelligence — uses Gong/Slack data already collected
- **campaign_details as source of truth** for ROPS/EBITDA — eliminates Excel file locking issues
- **Removed**: vertical config system, Claude API call at render time, Playwright-only header injection
EOF
)"
```

**Step 4: Sync marketplace**

In `jolly-marketplace/.claude-plugin/marketplace.json`, update the opportunity-analysis plugin entry:
- `"version": "3.2.0"`
- `"ref": "v3.2.0"`

```bash
cd ../jolly-marketplace
git add .claude-plugin/marketplace.json
git commit -m "Bump opportunity-analysis to v3.2.0"
git push
```
