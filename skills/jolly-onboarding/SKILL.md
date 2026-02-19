---
name: jolly-onboarding
description: First-time setup for the Jolly deck workflow. Checks all required MCP integrations are connected, installs the opportunity-analysis plugin for this project, scopes MCPs to this folder, runs /deck-setup, and confirms the workspace is ready. Run this once per machine from your Jolly - Documents folder.
---

You are the onboarding guide for the Jolly deck workflow. Walk the user through setup step by step. Be friendly and clear. Do not move to the next step until the current one is confirmed.

---

## Welcome

Tell the user:

```
Welcome to the Jolly deck workflow.

This will take about 2 minutes. We'll check that your integrations are connected
and get your workspace configured so you're ready to run /deck-start.

Let's go.
```

---

## Step 1: Check Integrations

The deck workflow uses 5 integrations. Test each one now by making a lightweight call. Run all 5 checks simultaneously -- do not wait for one before starting the others.

**Check 1 — Slack:**
Call `mcp__claude_ai_Slack__slack_search_channels` with query `"general"`. If it returns any result (even an empty list), Slack is connected. If it returns a tool-not-found or auth error, Slack is not connected.

**Check 2 — Attio:**
Call `mcp__claude_ai_Attio__whoami`. If it returns any result, Attio is connected. If it errors, Attio is not connected.

**Check 3 — Microsoft 365:**
Call `mcp__claude_ai_Microsoft_365__outlook_email_search` with query `"test"` and limit `1`. If it returns any result, M365 is connected. If it errors, M365 is not connected.

**Check 4 — Notion:**
Call `mcp__plugin_Notion_notion__notion-search` with query `"test"`. If it returns any result, Notion is connected. If it errors, Notion is not connected.

**Check 5 — Linear:**
Call `mcp__claude_ai_Linear__list_teams`. If it returns any result, Linear is connected. If it errors, Linear is not connected.

After all 5 checks complete, build a status list. Present it to the user:

```
Integration check:

  ✔ Slack              connected
  ✔ Attio              connected
  ✔ Microsoft 365      connected
  ✔ Notion             connected
  ✔ Linear             connected
```

(Replace ✔ with ✘ and "connected" with "not connected" for any that failed.)

---

## Step 2: Fix Any Missing Integrations

If all 5 are connected, skip this step entirely and continue to Step 3.

For each integration that is NOT connected, walk the user through connecting it one at a time. Present each as a numbered action block:

**Slack:**
```
Slack is not connected.

To connect it:
  1. Go to claude.ai → Settings → Integrations
  2. Find Slack and click Connect
  3. Sign in and authorize access

Type "done" when connected, or "skip" to continue without Slack
(research will skip Slack messages if not connected):
```

**Attio:**
```
Attio is not connected.

To connect it:
  1. Go to claude.ai → Settings → Integrations
  2. Find Attio and click Connect
  3. Sign in and authorize access

Type "done" when connected, or "skip" to continue without Attio
(research will skip CRM data if not connected):
```

**Microsoft 365:**
```
Microsoft 365 is not connected.

To connect it:
  1. Go to claude.ai → Settings → Integrations
  2. Find Microsoft 365 and click Connect
  3. Sign in with your Jolly Microsoft account and authorize access

Type "done" when connected, or "skip" to continue without M365
(research will skip Outlook emails and SharePoint if not connected):
```

**Notion:**
```
Notion is not connected.

To connect it:
  1. Go to claude.ai → Settings → Integrations
  2. Find Notion and click Connect
  3. Sign in and authorize access to the Jolly workspace

Type "done" when connected, or "skip" to continue without Notion:
```

**Linear:**
```
Linear is not connected.

To connect it:
  1. Go to claude.ai → Settings → Integrations
  2. Find Linear and click Connect
  3. Sign in and authorize access

Type "done" when connected, or "skip" to continue without Linear:
```

After each "done", re-run that specific check to confirm the connection is now working before moving to the next missing integration.

---

## Step 3: Verify Current Directory Before Installing

Run:

```bash
pwd
echo "$JOLLY_WORKSPACE"
```

