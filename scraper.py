"""
Apartment listing scraper for inberlinwohnen.de

This module provides functionality to scrape apartment listings from the
inberlinwohnen.de website. It handles:
- Browser automation using Selenium
- Privacy banner acceptance
- Search filter configuration
- Listing extraction and parsing
- Database storage and duplicate detection
- Integration with notification system

The scraper is designed to work with Livewire/Alpine.js components and handles
dynamic content loading. It extracts apartment details including:
- Basic info (rooms, area, price, address)
- Additional costs (Nebenkosten)
- WBS permit requirements
- Apartment images
- Deep links to property details

Example:
    >>> from scraper import scrape_apartments, init_database
    >>> init_database()
    >>> new_count = scrape_apartments()
    >>> print(f"Found {new_count} new listings")
"""
import time
import random
import sqlite3
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import config
from notifications import send_notification


def init_driver():
    """
    Initialize and configure Chrome WebDriver for scraping.
    
    Sets up Chrome with options to:
    - Run headless (if configured)
    - Avoid detection as automation
    - Use a realistic user agent
    - Disable automation flags
    
    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance
        
    Raises:
        Exception: If ChromeDriver is not found or Chrome cannot be started
    """
    chrome_options = Options()
    if config.HEADLESS_BROWSER:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # User agent to appear more like a real browser
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def accept_privacy_settings(driver, wait_time=10):
    """
    Accept privacy/cookie settings by clicking the 'Alle akzeptieren' button.
    
    This function handles the cookie consent banner that appears on the website.
    It tries multiple selector strategies to find the accept button, as the site
    uses Livewire components that may render differently.
    
    Args:
        driver (webdriver.Chrome): The Selenium WebDriver instance
        wait_time (int, optional): Maximum time to wait for the button to appear.
            Defaults to 10 seconds.
    
    Returns:
        bool: True if privacy settings were accepted (or already accepted),
            False if the button could not be found or clicked.
    
    Note:
        The function gracefully handles cases where the banner is already
        accepted or doesn't appear, returning False without raising an error.
    """
    try:
        # Wait for privacy banner to appear and Livewire to be ready
        wait = WebDriverWait(driver, wait_time)
        
        # Wait a bit for Livewire to initialize
        time.sleep(2)
        
        # Try multiple strategies to find the accept button
        # The button has id="accept-all-cookies" and contains a span with "Alle akzeptieren"
        # It's a Livewire component with wire:click="onCookieAll"
        accept_selectors = [
            (By.ID, "accept-all-cookies"),
            (By.XPATH, "//button[@id='accept-all-cookies']"),
            (By.XPATH, "//button[@wire:click='onCookieAll']"),
            (By.XPATH, "//button[.//span[contains(text(), 'Alle akzeptieren')]]"),
            (By.XPATH, "//button[contains(text(), 'Alle akzeptieren')]"),
        ]
        
        accept_button = None
        for by, selector in accept_selectors:
            try:
                accept_button = wait.until(EC.element_to_be_clickable((by, selector)))
                break
            except:
                continue
        
        if accept_button:
            # Try regular click first
            try:
                accept_button.click()
            except:
                # If regular click fails, use JavaScript click (more reliable for Livewire)
                driver.execute_script("arguments[0].click();", accept_button)
            
            print("✓ Privacy settings accepted")
            time.sleep(3 + random.uniform(0, 1))  # Wait for banner to disappear and Livewire to process
            return True
        else:
            print("⚠ Privacy banner not found (might already be accepted)")
            return False
    except TimeoutException:
        print("⚠ Privacy banner not found (might already be accepted)")
        return False
    except Exception as e:
        print(f"⚠ Error accepting privacy settings: {e}")
        return False


