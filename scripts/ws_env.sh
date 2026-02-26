#!/usr/bin/env bash
# Source this at the top of every bash block in skills.
# Replaces the 3-line preamble with: source "$WS/.claude/scripts/ws_env.sh"
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
export CLIENT_ROOT=$(python3 -c "import json;print(json.load(open('$WS/.claude/data/workspace_config.json'))['client_root'])" 2>/dev/null || echo "Clients")
export TEMPLATES_ROOT=$(python3 -c "import json;print(json.load(open('$WS/.claude/data/workspace_config.json')).get('templates_root','Templates'))" 2>/dev/null || echo "Templates")
