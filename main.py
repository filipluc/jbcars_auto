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
FILTER_TITLES = ["peugeot partner TEPEE 1.2 i/CAR PASS/euro 6b/Garantie"]

# Leave empty for no exclusions.
# Set to one or more title substrings to skip matching cars.
EXCLUDE_TITLES = []

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

    try:
        # Step 1: Scrape all listings (downloads photos too)
        cars = scraper.scrape_all_listings(driver, filter_titles=FILTER_TITLES if FILTER_TITLES else None, exclude_titles=EXCLUDE_TITLES if EXCLUDE_TITLES else None)

        if not cars:
            print("No listings to process. Exiting.")
            return

        print(f"\n--- Starting re-post loop for {len(cars)} car(s) ---\n")

        for i, car in enumerate(cars, start=1):
            print(f"[{i}/{len(cars)}] Processing: {car.var_title}")
            try:
                poster.post_listing(driver, car, max_photos=MAX_PHOTOS, desc_footer=DESC_FOOTER)
                time.sleep(2)
                if DELETE_AFTER_POST:
                    poster.delete_old_listing(driver, car)
                else:
                    print(f"  Skipping delete (DELETE_AFTER_POST=False).")
                print(f"  Done.\n")
            except Exception as e:
                print(f"  ERROR processing '{car.var_title}': {e}")
                print("  Continuing with next car...\n")

    finally:
        driver.quit()
        print("=== Finished ===")


if __name__ == "__main__":
    main()
