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
        return str(v)
    sign = "-" if v < 0 else ""
    av = abs(v)
    if 0 < av < 1:
        return f"{v * 100:.1f}%"
    if av == 0:
        return f"{prefix}0" if prefix else "0"
    if av >= 1_000_000_000:
        return f"{sign}{prefix}{av / 1_000_000_000:.1f}B"
    if av >= 1_000_000:
        return f"{sign}{prefix}{av / 1_000_000:.1f}M"
    if av >= 1_000:
        return f"{sign}{prefix}{av / 1_000:.1f}K"
    if v == int(v):
        return f"{sign}{prefix}{int(av)}"
    return f"{sign}{prefix}{av:.2f}" if prefix else str(round(av, 2))


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
        f'<div class="section-label"><span class="s-icon">{esc(icon)}</span>{esc(title)}</div>'
        f'{content}'
        f'</div>'
    )


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

/* ── Banner ── */
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

/* Table header */
.assump-hdr th, .objection-hdr td {{
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

/* ── Pills ── */
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
    revenue    = basics.get("annual_revenue")
    units      = basics.get("unit_count")
    employees  = basics.get("employee_count")
    unit_label = basics.get("unit_count_label") or "Locations"

    def _src_tag(field):
        s = basics.get(f"{field}_source") or ""
        return f'<div class="kpi-src">{esc(s)}</div>' if s else ""

    kpi_content = (
        f'<div class="kpi-strip">'
        f'<div class="kpi-card"><div class="kpi-v">{fmt(revenue)}</div>'
        f'<div class="kpi-l">Annual Revenue</div>{_src_tag("annual_revenue")}</div>'
        f'<div class="kpi-card"><div class="kpi-v">{fmt_plain(units)}</div>'
        f'<div class="kpi-l">{esc(unit_label)}</div>{_src_tag("unit_count")}</div>'
        f'<div class="kpi-card"><div class="kpi-v">{fmt_plain(employees)}</div>'
        f'<div class="kpi-l">Employees</div>{_src_tag("employee_count")}</div>'
        f'</div>'
    )
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
            if key == "estimated_arr_usd":
                display = fmt(v)
            elif isinstance(v, list):
                display = ", ".join(str(x) for x in v)
            else:
                display = str(v)
            profile_rows.append((label, display))
    slack_list = research.get("slack_insights") or []
    slack = slack_list[0] if slack_list else {}
    for key, label in [("deal_stage", "Deal Stage"), ("primary_contact", "Primary Contact")]:
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
            f'<div class="bk-cell"><div class="bk-v">{fmt_plain(v)}</div>'
            f'<div class="bk-l">{esc(k.replace("_", " ").title())}</div></div>'
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

    return (
        f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head>'
        f'<body>'
        f'<div class="banner"><div>'
        f'<div class="banner-eyebrow">JOLLY.COM &middot; CONFIDENTIAL</div>'
        f'<div class="banner-title">{esc(company)}</div>'
        f'<div class="banner-sub">Company Cheat Sheet &middot; {today}</div>'
        f'</div></div>'
        f'<div class="body">'
        f'{kpi_html}{profile_html}{breakdown_html}{bench_html}{source_html}'
        f'<div class="footer">'
        f'<span>Jolly.com</span><span>Confidential — Internal Use Only</span><span>{today}</span>'
        f'</div>'
        f'</div></body></html>'
    )
