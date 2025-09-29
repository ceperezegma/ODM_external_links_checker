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
from src.startup import initializer
from src.navigator import visit_links_tabs
from src.links_cleaner import clean_links_for_tab, clean_links_for_dimensions
from src.links_validator import check_and_save_link_statuses_by_tab
# from src.validator import validate_downloads
from src.reporter import generate_screen_report
from config import EXPECTED_FILES_PATH


def main():

    start_time = time.time()
    print("\n1️⃣ Starting ODM External Links Checker...")

    # Step 1: Log in, get browser/page, and clean used folders
    browser, page = login_to_spa()
    initializer()

    # Step 2: Navigate all tabs and collect external links
    retrieved_links = visit_links_tabs(page)

    # Step 3: Clean/filter links per tab against the manifesto
    print(f"\n-------------------------------------")
    print(f"2️⃣ Cleaning retrieved external links")
    print(f"-------------------------------------")

    try:
        manifest_path = "ODM_external_links_manifesto.json"
        rec_clean = clean_links_for_tab(retrieved_links.get('recommendations', []), "Recommendations", manifest_path)
        dim_clean = clean_links_for_tab(retrieved_links.get('dimensions', []), "Dimensions", manifest_path)
        cprof_clean = clean_links_for_tab(retrieved_links.get('country_profiles', []), "Country profiles", manifest_path)

        print("\n[i] Cleaned links summary (after intersecting with manifesto):")
        print(f"  - Recommendations: {len(rec_clean)} kept out of {len(retrieved_links.get('recommendations', []))}")
        print(f"  - Dimensions: {len(dim_clean)} kept out of {len(retrieved_links.get('dimensions', []))}")
        print(f"  - Country profiles: {len(cprof_clean)} kept out of {len(retrieved_links.get('country_profiles', []))}")
    except Exception as e:
        print(f"[❌] Error while cleaning links against manifesto: {e}")
        rec_clean, dim_clean, cprof_clean = [], [], []

    # Step 4: Check HTTP status for cleaned links and save structured results
    print(f"\n----------------------------------------")
    print(f"3️⃣ Checking external links HTTP status ")
    print(f"----------------------------------------")

    try:
        links_by_tab = {
            'recommendations': rec_clean,
            'dimensions': dim_clean,
            'country_profiles': cprof_clean,
        }
        outputs = check_and_save_link_statuses_by_tab(links_by_tab, output_dir="link_status", max_workers=12, timeout=10, verify_ssl=True)
        print("\n[i] Saved HTTP status results:")
        for tab, out_path in outputs.items():
            print(f"  - {tab}: {out_path}")
    except Exception as e:
        print(f"[❌] Error while checking/saving link statuses: {e}")

    # Step 5: On-screen reporting from saved JSONs
    print(f"\n-------------------------------------")
    print(f"4️⃣ Generating on-screen report ")
    print(f"-------------------------------------")
    try:
        generate_screen_report(status_dir="link_status", manifest_path=manifest_path)
    except Exception as e:
        print(f"[❌] Error while generating report: {e}")

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
