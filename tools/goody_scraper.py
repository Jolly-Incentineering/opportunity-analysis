"""
Goody Swag Scraper
==================

Download branded product mockups from ongoody.com/swag.
Auto-detects Microsoft Edge or Chrome. Falls back to local logo
compositing (via logo_compositor) when Goody can't find a domain.

Usage:
  python goody_scraper.py --domain starbucks.com
  python goody_scraper.py --domain x.com --logo-path icon.png --fallback
  python goody_scraper.py --domain x.com --output "path/to/2. Swag/"
  python goody_scraper.py --logo-path icon.png --force-local
  python goody_scraper.py --capture-templates --domain starbucks.com

Requirements:
  pip install selenium pillow requests
"""

import argparse
import os
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
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    _DEPS_AVAILABLE = True
except ImportError as e:
    _DEPS_AVAILABLE = False
    _DEPS_ERROR = str(e)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GOODY_URL = "https://www.ongoody.com/swag"
MAX_IMAGES = 10
MOCKUP_SELECTOR = "img[src*='lambda-url']"
MOCKUP_WAIT_SEC = 30
DOWNLOAD_TIMEOUT = 30
DL_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _sanitize(name, max_len=200):
    """Remove filesystem-unsafe characters from *name*."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip('. ')
    return name[:max_len]


def _company_from_domain(domain):
    """Derive a display name from a bare domain."""
    return domain.lower().replace('www.', '').split('.')[0].capitalize()


# ---------------------------------------------------------------------------
# Browser helpers
# ---------------------------------------------------------------------------
_BROWSER_ARGS = [
    "--start-maximized",
    "--disable-blink-features=AutomationControlled",
]
_BROWSER_EXP = {
    "excludeSwitches": ["enable-automation"],
    "useAutomationExtension": False,
    "prefs": {"profile.default_content_setting_values.notifications": 2},
}


def _make_options(cls):
    """Build browser options for *cls* (EdgeOptions or ChromeOptions)."""
    opts = cls()
    for arg in _BROWSER_ARGS:
        opts.add_argument(arg)
    for key, val in _BROWSER_EXP.items():
        opts.add_experimental_option(key, val)
    return opts


def _create_driver():
    """Return (driver, browser_name) trying Edge first, then Chrome."""
    for cls, driver_cls, name in [
        (EdgeOptions, webdriver.Edge, "Microsoft Edge"),
        (ChromeOptions, webdriver.Chrome, "Google Chrome"),
    ]:
        try:
            driver = driver_cls(options=_make_options(cls))
            return driver, name
        except WebDriverException:
            continue
    return None, None


# ---------------------------------------------------------------------------
# Image download (parallelised)
# ---------------------------------------------------------------------------
def _download_one(url, dest):
    """Download a single image URL to *dest*. Returns dest on success."""
    resp = requests.get(url, headers={"User-Agent": DL_USER_AGENT}, timeout=DOWNLOAD_TIMEOUT)
    resp.raise_for_status()
    img = Image.open(BytesIO(resp.content))
    if img.mode in ('P', 'LA'):
        img = img.convert('RGBA')
    img.save(dest, 'PNG')
    return dest


# ---------------------------------------------------------------------------
# Local-fallback wrapper (lazy import)
# ---------------------------------------------------------------------------
def _run_local_fallback(logo_path, company_name, output_folder):
    """Composite logo onto cached blank templates. Returns image count."""
    try:
        from logo_compositor import generate_all_swag
        return generate_all_swag(logo_path, company_name, output_folder,
                                 sanitize_fn=_sanitize)
    except ImportError:
        print("[FAIL] logo_compositor not available — install it or skip fallback")
        return 0


# ---------------------------------------------------------------------------
# GoodySwagScraper
# ---------------------------------------------------------------------------
class GoodySwagScraper:
    """Scrape branded swag mockups from ongoody.com/swag."""

    def __init__(self, output_dir=None):
        self.driver = None
        self.browser_name = None
        self._custom_output = output_dir is not None
        self._base = Path(output_dir) if output_dir else (
            Path.home() / "Downloads" / "goody_downloads"
        )
        self._base.mkdir(parents=True, exist_ok=True)

    # -- context manager for safe cleanup --
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    # ------------------------------------------------------------------
    # Browser lifecycle
    # ------------------------------------------------------------------
    def _start_browser(self):
        self.driver, self.browser_name = _create_driver()
        if not self.driver:
            print("[FAIL] No supported browser (install Edge or Chrome)")
            return False
        print(f"[OK] Browser: {self.browser_name}")
        return True

    def _load_page(self):
        """Navigate to Goody and wait for React to render."""
        self.driver.get(GOODY_URL)
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "h3"))
        )
        time.sleep(2)

    # ------------------------------------------------------------------
    # Domain submission + "no images" detection + logo upload
    # ------------------------------------------------------------------
    def _submit_domain(self, domain):
        """Type domain into the search field and press Enter."""
        inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
        field = next((i for i in inputs if i.is_displayed()), None)
        if not field:
            raise RuntimeError("Domain input field not found")
        field.click()
        time.sleep(0.5)
        field.clear()
        field.send_keys(domain)
        time.sleep(1)
        field.send_keys(Keys.RETURN)
        time.sleep(5)  # let Goody process

    def _has_no_images_dialog(self):
        """True if Goody is showing 'No images found for this domain'."""
        try:
            elems = self.driver.find_elements(
                By.XPATH, "//*[contains(text(),'No images found')]")
            return any(e.is_displayed() for e in elems)
        except Exception:
            return False

    def _upload_logo(self, logo_path):
        """Upload a local logo PNG via Goody's file input. Returns True on success."""
        print(f"  Uploading {Path(logo_path).name}...")

        # Click any visible "upload" link to reveal the hidden file input
        for btn in self.driver.find_elements(
                By.XPATH, "//*[contains(text(),'upload') or contains(text(),'Upload')]"):
            try:
                if btn.is_displayed():
                    btn.click()
                    time.sleep(1)
                    break
            except Exception:
                continue

        file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        if not file_inputs:
            print("  [WARN] No file input found")
            return False

        # Unhide the input (Goody keeps it display:none)
        inp = file_inputs[0]
        self.driver.execute_script(
            "arguments[0].style.display='block';"
            "arguments[0].style.visibility='visible';", inp)
        inp.send_keys(os.path.abspath(logo_path))
        print("  [OK] Logo uploaded")
        time.sleep(5)
        return True

    # ------------------------------------------------------------------
    # Wait for branded mockups to render
    # ------------------------------------------------------------------
    def _wait_for_mockups(self):
        """Scroll page to trigger lazy loads, then poll for lambda-url images."""
        # Scroll through the grid
        for px in range(0, 5000, 500):
            self.driver.execute_script(f"window.scrollTo(0, {px});")
            time.sleep(0.4)
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        # Poll until we have enough images or timeout
        waited = 0
        while waited < MOCKUP_WAIT_SEC:
            imgs = self.driver.find_elements(By.CSS_SELECTOR, MOCKUP_SELECTOR)
            if len(imgs) >= MAX_IMAGES:
                break
            time.sleep(2)
            waited += 2

        count = len(self.driver.find_elements(By.CSS_SELECTOR, MOCKUP_SELECTOR))
        print(f"  {count} branded mockups loaded")
        return count

    # ------------------------------------------------------------------
    # Extract product cards (name + image URL)
    # ------------------------------------------------------------------
    def _extract_products(self):
        """Return list of {name, url} dicts for up to MAX_IMAGES products."""
        time.sleep(2)
        products = []

        for h3 in self.driver.find_elements(By.TAG_NAME, "h3")[:MAX_IMAGES]:
            name = h3.text.strip()
            if not name:
                continue
            # Walk up to the nearest ancestor <a> and find its <img>
            try:
                card = h3.find_element(By.XPATH, "ancestor::a")
                img = card.find_element(By.TAG_NAME, "img")
            except Exception:
                continue
            url = img.get_attribute("src") or ""
            if url and not url.startswith("data:"):
                products.append({"name": name, "url": url})

        return products

    # ------------------------------------------------------------------
    # Download all extracted images (parallel)
    # ------------------------------------------------------------------
    def _download_all(self, products, output_folder, company_name):
        """Download product images in parallel. Returns count of successes."""
        ok = 0
        total = len(products)

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {}
            for item in products:
                fn = _sanitize(f"{company_name} - {item['name']}.png")
                dest = output_folder / fn
                futures[pool.submit(_download_one, item['url'], dest)] = item['name']

            for fut in as_completed(futures):
                name = futures[fut]
                try:
                    fut.result()
                    ok += 1
                    print(f"  [{ok}/{total}] {name} [OK]")
                except Exception as e:
                    print(f"  {name} [FAIL] {str(e)[:60]}")

        return ok

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, domain=None, company_name=None, logo_path=None,
            fallback=False, force_local=False, capture_templates=False):
        """Main entry point.

        Returns True if at least one image was saved.
        """
        company_name = company_name or (
            _company_from_domain(domain) if domain else
            Path(logo_path).parent.parent.parent.name if logo_path else "Unknown"
        )
        # If caller provided --output, use _base directly (already the target).
        # Otherwise nest under a company subfolder in the default downloads dir.
        if self._custom_output:
            output = self._base
        else:
            output = self._base / _sanitize(company_name)
        output.mkdir(parents=True, exist_ok=True)

        # --- Force-local: skip Goody entirely ---
        if force_local:
            if not logo_path:
                print("[FAIL] --force-local requires --logo-path")
                return False
            return _run_local_fallback(logo_path, company_name, output) > 0

        if not domain:
            print("[FAIL] Domain required (use --force-local to skip Goody)")
            return False

        # --- Goody online flow ---
        print(f"Scraping swag for {company_name} ({domain})")
        print(f"Output: {output}\n")

        try:
            if not self._start_browser():
                return False

            self._load_page()
            print(f"[OK] {GOODY_URL} loaded")

            self._submit_domain(domain)
            print(f"[OK] Domain submitted: {domain}")

            # Handle "No images found" dialog — upload logo if available
            if self._has_no_images_dialog():
                print("[INFO] Goody: 'No images found for this domain'")
                if logo_path and self._upload_logo(logo_path):
                    print("[OK] Retrying with uploaded logo...")
                elif logo_path:
                    print("[WARN] Upload failed")
                else:
                    print("[WARN] No logo to upload")

            mockup_count = self._wait_for_mockups()
            products = self._extract_products()

            if not products:
                print("[WARN] No products extracted from Goody")
                if fallback and logo_path:
                    print("[INFO] Falling back to local compositing...")
                    self.close()
                    return _run_local_fallback(logo_path, company_name, output) > 0
                return False

            print(f"\n[OK] {len(products)} products found — downloading...")
            downloaded = self._download_all(products, output, company_name)

            # Optionally capture as reusable templates
            if capture_templates and downloaded > 0:
                try:
                    from logo_compositor import capture_templates as save_tpl
                    items = [
                        {"name": p["name"],
                         "filepath": str(output / _sanitize(f"{company_name} - {p['name']}.png"))}
                        for p in products
                        if (output / _sanitize(f"{company_name} - {p['name']}.png")).exists()
                    ]
                    if items:
                        save_tpl(items, None)
                except ImportError:
                    pass

            if downloaded > 0:
                print(f"\n{'='*50}")
                print(f"Done — {downloaded} images saved to {output}")
                print(f"{'='*50}")
                return True

            # Downloaded 0 despite having products — try fallback
            if fallback and logo_path:
                print("[WARN] Downloads failed — falling back to local compositing...")
                self.close()
                return _run_local_fallback(logo_path, company_name, output) > 0

            return False

        except KeyboardInterrupt:
            print("\n[CANCELLED]")
            return False
        except Exception as e:
            print(f"\n[FAIL] {e}")
            return False
        finally:
            self.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    if not _DEPS_AVAILABLE:
        print(f"ERROR: Missing dependency: {_DEPS_ERROR}. Run: pip install selenium Pillow requests", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Download branded swag mockups from ongoody.com/swag")
    parser.add_argument("--domain", "-d", help="Company domain (e.g. starbucks.com)")
    parser.add_argument("--company-name", "-n", help="Override company name")
    parser.add_argument("--logo-path", "-l", help="Local logo PNG for upload/fallback")
    parser.add_argument("--output", "-o",
                        help="Download directly to this folder (skips ~/Downloads)")
    parser.add_argument("--fallback", action="store_true",
                        help="Fall back to local compositing if Goody fails")
    parser.add_argument("--force-local", action="store_true",
                        help="Skip Goody; composite logo onto cached templates")
    parser.add_argument("--capture-templates", action="store_true",
                        help="Save downloads as reusable blank templates")
    args, _ = parser.parse_known_args()

    # Interactive prompt if no domain/force-local
    if not args.domain and not args.force_local:
        domain = input("Enter company domain (e.g. google.com): ").strip()
        if not domain or not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
            print("[FAIL] Invalid or empty domain")
            sys.exit(1)
        args.domain = domain

    with GoodySwagScraper(output_dir=args.output) as scraper:
        ok = scraper.run(
            domain=args.domain,
            company_name=args.company_name,
            logo_path=args.logo_path,
            fallback=args.fallback,
            force_local=args.force_local,
            capture_templates=args.capture_templates,
        )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
