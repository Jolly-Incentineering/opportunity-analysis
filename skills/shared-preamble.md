# Shared Preamble

All deck workflow skills inherit these rules and conventions. Do not repeat them in individual skills - reference this file instead.

## Hard Rules - NEVER VIOLATE

1. Do NOT generate or invent campaign names. Read them from the template config JSON.
2. Do NOT make tool calls or add steps not listed in the skill's instructions.
3. Do NOT write to formula cells under any circumstances.
4. Do NOT skip gates marked with AskUserQuestion - but do NOT add extra gates.
5. Do NOT open files you are about to write to programmatically. Keep them closed during writes.
6. Do NOT proceed past a failed step - stop and report. Do NOT retry more than once.
7. Keep all client-specific data in the client folder under 4. Reports/. Never write client data to .claude/data/.
8. All Attio, Slack, and other MCP tools are READ-ONLY. Never use create, update, or delete MCP actions.
9. Use HAIKU for research agents unless explicitly told otherwise. (Only applies to skills that dispatch agents: deck-start, deck-research.)

## Bash Preamble

Use at the start of every bash block:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
```

## Executive Audience Rule

Intro decks are reviewed by C-suite executives (CEO, CFO, COO). Never include internal process language in any text written to the deck:
- References to calls, meetings, or conversations ("as discussed on our call", "per our meeting", "as mentioned")
- References to internal research steps ("our analysis found", "based on our review")
- References to data sourcing ("according to SEC filings", "per Glassdoor")
- Hedging language ("we believe", "we think", "it appears")
- Any language that reveals the deck was built by an automated process or external team

All campaign descriptions, commentary, and insights must read as confident, client-facing strategic recommendations - not internal working notes.

## Session State Loader

Standard pattern for loading session state at the start of any phase skill:

```python
python3 -c "
import json, glob, os
ws = os.environ.get('JOLLY_WORKSPACE', '.')
files = sorted(glob.glob(f'{ws}/.claude/data/session_state_*.json'))
if not files: raise SystemExit('No session state found')
data = json.load(open(files[-1], encoding='utf-8'))
for k, v in data.items():
    if isinstance(v, dict):
        print(f'{k}:', json.dumps(v))
    else:
        print(f'{k}:', v)
"
```

## Company Slug

Derive from company name: lowercase, spaces to underscores, remove special characters. Compute once, reuse throughout the skill.
