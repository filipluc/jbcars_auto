import os
import random
import re
import time
import requests

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from models import CarData


PHOTOS_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photos")


def _w(base, lo=0.8, hi=1.3):
    """Return base * random factor for natural timing variation."""
    return base * random.uniform(lo, hi)
DASHBOARD_URL = "https://www.2dehands.be/my-account/sell/index.html"


def collect_listings(driver, filter_titles=None, exclude_titles=None):
    """
    Navigate to the seller dashboard and return the filtered list of listing
    items to process, plus stats.  Does NOT scrape each listing yet.

    Returns: (items, stats)
      items: list of (title, edit_url) for listings that pass all filters
      stats: dict with 'total', 'reserved', 'skipped' counts
    """
    driver.get(DASHBOARD_URL)
    time.sleep(4)

    listing_items = _collect_listing_items(driver)
    print(f"Found {len(listing_items)} listing(s) on dashboard.")

    def _norm(t):
        return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]', ' ', t.lower())).strip()

    stats = {'total': len(listing_items), 'reserved': 0, 'skipped': 0}
    filtered = []

    for title, edit_url, is_reserved in listing_items:
        if is_reserved:
            print(f"  SKIP (Gereserveerd): {title}")
            stats['reserved'] += 1
            continue

        if filter_titles:
            if not any(_norm(f) in _norm(title) for f in filter_titles):
                print(f"  SKIP (not in filter): {title}")
                stats['skipped'] += 1
                continue

        if exclude_titles:
            if any(_norm(e) in _norm(title) for e in exclude_titles):
                print(f"  SKIP (excluded): {title}")
                stats['skipped'] += 1
                continue

        filtered.append((title, edit_url))

    print(f"\n{len(filtered)} car(s) to process.")
    return filtered, stats


def _collect_listing_items(driver):
    """
    Parse the dashboard page and return a list of tuples:
        (title_text, edit_url, is_reserved)

    Listing view URLs follow the pattern /v/auto-s/[brand]/m[id]-[slug].
    The edit URL is the view URL (without query params) + /bewerken.
    The title is read from a span inside the listing anchor element.
    """
    items = []

    # Wait for at least one listing link to appear
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/v/auto-s/')]"))
        )
    except TimeoutException:
        print("Warning: no listing links found on dashboard within timeout.")
        return items

    listing_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/v/auto-s/')]")

    seen_urls = set()
    for link in listing_links:
        href = link.get_attribute("href") or ""
        if not href or "/seller/" in href:
            continue

        base_url = href.split("?")[0].rstrip("/")
        if base_url in seen_urls:
            continue
        seen_urls.add(base_url)

        # Try to read title from a span inside the anchor
        try:
            title = link.find_element(By.XPATH, ".//span").text.strip()
        except NoSuchElementException:
            # Fallback: derive from URL slug
            slug = base_url.split("/")[-1]
            slug = re.sub(r'^m\d+-', '', slug)
            title = slug.replace("-", " ").strip()

        # Build seller view URL from listing ID (e.g. m2368587070)
        slug = base_url.split("/")[-1]
        m = re.match(r'^(m\d+)', slug)
        listing_id = m.group(1) if m else slug
        seller_view_url = f"https://www.2dehands.be/seller/view/{listing_id}"

        is_reserved = _is_reserved(driver, link)

        items.append((title, seller_view_url, is_reserved))

    return items


def _is_reserved(driver, link_element):
    """Return True if the listing card contains a 'Gereserveerd' badge."""
    try:
        card = link_element.find_element(By.XPATH, "./ancestor::*[contains(@class,'listing') or contains(@class,'advertisement') or contains(@class,'item')][1]")
        badges = card.find_elements(By.XPATH, ".//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'gereserveerd')]")
        return len(badges) > 0
    except NoSuchElementException:
        return False


