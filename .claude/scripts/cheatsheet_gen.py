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
