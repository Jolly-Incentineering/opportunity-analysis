---
name: jolly-onboarding
description: First-time setup guide for connecting integrations, configuring workspace, and running your first deck.
---

Welcome to Jolly's Opportunity Analysis workflow! This guide walks you through one-time setup in plain language. Takes about 10 minutes.

---

## Section 1: Connect Integrations in Claude

Before running any deck commands, you need to connect two tools in Claude. This is a one-time setup per workspace.

### Step 1: Connect Slack

1. Click your profile picture (top right in Claude).
2. Click "Settings".
3. Click "Integrations" in the left menu.
4. Find "Slack" and click "Connect".
5. Sign in with your Jolly Slack account.
6. Click "Allow".

**Done** — Claude can now search Slack messages during research.

### Step 2: Connect Attio (CRM)

1. In the same Integrations page, find "Attio".
2. Click "Connect".
3. Sign in with your Jolly Attio account.
4. Click "Allow".

**Done** — Claude can now pull CRM records and notes during research.

Tell me when both are connected:

```
✓ Slack connected
✓ Attio connected
```

---

## Section 2: Set Your Jolly Workspace Path (Environment Variable)

Claude needs to know where your Jolly folder lives on your computer. This is a one-time setting.

### For Windows

1. Press the Windows key, then type: `environment variables`
2. Click "Edit the system environment variables".
3. In the window that opens, click "Environment Variables..." (near the bottom).
4. Under "System variables" (the LOWER half), click "New...".
5. Fill in exactly:
   ```
   Variable name:   JOLLY_WORKSPACE
   Variable value:  [the full path to your Jolly - Documents folder]
   ```

   Your path will look something like:
   ```
   C:\Users\YourName\OneDrive - Default Directory\Jolly - Documents
   ```

   **Not sure what your path is?**
   - Open File Explorer
   - Navigate to your Jolly - Documents folder
   - Click the address bar at the top
   - Copy the full path

6. Click OK on all windows.
7. **IMPORTANT: Close and fully reopen Claude Code.** The setting only takes effect after a restart.

### For Mac

1. Open Terminal (Applications → Utilities → Terminal).
2. Paste this command (replace the path with yours):
   ```bash
   echo 'export JOLLY_WORKSPACE="/Users/YourName/Jolly - Documents"' >> ~/.zshrc
   ```
3. Close Terminal.
4. **IMPORTANT: Close and fully reopen Claude Code.**

Tell me when you have restarted Claude Code:

```
✓ JOLLY_WORKSPACE configured
✓ Claude Code restarted
```

---

## Section 3: Run /deck-setup

You're almost done! One final command sets up your workspace.

Run:

```
/deck-setup
```

Claude will:
- Scan your Jolly folder for client templates
- Detect your Gong integration setting (if you use Gong for call transcripts)
- Ask one question about Rube (optional manual Gong setup)
- Save everything to your workspace config

Takes about 30 seconds.

---

## Section 4: Create Your First Deck

You're ready! To start your first opportunity analysis:

```
/deck-auto [Company Name]
```

Example:

```
/deck-auto Firebirds
```

Claude will ask whether this is a "before call" or "after call" deck, then walk you through every step. If you need to pause, run the same command again and it picks up where you left off.

**Time to complete:**
- Without Commentary (no call yet): ~10–15 minutes
- With Commentary (after a call): ~20–25 minutes

---

## Troubleshooting

**"Workspace is not configured"**
- → You haven't run `/deck-setup` yet. Do that first.

**"JOLLY_WORKSPACE not set"**
- → Your environment variable isn't saved or Claude Code wasn't restarted. Try again and make sure to fully restart Claude Code after setting the variable.

**"I can't find my Jolly - Documents folder path"**
- → Open File Explorer, search for "Jolly", right-click the folder, click "Rename" to see its full path. Or check the address bar when you navigate to it.

**"The Slack/Attio connections failed"**
- → Check that you're signed in with the correct Jolly account in Claude's integrations. If you see a "permission denied" error, you may not have access to that workspace — ask your admin.

---

## Next Steps

Once setup is done:
- Run `/deck-help` to see all available commands
- Run `/deck-auto [Company]` to start an opportunity analysis
- Questions? Ask Claude — it's here to help!

Happy analyzing!

