# -*- coding: utf-8 -*-
"""
Utilities for locating and interacting with tab-scoped selector buttons.

This module provides helpers to:
- Build locators for dimension and country buttons based on provided labels.
- Click a specific button and log the interaction outcome.

These functions are intended to be used by higher-level navigation and download
workflows that iterate over dimensions or countries within a tab.
"""

def retrieve_buttons(page, labels):
    """
    Locate and retrieve all country button elements on the page.

    Args:
        page (playwright.sync_api.Page): Active Playwright page object used to
            locate button elements.
        labels (list): List of tuples containing (country_name, country_code) pairs
            used to identify the country buttons.

    Returns:
        list: List of Playwright Locator objects representing the country buttons
            found on the page.
    """
    # Localizes the 34 countries buttons
    buttons = [page.locator(f"button[id='country_{country_code}'][aria-label='Select {country}']") for country, country_code in labels]
    print(f"[i] Found {len(buttons)} country buttons in the country profiles tab")

    return buttons


def select_button(page, button, label):
    """
    Click a button element and wait for the page to update.

    Args:
        page (playwright.sync_api.Page): Active Playwright page object used for
            waiting and interaction.
        button (playwright.sync_api.Locator): Playwright Locator object representing
            the button to be clicked.
        label (tuple or str): Button identifier used for logging purposes. Can be a
            tuple (country_name, country_code) or a string (dimension name).

    Returns:
        None
    """
    # Clicks on a specific dimension button
    try:
        button.click()
        page.wait_for_timeout(1000)
        print(f"[i] Clicked on {label[0]} button")

    except Exception as e:
        if label in ('Policy', 'Portal', 'Quality', 'Impact'):
            print(f"\n[❌] Failed to click on {label} button: {e}")
        else:
            print(f"\n[❌] Failed to click on {label[0]} button: {e}")