def open_search_filters(driver, wait_time=10):
    """
    Open the search filter modal by clicking the 'Suchfilter' button.
    
    This function locates and clicks the button that opens the search filter
    modal/dialog. The button is identified by its aria-label attribute or
    by containing a search icon.
    
    Args:
        driver (webdriver.Chrome): The Selenium WebDriver instance
        wait_time (int, optional): Maximum time to wait for the button to appear.
            Defaults to 10 seconds.
    
    Returns:
        bool: True if the filter modal was successfully opened,
            False if the button could not be found or clicked.
    
    Note:
        After clicking, the function waits a random amount of time (2-3 seconds)
        to allow the modal to fully open and render.
    """
    try:
        wait = WebDriverWait(driver, wait_time)
        
        # Find the "Suchfilter" button - it has aria-label="Suchfilter" and opens a modal
        filter_selectors = [
            (By.XPATH, "//button[@aria-label='Suchfilter']"),
            (By.XPATH, "//button[contains(@class, 'button--icon') and .//i[contains(@class, 'fa-search')]]"),
            (By.XPATH, "//button[.//span[contains(text(), 'Suchfilter')]]"),
        ]
        
        filter_button = None
        for by, selector in filter_selectors:
            try:
                filter_button = wait.until(EC.element_to_be_clickable((by, selector)))
                break
            except:
                continue
        
        if filter_button:
            filter_button.click()
            print("✓ Search filters opened")
            time.sleep(2 + random.uniform(0, 1))  # Wait for filter panel/modal to open
            return True
        else:
            print("✗ Could not find 'Suchfilter' button")
            return False
    except TimeoutException:
        print("✗ Could not find 'Suchfilter' button")
        return False
    except Exception as e:
        print(f"✗ Error opening search filters: {e}")
        return False


