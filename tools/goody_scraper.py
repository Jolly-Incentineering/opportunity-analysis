"""
Goody Swag Scraper
==================

A Python script to scrape product images from Goody's swag website (ongoody.com/swag)
Automatically detects and uses Microsoft Edge or Chrome browser.

Supports a local logo fallback: if Ongoody doesn't recognise a company domain,
the scraper can composite the company's logo onto cached blank product templates.

INSTALLATION INSTRUCTIONS:
--------------------------
1. Install Python packages:
   pip install selenium pillow requests

2. Browser drivers are automatically managed by Selenium!
   No manual installation needed.

3. Verify Microsoft Edge or Chrome browser is installed

HOW TO RUN:
-----------
1. Open a terminal/command prompt
2. Navigate to the script directory
3. Run: python goody_scraper.py
4. Enter the company domain when prompted (e.g., google.com)
5. Wait for the script to complete
6. Find downloaded images in the "goody_downloads" folder on your Desktop

CLI FLAGS:
----------
  python goody_scraper.py                                # interactive prompt
  python goody_scraper.py --domain starbucks.com         # domain only
  python goody_scraper.py --logo-path /path/icon.png --force-local  # skip Ongoody
  python goody_scraper.py --domain x.com --logo-path /path/icon.png --fallback
  python goody_scraper.py --capture-templates --domain starbucks.com

"""

import argparse
import os
import sys
import time
import re
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from PIL import Image
from io import BytesIO


