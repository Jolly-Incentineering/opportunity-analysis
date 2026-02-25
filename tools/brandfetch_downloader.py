"""
Brandfetch Logo Downloader
===========================

Download brand logos from Brandfetch API.  Runs in two modes:

  CLI (headless)  — for agent/script usage:
      python brandfetch_downloader.py --api-key KEY --brand domain.com --output ./logos

  GUI             — for interactive use (requires customtkinter):
      python brandfetch_downloader.py

INSTALLATION:
  pip install requests                       # required (CLI + GUI)
  pip install pillow customtkinter           # optional (GUI only)

FEATURES:
- CLI mode: no GUI dependencies, parallel downloads, machine-friendly output
- GUI mode: beautiful interface, real-time progress, Jolly.com theme
- Download logos in multiple formats (SVG, PNG)
- Save brand colors and fonts information
"""

import argparse
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# GUI imports — deferred so CLI mode works without customtkinter / tkinter
# ---------------------------------------------------------------------------
ctk = None
tk = None
filedialog = None
messagebox = None


def _ensure_gui_imports():
    """Lazy-import GUI libraries. Raises ImportError with a friendly message."""
    global ctk, tk, filedialog, messagebox
    if ctk is not None:
        return
    try:
        import tkinter as _tk
        from tkinter import filedialog as _fd, messagebox as _mb
        import customtkinter as _ctk
    except ImportError as exc:
        print(
            "[ERROR] GUI mode requires customtkinter and tkinter.\n"
            "Install with:  pip install customtkinter\n"
            f"({exc})"
        )
        sys.exit(1)
    ctk = _ctk
    tk = _tk
    filedialog = _fd
    messagebox = _mb


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


# Jolly.com Color Scheme (used by GUI widgets only)
JOLLY_COLORS = {
    'primary_blue': '#123769',
    'neutral_gray': '#666D80',
    'light_gray': '#818898',
    'white': '#FFFFFF',
    'off_white': '#F6F8FA',
    'success_green': '#10B981',
    'error_red': '#EF4444',
    'hover_blue': '#1E4976',
}


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
# GUI mode — classes defined inside a factory so that `ctk` is only
# resolved after _ensure_gui_imports() has run.
# ===================================================================

def _build_gui_classes():
    """Return (ModernButton, ModernEntry, ModernLabel) bound to the live ctk module."""

    class ModernButton(ctk.CTkButton):
        """Styled button matching Jolly.com theme."""
        def __init__(self, master, **kwargs):
            defaults = {
                'fg_color': JOLLY_COLORS['primary_blue'],
                'hover_color': JOLLY_COLORS['hover_blue'],
                'text_color': JOLLY_COLORS['white'],
                'font': ('Segoe UI', 14, 'bold'),
                'corner_radius': 8,
                'height': 45,
                'border_width': 0
            }
            defaults.update(kwargs)
            super().__init__(master, **defaults)

    class ModernEntry(ctk.CTkEntry):
        """Styled entry field matching Jolly.com theme."""
        def __init__(self, master, **kwargs):
            defaults = {
                'fg_color': JOLLY_COLORS['white'],
                'text_color': JOLLY_COLORS['neutral_gray'],
                'border_color': JOLLY_COLORS['light_gray'],
                'font': ('Segoe UI', 12),
                'corner_radius': 8,
                'height': 45,
                'border_width': 2
            }
            defaults.update(kwargs)
            super().__init__(master, **defaults)

    class ModernLabel(ctk.CTkLabel):
        """Styled label matching Jolly.com theme."""
        def __init__(self, master, **kwargs):
            defaults = {
                'text_color': JOLLY_COLORS['neutral_gray'],
                'font': ('Segoe UI', 12)
            }
            defaults.update(kwargs)
            super().__init__(master, **defaults)

    return ModernButton, ModernEntry, ModernLabel


