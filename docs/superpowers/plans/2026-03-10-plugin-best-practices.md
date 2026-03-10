# Plugin Best Practices Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Incorporate Claude Code best practices into the opportunity-analysis plugin - hooks for guardrail enforcement, disable-model-invocation on side-effect skills, fix stale marketplace.json, and version bump to v3.9.0.

**Architecture:** Add PreToolUse hooks to deterministically block MCP write operations and enforce client folder boundaries (replacing advisory-only HARD RULES). Add `disable-model-invocation: true` to all skills that have side effects so they're only triggered via explicit `/skill-name` commands. Clean up stale internal marketplace.json.

**Tech Stack:** Claude Code plugin system (plugin.json hooks, SKILL.md frontmatter)

---

## Chunk 1: Hooks for Guardrail Enforcement

### Task 1: Create MCP read-only enforcement hook script

**Files:**
- Create: `hooks/block_mcp_writes.sh`

- [ ] **Step 1: Create hooks directory**

```bash
mkdir -p hooks
```

- [ ] **Step 2: Write the hook script**

Create `hooks/block_mcp_writes.sh`:

```bash
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
```

- [ ] **Step 3: Make the script executable**

```bash
chmod +x hooks/block_mcp_writes.sh
```

### Task 2: Create client folder boundary hook script

**Files:**
- Create: `hooks/enforce_client_folder.sh`

- [ ] **Step 1: Write the hook script**

This hook blocks Write/Edit operations that target `.claude/data/` with client-specific content. Client data must stay in the client folder under `4. Reports/`.

```bash
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
```

- [ ] **Step 2: Make the script executable**

```bash
chmod +x hooks/enforce_client_folder.sh
```

### Task 3: Register hooks in plugin.json

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Add hooks configuration to plugin.json**

Update `.claude-plugin/plugin.json` to include the hooks field:

```json
{
  "name": "opportunity-analysis",
  "description": "Opportunity Analysis workflow for Jolly - research, model, and format a client intro deck. Bundled with scripts, template configs, and guardrails.",
  "version": "3.9.0",
  "author": {
    "name": "Jolly"
  },
  "repository": "https://github.com/Jolly-Incentineering/opportunity-analysis",
  "license": "UNLICENSED",
  "keywords": [
    "jolly",
    "deck",
    "qsr",
    "manufacturing",
    "retail",
    "workflow"
  ],
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__.*__(create|update|delete|upsert|save|send|schedule|respond).*",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/block_mcp_writes.sh"
          }
        ]
      }
    ]
  }
}
```

Note: The matcher regex handles most MCP write tools at the pattern level. The shell script is the fallback for edge cases where the tool name doesn't match the pattern but is still a write operation.

- [ ] **Step 2: Verify the JSON is valid**

```bash
python3 -c "import json; json.load(open('.claude-plugin/plugin.json')); print('Valid JSON')"
```

- [ ] **Step 3: Commit hooks**

```bash
git add hooks/block_mcp_writes.sh hooks/enforce_client_folder.sh .claude-plugin/plugin.json
git commit -m "feat: add PreToolUse hooks for MCP read-only and client folder enforcement"
```

---

## Chunk 2: disable-model-invocation on Side-Effect Skills

### Task 4: Add disable-model-invocation to all side-effect skills

**Files:**
- Modify: `skills/deck-auto/SKILL.md` (line 3)
- Modify: `skills/deck-start/SKILL.md` (line 3)
- Modify: `skills/deck-research/SKILL.md` (line 3)
- Modify: `skills/deck-model/SKILL.md` (line 3)
- Modify: `skills/deck-format/SKILL.md` (line 3)
- Modify: `skills/deck-qa/SKILL.md` (line 3)
- Modify: `skills/deck-new-template/SKILL.md` (line 3)
- Modify: `skills/deck-setup/SKILL.md` (line 3)
- Modify: `skills/deck-continue/SKILL.md` (line 3)

Do NOT modify:
- `skills/deck-help/SKILL.md` - read-only, safe for auto-invocation
- `skills/jolly-onboarding/SKILL.md` - setup guide, safe for auto-invocation

- [ ] **Step 1: Add frontmatter field to deck-auto**

In `skills/deck-auto/SKILL.md`, add `disable-model-invocation: true` after the description line:

```yaml
---
name: deck-auto
description: Run the full intro deck workflow automatically for a company. Saves progress after every phase and resumes if interrupted. Usage: /deck-auto [Company Name].
disable-model-invocation: true
---
```

- [ ] **Step 2: Add frontmatter field to deck-start**

```yaml
---
name: deck-start
description: Initialize a new intro deck engagement -- verify folder, copy templates, detect branch, and launch asset gathering.
disable-model-invocation: true
---
```

- [ ] **Step 3: Add frontmatter field to deck-research**

```yaml
---
name: deck-research
description: Run research workstreams via 3 parallel agents, merge results, and select campaigns for an in-progress intro deck.
disable-model-invocation: true
---
```

- [ ] **Step 4: Add frontmatter field to deck-model**