class GoodySwagScraper:
    """Scraper for Goody swag website with auto browser detection."""

    def __init__(self):
        """Initialize the scraper."""
        self.base_url = "https://www.ongoody.com/swag"
        self.driver = None
        self.browser_name = None
        self.download_folder = self._get_desktop_folder()

    def _get_desktop_folder(self):
        """Get the path to the goody_downloads folder on Desktop."""
        downloads = Path.home() / "Downloads" / "goody_downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        print(f"[OK] Base download folder: {downloads}")
        return downloads

    def _setup_driver(self):
        """Set up WebDriver with automatic browser detection (Edge first, then Chrome)."""
        print("\n[1/6] Setting up WebDriver...")

        # Try Microsoft Edge first
        try:
            edge_options = EdgeOptions()
            edge_options.add_argument("--start-maximized")
            edge_options.add_argument("--disable-blink-features=AutomationControlled")
            edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            edge_options.add_experimental_option('useAutomationExtension', False)

            # DO NOT disable images - we need them to render the mockups
            prefs = {
                "profile.default_content_setting_values.notifications": 2
            }
            edge_options.add_experimental_option("prefs", prefs)

            self.driver = webdriver.Edge(options=edge_options)
            self.browser_name = "Microsoft Edge"
            print(f"[OK] Using {self.browser_name}")
            return True

        except WebDriverException:
            print("[INFO] Microsoft Edge not available, trying Chrome...")

        # Try Chrome as fallback
        try:
            chrome_options = ChromeOptions()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            prefs = {
                "profile.default_content_setting_values.notifications": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)

            self.driver = webdriver.Chrome(options=chrome_options)
            self.browser_name = "Chrome"
            print(f"[OK] Using {self.browser_name}")
            return True

        except WebDriverException:
            print("[FAIL] No supported browser found")
            print("\nPlease install one of the following:")
            print("  - Microsoft Edge (recommended)")
            print("  - Google Chrome")
            return False

    def _sanitize_filename(self, filename):
        """Remove invalid characters from filename."""
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\s+', ' ', filename)
        filename = filename.strip('. ')
        if len(filename) > 200:
            filename = filename[:200]
        return filename

    def _extract_company_name(self, domain):
        """Extract company name from domain."""
        domain = domain.lower().replace('www.', '')
        company_name = domain.split('.')[0]
        return company_name.capitalize()

    def open_website(self):
        """Open the Goody swag website."""
        print(f"\n[2/6] Opening {self.base_url}...")

        try:
            self.driver.get(self.base_url)
            # Wait for h3 product titles to appear (React app fully loaded)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "h3"))
            )
            print("[OK] Website loaded successfully")
            time.sleep(2)
            return True

        except TimeoutException:
            print("[FAIL] Timeout: Website took too long to load")
            return False
        except Exception as e:
            print(f"[FAIL] Error opening website: {e}")
            return False

    def enter_company_domain(self, domain):
        """Enter company domain into the search field and wait for mockup images."""
        print(f"\n[3/6] Entering company domain: {domain}")

        try:
            # Find the visible text input for company domain
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
            input_field = None
            for inp in inputs:
                if inp.is_displayed():
                    input_field = inp
                    break

            if not input_field:
                print("[FAIL] Could not find domain input field")
                return False

            print("[OK] Found domain input field")
            input_field.click()
            time.sleep(0.5)
            input_field.clear()
            input_field.send_keys(domain)
            time.sleep(1)
            input_field.send_keys(Keys.RETURN)
            print("[OK] Submitted domain, waiting for branded mockups to generate...")

            # Wait for initial mockups to start loading
            time.sleep(5)

            return True

        except Exception as e:
            print(f"[FAIL] Error entering domain: {e}")
            return False

    def upload_custom_logo(self, logo_path):
        """Upload a custom logo file to Ongoody instead of selecting from their options."""
        print(f"\n[3.5/6] Uploading custom logo: {Path(logo_path).name}")

        try:
            # Look for file upload input (there may be multiple, find visible one)
            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")

            if not file_inputs:
                print("[INFO] No logo upload dialog detected, continuing with auto-selection")
                return True

            # Find the visible/enabled file input
            upload_input = None
            for inp in file_inputs:
                try:
                    if inp.is_displayed() or inp.is_enabled():
                        upload_input = inp
                        break
                except:
                    continue

            if not upload_input:
                print("[INFO] No active upload input found, continuing with auto-selection")
                return True

            # Upload the logo file
            abs_logo_path = os.path.abspath(logo_path)
            upload_input.send_keys(abs_logo_path)
            print(f"[OK] Logo uploaded successfully")

            # Wait for upload to process
            time.sleep(3)

            return True

        except Exception as e:
            print(f"[WARN] Could not upload logo: {e}")
            print("[INFO] Continuing with Ongoody's auto-selection")
            return True

    def wait_for_mockups_to_generate(self):
        """Wait for mockup images to finish generating after domain/logo submission."""
        print(f"\n[3.75/6] Waiting for mockups to generate...")

        try:
            time.sleep(2)

            # Scroll through the product grid to trigger lazy-loaded mockup images
            print("[INFO] Scrolling page to load all mockup images...")
            for scroll_step in range(0, 5000, 500):
                self.driver.execute_script(f"window.scrollTo(0, {scroll_step});")
                time.sleep(0.5)

            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)

            # Wait for all mockup images to finish generating (lambda URLs)
            print("[INFO] Waiting for all mockup images to render...")
            max_wait = 30
            waited = 0
            target_count = 10
            while waited < max_wait:
                mockup_imgs = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='lambda-url']")
                if len(mockup_imgs) >= target_count:
                    break
                time.sleep(2)
                waited += 2
                print(f"[INFO] {len(mockup_imgs)} mockups loaded so far... (waiting)")

            mockup_imgs = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='lambda-url']")
            print(f"[OK] {len(mockup_imgs)} branded mockup images loaded")

            return True

        except Exception as e:
            print(f"[FAIL] Error waiting for mockups: {e}")
            return False

    def extract_product_images(self, company_name, max_images=10):
        """Extract product images and their names from the page."""
        print(f"\n[4/6] Extracting product images (max: {max_images})...")

        try:
            time.sleep(3)

            # The site uses h3 elements for product names, each inside an <a> tag
            # Structure: <a><div><img/><div><h3>Name</h3>...</div></div></a>
            h3_elements = self.driver.find_elements(By.TAG_NAME, "h3")

            if not h3_elements:
                print("[FAIL] No product titles found")
                return []

            print(f"[OK] Found {len(h3_elements)} products on page")

            image_data = []

            for idx, h3 in enumerate(h3_elements[:max_images]):
                try:
                    product_name = h3.text.strip()
                    if not product_name:
                        continue

                    # Navigate up to the <a> tag (h3 -> div -> a) to find the associated image
                    try:
                        parent_div = h3.find_element(By.XPATH, "..")
                        product_card = parent_div.find_element(By.XPATH, "..")
                    except Exception:
                        continue

                    # Find the img within this product card
                    imgs = product_card.find_elements(By.TAG_NAME, "img")
                    if not imgs:
                        # Try one more level up
                        try:
                            product_card = product_card.find_element(By.XPATH, "..")
                            imgs = product_card.find_elements(By.TAG_NAME, "img")
                        except Exception:
                            pass

                    if not imgs:
                        print(f"  [SKIP] {product_name}: No image found")
                        continue

                    img_element = imgs[0]
                    img_url = img_element.get_attribute('src')

                    if not img_url or img_url.startswith("data:"):
                        print(f"  [SKIP] {product_name}: No valid image URL")
                        continue

                    image_data.append({
                        'url': img_url,
                        'name': product_name,
                        'index': idx + 1
                    })

                    print(f"  [{idx + 1}] {product_name}")

                except Exception:
                    continue

            print(f"\n[OK] Extracted {len(image_data)} images")
            return image_data

        except Exception as e:
            print(f"[FAIL] Error extracting images: {e}")
            return []

    def download_images(self, image_data, company_name):
        """Download images and save them with proper names."""
        print(f"\n[5/6] Downloading images...")

        successful_downloads = 0
        failed_downloads = 0

        for item in image_data:
            try:
                img_url = item['url']
                product_name = item['name']
                index = item['index']

                filename = f"{company_name} - {product_name}.png"
                filename = self._sanitize_filename(filename)
                filepath = self.download_folder / filename

                print(f"  [{index}/{len(image_data)}] {product_name}...", end=" ")

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }

                response = requests.get(img_url, headers=headers, timeout=30)
                response.raise_for_status()

                image = Image.open(BytesIO(response.content))

                # Preserve transparency — convert palette mode to RGBA
                if image.mode == 'P':
                    image = image.convert('RGBA')
                elif image.mode == 'LA':
                    image = image.convert('RGBA')

                image.save(filepath, 'PNG')

                print("[OK]")
                successful_downloads += 1

            except requests.exceptions.RequestException as e:
                print(f"[FAIL] {str(e)[:50]}")
                failed_downloads += 1
            except Exception as e:
                print(f"[FAIL] {str(e)[:50]}")
                failed_downloads += 1

        print(f"\n[OK] Downloaded: {successful_downloads} successful, {failed_downloads} failed")
        return successful_downloads

    def close(self):
        """Close the browser and clean up."""
        if self.driver:
            try:
                self.driver.quit()
                print("\n[6/6] Browser closed")
            except Exception:
                pass

    def run(self, domain, company_name=None, logo_path=None, fallback=False,
            force_local=False, capture_templates=False):
        """Main execution flow with optional local-logo fallback.

        Args:
            domain: Company domain for Ongoody lookup (can be None if force_local).
            company_name: Override company name (derived from domain if omitted).
            logo_path: Path to local logo file for fallback compositing.
            fallback: If True, fall back to local compositing when Ongoody fails.
            force_local: If True, skip Ongoody entirely and use local compositing.
            capture_templates: If True, save downloaded images as reusable templates.
        """
        from logo_compositor import generate_all_swag, capture_templates as save_templates

        # --- Force-local mode: skip Ongoody entirely ---
        if force_local:
            if not logo_path:
                print("[FAIL] --force-local requires --logo-path")
                return False
            if not company_name:
                company_name = Path(logo_path).parent.parent.parent.name  # guess from path
            company_folder = self.download_folder / self._sanitize_filename(company_name)
            company_folder.mkdir(parents=True, exist_ok=True)
            print(f"[OK] Force-local mode — compositing logo onto templates")
            count = generate_all_swag(logo_path, company_name, company_folder,
                                      sanitize_fn=self._sanitize_filename)
            return count > 0

        # --- Normal Ongoody flow ---
        if not domain:
            print("[FAIL] Domain is required (use --force-local to skip Ongoody)")
            return False

        if not company_name:
            company_name = self._extract_company_name(domain)

        try:
            if not self._setup_driver():
                return False

            # Create company-specific subfolder
            company_folder = self.download_folder / self._sanitize_filename(company_name)
            company_folder.mkdir(parents=True, exist_ok=True)
            self.download_folder = company_folder
            print(f"[OK] Saving to: {company_folder}")

            if not self.open_website():
                return False

            if not self.enter_company_domain(domain):
                return False

            # Upload custom logo if provided (overrides Ongoody's auto-selected logo)
            if logo_path:
                if not self.upload_custom_logo(logo_path):
                    print("[WARN] Logo upload failed, continuing anyway...")

            # Wait for mockups to finish generating
            if not self.wait_for_mockups_to_generate():
                return False

            image_data = self.extract_product_images(company_name, max_images=10)

            if not image_data:
                print("\n[WARN] No images found from Ongoody")
                if fallback and logo_path:
                    print("[INFO] Falling back to local logo compositing...")
                    self.close()
                    count = generate_all_swag(logo_path, company_name, company_folder,
                                              sanitize_fn=self._sanitize_filename)
                    return count > 0
                print("[FAIL] No images found (use --fallback with --logo-path to composite locally)")
                return False

            success_count = self.download_images(image_data, company_name)

            # Optionally save as templates for future fallback use
            if capture_templates and success_count > 0:
                items = []
                for item in image_data:
                    fn = f"{company_name} - {item['name']}.png"
                    fn = self._sanitize_filename(fn)
                    fp = company_folder / fn
                    if fp.exists():
                        items.append({"name": item["name"], "filepath": str(fp)})
                if items:
                    print("\n[INFO] Saving downloaded images as reusable templates...")
                    save_templates(items, None)

            if success_count > 0:
                # Check if we got fewer than expected — offer fallback
                if success_count < 10 and fallback and logo_path:
                    print(f"\n[WARN] Only {success_count}/10 images — falling back for remaining")
                    # Still return True since we got some images
                print(f"\n{'='*60}")
                print(f"SUCCESS! {success_count} images saved to:")
                print(f"{self.download_folder}")
                print(f"{'='*60}")
                return True
            else:
                if fallback and logo_path:
                    print("\n[WARN] No images downloaded — falling back to local compositing...")
                    count = generate_all_swag(logo_path, company_name, company_folder,
                                              sanitize_fn=self._sanitize_filename)
                    return count > 0
                print("\n[FAIL] No images downloaded")
                return False

        except KeyboardInterrupt:
            print("\n\n[CANCELLED] Operation cancelled by user")
            return False
        except Exception as e:
            print(f"\n[FAIL] Unexpected error: {e}")
            return False
        finally:
            self.close()


