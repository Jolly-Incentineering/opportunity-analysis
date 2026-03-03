"""
Goody Manual Scraper
====================

Opens Goody in a browser so YOU can enter the domain and upload a logo.
Once mockups are showing, press Enter here and the script downloads them.

Usage:
  python goody_manual.py
  python goody_manual.py --company "Starbucks" --output "path/to/2. Swag/"

Requirements:
  pip install selenium pillow requests
"""

import argparse
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

try:
    import requests
    from PIL import Image
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError as e:
    print(f"Missing dependency: {e}\nRun: pip install selenium Pillow requests",
          file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
GOODY_URL = "https://www.ongoody.com/swag"
MAX_IMAGES = 10
MOCKUP_SELECTOR = "img[src*='lambda-url']"
DL_TIMEOUT = 30
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _sanitize(name):
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    return re.sub(r'\s+', ' ', name).strip('. ')[:200]


# ---------------------------------------------------------------------------
# Browser
# ---------------------------------------------------------------------------
def _create_driver():
    args = ["--start-maximized", "--disable-blink-features=AutomationControlled"]
    exp = {"excludeSwitches": ["enable-automation"], "useAutomationExtension": False}

    for OptCls, DrvCls, name in [
        (EdgeOptions, webdriver.Edge, "Edge"),
        (ChromeOptions, webdriver.Chrome, "Chrome"),
    ]:
        try:
            opts = OptCls()
            for a in args:
                opts.add_argument(a)
            for k, v in exp.items():
                opts.add_experimental_option(k, v)
            return DrvCls(options=opts), name
        except WebDriverException:
            continue
    return None, None


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------
def _download_one(url, dest):
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=DL_TIMEOUT)
    resp.raise_for_status()
    img = Image.open(BytesIO(resp.content))
    if img.mode in ('P', 'LA'):
        img = img.convert('RGBA')
    img.save(dest, 'PNG')
    return dest


def _download_all(products, folder, company):
    ok = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {}
        for p in products:
            fn = _sanitize(f"{company} - {p['name']}.png")
            futs[pool.submit(_download_one, p['url'], folder / fn)] = p['name']
        for fut in as_completed(futs):
            try:
                fut.result()
                ok += 1
                print(f"  [{ok}/{len(futs)}] {futs[fut]}")
            except Exception as e:
                print(f"  {futs[fut]} [FAIL] {str(e)[:60]}")
    return ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(company, output_dir=None):
    folder = Path(output_dir) if output_dir else Path.home() / "Downloads" / "goody_downloads" / _sanitize(company)
    folder.mkdir(parents=True, exist_ok=True)

    driver, browser = _create_driver()
    if not driver:
        print("[FAIL] No supported browser found (need Edge or Chrome + WebDriver)")
        return False

    try:
        print(f"[OK] Browser: {browser}")
        driver.get(GOODY_URL)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "h3")))

        print()
        print("=" * 55)
        print("  GOODY IS OPEN — follow these steps in the browser:")
        print("=" * 55)
        print()
        print("  1. Type the company domain in the search field")
        print("     (e.g. starbucks.com) and press Enter")
        print()
        print("  2. If Goody says 'No images found':")
        print("     - Click 'upload' and select the company logo")
        print("     - Wait for mockups to generate (~10 seconds)")
        print()
        print("  3. Scroll down to see all the branded mockups")
        print()
        print("=" * 55)
        input("  Press ENTER here when mockups are showing... ")
        print()

        # Scroll to trigger any lazy loads
        for px in range(0, 5000, 500):
            driver.execute_script(f"window.scrollTo(0, {px});")
            time.sleep(0.3)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        # Extract products
        products = []
        for h3 in driver.find_elements(By.TAG_NAME, "h3")[:MAX_IMAGES]:
            name = h3.text.strip()
            if not name:
                continue
            try:
                card = h3.find_element(By.XPATH, "ancestor::a")
                img = card.find_element(By.TAG_NAME, "img")
            except Exception:
                continue
            url = img.get_attribute("src") or ""
            if url and not url.startswith("data:"):
                products.append({"name": name, "url": url})

        if not products:
            print("[FAIL] No product mockups found on page")
            print("       Make sure branded images are visible before pressing Enter")
            return False

        print(f"[OK] {len(products)} products found — downloading to {folder}\n")
        downloaded = _download_all(products, folder, company)

        if downloaded > 0:
            print(f"\nDone — {downloaded} images saved to {folder}")
            return True

        print("[FAIL] All downloads failed")
        return False

    except KeyboardInterrupt:
        print("\n[CANCELLED]")
        return False
    except Exception as e:
        print(f"\n[FAIL] {e}")
        return False
    finally:
        driver.quit()


def main():
    p = argparse.ArgumentParser(description="Manual Goody scraper — you browse, script downloads")
    p.add_argument("--company", "-c", help="Company name for file naming")
    p.add_argument("--output", "-o", help="Output folder")
    args = p.parse_args()

    if not args.company:
        args.company = input("Enter company name: ").strip()
        if not args.company:
            print("[FAIL] Company name required")
            sys.exit(1)

    sys.exit(0 if run(args.company, args.output) else 1)


if __name__ == "__main__":
    main()
