#!/usr/bin/env bash
# Block all MCP create/update/delete/upsert operations.
# Attio, Slack, and all MCP tools are READ-ONLY in this plugin.
#
# Claude Code passes tool info as JSON on stdin for PreToolUse hooks.
# Exit 0 = allow, Exit 2 = block (stderr shown to Claude).

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')

# Block any MCP tool containing create, update, delete, upsert, save, send, schedule
if echo "$TOOL_NAME" | grep -qiE '(create|update|delete|upsert|save|send|schedule|respond)'; then
  echo "BLOCKED: MCP tool '$TOOL_NAME' is a write operation. All MCP tools are READ-ONLY in this plugin." >&2
  exit 2
fi

exit 0