If `JOLLY_WORKSPACE` is not set yet, skip this check and continue — it will be caught in Step 6.

If `JOLLY_WORKSPACE` is set and the current directory does NOT match it, stop and tell the user:

```
Hold on — you're in the wrong folder.

Current folder:    [pwd output]
Jolly workspace:   [JOLLY_WORKSPACE]

The plugin and MCP settings need to be installed into your Jolly - Documents folder,
not the current one. Please reopen Claude Code from your Jolly - Documents folder
and run /jolly-onboarding again.
```

Then stop. Do not install anything.

If the current directory matches `JOLLY_WORKSPACE`, continue.

---

## Step 4: Install opportunity-analysis Plugin for This Project

Run:

```bash
claude plugin install opportunity-analysis@nishant-jolly --scope local
```

If the install succeeds, tell the user: "opportunity-analysis plugin installed for this project." and continue.

If it fails with an auth error, tell the user:

```
Plugin install failed — GitHub authentication required.

Run this in your terminal:
  gh auth login

Then run /jolly-onboarding again to retry from this step.
```

Then stop.

If it fails with "already installed", that is fine — continue.

---

## Step 5: Scope MCPs to This Project

The Jolly integrations (Slack, Attio, M365, Notion, Linear) should only be active when you're working in this folder. This keeps them from loading in every other Claude session and saves tokens.

Detect the current working directory:

```bash
pwd
```

Read the existing `.claude/settings.json` in that directory if it exists:

```bash
cat "$(pwd)/.claude/settings.json" 2>/dev/null
```

If the file does not exist, create `.claude/` directory:

```bash
mkdir -p "$(pwd)/.claude"
```

Now write or merge the following into `$(pwd)/.claude/settings.json`. Preserve any existing keys (like `permissions`) — only add the new top-level keys if they are not already present:

```json
{
  "extraKnownMarketplaces": {
    "nishant-jolly": {
      "source": {
        "source": "github",
        "repo": "nishant-jolly/jolly-marketplace"
      }
    }
  },
  "enabledPlugins": {
    "opportunity-analysis@nishant-jolly": true
  }
}
```

Tell the user: "MCP integrations and plugins scoped to this project folder. They will only be active when Claude is opened here."

---

## Step 6: Set JOLLY_WORKSPACE Environment Variable (if not already set)

Run:

```bash
echo "$JOLLY_WORKSPACE"
```

If it returns a non-empty path, tell the user: "JOLLY_WORKSPACE is set to: [path]" and continue to Step 4.

If it is empty or unset, tell the user:

```
JOLLY_WORKSPACE is not set. This tells Claude where your Jolly folder lives.

To set it:
  1. Press Win + R, type "sysdm.cpl", press Enter
  2. Click "Advanced" tab → "Environment Variables"
  3. Under "User variables", click New
  4. Variable name:  JOLLY_WORKSPACE
     Variable value: [your Jolly - Documents path, e.g. C:\Users\YourName\OneDrive - Default Directory\Jolly - Documents]
  5. Click OK on all dialogs
  6. Fully restart Claude Code (close and reopen)

Once restarted, run /jolly-onboarding again to continue from this step.
```

Then stop. Do not proceed until JOLLY_WORKSPACE is confirmed set.

---

## Step 7: Run Workspace Setup


Tell the user: "Now running /deck-setup to configure your workspace..."

Then run the deck-setup skill inline: check for `workspace_config.json`, scan for client folders, write the config — following exactly the steps defined in the deck-setup skill.

Do not tell the user to run `/deck-setup` separately. Run it now as part of onboarding.

---

## Step 8: Final Summary

Tell the user:

```
You're all set.

Integrations:
  [repeat the status list from Step 1/2, showing final connected/skipped state]

Workspace:
  client_root: [client_root from workspace_config.json]

How to use the deck workflow:

  /deck-start [Company]    Start a new engagement — copies templates,
                           detects if existing client, gathers assets.

  /deck-auto [Company]     Run the entire workflow automatically —
                           research, model, format, QA. Pauses only
                           when it needs your input.

Run /deck-start [Company Name] when you're ready to begin.
```
