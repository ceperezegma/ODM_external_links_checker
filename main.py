# -*- coding: utf-8 -*-
"""
Entry point for the ODM File Checker workflow.

High-level steps coordinated by this script:
1. Initialize and clean the environment.
2. Authenticate and open the SPA in a Playwright browser.
3. Visit all relevant tabs and trigger file downloads.
4. Validate the downloaded files against expectations.
5. Generate a final report.
6. Keep the browser open until the user confirms exit.

This module is intended to be executed as a script.
"""

import time
from src.auth import login_to_spa
from src.navigator import visit_links_tabs
# TODO: To delete from src.startup import initializer
# from src.validator import validate_downloads
# from src.reporter import generate_report
from config import EXPECTED_FILES_PATH


def main():
    """
    Orchestrate the end-to-end ODM File Checker process.

    Workflow:
    - Records the start time.
    - Runs initializer() to clean the workspace.
    - Logs in via login_to_spa() and obtains the Browser/Page.
    - Navigates all tabs and triggers downloads with visit_all_tabs(page).
    - Validates results using validate_downloads(EXPECTED_FILES_PATH).
    - Generates a report from the validation results.
    - Prints the total execution time.
    - Waits for user input before closing the browser.

    Side Effects:
    - Deletes files during initialization (see initializer()).
    - Launches a browser and interacts with a website.
    - Writes progress and timing information to stdout.
    - Creates a report as defined by generate_report().

    Raises:
    - Any unhandled exceptions from called functions will propagate and may stop the flow.

    Example:
        if __name__ == "__main__":
            main()
    """
    start_time = time.time()
    print("[*] Starting ODM External Links Checker...")

    # Make all the cleaning and setup to start the program from the right inital state
    # TODO: To delete initializer()

    # Step 1: Log in and get browser/page
    browser, page = login_to_spa()

    # Step 2: Navigate all tabs and download files
    visit_links_tabs(page)

    # # Step 3: Validate downloaded files
    # validation_results = validate_downloads(EXPECTED_FILES_PATH)
    #
    # # Step 4: Generate report
    # generate_report(validation_results)

    # Calculate and display execution time
    end_time = time.time()
    execution_time = end_time - start_time
    minutes, seconds = divmod(execution_time, 60)
    print(f"\n[i] Total execution time: {int(minutes)} minutes and {seconds:.2f} seconds")
    
    # Keep browser open
    input("Press Enter to close browser and exit...")
    browser.close()


if __name__ == "__main__":
    main()
