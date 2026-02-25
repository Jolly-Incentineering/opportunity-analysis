---
name: jolly-onboarding
description: First-time setup guide for connecting integrations, configuring workspace, and running your first deck.
---

Welcome to Jolly's Opportunity Analysis workflow! This guide walks you through one-time setup in plain language. Takes about 10 minutes.

---

## Section 0: Check Prerequisites (Git)

The plugin system uses Git to download and update plugins. Let's make sure it's installed and configured.

### Step 0a: Check if Git is installed

Run:

```bash
git --version
```

If you see a version number (e.g. `git version 2.x.x`), skip to Step 0c.

If Git is not found, follow the instructions for your operating system:

**Windows:**
1. Download the Git installer from https://git-scm.com/download/win
2. Run the installer — use the default settings throughout (just click Next until it finishes).
3. Close and reopen your terminal.
4. Verify by running `git --version`.

**Mac:**
1. Run this command in Terminal:
   ```bash
   xcode-select --install
   ```
2. A dialog will pop up asking to install developer tools — click **Install** and wait (~2–5 minutes).
3. Once it completes, verify by running `git --version`.

→ Type "done" when Git is installed

### Step 0b: Configure Git to use HTTPS for GitHub

This prevents "Permission denied (publickey)" errors when installing plugins. Run this once:

```bash
git config --global url."https://github.com/".insteadOf git@github.com:
```

This tells Git to use HTTPS instead of SSH for all GitHub repositories. On Windows, the built-in credential manager will prompt you to log in to GitHub once and then remember it. On Mac, you'll be prompted for your GitHub username and a personal access token (generate one at https://github.com/settings/tokens with "repo" scope).

### Step 0c: Verify GitHub access

Run:

```bash
git ls-remote https://github.com/Jolly-Incentineering/opportunity-analysis.git HEAD
```

If you see a commit hash, you're good. If you get an authentication error, you need to log in to GitHub — the next time you install or update a plugin, Git will prompt you for credentials.

→ Type "done" when ready to continue

---

## Section 0.5: Install Python Packages

The plugin uses Python scripts to read and write Excel and PowerPoint files. Run this once:

```bash
pip install openpyxl python-pptx requests
```

If this fails, try `pip3` instead of `pip`. If you get a "pip not found" error:

**Windows:** Python is usually bundled with Claude Code. Try: `python -m pip install openpyxl python-pptx requests`

**Mac:** Try: `python3 -m pip install openpyxl python-pptx requests`

Optional packages (for SEC filings and cheat sheet PDFs — skip if unsure):
```bash
pip install edgartools pypdf
```

→ Type "done" when packages are installed

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

→ Type "done" when both are connected

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

→ Type "done" when Claude Code has been restarted

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
- Pre-call (before a call): ~8–12 minutes
- Post-call (after a call): ~14–20 minutes

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