def scrape_one_listing(driver, edit_url):
    """
    Navigate to a listing edit page, extract all field values, download photos,
    and return a CarData object.
    Returns None if the page cannot be scraped.
    """
    driver.get(edit_url)
    time.sleep(_w(3))

    # Click "Wijzig" to open the edit form
    try:
        wijzig = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(),'Wijzig')]"))
        )
        wijzig.click()
        time.sleep(_w(4))
    except TimeoutException:
        print(f"    Warning: Wijzig button not found at {edit_url}")
        return None

    car = CarData()
    car.edit_url = edit_url

    # --- Title ---
    car.var_title = _get_input_value(driver, By.ID, "title_nl-BE")

    # --- Description ---
    car.var_desc = _get_text(driver, By.CSS_SELECTOR, "div.RichTextEditor-module-editorInput[contenteditable='true']")

    # --- Price ---
    car.var_price = _get_input_value(driver, By.XPATH, "//input[contains(@name, 'price.value')]")

    # --- Single-select attributes ---
    car.var_model       = _get_select_value(driver, "singleSelectAttribute[model]") or \
                          _get_select_value(driver, "singleSelectAttribute[brand]")
    car.var_gas         = _get_select_value(driver, "singleSelectAttribute[fuel]")
    car.var_euro        = _get_select_value(driver, "singleSelectAttribute[euronormBE]")
    car.var_carroserie  = _get_select_value(driver, "singleSelectAttribute[body]")
    car.var_doors       = _get_select_value(driver, "singleSelectAttribute[aantaldeurenBE]")
    car.var_transmissie = _get_select_value(driver, "singleSelectAttribute[transmission]")
    car.var_carcolor    = _get_select_value(driver, "singleSelectAttribute[color]")
    car.var_interiorcolor = _get_select_value(driver, "singleSelectAttribute[interiorcolor]")
    car.var_pricetype   = _get_select_value(driver, "singleSelectAttribute[priceType]")
    car.var_upholstery  = _get_select_value(driver, "singleSelectAttribute[upholstery]")
    car.var_drivetrain  = _get_select_value(driver, "singleSelectAttribute[driveTrain]")
    car.var_warranty    = _get_select_value(driver, "singleSelectAttribute[warranty]")

    # --- Category and brand from breadcrumb (e.g. Auto's › Citroën) ---
    car.var_categorie = "Auto's"
    car.var_brand = ""
    try:
        breadcrumbs = driver.find_elements(
            By.XPATH, "//li[contains(@class,'hz-Breadcrumb') and not(@aria-current='page')]"
        )
        texts = [bc.text.strip() for bc in breadcrumbs if bc.text.strip()]
        # texts = ["Auto's", "Citroën"] → last entry is the brand
        if len(texts) >= 2:
            car.var_brand = texts[-1]
    except Exception:
        pass

    # --- Numeric attributes ---
    car.var_year     = _get_input_value(driver, By.XPATH, "//input[contains(@id, 'numericAttribute[constructionYear]')]")
    car.var_co2      = _get_input_value(driver, By.XPATH, "//input[contains(@id, 'numericAttribute[co2emission]')]")
    car.var_km       = _get_input_value(driver, By.XPATH, "//input[contains(@id, 'numericAttribute[mileage]')]")
    car.var_cilinder = _get_input_value(driver, By.XPATH, "//input[contains(@id, 'numericAttribute[engineDisplacement]')]")
    car.var_seats         = _get_input_value(driver, By.XPATH, "//input[contains(@id, 'numericAttribute[numberOfSeatsBE]')]")
    car.var_carpass       = _get_input_value(driver, By.XPATH, "//input[contains(@id, 'textAttribute[carPassUrl]')]")
    car.var_emptyweight   = _get_input_value(driver, By.XPATH, "//input[contains(@id, 'numericAttribute[emptyWeightCars]')]")
    car.var_numcylinders  = _get_input_value(driver, By.XPATH, "//input[contains(@id, 'numericAttribute[numberOfCylinders]')]")
    car.var_towingbraked   = _get_input_value(driver, By.XPATH, "//input[contains(@id, 'numericAttribute[towingWeightBrakes]')]")
    car.var_towingunbraked = _get_input_value(driver, By.XPATH, "//input[contains(@id, 'numericAttribute[towingWeightNoBrakes]')]")

    # --- Checked checkboxes (options, warranty, service history, etc.) ---
    all_checkboxes = driver.find_elements(By.XPATH, "//input[starts-with(@name, 'multiSelectAttribute')]")
    option_values = [cb.get_attribute("value") for cb in all_checkboxes if cb.is_selected() and cb.get_attribute("value")]
    car.var_options = ",".join(option_values)

    # --- Photos ---
    photo_urls = _collect_photo_urls(driver)
    if photo_urls:
        safe_title = _sanitize_dirname(car.var_title)
        local_dir = os.path.join(PHOTOS_BASE_DIR, safe_title)
        download_photos(photo_urls, local_dir)
        car.var_picspath = local_dir
    else:
        car.var_picspath = ""

    print(f"    Scraped: '{car.var_title}' | {len(photo_urls)} photo(s) | options: {car.var_options[:60]}...")
    return car


