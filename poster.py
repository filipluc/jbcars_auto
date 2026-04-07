"""
poster.py — Posts a new listing on 2dehands.be using scraped CarData,
            then deletes the original old listing.

Logic adapted from jbcars/AddCars/general.py (addCarFunction / deleteCarFunction).
"""

import os
import random
import time


def _w(base, lo=0.8, hi=1.3):
    """Return base * random factor to add natural timing variation."""
    return base * random.uniform(lo, hi)

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from models import CarData


DASHBOARD_URL = "https://www.2dehands.be/my-account/sell/index.html"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def listing_exists(driver, title):
    """Return True if a listing with the given title is visible on the dashboard."""
    try:
        driver.find_element(By.XPATH, f"//span[contains(text(),'{title}')]")
        return True
    except NoSuchElementException:
        return False


def post_listing(driver, car: CarData, max_photos=None, desc_footer=""):
    """Add a new listing on 2dehands.be using the scraped CarData.
    max_photos: if set, only upload that many photos (None = all).
    desc_footer: text appended to the description."""
    driver.get(DASHBOARD_URL)
    time.sleep(_w(3))

    # Navigate to "Plaats zoekertje" form
    plaats_link = driver.find_element(By.CSS_SELECTOR, "a[data-role='placeAd']")
    href = plaats_link.get_attribute('href')
    print(f"      Step: plaats zoekertje | href={href}")
    driver.get(href)
    try:
        WebDriverWait(driver, 15).until(EC.title_contains("tweedehands"))
    except TimeoutException:
        pass
    print(f"      Step: plaats zoekertje navigated | url={driver.current_url}")
    time.sleep(_w(7))

    # --- Title ---
    print(f"      Step: title | url={driver.current_url} | value={repr(car.var_title)}")
    elem_title = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "//input[@id='title_nl-BE' or @id='TextField-vulEenTitelIn']"))
    )
    print(f"      Step: title element found, id={elem_title.get_attribute('id')}")
    time.sleep(_w(1))
    driver.execute_script(
        "arguments[0].focus(); document.execCommand('insertText', false, arguments[1]);",
        elem_title, car.var_title
    )
    time.sleep(_w(1))

    # --- Category and brand (top-level dropdowns) ---
    print(f"      Step: category/brand")
    select_cat = Select(driver.find_element(By.ID, 'cat_sel_1'))
    select_cat.select_by_visible_text(car.var_categorie)
    time.sleep(_w(1))

    select_brand = Select(driver.find_element(By.ID, 'cat_sel_2'))
    select_brand.select_by_visible_text(car.var_brand if car.var_brand else "Bestelwagens en Lichte vracht")
    time.sleep(_w(1))

    submit_btn = driver.find_element(By.CLASS_NAME, 'CategorySelection-module-submitButton')
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", submit_btn)
    time.sleep(0.3)
    driver.execute_script("arguments[0].click();", submit_btn)
    print(f"      Step: category submit clicked")
    time.sleep(_w(6))

    # --- Photos (upload all at once) ---
    print(f"      Step: photos")
    if car.var_picspath and os.path.isdir(car.var_picspath):
        import shutil
        all_files = []
        for dirname, _, filenames in os.walk(car.var_picspath):
            for filename in sorted(filenames):
                if max_photos is not None and len(all_files) >= max_photos:
                    break
                all_files.append(os.path.join(dirname, filename))
        if all_files:
            time.sleep(_w(5))
            upload_inputs = driver.find_elements(By.XPATH, "//input[contains(@id, 'imageUploader')]")
            if not upload_inputs:
                print(f"      Warning: image uploader not found, skipping photos")
            else:
                upload_input = upload_inputs[-1]
                print(f"      Step: photos upload input found, sending {len(all_files)} file(s)")
                upload_input.send_keys('\n'.join(all_files))
            wait_secs = max(15, len(all_files) * 1.5)
            time.sleep(_w(wait_secs))
            print(f"      Photos sent: {len(all_files)}")
        # Move the photo folder to photos/old/ only after confirmed upload
        old_dir = os.path.join(os.path.dirname(car.var_picspath), "old")
        os.makedirs(old_dir, exist_ok=True)
        dest = os.path.join(old_dir, os.path.basename(car.var_picspath))
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.move(car.var_picspath, dest)
        print(f"      Moved photos to: {dest}")
        time.sleep(_w(2))

    # --- Description ---
    print(f"      Step: description")
    elem_desc = driver.find_element(By.CSS_SELECTOR, "div.RichTextEditor-module-editorInput[contenteditable='true']")
    footer_to_add = "" if (desc_footer and desc_footer.strip() in car.var_desc) else desc_footer
    elem_desc.send_keys(car.var_desc + footer_to_add)
    time.sleep(_w(1))

    # --- Website URL ---
    print(f"      Step: url")
    try:
        elem_url = driver.find_element(By.XPATH, "//input[contains(@id, 'url')]")
        elem_url.send_keys("www.jbcars.be")
        time.sleep(_w(0.3))
    except NoSuchElementException:
        pass

    # --- Model / brand sub-select ---
    print(f"      Step: model")
    elem_model = None
    try:
        elem_model = driver.find_element(By.XPATH, "//select[@name='singleSelectAttribute[model]']")
    except NoSuchElementException:
        try:
            elem_model = driver.find_element(By.XPATH, "//select[@name='singleSelectAttribute[brand]']")
        except NoSuchElementException:
            pass
    if elem_model and car.var_model:
        elem_model.click()
        elem_model.send_keys(car.var_model)
        elem_model.send_keys(Keys.TAB)
        time.sleep(_w(0.5))

    # --- Single-select attributes ---
    print(f"      Step: selects")
    _set_select(driver, "singleSelectAttribute[priceType]",     car.var_pricetype)
    _set_select(driver, "singleSelectAttribute[fuel]",          car.var_gas)
    _set_select(driver, "singleSelectAttribute[euronormBE]",    car.var_euro)
    _set_select(driver, "singleSelectAttribute[body]",          car.var_carroserie)
    _set_select(driver, "singleSelectAttribute[aantaldeurenBE]", car.var_doors)
    _set_select(driver, "singleSelectAttribute[transmission]",  car.var_transmissie)
    _set_select(driver, "singleSelectAttribute[color]",         car.var_carcolor)
    _set_select(driver, "singleSelectAttribute[interiorcolor]", car.var_interiorcolor)
    _set_select(driver, "singleSelectAttribute[upholstery]",    car.var_upholstery)
    _set_select(driver, "singleSelectAttribute[driveTrain]",    car.var_drivetrain)
    _set_select(driver, "singleSelectAttribute[warranty]",      car.var_warranty)

    # --- Numeric attributes ---
    print(f"      Step: numerics")
    _set_numeric(driver, "numericAttribute[constructionYear]",   car.var_year)
    _set_numeric(driver, "numericAttribute[co2emission]",        car.var_co2)
    _set_numeric(driver, "numericAttribute[mileage]",            car.var_km)
    _set_numeric(driver, "numericAttribute[engineDisplacement]", car.var_cilinder)
    _set_numeric(driver, "numericAttribute[numberOfSeatsBE]",    car.var_seats)
    _set_numeric(driver, "textAttribute[carPassUrl]",            car.var_carpass)
    _set_numeric(driver, "numericAttribute[emptyWeightCars]",    car.var_emptyweight)
    _set_numeric(driver, "numericAttribute[numberOfCylinders]",  car.var_numcylinders)
    _set_numeric(driver, "numericAttribute[towingWeightBrakes]", car.var_towingbraked)
    _set_numeric(driver, "numericAttribute[towingWeightNoBrakes]", car.var_towingunbraked)

    # --- Options (checkboxes) ---
    print(f"      Step: options")
    # We use the raw form values scraped directly from the edit page, so no mapping needed.
    if car.var_options:
        for opt_value in car.var_options.split(','):
            opt_value = opt_value.strip()
            if not opt_value:
                continue
            try:
                cb = driver.find_element(By.XPATH, f"//input[starts-with(@name, 'multiSelectAttribute') and @value='{opt_value}']")
                if not cb.is_selected():
                    cb.click()
                time.sleep(_w(0.1))
            except NoSuchElementException:
                print(f"    Warning: option not found on form: '{opt_value}'")

    # --- Price ---
    print(f"      Step: price")
    elem_price = driver.find_element(By.XPATH, "//input[contains(@name, 'price.value')]")
    elem_price.click()
    elem_price.send_keys(car.var_price)
    elem_price.send_keys(Keys.TAB)
    time.sleep(_w(0.5))

    # --- Disable bidding toggle ---
    print(f"      Step: bidding")
    try:
        elem_bid = driver.find_element(By.XPATH, "//div/label[contains(@id, 'syi-bidding-switch')]")
        elem_bid.click()
        time.sleep(_w(0.5))
    except NoSuchElementException:
        pass

    # --- Select free plan ---
    print(f"      Step: free plan")
    FREE_XPATHS = [
        "//span[normalize-space(text())='Gratis']",
        "//label[.//span[normalize-space(text())='Gratis']]",
        "//*[@id='feature-bundles']//*[normalize-space(text())='Gratis']",
    ]
    free_clicked = False
    for xp in FREE_XPATHS:
        try:
            driver.find_element(By.XPATH, xp).click()
            time.sleep(_w(1))
            free_clicked = True
            break
        except NoSuchElementException:
            continue
    if not free_clicked:
        raise RuntimeError("Could not select free plan — skipping to avoid paid submission")

    # --- Submit ---
    print(f"      Step: submit")
    form_url = driver.current_url
    elem_submit = driver.find_element(By.XPATH, "//button[contains(@data-testid, 'place-listing-submit-button')]")
    elem_submit.click()
    time.sleep(_w(20))
    post_url = driver.current_url
    print(f"      Step: submit done | url={post_url}")
    if post_url == form_url or '/plaats' in post_url:
        raise RuntimeError(
            f"Post submission failed — URL did not navigate away from form ({post_url}). "
            f"Skipping delete to preserve original listing."
        )
    print(f"    Posted new listing: '{car.var_title}'")


