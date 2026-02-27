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
            import shutil as _shutil
            _shutil.copy2(model_path, tmp_path)
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