class BrandfetchDownloaderGUI:
    """Main GUI application for Brandfetch logo downloader."""

    def __init__(self):
        _ensure_gui_imports()
        self.ModernButton, self.ModernEntry, self.ModernLabel = _build_gui_classes()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Brandfetch Logo Downloader")
        self.root.geometry("750x900")
        self.root.resizable(False, False)
        self.root.configure(fg_color=JOLLY_COLORS['off_white'])

        # Variables
        self.api_key = tk.StringVar()
        self.brand_query = tk.StringVar()
        self.output_folder = tk.StringVar(value=str(Path.home() / "Downloads" / "brandfetch_logos"))
        self.is_downloading = False

        self.setup_ui()

    def setup_ui(self):
        """Set up the main user interface."""
        main_frame = ctk.CTkFrame(self.root, fg_color=JOLLY_COLORS['off_white'], corner_radius=0)
        main_frame.pack(fill='both', expand=True, padx=40, pady=30)

        self.create_header(main_frame)
        self.create_instructions(main_frame)
        self.create_input_section(main_frame)
        self.create_action_section(main_frame)
        self.create_progress_section(main_frame)
        self.create_footer(main_frame)

    def create_header(self, parent):
        """Create header with title and subtitle."""
        header_frame = ctk.CTkFrame(parent, fg_color='transparent')
        header_frame.pack(fill='x', pady=(0, 20))

        ctk.CTkLabel(
            header_frame, text="Brandfetch Logo Downloader",
            font=('Segoe UI', 32, 'bold'), text_color=JOLLY_COLORS['primary_blue']
        ).pack(pady=(0, 5))

        ctk.CTkLabel(
            header_frame, text="Download High-Quality Brand Logos",
            font=('Segoe UI', 14), text_color=JOLLY_COLORS['light_gray']
        ).pack()

        ctk.CTkFrame(header_frame, height=2, fg_color=JOLLY_COLORS['light_gray']).pack(fill='x', pady=(15, 0))

    def create_instructions(self, parent):
        """Create instructions section."""
        instructions_frame = ctk.CTkFrame(parent, fg_color=JOLLY_COLORS['white'], corner_radius=12)
        instructions_frame.pack(fill='x', pady=(0, 20))

        instructions_inner = ctk.CTkFrame(instructions_frame, fg_color='transparent')
        instructions_inner.pack(fill='both', padx=20, pady=15)

        ctk.CTkLabel(
            instructions_inner, text="📖 Quick Setup:",
            font=('Segoe UI', 13, 'bold'), text_color=JOLLY_COLORS['primary_blue']
        ).pack(anchor='w')

        instructions_text = """
1. Get your FREE API key: https://brandfetch.com/api
2. Click "Sign Up" → Verify email → Copy your API key
3. Paste the API key below (it will be hidden for security)
4. Enter any brand name or website (e.g., "Nike" or "nike.com")
5. Click "Download Logos" and wait for the magic ✨
        """.strip()

        ctk.CTkLabel(
            instructions_inner, text=instructions_text,
            font=('Segoe UI', 11), text_color=JOLLY_COLORS['neutral_gray'],
            justify='left'
        ).pack(anchor='w', pady=(5, 0))

    def create_input_section(self, parent):
        """Create input fields section."""
        input_frame = ctk.CTkFrame(parent, fg_color=JOLLY_COLORS['white'], corner_radius=12, border_width=0)
        input_frame.pack(fill='x', pady=(0, 20))

        input_inner = ctk.CTkFrame(input_frame, fg_color='transparent')
        input_inner.pack(fill='both', padx=25, pady=25)

        # API Key field
        self.ModernLabel(
            input_inner, text="Brandfetch API Key (required)",
            font=('Segoe UI', 12, 'bold')
        ).grid(row=0, column=0, sticky='w', pady=(0, 5))

        self.ModernEntry(
            input_inner, textvariable=self.api_key,
            placeholder_text="Paste your API key here...",
            show="•"  # Hide API key like a password
        ).grid(row=1, column=0, sticky='ew', pady=(0, 15))

        # Brand name/website field
        self.ModernLabel(
            input_inner, text="Brand Name or Website",
            font=('Segoe UI', 12, 'bold')
        ).grid(row=2, column=0, sticky='w', pady=(0, 5))

        self.ModernEntry(
            input_inner, textvariable=self.brand_query,
            placeholder_text="e.g., Nike, nike.com, apple.com"
        ).grid(row=3, column=0, sticky='ew', pady=(0, 15))

        # Output folder field
        self.ModernLabel(
            input_inner, text="Save Logos To",
            font=('Segoe UI', 12, 'bold')
        ).grid(row=4, column=0, sticky='w', pady=(0, 5))

        folder_frame = ctk.CTkFrame(input_inner, fg_color='transparent')
        folder_frame.grid(row=5, column=0, sticky='ew')
        folder_frame.grid_columnconfigure(0, weight=1)

        self.ModernEntry(
            folder_frame, textvariable=self.output_folder,
            placeholder_text="Select output folder..."
        ).grid(row=0, column=0, sticky='ew', padx=(0, 10))

        ctk.CTkButton(
            folder_frame, text="Browse", command=self.browse_folder,
            fg_color=JOLLY_COLORS['light_gray'], hover_color=JOLLY_COLORS['neutral_gray'],
            text_color=JOLLY_COLORS['white'], font=('Segoe UI', 12, 'bold'),
            corner_radius=8, width=100, height=45
        ).grid(row=0, column=1)

        input_inner.grid_columnconfigure(0, weight=1)

    def create_action_section(self, parent):
        """Create action button section."""
        action_frame = ctk.CTkFrame(parent, fg_color='transparent')
        action_frame.pack(fill='x', pady=(0, 20))

        self.download_button = self.ModernButton(
            action_frame, text="Download Logos", command=self.start_download,
            height=55, font=('Segoe UI', 16, 'bold')
        )
        self.download_button.pack(fill='x')

    def create_progress_section(self, parent):
        """Create progress bar and status log section."""
        progress_frame = ctk.CTkFrame(parent, fg_color=JOLLY_COLORS['white'], corner_radius=12)
        progress_frame.pack(fill='both', expand=True, pady=(0, 20))

        progress_inner = ctk.CTkFrame(progress_frame, fg_color='transparent')
        progress_inner.pack(fill='both', expand=True, padx=25, pady=25)

        self.ModernLabel(
            progress_inner, text="Status", font=('Segoe UI', 13, 'bold')
        ).pack(anchor='w', pady=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(
            progress_inner, fg_color=JOLLY_COLORS['off_white'],
            progress_color=JOLLY_COLORS['primary_blue'], corner_radius=8, height=12
        )
        self.progress_bar.pack(fill='x', pady=(0, 15))
        self.progress_bar.set(0)

        self.status_text = ctk.CTkTextbox(
            progress_inner, fg_color=JOLLY_COLORS['off_white'],
            text_color=JOLLY_COLORS['neutral_gray'], font=('Consolas', 11),
            corner_radius=8, border_width=0, height=280, wrap='word'
        )
        self.status_text.pack(fill='both', expand=True)
        self.status_text.insert('1.0', "Ready! Fill in your API key and brand name, then click 'Download Logos'.")
        self.status_text.configure(state='disabled')

    def create_footer(self, parent):
        """Create footer with attribution."""
        ctk.CTkLabel(
            parent, text="Powered by Brandfetch API & Jolly Design",
            font=('Segoe UI', 10), text_color=JOLLY_COLORS['light_gray']
        ).pack(pady=(10, 0))

    def browse_folder(self):
        """Open folder browser dialog."""
        folder = filedialog.askdirectory(title="Select Output Folder", initialdir=self.output_folder.get())
        if folder:
            self.output_folder.set(folder)

    def validate_inputs(self):
        """Validate user inputs before starting download."""
        if not self.api_key.get().strip():
            messagebox.showerror("Error", "Please enter your Brandfetch API key.\n\nGet one free at: https://brandfetch.com/api")
            return False
        if not self.brand_query.get().strip():
            messagebox.showerror("Error", "Please enter a brand name or website.")
            return False
        if not self.output_folder.get().strip():
            messagebox.showerror("Error", "Please select an output folder.")
            return False
        return True

    def log_message(self, message):
        """Add message to status log."""
        def _log():
            self.status_text.configure(state='normal')
            self.status_text.insert('end', message + '\n')
            self.status_text.see('end')
            self.status_text.configure(state='disabled')
        self.root.after(0, _log)

    def update_progress(self, value):
        """Update progress bar value."""
        self.root.after(0, lambda: self.progress_bar.set(value))

    def start_download(self):
        """Start download process in background thread."""
        if self.is_downloading:
            return
        if not self.validate_inputs():
            return

        self.is_downloading = True
        self.download_button.configure(state='disabled', text='Downloading...')

        # Clear status log
        self.status_text.configure(state='normal')
        self.status_text.delete('1.0', 'end')
        self.status_text.configure(state='disabled')
        self.update_progress(0)

        # Start download in background thread
        thread = threading.Thread(target=self.run_download, daemon=True)
        thread.start()

    def run_download(self):
        """Main download logic running in background thread."""
        try:
            api_key = self.api_key.get().strip()
            query = self.brand_query.get().strip()
            output_folder = Path(self.output_folder.get().strip())

            self.log_message("=" * 70)
            self.log_message(f"Starting Brandfetch download for: {query}")
            self.log_message(f"Output: {output_folder}")
            self.log_message("=" * 70 + "\n")

            # Create output folder
            output_folder.mkdir(parents=True, exist_ok=True)

            # Step 1: Search for brand
            self.update_progress(0.1)
            self.log_message("[1/4] Searching for brand on Brandfetch...")

            brand_domain = self.search_brand(api_key, query)
            if not brand_domain:
                self.log_message("\n[FAIL] Could not find brand. Try a different name or website.")
                self.finish_download(False)
                return

            self.log_message(f"[OK] Found brand: {brand_domain}")

            # Step 2: Fetch brand data
            self.update_progress(0.3)
            self.log_message(f"\n[2/4] Fetching brand data from Brandfetch...")

            brand_data = self.fetch_brand_data(api_key, brand_domain)
            if not brand_data:
                self.log_message("\n[FAIL] Could not fetch brand data.")
                self.finish_download(False)
                return

            brand_name = brand_data.get('name', query)
            self.log_message(f"[OK] Brand: {brand_name}")

            # Create brand-specific subfolder
            brand_folder = output_folder / _sanitize_filename(brand_name)
            brand_folder.mkdir(parents=True, exist_ok=True)
            self.log_message(f"[OK] Saving to: {brand_folder}\n")

            # Step 3: Download logos (parallel)
            self.update_progress(0.5)
            self.log_message("[3/4] Downloading logo files...")

            logos_downloaded = self._download_logos_gui(brand_data, brand_folder)

            if logos_downloaded == 0:
                self.log_message("\n[WARN] No logo files downloaded")

            # Step 4: Save brand info
            self.update_progress(0.8)
            self.log_message("\n[4/4] Saving brand information...")

            _save_brand_info(brand_data, brand_folder)
            self.log_message("[OK] Brand info saved to brand_info.json")

            self.update_progress(1.0)

            if logos_downloaded > 0:
                self.log_message(f"\n{'='*70}")
                self.log_message(f"SUCCESS! Downloaded {logos_downloaded} logo files")
                self.log_message(f"Location: {brand_folder}")
                self.log_message("="*70)
                self.finish_download(True, brand_folder)
            else:
                self.log_message("\n[FAIL] No logos were downloaded")
                self.finish_download(False)

        except Exception as e:
            self.log_message(f"\n[FAIL] Error: {str(e)}")
            import traceback
            self.log_message(f"\n{traceback.format_exc()}")
            self.finish_download(False)

    def search_brand(self, api_key, query):
        """Search for a brand and return its domain."""
        try:
            # If query looks like a domain, use it directly
            if '.' in query and ' ' not in query:
                return query

            # Otherwise, search using Brandfetch API
            url = "https://api.brandfetch.io/v2/search/" + query
            headers = {"Authorization": f"Bearer {api_key}"}

            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 401:
                self.log_message("\n[FAIL] Invalid API key. Please check your API key.")
                return None
            elif response.status_code == 404:
                self.log_message(f"\n[FAIL] Brand '{query}' not found.")
                return None

            response.raise_for_status()
            data = response.json()

            # Return first result's domain
            if data and len(data) > 0:
                return data[0].get('domain')

            return None

        except requests.exceptions.RequestException as e:
            self.log_message(f"\n[FAIL] Search error: {str(e)}")
            return None

    def fetch_brand_data(self, api_key, domain):
        """Fetch full brand data from Brandfetch."""
        try:
            url = f"https://api.brandfetch.io/v2/brands/{domain}"
            headers = {"Authorization": f"Bearer {api_key}"}

            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            self.log_message(f"\n[FAIL] Fetch error: {str(e)}")
            return None

    def _download_logos_gui(self, brand_data, output_folder):
        """Download all logo files with parallel I/O, logging to the GUI."""
        logos = brand_data.get('logos', [])
        if not logos:
            self.log_message("  [WARN] No logos found in brand data")
            return 0

        self.log_message(f"  Found {len(logos)} logo variation(s)\n")

        # Build work items
        tasks = []
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
                    self.log_message(f"    Downloaded {label} [OK]")
                    downloaded += 1
                else:
                    self.log_message(f"    [FAIL] {label}")

        return downloaded

    def finish_download(self, success, folder=None):
        """Finish download and update UI."""
        def _finish():
            self.is_downloading = False
            self.download_button.configure(state='normal', text='Download Logos')
            if success:
                messagebox.showinfo(
                    "Success",
                    f"Successfully downloaded brand logos!\n\nSaved to:\n{folder}"
                )
            else:
                messagebox.showerror("Error", "Download failed. Check the status log for details.")
        self.root.after(0, _finish)

    def run(self):
        """Start the GUI application."""
        self.root.mainloop()


# ===================================================================
# Entry point — CLI vs GUI routing
# ===================================================================

def _parse_args():
    """Parse CLI arguments. Returns namespace (all None when no flags given)."""
    parser = argparse.ArgumentParser(
        description="Brandfetch Logo Downloader — CLI and GUI modes",
        epilog="If no flags are passed the GUI launches instead.",
    )
    parser.add_argument("--api-key", default=None, help="Brandfetch API key")
    parser.add_argument("--brand", default=None, help="Brand name or domain (e.g. nike.com)")
    parser.add_argument("--output", default=None, help="Output directory for downloaded logos")
    return parser.parse_args()


def main():
    """Main entry point — routes to CLI or GUI based on arguments."""
    args = _parse_args()

    # CLI mode: --brand was provided
    if args.brand:
        if not args.api_key:
            print("[ERROR] --api-key is required in CLI mode.")
            sys.exit(1)
        output = args.output or str(Path.home() / "Downloads" / "brandfetch_logos")
        run_cli(api_key=args.api_key, brand=args.brand, output=output)
        return

    # GUI mode
    try:
        app = BrandfetchDownloaderGUI()
        app.run()
    except Exception as e:
        # If GUI imports worked, use messagebox; otherwise just print
        if messagebox is not None:
            messagebox.showerror("Error", f"Failed to start application:\n{str(e)}")
        else:
            print(f"[ERROR] Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