# ---------------------------------------------------------------------------
# Helpers — field extraction
# ---------------------------------------------------------------------------

def _get_input_value(driver, by, locator):
    try:
        el = driver.find_element(by, locator)
        return el.get_attribute("value") or ""
    except NoSuchElementException:
        return ""


def _get_text(driver, by, locator):
    try:
        el = driver.find_element(by, locator)
        return el.text or ""
    except NoSuchElementException:
        return ""


def _get_select_value(driver, name):
    """Get the currently selected option value of a <select> by its name attribute."""
    try:
        sel = Select(driver.find_element(By.XPATH, f"//select[@name='{name}']"))
        return sel.first_selected_option.get_attribute("value") or ""
    except NoSuchElementException:
        return ""


def _get_select_text(driver, element_id):
    """Get the visible text of the selected option in a <select> by its id."""
    try:
        sel = Select(driver.find_element(By.ID, element_id))
        return sel.first_selected_option.text.strip()
    except NoSuchElementException:
        return ""


def _collect_photo_urls(driver):
    """Return a deduplicated list of full-size image URLs from the edit page."""
    imgs = driver.find_elements(By.XPATH, "//img[contains(@src, 'images.2dehands') or contains(@src, '2dehands')]")
    seen = set()
    urls = []
    for img in imgs:
        src = img.get_attribute("src") or ""
        # Prefer the largest version: strip size suffixes and use the base URL
        src = re.sub(r'_\d+x\d+', '', src)  # remove e.g. _320x240
        if src and src not in seen:
            seen.add(src)
            urls.append(src)
    return urls


# ---------------------------------------------------------------------------
# Photo download
# ---------------------------------------------------------------------------

def download_photos(photo_urls, local_dir):
    """Download photos from CDN URLs into local_dir."""
    import shutil
    if os.path.exists(local_dir):
        shutil.rmtree(local_dir)
    os.makedirs(local_dir, exist_ok=True)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "nl-BE,nl;q=0.9,fr;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.2dehands.be/",
        "Connection": "keep-alive",
    }
    for i, url in enumerate(photo_urls, start=1):
        filename = f"img_{i:03d}.jpg"
        filepath = os.path.join(local_dir, filename)
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(resp.content)
            print(f"      Downloaded photo {i}: {filename}")
        except Exception as e:
            print(f"      Warning: could not download photo {i} ({url}): {e}")
        if i < len(photo_urls):
            time.sleep(_w(1.0, lo=0.5, hi=1.5))


def _sanitize_dirname(title):
    """Convert a car title to a safe directory name."""
    safe = re.sub(r'[\\/*?:"<>|]', '', title)
    safe = re.sub(r'\s+', '_', safe.strip())
    return safe[:80]  # cap at 80 chars
