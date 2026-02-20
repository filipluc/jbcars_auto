"""
main.py — Entry point for jbcars_auto.

Full flow:
  1. Start Chrome with remote debugging (uses an existing logged-in profile).
  2. Scrape all active listings from the 2dehands.be seller dashboard.
  3. For each listing:
       a. Post a fresh new listing with the same data (bumps the date).
       b. Delete the old original listing.

To process only specific cars, set FILTER_TITLES to a list of substrings.
Leave it empty to process all active listings.

Examples:
    FILTER_TITLES = []                            # run all
    FILTER_TITLES = ["peugeot partner"]           # run only Peugeot Partners
    FILTER_TITLES = ["opel combo", "hyundai"]     # run Opels and Hyundais
"""

import datetime
import os
import subprocess
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import scraper
import poster


# ---------------------------------------------------------------------------
# Configuration — edit here before running
# ---------------------------------------------------------------------------

# Leave empty to process ALL active (non-Gereserveerd) listings.
# Set to one or more title substrings to only process matching cars.
FILTER_TITLES = []

# Leave empty for no exclusions.
# Set to one or more title substrings to skip matching cars.
EXCLUDE_TITLES = [
    "peugeot 208 GT line ,1.2 i/4600 km/alcantara/panorama dak",
    "peugeot partner TEPEE 1.2 i/CAR PASS/euro 6b/Garantie",
    "peugeot partner 1.6 hdi-92pk/CAR PASS/euro 5/garantie",
    "opel combo Tour1.6 cdti/GEKEURD/CAR PASS/eerste eigenaar",
    "peugeot boxer 2.0 hdi/GEKEURD/CAR PASS/euro 6b/6+1 pl/airco",
    "citroen berlingo 1.6 hdi/CAR PASS/garantie/euro 5"
]

# Set to False to only post a new listing without deleting the original.
DELETE_AFTER_POST = True

# Set to None to upload all photos, or a number (e.g. 1) to limit uploads for faster testing.
MAX_PHOTOS = None

# Text appended to every listing description.
DESC_FOOTER = (
    "\n\nMeer Info 0485/673404\n"
    "E-mail: jb.cars@hotmail.com\n"
    "Opgelet: Tijdelijk enkel op afspraak\n"
    "Attention: Temporairement uniquement sur rendez-vous\n\n"
    "adres\n"
    "LIERSESTEENWEG 153\n"
    "2547 LINT"
)

CHROME_PATH    = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
USER_DATA_DIR  = r'C:\ChromeDebugProfile'
DEBUG_PORT     = 2222
DASHBOARD_URL  = 'https://www.2dehands.be/my-account/sell/index.html'
REPORT_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.log")


# ---------------------------------------------------------------------------
# Chrome helpers
# ---------------------------------------------------------------------------

def kill_chrome():
    try:
        subprocess.run(['TASKKILL', '/IM', 'chrome.exe', '/F'], check=True, shell=True)
        print("Killed existing Chrome instances.")
    except subprocess.CalledProcessError:
        pass  # no Chrome was running


def launch_chrome():
    cmd = (
        f'"{CHROME_PATH}" '
        f'--remote-debugging-port={DEBUG_PORT} '
        f'--user-data-dir="{USER_DATA_DIR}" '
        f'--disable-blink-features=AutomationControlled '
        f'--start-maximized --new-window "{DASHBOARD_URL}"'
    )
    subprocess.Popen(cmd, shell=True)
    print("Launched Chrome with remote debugging.")
    time.sleep(4)