```yaml
---
name: deck-model
description: Populate the Excel intro model with researched values -- assumptions, campaign inputs, and sensitivities.
disable-model-invocation: true
---
```

- [ ] **Step 5: Add frontmatter field to deck-format**

```yaml
---
name: deck-format
description: Format the PowerPoint intro deck -- populate text, update banners, apply brand colors, and export PDF.
disable-model-invocation: true
---
```

- [ ] **Step 6: Add frontmatter field to deck-qa**

```yaml
---
name: deck-qa
description: Run final quality checks on the Excel model and PowerPoint deck before client delivery.
disable-model-invocation: true
---
```

- [ ] **Step 7: Add frontmatter field to deck-new-template**

```yaml
---
name: deck-new-template
description: Create a new vertical template (Excel model + PowerPoint deck + JSON config) by adapting an existing template.
disable-model-invocation: true
---
```

- [ ] **Step 8: Add frontmatter field to deck-setup**

```yaml
---
name: deck-setup
description: Run once per workspace to detect or create the client folder root and write workspace_config.json.
disable-model-invocation: true
---
```

- [ ] **Step 9: Add frontmatter field to deck-continue**

```yaml
---
name: deck-continue
description: Resume the most recent deck workflow from where it left off. No arguments needed -- reads session state automatically.
disable-model-invocation: true
---
```

- [ ] **Step 10: Verify no changes to deck-help or jolly-onboarding**

```bash
head -5 skills/deck-help/SKILL.md
head -5 skills/jolly-onboarding/SKILL.md
```

Both should NOT have `disable-model-invocation: true`.

- [ ] **Step 11: Commit skill changes**

```bash
git add skills/*/SKILL.md
git commit -m "feat: add disable-model-invocation to all side-effect skills"
```

---

## Chunk 3: Fix Stale Marketplace JSON and Version Bump

### Task 5: Remove stale internal marketplace.json

**Files:**
- Delete: `.claude-plugin/marketplace.json`

The jolly-marketplace repo is the source of truth for the marketplace registry. Having a stale copy inside the plugin at v3.7.0 is confusing and serves no purpose.

- [ ] **Step 1: Remove the stale file**

```bash
git rm .claude-plugin/marketplace.json
```

- [ ] **Step 2: Commit removal**

```bash
git commit -m "chore: remove stale internal marketplace.json (registry lives in jolly-marketplace)"
```

### Task 6: Fix em dash in plugin.json description

**Files:**
- Modify: `.claude-plugin/plugin.json`

The description contains an em dash which violates the user preference for hyphens only. This was already addressed in Task 3's version of plugin.json (changed to ` - `), but verify it's correct.

- [ ] **Step 1: Verify no em dashes remain**

```bash
grep -P '\x{2014}' .claude-plugin/plugin.json || echo "No em dashes found"
```

### Task 7: Bump version to v3.9.0

**Files:**
- Modify: `.claude-plugin/plugin.json` (already done in Task 3)

- [ ] **Step 1: Verify version is 3.9.0**

```bash
python3 -c "import json; d=json.load(open('.claude-plugin/plugin.json')); print('Version:', d['version']); assert d['version'] == '3.9.0'"
```

- [ ] **Step 2: Update deck-help with new version if referenced**

Check `skills/deck-help/SKILL.md` for any hardcoded version strings and update if found.

- [ ] **Step 3: Create final commit and tag**

```bash
git add -A
git status
git commit -m "release: v3.9.0 - hooks, disable-model-invocation, cleanup"
git tag v3.9.0
```

### Task 8: Update jolly-marketplace registry

**Files:**
- Modify: `../jolly-marketplace/.claude-plugin/marketplace.json`

- [ ] **Step 1: Update marketplace version and ref**

In `jolly-marketplace/.claude-plugin/marketplace.json`, update the opportunity-analysis entry:

```json
{
  "name": "opportunity-analysis",
  "description": "Opportunity Analysis Plugin - research, model, and format a client intro deck. Includes onboarding, scripts, template configs, and guardrails. Run /deck-help for the full command reference.",
  "version": "3.9.0",
  "source": {"source": "github", "repo": "Jolly-Incentineering/opportunity-analysis", "ref": "v3.9.0"},
  "author": {"name": "Jolly", "email": "team@jolly.com"}
}
```

- [ ] **Step 2: Commit marketplace update**

```bash
cd ../jolly-marketplace
git add .claude-plugin/marketplace.json
git commit -m "chore: bump opportunity-analysis to v3.9.0"
```

---

## Post-Implementation

### Push and Release

After all tasks complete:

```bash
cd ../opportunity-analysis
git push origin main
git push origin v3.9.0
gh release create v3.9.0 --title "v3.9.0" --notes "## What's new

- **Hooks:** PreToolUse hook enforces MCP read-only rule deterministically (no more relying on advisory HARD RULES alone)
- **disable-model-invocation:** All side-effect skills (deck-auto, deck-start, etc.) now require explicit /command invocation - Claude won't auto-trigger them
- **Cleanup:** Removed stale internal marketplace.json, fixed em dash in description

## Upgrading

Run: /plugin update opportunity-analysis"

cd ../jolly-marketplace
git push origin main
```
