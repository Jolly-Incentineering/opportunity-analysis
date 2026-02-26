"""
Brandfetch Logo Downloader
===========================

Download brand logos from Brandfetch API (CLI/headless mode).

Usage:
    python brandfetch_downloader.py --api-key KEY --brand domain.com --output ./logos

INSTALLATION:
  pip install requests

FEATURES:
- Parallel downloads, machine-friendly output
- Download logos in multiple formats (SVG, PNG)
- Save brand colors and fonts information
"""

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _sanitize_filename(filename: str) -> str:
    """Remove invalid characters from a filename."""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', ' ', filename)
    filename = filename.strip('. ')
    if len(filename) > 200:
        filename = filename[:200]
    return filename


# ===================================================================
# CLI (headless) mode
# ===================================================================

def _search_brand_cli(api_key: str, query: str) -> str | None:
    """Search for a brand and return its domain (CLI)."""
    if '.' in query and ' ' not in query:
        return query

    url = "https://api.brandfetch.io/v2/search/" + query
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(url, headers=headers, timeout=15)

    if resp.status_code == 401:
        print("[FAIL] Invalid API key. Check your key at https://brandfetch.com/api")
        return None
    if resp.status_code == 404:
        print(f"[FAIL] Brand '{query}' not found.")
        return None
    resp.raise_for_status()
    data = resp.json()
    if data and len(data) > 0:
        return data[0].get('domain')
    return None


def _fetch_brand_data_cli(api_key: str, domain: str) -> dict | None:
    """Fetch full brand data from Brandfetch (CLI)."""
    url = f"https://api.brandfetch.io/v2/brands/{domain}"
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _download_one_logo(src: str, filepath: Path, label: str) -> tuple[str, bool]:
    """Download a single logo file. Returns (label, success)."""
    try:
        resp = requests.get(src, timeout=30)
        resp.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(resp.content)
        return (label, True)
    except Exception as exc:
        return (f"{label} — {exc}", False)


def _download_logos_parallel(brand_data: dict, output_folder: Path) -> int:
    """Download all logo files using ThreadPoolExecutor. Returns count."""
    logos = brand_data.get('logos', [])
    if not logos:
        print("  [WARN] No logos found in brand data")
        return 0

    print(f"  Found {len(logos)} logo variation(s)\n")

    # Build work items
    tasks: list[tuple[str, Path, str]] = []
    for logo_group in logos:
        logo_type = logo_group.get('type', 'unknown')
        for fmt in logo_group.get('formats', []):
            src = fmt.get('src')
            if not src:
                continue
            format_type = fmt.get('format', 'unknown')
            ext = format_type if format_type in ('svg', 'png', 'jpg', 'jpeg', 'webp') else 'png'
            filename = f"{logo_type}_{format_type}.{ext}"
            tasks.append((src, output_folder / filename, filename))

    if not tasks:
        return 0

    downloaded = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_download_one_logo, src, fp, label): label
            for src, fp, label in tasks
        }
        for future in as_completed(futures):
            label, ok = future.result()
            if ok:
                print(f"    Downloaded {label} [OK]")
                downloaded += 1
            else:
                print(f"    [FAIL] {label}")

    return downloaded


def _save_brand_info(brand_data: dict, output_folder: Path) -> None:
    """Save brand information to JSON file."""
    info = {
        'name': brand_data.get('name'),
        'domain': brand_data.get('domain'),
        'description': brand_data.get('description'),
        'colors': brand_data.get('colors', []),
        'fonts': brand_data.get('fonts', []),
        'links': brand_data.get('links', []),
        'claimed': brand_data.get('claimed'),
    }
    info_file = output_folder / "brand_info.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2, ensure_ascii=False)


def run_cli(api_key: str, brand: str, output: str) -> None:
    """Run the full download pipeline in headless CLI mode."""
    output_folder = Path(output)

    print("=" * 70)
    print(f"Brandfetch Logo Downloader (CLI)")
    print(f"Brand:  {brand}")
    print(f"Output: {output_folder}")
    print("=" * 70 + "\n")

    output_folder.mkdir(parents=True, exist_ok=True)

    # 1 — Resolve brand domain
    print("[1/4] Searching for brand on Brandfetch...")
    domain = _search_brand_cli(api_key, brand)
    if not domain:
        print("[FAIL] Could not find brand. Try a different name or website.")
        sys.exit(1)
    print(f"[OK]   Found brand: {domain}")

    # 2 — Fetch brand data
    print("\n[2/4] Fetching brand data...")
    brand_data = _fetch_brand_data_cli(api_key, domain)
    if not brand_data:
        print("[FAIL] Could not fetch brand data.")
        sys.exit(1)
    brand_name = brand_data.get('name', brand)
    print(f"[OK]   Brand: {brand_name}")

    brand_folder = output_folder / _sanitize_filename(brand_name)
    brand_folder.mkdir(parents=True, exist_ok=True)
    print(f"[OK]   Saving to: {brand_folder}\n")

    # 3 — Download logos (parallel)
    print("[3/4] Downloading logo files...")
    logos_downloaded = _download_logos_parallel(brand_data, brand_folder)

    # 4 — Save brand info JSON
    print("\n[4/4] Saving brand information...")
    _save_brand_info(brand_data, brand_folder)
    print("[OK]   Brand info saved to brand_info.json")

    print(f"\n{'=' * 70}")
    if logos_downloaded > 0:
        print(f"SUCCESS! Downloaded {logos_downloaded} logo file(s)")
    else:
        print("WARNING: No logo files were downloaded")
    print(f"Location: {brand_folder}")
    print("=" * 70)


# ===================================================================
# Entry point
# ===================================================================

def _parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Brandfetch Logo Downloader — CLI mode",
    )
    parser.add_argument("--api-key", required=True, help="Brandfetch API key")
    parser.add_argument("--brand", required=True, help="Brand name or domain (e.g. nike.com)")
    parser.add_argument("--output", default=None, help="Output directory for downloaded logos")
    return parser.parse_args()


def main():
    """Main entry point — CLI mode only."""
    args = _parse_args()
    output = args.output or str(Path.home() / "Downloads" / "brandfetch_logos")
    run_cli(api_key=args.api_key, brand=args.brand, output=output)


if __name__ == "__main__":
    main()
