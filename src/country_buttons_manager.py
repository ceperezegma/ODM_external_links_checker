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

    # Localizes the 34 countries buttons
    buttons = [page.locator(f"button[id='country_{country_code}'][aria-label='Select {country}']") for country, country_code in labels]
    print(f"[i] Found {len(buttons)} country buttons in the country profiles tab")

    return buttons


def select_button(page, button, label):
    """
    Click the provided button and log the result.
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