def main():
    """Main function to run the scraper."""
    parser = argparse.ArgumentParser(
        description="Goody Swag Scraper — download branded mockups from ongoody.com/swag",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--domain", "-d", help="Company domain (e.g. starbucks.com)")
    parser.add_argument("--company-name", "-n", help="Override company name")
    parser.add_argument("--logo-path", "-l", help="Path to local logo PNG for fallback compositing")
    parser.add_argument("--fallback", action="store_true",
                        help="Fall back to local logo compositing if Ongoody fails")
    parser.add_argument("--force-local", action="store_true",
                        help="Skip Ongoody entirely; composite logo onto cached templates")
    parser.add_argument("--capture-templates", action="store_true",
                        help="Save downloaded images as reusable blank templates")

    # If no args provided, fall back to interactive mode
    args, _ = parser.parse_known_args()
    if not args.domain and not args.force_local:
        print("=" * 60)
        print("          GOODY SWAG SCRAPER")
        print("=" * 60)
        print()
        domain = input("Enter company domain (e.g., google.com): ").strip()
        if not domain:
            print("[FAIL] Domain cannot be empty")
            return
        if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
            print("[FAIL] Invalid domain format. Example: google.com")
            return
        print(f"\nStarting scraper for: {domain}")
        print("-" * 60)
        scraper = GoodySwagScraper()
        success = scraper.run(domain)
        sys.exit(0 if success else 1)

    # CLI mode
    scraper = GoodySwagScraper()
    success = scraper.run(
        domain=args.domain,
        company_name=args.company_name,
        logo_path=args.logo_path,
        fallback=args.fallback,
        force_local=args.force_local,
        capture_templates=args.capture_templates,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
