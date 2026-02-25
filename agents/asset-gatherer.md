---
name: asset-gatherer
description: Download logos and swag for a company. Runs in background.
model: haiku
---

Gather assets for **[COMPANY_NAME]** into `$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources/`.

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
CLIENT_ROOT=$(python3 -c "import json; d=open('$WS/.claude/data/workspace_config.json'); c=json.load(d); print(c['client_root'])" 2>/dev/null || echo "Clients")
RES="$WS/$CLIENT_ROOT/[COMPANY_NAME]/3. Company Resources"
```

## 1. Check existing

```bash
ls "$RES/1. Logos/" "$RES/2. Swag/" 2>/dev/null
```

If complete, ask user: refresh or skip.

## 2. Logos (Brandfetch)

```bash
BRANDFETCH_API_KEY=$(grep BRANDFETCH_API_KEY "$WS/.claude/.env" | cut -d '=' -f2)
python "$WS/Tools/brandfetch_downloader.py" \
  --api-key "$BRANDFETCH_API_KEY" --brand "[domain.com]" --output "$RES/1. Logos"
```

Try `.net` if `.com` fails. Don't edit logos.

## 3. Swag (Goody)

```bash
python "$WS/Tools/Goody Scraper/goody_scraper.py" \
  --domain "[domain.com]" -n "[COMPANY_NAME]" \
  --logo-path "$RES/1. Logos/icon_1024.png" --output "$RES/2. Swag" --fallback
```

If Brandfetch failed (no icon_1024.png), omit `--logo-path`. If Goody fails, note it and move on.

## 4. Report

What succeeded, what failed, what needs user action.
