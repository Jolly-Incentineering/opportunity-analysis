---
name: deck-figma
description: Generate campaign text and points for Figma app screens. Takes a screenshot as input, outputs ready-to-paste text. Usage: /deck-figma [Company Name] then paste or drag a screenshot.
disable-model-invocation: true
---

Read and follow all rules in skills/shared-preamble.md before proceeding.

---

You are generating text content for Figma app mockup screens. The user will provide a screenshot of the Figma layout and you will output campaign-specific text and points values they can paste in.

Set workspace root using the bash preamble from shared-preamble.md.

---

## Step 1: Load Session State and Research Output

Load session state using the standard loader from shared-preamble.md.

Extract: company_name, client_root, campaigns_selected, vertical.

If no session state exists, tell the user: "No active session found. Run /deck-start [Company] first." Then stop.

Derive company_slug from company name (see shared-preamble.md).

Read research output:

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
source "$WS/.claude/scripts/ws_env.sh"
cat "$WS/$CLIENT_ROOT/[COMPANY_NAME]/4. Reports/research_output_[company_slug].json"
```

Extract from research output:
- `campaign_details` - each campaign's name, description, rops_base, incentive_cost_base, ebitda_uplift_base
- `company_profile` - company name, vertical, revenue, unit count

---

## Step 2: Receive Screenshot

Tell the user:

```
Ready to generate Figma text for [COMPANY_NAME].

Paste or drag a screenshot of the Figma screens you need text for.
I'll identify each screen type and generate the right content.
```

Wait for the user to provide a screenshot. Use the Read tool to view the image.

---

## Step 3: Identify Screen Types

Analyze the screenshot to identify which app screen types are shown. Common screen types in Jolly app mockups:

- **Inbox/Feed screen** - push notification cards showing campaign rewards
- **Campaign detail screen** - full campaign description with reward amount and rules
- **Rewards summary screen** - list of active campaigns with points totals
- **Leaderboard screen** - ranking display with names and points
- **Achievement/badge screen** - milestone rewards with icons
- **Home/dashboard screen** - overview with total points and active campaigns

For each screen identified, note:
- Screen type
- Number of text fields visible (titles, subtitles, body text, point values)
- Layout structure (cards, list items, headers)

---

## Step 4: Generate Text for Each Screen

For each screen type identified, generate text using the campaign data from research_output.

### Points Calculation

Standard conversion: **200 points per $1 of incentive cost**.

For each campaign, compute:
- Points value = `incentive_cost_base * 200` (round to nearest 50)
- Sort campaigns by points value descending for feed/inbox displays

### Inbox/Feed Cards

For each campaign, generate a notification card:

```
TITLE: [Campaign Name]
SUBTITLE: Earn [X] pts
BODY: [1 sentence - what to do to earn the reward, written as an action prompt]
POINTS BADGE: [X] pts
```

Example:
```
TITLE: Visit Order Amounts
SUBTITLE: Earn 2,400 pts
BODY: Ring up orders over $15 to earn bonus points this week.
POINTS BADGE: 2,400 pts
```

### Campaign Detail Screen

```
HEADER: [Campaign Name]
POINTS: [X] points
DESCRIPTION: [2-3 sentences explaining the campaign mechanic and reward. Written for the employee, not the executive. Simple, direct language.]
HOW TO EARN: [1-2 bullet points with specific trackable actions]
REWARD: [Points amount] points ([dollar equivalent at 200:$1])
```

### Rewards Summary

For each campaign in the approved list:
```
[Campaign Name]          [X] pts
```

Total at bottom:
```
Total Available          [sum] pts
```

### Leaderboard

Generate 5-8 sample names with realistic point spreads:
```
1. [Name]    [highest pts]
2. [Name]    [slightly less]
...
```

Use common first names appropriate to the vertical and region.

---

## Step 5: Present Output

Present all generated text in a structured, copy-paste-friendly format:

```
FIGMA TEXT - [COMPANY NAME]
Generated from [N] approved campaigns

====================================
SCREEN: [Screen Type]
====================================

[Card/field 1]
---
[Card/field 2]
---
...

====================================
SCREEN: [Screen Type 2]
====================================
...

POINTS SUMMARY:
  [Campaign 1]: [X] pts ($[Y] incentive)
  [Campaign 2]: [X] pts ($[Y] incentive)
  ...
  Total: [sum] pts ($[sum] incentive)
```

Tell the user:

```
Text generated for [N] screens. Copy each section into the matching Figma frame.

If you have more screens to fill, paste another screenshot.
If the text needs adjustments (tone, length, specific wording), tell me what to change.
```

Do not update session state. This skill is stateless - it reads research data and outputs text.
