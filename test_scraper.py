"""
Test script for debugging the scraper and inspecting website structure.

This script is used for development and debugging purposes. It:
- Opens the website in a visible browser window
- Inspects page structure and elements
- Tests privacy banner acceptance
- Tests filter opening and form submission
- Tests listing extraction
- Saves page source HTML for inspection

Use this script when:
- Selectors need to be updated due to website changes
- Debugging why scraping fails
- Understanding the website's HTML structure
- Testing new extraction logic

Example:
    Run the test script:
    >>> python test_scraper.py
    
    The script will:
    1. Open browser and navigate to the website
    2. Inspect page structure
    3. Try to accept privacy settings
    4. Try to open filters
    5. Try to set search criteria and submit
    6. Try to extract listings
    7. Save page source to test_page_source.html
    8. Wait for user input before closing
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
from scraper import extract_listings

def init_driver():
    """
    Initialize Chrome WebDriver for testing (non-headless).
    
    Creates a Chrome driver with options to avoid detection, but runs
    in visible mode (not headless) so you can see what's happening.
    
    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance
    """
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def inspect_page(driver):
    """
    Inspect and print information about page structure for debugging.
    
    This function examines various elements on the page and prints useful
    information to help debug selector issues. It checks for:
    - Privacy banner elements
    - Search filter buttons
    - Input fields
    - Buttons
    
    It also saves the full page source HTML to test_page_source.html for
    manual inspection.
    
    Args:
        driver (webdriver.Chrome): The Selenium WebDriver instance
    
    Side Effects:
        - Prints inspection results to console
        - Saves page source to test_page_source.html
    """
    print("\n=== PAGE INSPECTION ===\n")
    
    # Print page title
    print(f"Page Title: {driver.title}")
    print(f"Current URL: {driver.current_url}\n")
    
    # Look for privacy banner
    print("Looking for privacy banner...")
    try:
        # Try by ID first
        try:
            privacy_by_id = driver.find_element(By.ID, "accept-all-cookies")
            print(f"  ✓ Found button by ID: {privacy_by_id.tag_name}, Visible: {privacy_by_id.is_displayed()}")
        except Exception:
            print("  ✗ Button with id='accept-all-cookies' not found")
        
        # Try by wire:click
        try:
            privacy_by_wire = driver.find_elements(By.XPATH, "//button[@wire:click='onCookieAll']")
            print(f"  Found {len(privacy_by_wire)} buttons with wire:click='onCookieAll'")
        except Exception:
            print("  No buttons with wire:click found")
        
        # Try by text content
        privacy_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Alle akzeptieren')]")
        print(f"Found {len(privacy_elements)} elements with 'Alle akzeptieren' text")
        for elem in privacy_elements[:5]:  # Show first 5
            try:
                print(f"  - Tag: {elem.tag_name}, Text: {elem.text[:50]}, Visible: {elem.is_displayed()}")
            except Exception:
                print(f"  - Tag: {elem.tag_name}, Text: {elem.text[:50]}")
    except Exception as e:
        print(f"  Error looking for privacy elements: {e}")
    
    # Look for Suchfilter button
    print("\nLooking for 'Suchfilter' button...")
    try:
        filter_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Suchfilter')]")
        print(f"Found {len(filter_elements)} elements with 'Suchfilter' text")
        for elem in filter_elements:
            print(f"  - Tag: {elem.tag_name}, Text: {elem.text[:50]}")
    except Exception:
        print("  No Suchfilter elements found")
    
    # Look for input fields
    print("\nLooking for input fields...")
    try:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"Found {len(inputs)} input elements")
        for inp in inputs[:10]:  # Show first 10
            placeholder = inp.get_attribute("placeholder") or ""
            name = inp.get_attribute("name") or ""
            input_id = inp.get_attribute("id") or ""
            print(f"  - Type: {inp.get_attribute('type')}, Placeholder: {placeholder[:30]}, Name: {name}, ID: {input_id[:30]}")
    except Exception:
        print("  No input elements found")
    
    # Look for buttons
    print("\nLooking for buttons...")
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        print(f"Found {len(buttons)} button elements")
        for btn in buttons[:10]:  # Show first 10
            print(f"  - Text: {btn.text[:50]}, Type: {btn.get_attribute('type')}")
    except Exception:
        print("  No button elements found")
    
    # Save page source
    print("\nSaving page source to test_page_source.html...")
    with open("test_page_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("✓ Page source saved")

if __name__ == "__main__":
    driver = None
    try:
        driver = init_driver()
        driver.get("https://www.inberlinwohnen.de/wohnungsfinder")
        
        print("Waiting for page to load...")
        time.sleep(5)
        
        # Inspect initial page
        inspect_page(driver)
        
        # Try to accept privacy
        print("\n=== ACCEPTING PRIVACY ===\n")
        try:
            # Wait for page to fully load
            wait = WebDriverWait(driver, 10)
            time.sleep(2)  # Wait for Livewire to initialize
            
            # Try multiple selectors for the privacy button
            accept_selectors = [
                (By.ID, "accept-all-cookies"),
                (By.XPATH, "//button[@id='accept-all-cookies']"),
                (By.XPATH, "//button[@wire:click='onCookieAll']"),
                (By.XPATH, "//button[.//span[contains(text(), 'Alle akzeptieren')]]"),
            ]
            
            accept_btn = None
            for by, selector in accept_selectors:
                try:
                    accept_btn = wait.until(EC.element_to_be_clickable((by, selector)))
                    break
                except Exception:
                    continue
            
            if accept_btn:
                try:
                    accept_btn.click()
                except Exception:
                    # Use JavaScript click as fallback for Livewire
                    driver.execute_script("arguments[0].click();", accept_btn)
                print("✓ Clicked 'Alle akzeptieren'")
                time.sleep(3)
            else:
                print("⚠ Could not find privacy button")
        except Exception as e:
            print(f"⚠ Could not accept privacy: {e}")
            import traceback
            traceback.print_exc()
        
        # Try to open filters
        print("\n=== OPENING FILTERS ===\n")
        try:
            wait = WebDriverWait(driver, 10)
            filter_selectors = [
                (By.XPATH, "//button[@aria-label='Suchfilter']"),
                (By.XPATH, "//button[contains(@class, 'button--icon') and .//i[contains(@class, 'fa-search')]]"),
                (By.XPATH, "//button[.//span[contains(text(), 'Suchfilter')]]"),
            ]
            
            filter_btn = None
            for by, selector in filter_selectors:
                try:
                    filter_btn = wait.until(EC.element_to_be_clickable((by, selector)))
                    break
                except Exception:
                    continue
            
            if filter_btn:
                filter_btn.click()
                print("✓ Clicked 'Suchfilter'")
                time.sleep(3)
                
                # Inspect page after opening filters
                inspect_page(driver)
                
                # Try to set values and submit
                print("\n=== SETTING VALUES AND SUBMITTING ===\n")
                try:
                    # Wait for modal
                    wait.until(EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Meine Suchkriterien')]")))
                    time.sleep(2)
                    
                    # Set Kaltmiete max
                    try:
                        kaltmiete_max = wait.until(EC.presence_of_element_located((By.NAME, "searchParams.rentNet.max")))
                        kaltmiete_max.clear()
                        kaltmiete_max.send_keys("460")
                        print("✓ Set Kaltmiete max to 460")
                    except Exception as e:
                        print(f"⚠ Could not set Kaltmiete: {e}")
                    
                    # Set Zimmer min
                    try:
                        zimmer_min = wait.until(EC.presence_of_element_located((By.NAME, "searchParams.rooms.min")))
                        zimmer_min.clear()
                        zimmer_min.send_keys("1")
                        print("✓ Set Zimmer min to 1")
                    except Exception as e:
                        print(f"⚠ Could not set Zimmer min: {e}")
                    
                    # Set Zimmer max
                    try:
                        zimmer_max = wait.until(EC.presence_of_element_located((By.NAME, "searchParams.rooms.max")))
                        zimmer_max.clear()
                        zimmer_max.send_keys("2")
                        print("✓ Set Zimmer max to 2")
                    except Exception as e:
                        print(f"⚠ Could not set Zimmer max: {e}")
                    
                    # Set Wohnfläche max
                    try:
                        wohnflaeche_max = wait.until(EC.presence_of_element_located((By.NAME, "searchParams.area.max")))
                        wohnflaeche_max.clear()
                        wohnflaeche_max.send_keys("50")
                        print("✓ Set Wohnfläche max to 50")
                    except Exception as e:
                        print(f"⚠ Could not set Wohnfläche: {e}")
                    
                    # Find and click submit button
                    try:
                        submit_selectors = [
                            "//button[@type='submit' and contains(., 'Wohnung suchen')]",
                            "//form//button[@type='submit']",
                            "//button[contains(., 'Wohnung suchen')]",
                        ]
                        
                        submit_btn = None
                        for selector in submit_selectors:
                            try:
                                submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                                print(f"✓ Found submit button: {selector}")
                                break
                            except Exception:
                                continue
                        
                        if submit_btn:
                            driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].click();", submit_btn)
                            print("✓ Clicked submit button")
                            time.sleep(5)
                            print("✓ Waiting for results...")
                            
                            # Now try to extract listings
                            print("\n=== EXTRACTING LISTINGS ===\n")
                            try:
                                listings = extract_listings(driver)
                                if listings:
                                    print(f"\n✓ Successfully extracted {len(listings)} listings!")
                                    print("\nFirst few listings:")
                                    for i, listing in enumerate(listings[:3], 1):
                                        print(f"\n  Listing {i}:")
                                        print(f"    URL: {listing.get('url', 'N/A')}")
                                        print(f"    Title: {listing.get('title', 'N/A')[:60]}")
                                        print(f"    Address: {listing.get('address', 'N/A')}")
                                        print(f"    Rooms: {listing.get('rooms', 'N/A')}")
                                        print(f"    Area: {listing.get('area', 'N/A')} m²")
                                        print(f"    Price: {listing.get('price', 'N/A')} €")
                                        print(f"    Nebenkosten: {listing.get('extra_costs', 'N/A')}")
                                        print(f"    WBS: {listing.get('wbs', 'N/A')}")
                                        print(f"    Image URL: {listing.get('image_url', 'N/A')}")
                                else:
                                    print("⚠ No listings extracted")
                            except Exception as e:
                                print(f"✗ Error extracting listings: {e}")
                                import traceback
                                traceback.print_exc()
                        else:
                            print("✗ Could not find submit button")
                    except Exception as e:
                        print(f"⚠ Error submitting: {e}")
                        import traceback
                        traceback.print_exc()
                        
                except Exception as e:
                    print(f"⚠ Error setting values: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("⚠ Could not find Suchfilter button")
        except Exception as e:
            print(f"⚠ Could not open filters: {e}")
        
        print("\n=== TEST COMPLETE ===")
        print("Check test_page_source.html for full HTML structure")
        print("\nPress Enter to close browser...")
        input()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()

