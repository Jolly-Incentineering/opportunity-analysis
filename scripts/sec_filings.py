"""
sec_filings.py - Pull financial data for a public company via EdgarTools
=============================================================================
Usage:
  python .claude/scripts/sec_filings.py --ticker WING
  python .claude/scripts/sec_filings.py --ticker WING --output .claude/data/sec_WING.json

Output: JSON with revenue, operating income, net income across last 4 filings,
        plus growth trend and EBITDA margin estimate.

Requires: pip install edgartools
SEC_IDENTITY must be set in .claude/.env  (e.g.  SEC_IDENTITY=you@company.com)

API strategy (per edgartools docs — Choosing the Right API):
  1. company.get_facts()     — fastest, cached, for summary metrics
  2. company.get_financials() — multi-period standardized statements
  3. Per-filing fallback      — filing.obj().financials.income_statement()
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import argparse
import json
import os
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_identity():
    ws = Path(os.environ.get('JOLLY_WORKSPACE', '.')).resolve()
    env_path = ws / '.claude' / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if line.startswith('SEC_IDENTITY='):
                return line.split('=', 1)[1].strip()
    return os.environ.get('SEC_IDENTITY', 'research@company.com')


def safe_pct(a, b):
    """Return (a-b)/b as a float, or None if inputs are invalid."""
    try:
        if a and b and b != 0:
            return round((a - b) / abs(b), 4)
    except Exception:
        pass
    return None


def safe_int(val):
    """Convert a value to int, returning None for NaN/None."""
    if val is None:
        return None
    try:
        import math
        if math.isnan(val):
            return None
        return int(val)
    except (TypeError, ValueError):
        return None


def extract_from_facts(company):
    """Use Company Facts API (fastest, cached) for summary metrics."""
    try:
        facts = company.get_facts()
        return {
            'revenue':       safe_int(getattr(facts, 'get_revenue', lambda: None)()),
            'net_income':    safe_int(getattr(facts, 'get_net_income', lambda: None)()),
            'total_assets':  safe_int(getattr(facts, 'get_total_assets', lambda: None)()),
            'equity':        safe_int(getattr(facts, 'get_shareholders_equity', lambda: None)()),
        }, None
    except Exception as e:
        return {}, f'get_facts error: {e}'


def extract_from_financials(company):
    """Use Financials API (multi-period standardized statements)."""
    try:
        financials = company.get_financials()
        income = financials.income_statement()
        df = income.to_dataframe()
        return df, None
    except Exception as e:
        return None, f'get_financials error: {e}'


def extract_from_filing(filing):
    """Per-filing fallback using filing.obj().financials.income_statement()."""
    try:
        report = filing.obj()
        # Modern API: report.financials.income_statement()
        if hasattr(report, 'financials'):
            inc = report.financials.income_statement()
        else:
            # Legacy fallback
            inc = report.income_statement
        df = inc.to_dataframe()
        return df, None
    except Exception as e:
        return None, f'filing parse error: {e}'


# Key XBRL concepts for the per-filing fallback approach
KEY_CONCEPTS = {
    'revenue':          'us-gaap_Revenues',
    'operating_income': 'us-gaap_OperatingIncomeLoss',
    'net_income':       'us-gaap_NetIncomeLoss',
    'gross_profit':     'us-gaap_GrossProfit',
    'cost_of_revenue':  'us-gaap_CostOfRevenue',
    'sga':              'us-gaap_SellingGeneralAndAdministrativeExpense',
}

METADATA_COLS = {
    'concept', 'label', 'standard_concept', 'level', 'abstract',
    'dimension', 'is_breakdown', 'dimension_axis', 'dimension_member',
    'dimension_member_label', 'dimension_label', 'balance', 'weight',
    'preferred_sign', 'parent_concept', 'parent_abstract_concept',
}


def parse_df_to_financials(df):
    """Extract key financials from a statement DataFrame."""
    period_cols = [c for c in df.columns if c not in METADATA_COLS]

    # Top-level, non-segmented rows only
    mask = True
    for col in ['abstract', 'dimension', 'is_breakdown']:
        if col in df.columns:
            mask = mask & (df[col] == False)
    clean = df[mask] if not isinstance(mask, bool) else df

    result = {}
    for key, concept in KEY_CONCEPTS.items():
        row = clean[clean['concept'] == concept] if 'concept' in clean.columns else clean[clean.index == concept]
        if not row.empty:
            result[key] = {
                col: safe_int(row.iloc[0][col])
                for col in period_cols
            }

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Pull SEC financials via EdgarTools')
    parser.add_argument('--ticker', required=True, help='Stock ticker (e.g. WING)')
    parser.add_argument('--output', help='Write JSON output to this file path')
    parser.add_argument('--include-text', action='store_true',
                        help='Extract MD&A and business section text from most recent 10-K')
    parser.add_argument('--save-pdf', action='store_true',
                        help='Save most recent 10-K as PDF (requires --output; falls back to HTML if WeasyPrint unavailable)')
    args = parser.parse_args()

    try:
        from edgar import Company, set_identity
    except ImportError:
        print(json.dumps({'error': 'edgartools not installed. Run: python -m pip install edgartools'}))
        sys.exit(1)

    set_identity(get_identity())

    # --- Look up company ---
    try:
        company = Company(args.ticker.upper())
    except Exception as e:
        print(json.dumps({'error': f'Company not found for ticker {args.ticker}: {e}', 'is_public': False}))
        sys.exit(0)

    if not company:
        print(json.dumps({'error': f'No EDGAR record for ticker {args.ticker}', 'is_public': False}))
        sys.exit(0)

    output = {
        'ticker':         args.ticker.upper(),
        'company_name':   company.name,
        'is_public':      True,
        'retrieved_at':   datetime.today().strftime('%Y-%m-%d'),
        'filings':        [],
        'facts_summary':  {},
        'summary':        {},
        'notes':          [],
        'api_used':       'unknown',
    }

    # --- Approach 1: Company Facts API (fastest, cached) ---
    facts_data, facts_err = extract_from_facts(company)
    if facts_err:
        output['notes'].append(f'Facts API: {facts_err}')
    else:
        output['facts_summary'] = facts_data

    # --- Approach 2: Get filing metadata for per-filing details ---
    revenues_by_period = {}
    try:
        annual_filing = company.get_filings(form='10-K').latest(1)
        quarters      = company.get_filings(form='10-Q').latest(3)
        all_filings   = [(annual_filing, '10-K')] + [(q, '10-Q') for q in quarters]
    except Exception as e:
        output['notes'].append(f'Could not retrieve filings: {e}')
        all_filings = []

    for filing, form_type in all_filings:
        period   = str(getattr(filing, 'period_of_report', 'unknown'))
        filed_on = str(getattr(filing, 'filing_date',       'unknown'))

        entry = {
            'form':          form_type,
            'period':        period,
            'filed':         filed_on,
            'filing_url':    getattr(filing, 'filing_url', None),
            'financials':    {},
            'parse_error':   None,
        }

        # Use per-filing extraction with modern API
        df, err = extract_from_filing(filing)
        if err:
            entry['parse_error'] = err
            output['notes'].append(f'{form_type} {period}: {err}')
        elif df is not None:
            financials = parse_df_to_financials(df)
            entry['financials'] = financials
            output['api_used'] = 'per_filing'

            rev_data = financials.get('revenue', {})
            if rev_data:
                primary_period = max(rev_data.keys())
                rev_val = rev_data.get(primary_period)
                if rev_val:
                    revenues_by_period[period] = rev_val

        output['filings'].append(entry)

    # --- Build summary from most recent filing ---
    if output['filings']:
        latest = output['filings'][0]
        fin    = latest.get('financials', {})

        def most_recent_val(concept_key):
            data = fin.get(concept_key, {})
            if not data:
                return None
            return data.get(max(data.keys()))

        revenue   = most_recent_val('revenue')
        op_income = most_recent_val('operating_income')
        net_inc   = most_recent_val('net_income')
        gp        = most_recent_val('gross_profit')

        ebitda_est = op_income

        rev_yoy = None
        rev_data = fin.get('revenue', {})
        if rev_data and len(rev_data) >= 2:
            periods_sorted = sorted(rev_data.keys(), reverse=True)
            rev_yoy = safe_pct(rev_data[periods_sorted[0]], rev_data[periods_sorted[1]])

        trend = [
            {'period': p, 'revenue': v}
            for p, v in sorted(revenues_by_period.items(), reverse=True)
        ]

        op_margin = round(op_income / revenue, 4) if (revenue and op_income) else None

        # Prefer facts_summary if per-filing revenue is missing
        if not revenue and output['facts_summary'].get('revenue'):
            revenue = output['facts_summary']['revenue']
            output['notes'].append('Revenue from Company Facts API (per-filing parse failed).')
        if not net_inc and output['facts_summary'].get('net_income'):
            net_inc = output['facts_summary']['net_income']
            output['notes'].append('Net income from Company Facts API (per-filing parse failed).')

        output['summary'] = {
            'most_recent_period':       latest.get('period'),
            'most_recent_form':         latest.get('form'),
            'revenue':                  revenue,
            'operating_income':         op_income,
            'net_income':               net_inc,
            'gross_profit':             gp,
            'ebitda_estimate':          ebitda_est,
            'operating_margin_pct':     op_margin,
            'revenue_yoy_growth':       rev_yoy,
            'revenue_trend_4_periods':  trend,
        }

    output['notes'].extend([
        'EBITDA estimate = operating income only. '
        'Add back D&A from cash flow statement for true EBITDA.',
        'Use 10-K revenue as the annual figure for the model. '
        '10-Q revenues are YTD (cumulative), not single-quarter — do not sum them.',
    ])

    # --- Optional: extract filing text (MD&A + business) for unit/employee count ---
    if args.include_text and all_filings:
        annual_filing = next((f for f, ft in all_filings if ft == '10-K'), None)
        if annual_filing:
            try:
                report = annual_filing.obj()
                # edgartools TenK exposes section text as attributes
                mda      = str(getattr(report, 'mda',      None) or '')[:8000]
                business = str(getattr(report, 'business', None) or '')[:8000]
                output['filing_text'] = {'mda': mda, 'business': business}
            except Exception as e:
                output['filing_text'] = {'error': str(e)}
        else:
            output['filing_text'] = {'error': 'no 10-K in filing list'}

    # --- Optional: save 10-K filing as PDF (or HTML fallback) ---
    if args.save_pdf and all_filings:
        if not args.output:
            output['notes'].append('--save-pdf ignored: requires --output to determine save directory.')
        else:
            annual = next((f for f, ft in all_filings if ft == '10-K'), None)
            if annual:
                out_dir  = Path(args.output).parent
                ticker   = args.ticker.upper()
                period   = str(getattr(annual, 'period_of_report', 'unknown'))
                stem     = f"10K_{ticker}_{period}"
                saved    = {}
                try:
                    html = annual.html()
                    if not html:
                        raise ValueError('filing.html() returned empty content')
                    html_path = out_dir / f"{stem}.html"
                    html_path.write_text(html, encoding='utf-8')
                    saved['html'] = str(html_path)
                    # Attempt PDF conversion via WeasyPrint
                    try:
                        from weasyprint import HTML as WP_HTML
                        pdf_path = out_dir / f"{stem}.pdf"
                        WP_HTML(string=html, base_url=str(out_dir)).write_pdf(str(pdf_path))
                        saved['pdf'] = str(pdf_path)
                        html_path.unlink()          # PDF succeeded — no need to keep HTML
                        del saved['html']
                    except ImportError:
                        saved['note'] = 'WeasyPrint not installed; saved as HTML. Run: pip install weasyprint'
                    except Exception as e:
                        saved['pdf_error'] = str(e)
                        saved['note']      = 'PDF conversion failed; HTML retained.'
                except Exception as e:
                    saved['error'] = str(e)
                output['filing_save'] = saved
            else:
                output['filing_save'] = {'error': 'no 10-K in filing list'}

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        output['saved_to'] = str(out_path)

    result_json = json.dumps(output, indent=2)
    print(result_json)

    if args.output:
        out_path.write_text(result_json, encoding='utf-8')


if __name__ == '__main__':
    main()
