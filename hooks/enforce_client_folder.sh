#!/usr/bin/env bash
# Enforce Rule 7: client-specific data stays in the client folder.
# Blocks writes to .claude/data/ that look like client output files.
#
# Exit 0 = allow, Exit 2 = block.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.command // empty')

# Block writes to .claude/data/ that contain client-specific patterns
# (session state and workspace config are allowed - they belong in .claude/data/)
if echo "$FILE_PATH" | grep -qE '\.claude/data/' ; then
  # Allow known config files
  if echo "$FILE_PATH" | grep -qE '(workspace_config|session_state|vertical_benchmarks)'; then
    exit 0
  fi
  # Block everything else in .claude/data/
  if echo "$FILE_PATH" | grep -qiE '(research_output|ws_attio|ws_slack|ws_public|template_config)'; then
    echo "BLOCKED: Client data file detected in .claude/data/. Write client data to the client folder under 4. Reports/ instead." >&2
    exit 2
  fi
fi

exit 0
