---
name: asset-gatherer
description: Gather all company assets in parallel with the research + model session — logos, swag, Figma frames, and banner alert.
model: haiku
---

Set workspace root:
```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
```
Use `$WS/$CLIENT_ROOT` as the prefix for all client folder paths below.

You are gathering assets for **[COMPANY_NAME]**. Run in parallel with the research + model session. Goal: populate `$WS/$CLIENT_ROOT/[Company Name]/3. Company Resources/` with everything needed for the deck.

## Step 1: Check What Already Exists

```bash
ls "$WS/$CLIENT_ROOT/[Company Name]/3. Company Resources/1. Logos/" 2>/dev/null
ls "$WS/$CLIENT_ROOT/[Company Name]/3. Company Resources/2. Swag/" 2>/dev/null
ls "$WS/$CLIENT_ROOT/[Company Name]/3. Company Resources/" 2>/dev/null | grep -i banner
```

If assets already exist and look complete, ask user if they want to refresh or skip.

## Step 2: Download Logos (Brandfetch)

```bash
BRANDFETCH_API_KEY=$(grep BRANDFETCH_API_KEY "$WS/.claude/.env" | cut -d '=' -f2)
python "$WS/Tools/Brandfetch Logo Downloader/brandfetch_cli.py" \
  --api-key "$BRANDFETCH_API_KEY" \
  --brand "[company-domain.com]" \
  --output "$WS/$CLIENT_ROOT/[Company Name]/3. Company Resources/1. Logos"
```

Expected: `icon_512.png`, `icon_1024.png`, `logo_400.png`, SVGs, `brand_info.json`

If `.com` fails try `.net`. Do NOT edit logos for transparency.

## Step 3: (Banner step removed - deck-start skips banner.)

## Step 4: Download Swag (Goody Scraper)

```bash
# Domain recognition ONLY — no --logo-path
python "$WS/Tools/Goody Scraper/goody_scraper.py" \
  --domain "[company-domain.com]" \
  -n "[Company Name]"
```

If popup appears (Ongoody doesn't recognize domain):
```
POPUP DETECTED: Please select the correct logo in the browser window, click Continue, then reply "done".
```

After download:
```bash
cp ~/Downloads/goody_downloads/"[Company Name]"/*.png \
   "$WS/$CLIENT_ROOT/[Company Name]/3. Company Resources/2. Swag/"
```

If Goody fails entirely, note it and move on — do not block.

## Step 5: Export Figma Frames

Automatically attempt Figma export. If it fails, note the failure and move on.

```bash
python "$WS/.claude/export_company_frames.py" --company "[Company Name]"
```

## Step 6: Verify and Report

```bash
echo "Logos:" && ls "$WS/$CLIENT_ROOT/[Company Name]/3. Company Resources/1. Logos/"
echo "Banner:" && ls "$WS/$CLIENT_ROOT/[Company Name]/3. Company Resources/" | grep -i banner
echo "Swag:" && ls "$WS/$CLIENT_ROOT/[Company Name]/3. Company Resources/2. Swag/" | wc -l
echo "Figma:" && ls "$WS/$CLIENT_ROOT/[Company Name]/3. Company Resources/" | grep -iE "(earn|shop|wallet|sticky|quick)"
```

Report status clearly — what succeeded, what failed, what still needs user action.
