# Cheatsheet Rewrite Design
**Date:** 2026-02-27
**Status:** Approved

## Problem

`cheatsheet_gen.py` is 2,171 lines and produces empty sections because:
1. **Vertical config system fails silently** — `load_vertical_config()` looks for `Templates/Cheat Sheets/report_config_{vertical}.json`. If missing, it calls Claude API, falls back to a generator, and if either returns `{}`, all profile/benchmark sections render empty.
2. **Meeting Intelligence calls Claude at runtime** — requires `ANTHROPIC_API_KEY` in env; returns `{}` if absent, silently dropping the section.
3. **Config-driven field paths** — `_deep_get()` with dot-notation strings from JSON config breaks silently when research schema differs slightly.

## Approach

Rewrite with WeasyPrint for PDF rendering. ~550 lines. No runtime API calls.

## Architecture

```
cheatsheet_gen.py (~550 lines)
├── Brand colors (~15 lines)
├── Helpers: fmt, esc, slugify, deep_get (~50 lines)
├── Data loaders
│   ├── get_workspace_config()
│   ├── find_research_json()       — reads research_output_[slug].json
│   ├── find_model()               — kept for assumptions table only
│   └── read_model_basics()        — Excel parsing for scenario assumptions only
├── CSS (~200 lines, consolidated)
├── _section(icon, title, content) — single section wrapper helper
├── build_company_html()           — ~100 lines
├── build_campaign_html()          — ~70 lines
├── render_pdf()                   — WeasyPrint → Playwright → HTML fallback
└── main()                         — ~40 lines
```

## Data Sources

All data read from `research_output_[company_slug].json` written by deck-research + deck-model phases. No runtime Claude API calls.

| Section | Source field |
|---------|-------------|
| KPI strip | `company_basics.annual_revenue`, `.unit_count`, `.employee_count` |
| Company Profile | `company_basics.*`, `attio_insights.*` |
| Employee Breakdown | `company_basics.employee_breakdown` |
| Industry Benchmarks | `comps_benchmarks.*` |
| Meeting Prep — Quick Take | `gong_insights.pain_points` (top 3) |
| Meeting Prep — Lead With | `gong_insights.verbatim_quotes` (top 3) |
| Meeting Prep — Deal Context | `slack_insights[0].deal_stage`, `.next_steps` |
| Meeting Prep — Objections | `gong_insights.key_objections` |
| Key Contacts | `gong_insights.champions` |
| Tech Stack | `gong_insights.tech_stack` |
| Research Sources | `source_summary.*` |
| Campaign cards | `campaigns_selected` + `campaign_details` (ROPS, EBITDA from deck-model) |
| Assumptions table | Excel model Inputs sheet — scenario rows only |

## Pages / Sections

- **Page 1 — Company Snapshot:** KPIs, Company Profile, Employee Breakdown, Industry Benchmarks
- **Page 2 — Meeting Prep:** Quick Take (pain points), Lead With (quotes), Deal Context (Slack), Objections, Key Contacts, Tech Stack, Research Sources
- **Page 3+ — Campaigns:** one card per campaign — name, priority badge, ROPS, EBITDA, evidence, client interest, assumptions table

## Renderer

`render_pdf()` tries in order:
1. **WeasyPrint** (`pip install weasyprint`) — primary
2. **Playwright** — if already installed
3. **Save HTML** — prints open instructions, never silently fails

## Removed from current code

- `load_vertical_config()` and all report config JSON machinery (~150 lines)
- `_generate_meeting_intelligence()` and `_call_claude_api()` (~110 lines)
- `_generate_config_with_claude()` and `_generate_config_fallback()` (~150 lines)
- `_build_header_template()` (Playwright-specific header injection, ~40 lines)
- `save_templates()` and `PLACEHOLDER_RESEARCH` (~60 lines)
- `fmt_bench()` — dead code (~15 lines)
- `.cover` CSS — unused (~35 lines)
- `_extract_body_div()` — only needed for Playwright header injection (~15 lines)

## Key Design Decisions

1. **No config files** — profile fields rendered directly from populated research JSON keys, not driven by a vertical config. If a field is present and non-null, it shows. No silent failures from missing config.
2. **No runtime API calls** — deck-research already gathered all intelligence. Cheatsheet is a renderer, not a researcher.
3. **`campaign_details` as source of truth for numbers** — deck-model writes ROPS/EBITDA to research JSON to avoid Excel file locking. Cheatsheet reads from there.
4. **Assumptions from Excel** — scenario table is the one thing that must come from the model directly (it's not written to research JSON).
5. **Renderer is a fallback chain** — never hard-fails; always produces something.
