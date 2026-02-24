"""
sec_filings.py - Pull last 4 SEC filings for a public company via EdgarTools
=============================================================================
Usage:
  python .claude/scripts/sec_filings.py --ticker WING
  python .claude/scripts/sec_filings.py --ticker WING --output .claude/data/sec_WING.json

Output: JSON with revenue, operating income, net income across last 4 filings,
        plus growth trend and EBITDA margin estimate.

Requires: pip install edgartools
SEC_IDENTITY must be set in .claude/.env  (e.g.  SEC_IDENTITY=you@company.com)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import argparse
import json
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

KEY_CONCEPTS = {
    'revenue':          'us-gaap_Revenues',
    'operating_income': 'us-gaap_OperatingIncomeLoss',
    'net_income':       'us-gaap_NetIncomeLoss',
    'gross_profit':     'us-gaap_GrossProfit',
    'cost_of_revenue':  'us-gaap_CostOfRevenue',
    'sga':              'us-gaap_SellingGeneralAndAdministrativeExpense',
}

# Period columns look like dates; exclude known metadata columns
METADATA_COLS = {
    'concept', 'label', 'standard_concept', 'level', 'abstract',
    'dimension', 'is_breakdown', 'dimension_axis', 'dimension_member',
    'dimension_member_label', 'dimension_label', 'balance', 'weight',
    'preferred_sign', 'parent_concept', 'parent_abstract_concept',
}


def get_identity():
    env_path = Path('.claude/.env')
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if line.startswith('SEC_IDENTITY='):
                return line.split('=', 1)[1].strip()
    # Fallback — SEC requires a contact email in User-Agent
    return 'nishant@jolly.com'


def extract_financials(report):
    """Return dict of {concept_key: {period: value}} from a TenQ/TenK report."""
    try:
        inc = report.income_statement
        df = inc.to_dataframe()
    except Exception as e:
        return {}, f'income_statement parse error: {e}'

    # Period columns are everything that isn't a metadata column
    period_cols = [c for c in df.columns if c not in METADATA_COLS]

    # Top-level, non-segmented rows only
    clean = df[
        (df['abstract'] == False) &
        (df['dimension'] == False) &
        (df['is_breakdown'] == False)
    ]

    result = {}
    for key, concept in KEY_CONCEPTS.items():
        row = clean[clean['concept'] == concept]
        if not row.empty:
            result[key] = {
                col: (None if row.iloc[0][col] != row.iloc[0][col]   # NaN check
                      else int(row.iloc[0][col]))
                for col in period_cols
            }

    return result, None


def safe_pct(a, b):
    """Return (a-b)/b as a float, or None if inputs are invalid."""
    try:
        if a and b and b != 0:
            return round((a - b) / abs(b), 4)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Pull last 4 SEC filings via EdgarTools')
    parser.add_argument('--ticker', required=True, help='Stock ticker (e.g. WING)')
    parser.add_argument('--output', help='Write JSON output to this file path')
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

    # --- Get last 4 filings (1 annual + 3 quarterly preferred) ---
    # Note: latest(1) returns a single EntityFiling; latest(N>1) returns EntityFilings
    try:
        annual_filing = company.get_filings(form='10-K').latest(1)
        quarters      = company.get_filings(form='10-Q').latest(3)
        all_filings   = [(annual_filing, '10-K')] + [(q, '10-Q') for q in quarters]
    except Exception as e:
        print(json.dumps({'error': f'Could not retrieve filings: {e}', 'ticker': args.ticker}))
        sys.exit(0)

    output = {
        'ticker':         args.ticker.upper(),
        'company_name':   company.name,
        'is_public':      True,
        'retrieved_at':   datetime.today().strftime('%Y-%m-%d'),
        'filings':        [],
        'summary':        {},
        'notes':          [],
    }

    revenues_by_period = {}   # period -> revenue (for trend calc across filings)

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

        try:
            report = filing.obj()
            financials, err = extract_financials(report)
            if err:
                entry['parse_error'] = err
                output['notes'].append(f'{form_type} {period}: {err}')
            else:
                entry['financials'] = financials
                # Collect revenue for the primary reporting period
                rev_data = financials.get('revenue', {})
                if rev_data:
                    primary_period = max(rev_data.keys())   # most recent column
                    rev_val = rev_data.get(primary_period)
                    if rev_val:
                        revenues_by_period[period] = rev_val
        except Exception as e:
            entry['parse_error'] = str(e)
            output['notes'].append(f'{form_type} {period}: unhandled error - {e}')

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

        # EBITDA estimate = operating income (D&A not in standard XBRL income stmt)
        ebitda_est = op_income  # caller should add back D&A from cash flow if needed

        # Revenue growth vs. prior year comparison period (second column in same filing)
        rev_yoy = None
        rev_data = fin.get('revenue', {})
        if rev_data and len(rev_data) >= 2:
            periods_sorted = sorted(rev_data.keys(), reverse=True)
            rev_yoy = safe_pct(rev_data[periods_sorted[0]], rev_data[periods_sorted[1]])

        # Revenue trend across the 4 filings
        trend = [
            {'period': p, 'revenue': v}
            for p, v in sorted(revenues_by_period.items(), reverse=True)
        ]

        # Operating margin = op_income / revenue  (not a growth calc)
        op_margin = round(op_income / revenue, 4) if (revenue and op_income) else None

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
        output['notes'].append(
            'EBITDA estimate = operating income only. '
            'Add back D&A from cash flow statement for true EBITDA.'
        )
        output['notes'].append(
            'Use 10-K revenue as the annual figure for the model. '
            '10-Q revenues are YTD (cumulative), not single-quarter — do not sum them.'
        )
        output['notes'].append(
            'Unit count (stores/restaurants/facilities) is not XBRL-tagged. '
            'Check MD&A section of most recent 10-Q/10-K for system unit count.'
        )
        output['notes'].append(
            'Employee count is not reliably XBRL-tagged. '
            'Check Item 1 (Human Capital) of most recent 10-K.'
        )

    result_json = json.dumps(output, indent=2)
    print(result_json)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result_json, encoding='utf-8')
        print(f'Saved to {args.output}', file=sys.stderr)


if __name__ == '__main__':
    main()
