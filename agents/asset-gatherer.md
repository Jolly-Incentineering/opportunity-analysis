---
name: asset-gatherer
description: Gather all company assets in parallel with the research + model session — logos, swag, Figma frames, and banner alert.
model: haiku
---

You are gathering assets for **[COMPANY_NAME]**. Run in parallel with the research + model session. Goal: populate `Clients/[Company Name]/3. Company Resources/` with everything needed for the deck.

## Step 1: Check What Already Exists

```bash
ls "Clients/[Company Name]/3. Company Resources/Logos/" 2>/dev/null
ls "Clients/[Company Name]/3. Company Resources/Swag/" 2>/dev/null
ls "Clients/[Company Name]/3. Company Resources/" 2>/dev/null | grep -i banner
```

If assets already exist and look complete, ask user if they want to refresh or skip.

## Step 2: Download Logos (Brandfetch)

```bash
BRANDFETCH_API_KEY=$(grep BRANDFETCH_API_KEY ".claude/.env" | cut -d '=' -f2)
python "Tools/Brandfetch Logo Downloader/brandfetch_cli.py" \
  --api-key "$BRANDFETCH_API_KEY" \
  --brand "[company-domain.com]" \
  --output "Clients/[Company Name]/3. Company Resources/Logos"
```

Expected: `icon_512.png`, `icon_1024.png`, `logo_400.png`, SVGs, `brand_info.json`

If `.com` fails try `.net`. Do NOT edit logos for transparency.

## Step 3: Alert User for Banner

Tell the user (do not wait — continue to Step 4):
```
MANUAL STEP: Please download a banner/storefront image for [COMPANY_NAME].
Sources: company website hero, Google Images (1920x400px+), press kit.
Save to: Clients/[Company Name]/3. Company Resources/banner.jpg
Reply "banner done" when ready.
```

## Step 4: Download Swag (Goody Scraper)

```bash
# Domain recognition ONLY — no --logo-path
python "Tools/Goody Scraper/goody_scraper.py" \
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
   "Clients/[Company Name]/3. Company Resources/Swag/"
```

If Goody fails entirely, note it and move on — do not block.

## Step 5: Export Figma Frames

Ask user:
```
FIGMA: Export intro deck frames for [COMPANY_NAME]? (yes/no)
Frames: Earn/Org/Joined, Quick Action/Claim, 7d-1d, Shop Coupon, Shop/For You, Sticky Elements, Wallet/Graph
```

If yes:
```bash
python ".claude/export_company_frames.py" --company "[Company Name]"
```

## Step 6: Verify and Report

```bash
echo "Logos:" && ls "Clients/[Company Name]/3. Company Resources/Logos/"
echo "Banner:" && ls "Clients/[Company Name]/3. Company Resources/" | grep -i banner
echo "Swag:" && ls "Clients/[Company Name]/3. Company Resources/Swag/" | wc -l
echo "Figma:" && ls "Clients/[Company Name]/3. Company Resources/" | grep -iE "(earn|shop|wallet|sticky|quick)"
```

Report status clearly — what succeeded, what failed, what still needs user action.