def delete_old_listing(driver, car: CarData):
    """
    Delete the OLD (original) listing on the dashboard.
    After post_listing() there are two listings with the same title;
    we delete the second one (index [1]) which is the older entry.
    """
    driver.get(DASHBOARD_URL)
    time.sleep(_w(3))

    try:
        # Safety check: both old and new listing must be visible (2 matches) before deleting.
        matches = driver.find_elements(By.XPATH, f"//span[contains(text(),'{car.var_title}')]")
        if len(matches) < 2:
            raise Exception(
                f"Cannot delete old listing: only {len(matches)} listing(s) found for "
                f"'{car.var_title}'. New listing may not be posted — skipping delete."
            )

        # Find the old listing by its known listing ID from the edit URL.
        listing_id = car.edit_url.rstrip('/').split('/')[-1]
        old_listings = driver.find_elements(By.XPATH, f"//a[contains(@href, '{listing_id}')]")
        if not old_listings:
            raise Exception(
                f"Cannot delete old listing: listing ID '{listing_id}' not found on dashboard. "
                f"It may have already been deleted."
            )

        old_listing = old_listings[0]
        driver.execute_script("arguments[0].click();", old_listing)
        time.sleep(_w(2))

        verwijder = driver.find_element(By.XPATH, "//span[text()='Verwijder']")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", verwijder)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", verwijder)
        time.sleep(_w(2))

        verkocht_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Verkocht via 2dehands')]")
        driver.execute_script("arguments[0].click();", verkocht_btn)
        time.sleep(_w(1))

        # Optional "Direct" confirmation
        try:
            direct_btn = driver.find_element(By.XPATH, "//button[text() = 'Direct']")
            driver.execute_script("arguments[0].click();", direct_btn)
            time.sleep(_w(1))
        except NoSuchElementException:
            pass

        time.sleep(_w(2))
        print(f"    Deleted old listing: '{car.var_title}'")

    except IndexError:
        print(f"    Warning: could not find a second (old) listing for '{car.var_title}' — skipping delete.")
    except NoSuchElementException as e:
        print(f"    Warning: delete flow element not found for '{car.var_title}': {e}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_select(driver, name, value):
    """Select an option in a <select> by its value attribute."""
    if not value:
        return
    try:
        el = driver.find_element(By.XPATH, f"//select[@name='{name}']")
        el.click()
        el.send_keys(value)
        el.send_keys(Keys.TAB)
        time.sleep(_w(0.5))
    except NoSuchElementException:
        pass


def _set_numeric(driver, id_fragment, value):
    """Set a numeric input field (matched by id substring)."""
    if not value:
        return
    try:
        el = driver.find_element(By.XPATH, f"//input[contains(@id, '{id_fragment}')]")
        el.click()
        el.send_keys(value)
        el.send_keys(Keys.TAB)
        time.sleep(_w(0.5))
    except NoSuchElementException:
        pass
