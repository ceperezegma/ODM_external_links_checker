# -*- coding: utf-8 -*-
"""
Tab navigation utilities.

This module contains helpers to iterate through the application's tabs and
delegate per-tab download processing to the downloader component. It uses a
robust strategy to activate each tab, attempting both href-based and text-based
selection, and reports navigation progress and potential issues.
"""

from src.links_extractor import external_links_extractor


def visit_links_tabs(page):
    """
    Navigate through application tabs and extract external links from each.

    Args:
        page (playwright.sync_api.Page): Active Playwright page object used to
            interact with the web application and navigate between tabs.

    Returns:
        dict: Dictionary mapping tab keys to lists of extracted URLs:
            - 'recommendations': List of URLs from Recommendations tab
            - 'dimensions': List of URLs from Dimensions tab
            - 'country_profiles': List of URLs from Country profiles tab
    """
    tabs = {
        'recommendations': '#recommendations',
        'dimensions': '#dimensions',
        'country_profiles': '#country-profiles'
    }

    retrieve_links_tab = {
        'recommendations': [],
        'dimensions': [],
        'country_profiles': []
    }

    for tab_name, tab_selector in tabs.items():
        match tab_name:
            case 'recommendations':
                tab_name = 'Recommendations'
            case 'dimensions':
                tab_name = 'Dimensions'
            case 'country_profiles':
                tab_name = 'Country profiles'

        print(f"\n-----------------------------------------")
        print(f"[*] Navigating to tab: {tab_name}")
        print(f"-----------------------------------------")

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
            print(f"[❌] Href strategy failed for {tab_name}: {e}")
        
        # Strategy 2: Try text match if href failed
        if not clicked:
            try:
                page.click(f"text={tab_name}")
                print(f"[+] Clicked on tab using text: {tab_name}")
                clicked = True
            except Exception as e:
                print(f"[❌] Text strategy failed for {tab_name}: {e}")
        
        if not clicked:
            print(f"[❌] Could not click tab '{tab_name}' with any strategy")
            continue

        # Verify we're on the correct tab by checking URL
        current_url = page.url
        if tab_selector not in current_url:
            print(f"[⚠️] Warning: Expected '{tab_selector}' in URL but got: {current_url}")
            print(f"[⚠️] Tab navigation may have failed for: {tab_name}")


        # Add logic to extract external links by tab
        match tab_name:
            case 'Recommendations':
                retrieve_links_tab['recommendations'].extend(external_links_extractor(page, tab_name))
            case 'Dimensions':
                retrieve_links_tab['dimensions'].extend(external_links_extractor(page, tab_name))
            case 'Country profiles':
                retrieve_links_tab['country_profiles'].extend(external_links_extractor(page, tab_name))
            case _:
                print(f"[❌] Error at tab selection. Selected '{tab_name}'")


    return retrieve_links_tab

