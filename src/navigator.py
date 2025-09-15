# -*- coding: utf-8 -*-
"""
Tab navigation utilities.

This module contains helpers to iterate through the application's tabs and
delegate per-tab download processing to the downloader component. It uses a
robust strategy to activate each tab, attempting both href-based and text-based
selection, and reports navigation progress and potential issues.
"""

# TODO from src.downloader import download_all_files


def visit_links_tabs(page):
    """
    Navigate through all known tabs and trigger downloads for each.

    Behavior:
    - Defines the ordered set of tabs to visit along with their expected hash/href.
    - For each tab:
        - Attempts to click using an href selector; if unavailable, falls back to a text-based click.
        - Waits briefly to allow content to load.
        - Warns if the current URL does not contain the expected tab selector.
        - Invokes download_all_files(page, tab_name) to handle tab-specific downloads.
    - Prints progress and diagnostic messages throughout.

    Parameters:
        page (playwright.sync_api.Page): The active Playwright page used to interact
            with the UI and switch between tabs.

    Returns:
        None

    Side Effects:
        - Performs UI interactions (clicks, waits).
        - Triggers downloads via the downloader component.
        - Writes diagnostic output to stdout.

    Example:
        # After successful authentication and landing on the main page:
        visit_all_tabs(page)
    """
    tabs = {
        'Recommendations': '#recommendations',
        'Dimensions': '#dimensions',
        'Country profiles': '#country-profiles'
    }

    for tab_name, tab_selector in tabs.items():
        print(f"\n---------------------------------")
        print(f"[*] Navigating to tab: {tab_name}")
        print(f"---------------------------------")

        # Find the tab element using multiple strategies
        clicked = False
        
        # Strategy 1: Try href selector
        try:
            tab_element = page.locator(f"a[href='{tab_selector}']")
            if tab_element.count() > 0:
                tab_element.nth(0).click()
                print(f"[+] Clicked on tab using href: {tab_name}")
                clicked = True
        except Exception as e:
            print(f"[!] Href strategy failed for {tab_name}: {e}")
        
        # Strategy 2: Try text match if href failed
        if not clicked:
            try:
                page.click(f"text={tab_name}")
                print(f"[+] Clicked on tab using text: {tab_name}")
                clicked = True
            except Exception as e:
                print(f"[!] Text strategy failed for {tab_name}: {e}")
        
        if not clicked:
            print(f"[❌] Could not click tab '{tab_name}' with any strategy")
            continue

        # Wait for tab-specific content to load
        page.wait_for_timeout(1000)  # Short buffer
        
        # Verify we're on the correct tab by checking URL
        current_url = page.url
        if tab_selector not in current_url:
            print(f"[⚠️] Warning: Expected '{tab_selector}' in URL but got: {current_url}")
            print(f"[!] Tab navigation may have failed for: {tab_name}")

        # Add logic to confirm content changed (by checking unique element)
        # TODO download_all_files(page, tab_name)