def connect_driver():
    options = Options()
    options.debugger_address = f"127.0.0.1:{DEBUG_PORT}"
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    # Hide the webdriver flag from JavaScript on every new page
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    time.sleep(3)
    return driver


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== jbcars_auto ===")
    if FILTER_TITLES:
        print(f"Filter active: only processing listings matching {FILTER_TITLES}")
    else:
        print("No filter set — processing ALL active listings.")

    kill_chrome()
    launch_chrome()
    driver = connect_driver()

    cars_added = 0
    total_to_process = 0
    cars_errors = []       # list of (title, error_message)
    cars_duplicates = []   # list of titles that appeared more than once
    scrape_stats = {'total': 0, 'reserved': 0, 'skipped': 0}

    try:
        # Step 1: Collect filtered listing items from dashboard (no scraping yet)
        items, scrape_stats = scraper.collect_listings(
            driver,
            filter_titles=FILTER_TITLES if FILTER_TITLES else None,
            exclude_titles=EXCLUDE_TITLES if EXCLUDE_TITLES else None,
        )

        if not items:
            print("No listings to process. Exiting.")
            return

        # Detect duplicate titles and remove them from the processing list
        from collections import Counter
        title_counts = Counter(title for title, _ in items)
        duplicate_titles = {t for t, c in title_counts.items() if c > 1}
        if duplicate_titles:
            for t in duplicate_titles:
                print(f"  SKIP (duplicate title): {t}")
                cars_duplicates.append(t)
            items = [(title, url) for title, url in items if title not in duplicate_titles]

        if not items:
            print("No listings to process after duplicate check. Exiting.")
            return

        total_to_process = len(items)
        print(f"\n--- Processing {total_to_process} car(s) one by one ---\n")

        for i, (title, edit_url) in enumerate(items, start=1):
            print(f"[{i}/{len(items)}] {title}")
            try:
                # Scrape this single car
                car = scraper.scrape_one_listing(driver, edit_url)
                if not car:
                    raise Exception("Scraping returned no data.")

                # Post new listing
                poster.post_listing(driver, car, max_photos=MAX_PHOTOS, desc_footer=DESC_FOOTER)
                time.sleep(2)

                # Delete old listing
                if DELETE_AFTER_POST:
                    poster.delete_old_listing(driver, car)
                else:
                    print(f"  Skipping delete (DELETE_AFTER_POST=False).")

                cars_added += 1
                print(f"  Done.\n")
            except Exception as e:
                print(f"  ERROR: {e}")
                cars_errors.append((title, str(e)))
                print("  Continuing with next car...\n")

            # Return to dashboard for next car
            driver.get('https://www.2dehands.be/my-account/sell/index.html')
            time.sleep(3)

    finally:
        driver.quit()

        # Build summary lines (printed to console and appended to report file)
        lines = []
        lines.append("=" * 50)
        lines.append(f"Run: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 50)
        lines.append(f"Filter titles               : {len(FILTER_TITLES)} ({', '.join(FILTER_TITLES) if FILTER_TITLES else 'all'})")
        if not FILTER_TITLES:
            lines.append(f"Total listings on dashboard : {scrape_stats['total']}")
        lines.append(f"Skipped (Gereserveerd)      : {scrape_stats['reserved']}")
        if EXCLUDE_TITLES and scrape_stats['skipped']:
            lines.append(f"Skipped (excluded)          : {scrape_stats['skipped']}")
        lines.append(f"Successfully added          : {cars_added}")
        if cars_duplicates:
            lines.append(f"Skipped (duplicate title)   : {len(cars_duplicates)}")
            for title in cars_duplicates:
                lines.append(f"  - {title}")
        if cars_errors:
            lines.append(f"Errors                      : {len(cars_errors)}")
            for title, err in cars_errors:
                lines.append(f"  - {title}")
                lines.append(f"    {err}")
        if cars_added < total_to_process:
            missing = total_to_process - cars_added
            lines.append("")
            lines.append(f"WARNING: {missing} car(s) were not re-posted successfully.")
            lines.append(f"         The dashboard may have fewer listings than before the run!")
        lines.append("=" * 50)

        print("\n" + "\n".join(lines))
        print("=== Finished ===")

        with open(REPORT_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n\n")


if __name__ == "__main__":
    main()