def set_search_criteria(driver, wait_time=15):
    """
    Set search criteria in the filter form and submit the search.
    
    This function fills in the search form with criteria from config.py:
    - Maximum cold rent (Kaltmiete)
    - Minimum and maximum number of rooms (Zimmer)
    - Maximum living area (Wohnfläche)
    
    After filling the form, it submits the search and waits for results to load.
    The function handles Livewire components which require special interaction
    methods (JavaScript clicks instead of regular clicks).
    
    Args:
        driver (webdriver.Chrome): The Selenium WebDriver instance
        wait_time (int, optional): Maximum time to wait for form elements.
            Defaults to 15 seconds.
    
    Returns:
        bool: True if search criteria were set and submitted successfully,
            False if any step failed.
    
    Note:
        - Uses JavaScript clicks for better compatibility with Livewire
        - Scrolls elements into view before interacting
        - Includes random delays to appear more human-like
        - Saves page source to debug file if submission fails
    """
    try:
        wait = WebDriverWait(driver, wait_time)
        
        # Wait for modal to be visible - look for "Meine Suchkriterien" heading
        print("Waiting for filter modal to fully load...")
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Meine Suchkriterien')]")))
            print("✓ Modal is visible")
        except:
            print("⚠ Modal heading not found, continuing anyway...")
        
        time.sleep(2)  # Additional wait for form fields to be ready
        
        # Set Kaltmiete maximum - use the actual field name from the website
        try:
            kaltmiete_max = wait.until(
                EC.presence_of_element_located((By.NAME, "searchParams.rentNet.max"))
            )
            # Scroll into view and wait for it to be visible
            driver.execute_script("arguments[0].scrollIntoView(true);", kaltmiete_max)
            time.sleep(0.5)
            kaltmiete_max.clear()
            kaltmiete_max.send_keys(str(config.SEARCH_CRITERIA["kaltmiete_max"]))
            print(f"✓ Set Kaltmiete max to {config.SEARCH_CRITERIA['kaltmiete_max']} €")
        except Exception as e:
            print(f"⚠ Could not set Kaltmiete max: {e}")
        
        # Set Zimmer minimum
        try:
            zimmer_min = wait.until(
                EC.presence_of_element_located((By.NAME, "searchParams.rooms.min"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", zimmer_min)
            time.sleep(0.5)
            zimmer_min.clear()
            zimmer_min.send_keys(str(config.SEARCH_CRITERIA["zimmer_min"]))
            print(f"✓ Set Zimmer min to {config.SEARCH_CRITERIA['zimmer_min']}")
        except Exception as e:
            print(f"⚠ Could not set Zimmer min: {e}")
        
        # Set Zimmer maximum
        try:
            zimmer_max = wait.until(
                EC.presence_of_element_located((By.NAME, "searchParams.rooms.max"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", zimmer_max)
            time.sleep(0.5)
            zimmer_max.clear()
            zimmer_max.send_keys(str(config.SEARCH_CRITERIA["zimmer_max"]))
            print(f"✓ Set Zimmer max to {config.SEARCH_CRITERIA['zimmer_max']}")
        except Exception as e:
            print(f"⚠ Could not set Zimmer max: {e}")
        
        # Set Wohnfläche maximum
        try:
            wohnflaeche_max = wait.until(
                EC.presence_of_element_located((By.NAME, "searchParams.area.max"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", wohnflaeche_max)
            time.sleep(0.5)
            wohnflaeche_max.clear()
            wohnflaeche_max.send_keys(str(config.SEARCH_CRITERIA["wohnflaeche_max"]))
            print(f"✓ Set Wohnfläche max to {config.SEARCH_CRITERIA['wohnflaeche_max']} m²")
        except Exception as e:
            print(f"⚠ Could not set Wohnfläche max: {e}")
        
        # Submit the search form
        # The form uses Livewire (wire:submit.prevent="submit") and the button has @click="showModal = false"
        print("Looking for submit button...")
        try:
            # Wait for the submit button to be visible and clickable
            # The button is inside the form and has type="submit" with text "Wohnung suchen"
            # Try multiple selectors
            search_button = None
            button_selectors = [
                "//button[@type='submit' and contains(., 'Wohnung suchen')]",
                "//form//button[@type='submit']",
                "//button[contains(., 'Wohnung suchen')]",
            ]
            
            for selector in button_selectors:
                try:
                    search_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    print(f"✓ Found submit button using: {selector}")
                    break
                except:
                    continue
            
            if not search_button:
                raise Exception("Could not find submit button with any selector")
            
            # Scroll button into view
            driver.execute_script("arguments[0].scrollIntoView(true);", search_button)
            time.sleep(0.5)
            
            print("✓ Found submit button, clicking...")
            
            # Use JavaScript click for Livewire/Alpine.js components
            driver.execute_script("arguments[0].click();", search_button)
            
            print("✓ Search submitted")
            time.sleep(3)  # Wait for modal to close
            
            # Wait for results to load (modal should close and results should appear)
            try:
                wait.until(EC.invisibility_of_element_located((By.XPATH, "//span[contains(text(), 'Meine Suchkriterien')]")))
                print("✓ Modal closed, waiting for results...")
            except:
                print("⚠ Modal might still be visible, continuing...")
            
            time.sleep(5 + random.uniform(0, 2))  # Additional wait for Livewire to process and results to render
            return True
        except Exception as e:
            print(f"⚠ Could not find/submit search button: {e}")
            # Try alternative selectors
            try:
                print("Trying alternative selectors...")
                # Try finding by text content
                search_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Wohnung suchen')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", search_button)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", search_button)
                print("✓ Search submitted (alternative method)")
                time.sleep(5)
                return True
            except Exception as e2:
                print(f"⚠ Alternative submit method also failed: {e2}")
                # Debug: save page source
                with open("debug_submit_failed.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("⚠ Saved page source to debug_submit_failed.html")
                return False
        
    except Exception as e:
        print(f"✗ Error setting search criteria: {e}")
        import traceback
        traceback.print_exc()
        return False


def extract_listings(driver):
    """
    Extract apartment listing data from the current search results page.
    
    This function finds all apartment listings on the page and extracts:
    - URL/deeplink to the property details page
    - Title and address
    - Number of rooms (Zimmeranzahl)
    - Living area (Wohnfläche) in m²
    - Cold rent (Kaltmiete) in EUR
    - Additional costs (Nebenkosten) in EUR
    - WBS permit requirement status
    - Apartment image URL
    
    The extraction uses multiple strategies:
    1. Parses text from listing buttons
    2. Extracts JSON data from wire:snapshot attributes (most reliable)
    3. Falls back to DOM element inspection if needed
    
    Args:
        driver (webdriver.Chrome): The Selenium WebDriver instance
    
    Returns:
        list[dict]: List of dictionaries, each containing:
            - url (str): Deep link to property details
            - title (str): Apartment title/address
            - address (str): Full address
            - price (str): Cold rent in EUR
            - rooms (str): Number of rooms
            - area (str): Living area in m²
            - extra_costs (str): Additional costs in EUR
            - wbs (str): WBS permit requirement status
            - image_url (str): URL to apartment image
            - raw_text (str): Raw text from listing button
            - extracted_at (str): ISO timestamp of extraction
    
    Note:
        - Gracefully handles end of listings (when no more are available)
        - Skips listings without identifying information
        - Saves page source to debug file if extraction fails completely
        - Returns empty list if no listings found
    """
    listings = []
    
    try:
        print("\n=== EXTRACTING LISTINGS ===\n")
        
        # Wait for listings to load
        wait = WebDriverWait(driver, 20)
        
        # First, wait for the results counter or any indication that results have loaded
        print("Waiting for results to appear...")
        try:
            # Wait for results counter text like "Wir haben X Wohnungen gefunden"
            wait.until(EC.presence_of_element_located((By.XPATH, 
                "//span[contains(text(), 'Wohnungen')]")))
            print("✓ Results counter found")
            time.sleep(2)  # Give Livewire a moment to render listings
        except Exception as e:
            print(f"⚠ Results counter not found: {e}")
            time.sleep(3)  # Wait anyway
        
        # Wait for listing buttons to appear
        print("Waiting for listing buttons...")
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 
                "button.list__item__title")))
            print("✓ Listing buttons found")
            time.sleep(1)  # Small additional wait for full rendering
        except Exception as e:
            print(f"⚠ Listing buttons not found immediately: {e}")
            print("Trying alternative selectors...")
            time.sleep(3)
        
        # Try multiple selectors to find listing buttons
        listing_buttons = []
        selectors_to_try = [
            (By.CSS_SELECTOR, "button.list__item__title"),
            (By.XPATH, "//button[contains(@class, 'list__item__title')]"),
            (By.XPATH, "//button[contains(@class, 'list__item')]"),
            (By.XPATH, "//div[starts-with(@id, 'apartment-')]//button"),
        ]
        
        for by, selector in selectors_to_try:
            try:
                buttons = driver.find_elements(by, selector)
                if buttons:
                    listing_buttons = buttons
                    print(f"✓ Found {len(buttons)} listing buttons using: {selector}")
                    break
            except Exception as e:
                print(f"  Selector failed: {selector} - {e}")
                continue
        
        if not listing_buttons:
            print("⚠ No listing buttons found with any selector")
            # Save page source for debugging
            with open("debug_extraction_failed.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("⚠ Saved page source to debug_extraction_failed.html for inspection")
            
            # Try to find what's actually on the page
            print("\nDebugging: Checking what elements are present...")
            try:
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                print(f"  Total buttons on page: {len(all_buttons)}")
                for i, btn in enumerate(all_buttons[:10]):
                    classes = btn.get_attribute("class") or ""
                    text = btn.text[:50] or ""
                    if "list" in classes.lower() or "item" in classes.lower():
                        print(f"  Button {i+1}: class='{classes[:50]}', text='{text}'")
            except:
                pass
            
            return []
        
        print(f"Found {len(listing_buttons)} listing buttons, processing...")
        
        for idx, button in enumerate(listing_buttons):
            try:
                listing_data = {
                    "url": None,
                    "title": "",
                    "address": "",
                    "price": "",
                    "rooms": "",
                    "area": "",
                    "extra_costs": "",
                    "wbs": "",
                    "image_url": "",
                    "raw_text": "",
                    "extracted_at": datetime.now().isoformat()
                }
                
                # Extract text content from the button
                text = button.text.strip()
                listing_data["raw_text"] = text
                
                # Parse the text format: "X,0 Zimmer, Y,YY m², Z.ZZZ,ZZ € | Address"
                import re
                
                # Extract rooms (format: "X,0 Zimmer")
                rooms_match = re.search(r'(\d+(?:,\d+)?)\s*Zimmer', text, re.IGNORECASE)
                if rooms_match:
                    listing_data["rooms"] = rooms_match.group(1)
                
                # Extract area (format: "Y,YY m²")
                area_match = re.search(r'(\d+(?:,\d+)?)\s*m²', text)
                if area_match:
                    listing_data["area"] = area_match.group(1)
                
                # Extract price (format: "Z.ZZZ,ZZ €" or "Z.ZZZ,ZZ €")
                price_match = re.search(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€', text)
                if price_match:
                    listing_data["price"] = price_match.group(1)
                
                # Extract address (format: "Street Number, ZIP City" after the | separator)
                address_match = re.search(r'\|\s*([^|]+)', text)
                if address_match:
                    listing_data["address"] = address_match.group(1).strip()
                
                # Try to find the parent div with id="apartment-XXXX"
                # If we can't find it, it means we've reached the end of available listings
                try:
                    parent_div = button.find_element(By.XPATH, "./ancestor::div[starts-with(@id, 'apartment-')]")
                except:
                    # No more listings available - this is expected after the first page
                    print(f"  ✓ Reached end of listings at {idx+1} listings")
                    break
                
                # Extract data from wire:snapshot (most reliable source)
                try:
                    snapshot_attr = parent_div.get_attribute("wire:snapshot")
                    if snapshot_attr:
                        # Extract deeplink
                        deeplink_match = re.search(r'"deeplink"\s*:\s*"([^"]+)"', snapshot_attr)
                        if deeplink_match:
                            listing_data["url"] = deeplink_match.group(1).replace('\\/', '/')
                        
                        # Extract extraCosts (Nebenkosten)
                        extra_costs_match = re.search(r'"extraCosts"\s*:\s*"([^"]+)"', snapshot_attr)
                        if extra_costs_match:
                            extra_costs_value = extra_costs_match.group(1).replace('\\/', '/')
                            # Format: "163,10" -> "163,10 €"
                            listing_data["extra_costs"] = f"{extra_costs_value} €"
                        
                        # Extract imagePath or imageUrl from main snapshot
                        # Try imagePath first (in item data)
                        image_match = re.search(r'"imagePath"\s*:\s*"([^"]+)"', snapshot_attr)
                        if not image_match:
                            # Try imageUrl as fallback
                            image_match = re.search(r'"imageUrl"\s*:\s*"([^"]+)"', snapshot_attr)
                        
                        if image_match:
                            image_path = image_match.group(1).replace('\\/', '/')
                            # Convert relative path to full URL
                            if image_path.startswith('images/'):
                                listing_data["image_url"] = f"https://www.inberlinwohnen.de/img/{image_path}"
                            elif image_path.startswith('/img/'):
                                listing_data["image_url"] = f"https://www.inberlinwohnen.de{image_path}"
                            elif not image_path.startswith('http'):
                                listing_data["image_url"] = f"https://www.inberlinwohnen.de/img/{image_path}"
                            else:
                                listing_data["image_url"] = image_path
                        
                        # If image not found in main snapshot, try child image component
                        if not listing_data["image_url"]:
                            try:
                                # Look for image component by class or wire:id pattern
                                image_divs = parent_div.find_elements(By.XPATH, 
                                    ".//div[contains(@wire:id, 'image') or contains(@class, 'image')]")
                                for img_div in image_divs:
                                    img_snapshot = img_div.get_attribute("wire:snapshot")
                                    if img_snapshot:
                                        img_match = re.search(r'"imageUrl"\s*:\s*"([^"]+)"', img_snapshot)
                                        if img_match:
                                            image_path = img_match.group(1).replace('\\/', '/')
                                            if image_path.startswith('images/'):
                                                listing_data["image_url"] = f"https://www.inberlinwohnen.de/img/{image_path}"
                                            elif not image_path.startswith('http'):
                                                listing_data["image_url"] = f"https://www.inberlinwohnen.de/img/{image_path}"
                                            else:
                                                listing_data["image_url"] = image_path
                                            break
                            except Exception as e:
                                print(f"    ⚠ Error finding image component: {e}")
                                pass
                        
                        # Extract WBS from details array in snapshot
                        # Look for {"label":"WBS",...,"value":"..."} pattern in the details array
                        # The pattern is: "label":"WBS" followed by "value":"..." somewhere after
                        wbs_match = re.search(r'"label"\s*:\s*"WBS"[^}]*?"value"\s*:\s*"([^"]+)"', snapshot_attr)
                        if not wbs_match:
                            # Try alternative pattern - WBS value might be in a different format
                            wbs_match = re.search(r'"WBS"[^}]*?"value"\s*:\s*"([^"]+)"', snapshot_attr)
                        if wbs_match:
                            wbs_value = wbs_match.group(1)
                            # Decode common escape sequences
                            wbs_value = (wbs_value.replace('\\u00e4', 'ä')
                                        .replace('\\u00f6', 'ö')
                                        .replace('\\u00fc', 'ü')
                                        .replace('\\u00c4', 'Ä')
                                        .replace('\\u00d6', 'Ö')
                                        .replace('\\u00dc', 'Ü')
                                        .replace('\\u00df', 'ß'))
                            listing_data["wbs"] = wbs_value
                except Exception as e:
                    print(f"    ⚠ Error extracting from snapshot: {e}")
                    pass
                
                # If snapshot didn't work, try finding elements directly
                if not listing_data["url"]:
                    try:
                        deeplink_links = parent_div.find_elements(By.XPATH, 
                            ".//a[contains(@href, 'degewo') or contains(@href, 'gesobau') or contains(@href, 'gewobag') or contains(@href, 'howoge') or contains(@href, 'stadtundland') or contains(@href, 'wbm')]")
                        if deeplink_links:
                            listing_data["url"] = deeplink_links[0].get_attribute("href")
                    except:
                        pass
                
                # Extract additional details from the details section
                # These are in <dt> and <dd> elements
                try:
                    # Find all detail rows
                    detail_rows = parent_div.find_elements(By.XPATH, ".//dl[@class='grid grid-cols-2']//dt")
                    for dt in detail_rows:
                        label = dt.text.strip()
                        try:
                            dd = dt.find_element(By.XPATH, "./following-sibling::dd[1]")
                            value = dd.text.strip()
                            
                            if "Nebenkosten" in label:
                                listing_data["extra_costs"] = value
                            elif "WBS" in label:
                                listing_data["wbs"] = value
                        except:
                            continue
                except:
                    pass
                
                # Extract title from aria-label if available
                aria_label = button.get_attribute("aria-label")
                if aria_label:
                    # aria-label format: "Wohnungsangebot - 3,0 Zimmer, 86,76 m², 837,93 € Kaltmiete | Address"
                    # Try to extract a meaningful title
                    if "Wohnungsangebot" in aria_label:
                        # Use the address as title if we don't have a better one
                        if listing_data["address"]:
                            listing_data["title"] = listing_data["address"]
                        else:
                            listing_data["title"] = text.split('|')[0].strip()[:200] if '|' in text else text[:200]
                    else:
                        listing_data["title"] = aria_label[:200]
                else:
                    # Use address or first part of text as title
                    if listing_data["address"]:
                        listing_data["title"] = listing_data["address"]
                    elif '|' in text:
                        listing_data["title"] = text.split('|')[0].strip()[:200]
                    else:
                        listing_data["title"] = text[:200]
                
                # Only add if we have some identifying information
                if listing_data["url"] or (listing_data["address"] and len(listing_data["address"]) > 5):
                    listings.append(listing_data)
                    debug_info = []
                    if listing_data.get('extra_costs'):
                        debug_info.append(f"Nebenkosten: {listing_data['extra_costs']}")
                    if listing_data.get('wbs'):
                        debug_info.append(f"WBS: {listing_data['wbs']}")
                    if listing_data.get('image_url'):
                        debug_info.append(f"Image: {listing_data['image_url'][:50]}...")
                    else:
                        debug_info.append("Image: ✗")
                    debug_str = f" ({', '.join(debug_info)})" if debug_info else ""
                    print(f"  ✓ Listing {idx+1}: {listing_data.get('rooms', '?')} Zimmer, {listing_data.get('area', '?')} m², {listing_data.get('price', '?')} € - {listing_data.get('address', 'No address')[:50]}{debug_str}")
                else:
                    print(f"  ⚠ Skipping listing {idx+1} - no identifying information")
                    
            except Exception as e:
                print(f"  ⚠ Error extracting listing {idx+1}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n✓ Successfully extracted {len(listings)} valid listings")
        return listings
        
    except Exception as e:
        print(f"✗ Error extracting listings: {e}")
        import traceback
        traceback.print_exc()
        return []


def init_database():
    """
    Initialize SQLite database and create listings table if it doesn't exist.
    
    Creates a database table to store apartment listings with the following columns:
    - id: Primary key (auto-increment)
    - url: Unique URL/deeplink to property
    - title: Apartment title
    - address: Full address
    - price: Cold rent
    - rooms: Number of rooms
    - area: Living area in m²
    - extra_costs: Additional costs
    - wbs: WBS permit requirement
    - image_url: URL to apartment image
    - raw_text: Raw extracted text
    - first_seen: ISO timestamp of first discovery
    - last_seen: ISO timestamp of last seen
    - notified: Boolean flag for notification status
    
    The function also handles schema migrations by adding new columns
    (extra_costs, wbs, image_url) if they don't exist, allowing the database
    to be upgraded without losing existing data.
    
    Database path is configured in config.DATABASE_PATH (default: "apartments.db").
    
    Note:
        - Safe to call multiple times (uses CREATE TABLE IF NOT EXISTS)
        - Handles existing databases gracefully
        - Prints confirmation message on success
    """
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            address TEXT,
            price TEXT,
            rooms TEXT,
            area TEXT,
            extra_costs TEXT,
            wbs TEXT,
            image_url TEXT,
            raw_text TEXT,
            first_seen TEXT,
            last_seen TEXT,
            notified INTEGER DEFAULT 0
        )
    """)
    
    # Add new columns if they don't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE listings ADD COLUMN extra_costs TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE listings ADD COLUMN wbs TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE listings ADD COLUMN image_url TEXT")
    except:
        pass
    
    conn.commit()
    conn.close()
    print("✓ Database initialized")


def get_seen_listing_urls():
    """
    Retrieve all listing URLs that have been seen before from the database.
    
    This function queries the database to get a set of all URLs that have
    been previously stored. This is used to detect new listings and avoid
    duplicates.
    
    Returns:
        set[str]: Set of URLs (strings) that have been seen before.
            Empty set if database is empty or no URLs exist.
    
    Note:
        - Only returns listings with non-null URLs
        - Used internally by save_listings() to detect new listings
    """
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT url FROM listings WHERE url IS NOT NULL")
    seen_urls = {row[0] for row in cursor.fetchall()}
    conn.close()
    return seen_urls


def save_listings(listings):
    """
    Save listings to database and identify which ones are new.
    
    This function compares incoming listings against the database to determine
    which listings are new (haven't been seen before). New listings are inserted
    into the database, while existing listings have their last_seen timestamp
    updated.
    
    Args:
        listings (list[dict]): List of listing dictionaries as returned by
            extract_listings(). Each dict should contain at least:
            - url (str): Unique identifier (or raw_text if URL unavailable)
            - Other fields as defined in extract_listings() return value
    
    Returns:
        list[dict]: List of new listings (those not previously in database).
            Empty list if all listings were already seen.
    
    Note:
        - Uses URL as primary identifier for duplicate detection
        - Falls back to raw_text[:100] if URL is not available
        - Updates last_seen timestamp for existing listings
        - Sets first_seen and last_seen to current timestamp for new listings
    """
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    
    seen_urls = get_seen_listing_urls()
    new_listings = []
    now = datetime.now().isoformat()
    
    for listing in listings:
        url = listing.get("url", "")
        if not url:
            # Use raw_text as identifier if no URL
            url = listing.get("raw_text", "")[:100]
        
        if url not in seen_urls:
            # New listing
            cursor.execute("""
                INSERT INTO listings (url, title, address, price, rooms, area, extra_costs, wbs, image_url, raw_text, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                listing.get("url"),
                listing.get("title", ""),
                listing.get("address", ""),
                listing.get("price", ""),
                listing.get("rooms", ""),
                listing.get("area", ""),
                listing.get("extra_costs", ""),
                listing.get("wbs", ""),
                listing.get("image_url", ""),
                listing.get("raw_text", ""),
                now,
                now
            ))
            new_listings.append(listing)
        else:
            # Update last_seen
            cursor.execute("UPDATE listings SET last_seen = ? WHERE url = ?", (now, url))
    
    conn.commit()
    conn.close()
    
    return new_listings


def scrape_apartments():
    """
    Main scraping function that orchestrates the entire scraping process.
    
    This is the primary entry point for scraping apartment listings. It:
    1. Initializes the browser and navigates to the website
    2. Accepts privacy settings
    3. Opens search filters
    4. Sets search criteria from config.py
    5. Extracts listings from results
    6. Saves listings to database
    7. Sends notifications for new listings
    8. Returns count of new listings found
    
    The function includes random delays between steps to appear more human-like
    and avoid detection. It handles errors gracefully and always cleans up the
    browser driver, even if an error occurs.
    
    Returns:
        int: Number of new listings found (0 if none found or error occurred)
    
    Side Effects:
        - Creates/updates database with listings
        - Sends email/system notifications for new listings
        - Prints progress messages to console
    
    Example:
        >>> new_count = scrape_apartments()
        >>> if new_count > 0:
        ...     print(f"Found {new_count} new apartments!")
    
    Note:
        - Always closes browser driver in finally block
        - Returns 0 on any error (doesn't raise exceptions)
        - Includes random delays for natural behavior
    """
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting apartment scrape...")
    
    driver = None
    try:
        driver = init_driver()
        driver.get(config.BASE_URL)
        
        # Wait for page to load (with small randomness)
        time.sleep(3 + random.uniform(0, 2))
        
        # Accept privacy settings
        accept_privacy_settings(driver)
        
        # Open search filters
        if not open_search_filters(driver):
            print("✗ Failed to open search filters")
            return 0
        
        # Set search criteria
        if not set_search_criteria(driver):
            print("✗ Failed to set search criteria")
            return 0
        
        # Wait a bit more for results to fully load (with small randomness)
        print("\nWaiting for search results to fully load...")
        time.sleep(3 + random.uniform(0, 2))
        
        # Extract listings
        print("\nCalling extract_listings...")
        listings = extract_listings(driver)
        print(f"extract_listings returned {len(listings) if listings else 0} listings")
        
        new_listings_count = 0
        if listings:
            # Save to database and get new ones
            new_listings = save_listings(listings)
            
            new_listings_count = len(new_listings) if new_listings else 0
            
            if new_listings:
                print(f"🎉 Found {new_listings_count} new listing(s)!")
                
                # Send a summary system notification
                if new_listings_count == 1:
                    listing = new_listings[0]
                    summary = f"{listing.get('address', 'New apartment')} - {listing.get('rooms', '?')} Zimmer, {listing.get('area', '?')} m², {listing.get('price', '?')} €"
                else:
                    summary = f"Found {new_listings_count} new apartments!"
                
                from notifications import send_system_notification
                send_system_notification(
                    title="🏠 New Apartment Found!",
                    message=summary,
                    sound=True
                )
                
                for listing in new_listings:
                    url = listing.get("url", "No URL")
                    title = listing.get("title", listing.get("address", "New listing"))[:100]
                    address = listing.get("address", "N/A")
                    rooms = listing.get("rooms", "N/A")
                    area = listing.get("area", "N/A")
                    price = listing.get("price", "N/A")
                    extra_costs = listing.get("extra_costs", "N/A")
                    wbs = listing.get("wbs", "N/A")
                    image_url = listing.get("image_url", "").strip()
                    
                    # Validate image URL
                    if image_url and not (image_url.startswith("http://") or image_url.startswith("https://")):
                        print(f"  ⚠ Invalid image URL format: {image_url[:50]}")
                        image_url = ""
                    
                    # Create plain text message
                    message = f"""New apartment found!

{title}
{address}

Zimmeranzahl: {rooms}
Wohnfläche: {area} m²
Kaltmiete: {price} €
Nebenkosten: {extra_costs}
WBS: {wbs}

{url}"""
                    
                    # Create HTML message
                    html_message = f"""<html>
<head></head>
<body>
    <h2>New apartment found!</h2>
    <h3>{title}</h3>
    <p><strong>Adresse:</strong> {address}</p>
    
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 5px 15px 5px 0;"><strong>Zimmeranzahl:</strong></td>
            <td style="padding: 5px;">{rooms}</td>
        </tr>
        <tr>
            <td style="padding: 5px 15px 5px 0;"><strong>Wohnfläche:</strong></td>
            <td style="padding: 5px;">{area} m²</td>
        </tr>
        <tr>
            <td style="padding: 5px 15px 5px 0;"><strong>Kaltmiete:</strong></td>
            <td style="padding: 5px;">{price} €</td>
        </tr>
        <tr>
            <td style="padding: 5px 15px 5px 0;"><strong>Nebenkosten:</strong></td>
            <td style="padding: 5px;">{extra_costs}</td>
        </tr>
        <tr>
            <td style="padding: 5px 15px 5px 0;"><strong>WBS:</strong></td>
            <td style="padding: 5px;">{wbs}</td>
        </tr>
    </table>
    
    {f'<p><img src="{image_url}" alt="Apartment image" style="max-width: 600px; border: 1px solid #ddd; border-radius: 4px;"></p>' if (image_url and len(image_url) > 10 and image_url.startswith("http")) else ''}
    
    <p><a href="{url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">View Details</a></p>
</body>
</html>"""
                    
                    # Debug: Print image URL if present
                    if image_url:
                        print(f"  Image URL: {image_url}")
                    
                    send_notification(message, html_message=html_message, image_url=image_url)
            else:
                print("✓ No new listings found")
        else:
            print("⚠ No listings extracted")
            new_listings_count = 0
        
        # Return the count of new listings found
        return new_listings_count
        
    except Exception as e:
        print(f"✗ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        return 0
    
    finally:
        if driver:
            driver.quit()
        print("✓ Scraping completed\n")


if __name__ == "__main__":
    init_database()
    scrape_apartments()

