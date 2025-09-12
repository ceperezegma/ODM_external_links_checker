# -*- coding: utf-8 -*-
"""
Authentication utilities for launching a Playwright browser and logging into the SPA.

This module exposes a single function `login_to_spa` that:
- Starts Playwright (Chromium).
- Launches a browser with a maximized window (headless mode controlled via configuration).
- Creates a browser context with HTTP Basic Authentication and a full-screen viewport.
- Navigates to the login URL and waits for the page to be fully loaded.
- Handles common UI pop-ups such as newsletter and cookie banners when present.

It returns both the Browser and Page instances for subsequent navigation and actions.
"""

from playwright.sync_api import sync_playwright
from config import LOGIN_URL, USERNAME, PASSWORD, HEADLESS, ENVIRONMENT


def login_to_spa():
    """
    Launch a Chromium browser via Playwright, authenticate using HTTP Basic Auth,
    navigate to the configured SPA login URL, and return the Browser and Page objects.

    Behavior:
    - Headless mode is controlled by the HEADLESS configuration.
    - The browser launches maximized and creates a context with HTTP Basic Auth using
      the configured USERNAME and PASSWORD.
    - The function navigates to LOGIN_URL and waits for the network to be idle.
    - Attempts best-effort dismissal of optional UI elements (newsletter banner and
      cookie consent for "Accept only essential cookies") if they appear.
    - Prints status messages for diagnostics.

    Returns:
        tuple:
            - browser (playwright.sync_api.Browser): The launched Chromium Browser instance.
            - page (playwright.sync_api.Page): The active Page within the authenticated context.

    Raises:
        This function internally catches exceptions related to navigation/authentication
        and prints diagnostic messages. In case of failure, it still returns the
        (browser, page) pair if available so the caller can decide on next steps.

    Side Effects:
        - Starts Playwright and launches a browser process.
        - Prints diagnostic output to stdout.
        - May interact with and dismiss certain pop-ups on the target page.

    Example:
        browser, page = login_to_spa()
        # Use the returned page for further navigation...
    """
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=HEADLESS,
        args=["--start-maximized"]
    )

    # Create context with HTTP Basic Auth and full screen viewport
    if ENVIRONMENT in ('DEV', 'H-PROD'):
        print('[i] 🔒 You are currently running in a environment protected by credentials.')
        context = browser.new_context(http_credentials={"username": USERNAME, "password": PASSWORD},
                                      viewport={"width": 1920, "height": 1080},
                                      no_viewport=True)  # Use full screen
    else:
        print('[i] 🔓 You are currently running in a public environment.')
        context = browser.new_context(viewport={"width": 1920, "height": 1080},
                                      no_viewport=True)  # Use full screen

    page = context.new_page()
    
    try:
        page.goto(LOGIN_URL)
        page.wait_for_load_state("networkidle")
        print(f"Successfully authenticated and loaded: {page.title()}")
    except Exception as e:
        print(f"Authentication failed: {e}")
        print("Manual login may be required.")

    # Close newsletter popup if it appears
    try:
        # Wait up to 3 seconds for the close button to appear
        page.wait_for_selector("button.close", timeout=3000)
        page.click("button.close")
        print("✅ Newsletter banner closed.")
    except Exception:
        print("ℹ️ Newsletter banner not found or already dismissed.")

    # Accept only essential cookies if cookie banner is shown
    try:
        page.wait_for_selector("button:has-text('Accept only essential cookies')", timeout=3000)
        page.click("button:has-text('Accept only essential cookies')")
        print("✅ Cookie consent accepted (only essential cookies).")
    except Exception:
        print("ℹ️ Cookie banner not found or already handled.")

    # Close the survey pop up if it appears
    try:
        page.locator('a:has-text("Remind me later")').click()
        print("✅ Survey participation rejected.")
    except Exception:
        print("ℹ️ Survey participation pop-up not found or already handled.")

    return browser, page
