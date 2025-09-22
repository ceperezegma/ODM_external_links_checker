# -*- coding: utf-8 -*-
# from playwright.sync_api import sync_playwright


def retrieve_external_links(page):

    return page.locator("""//a[@href 
                                        and not(starts-with(@href, 'https://data.europa.eu')) 
                                        and not(starts-with(@href, 'https://op.europa.eu')) 
                                        and not(starts-with(@href, 'https://european-union.europa.eu')) 
                                        and not(starts-with(@href, 'https://dataeuropa.gitlab.io')) 
                                        and not(starts-with(@href, 'https://twitter.com')) 
                                        and not(starts-with(@href, 'https://www.linkedin.com')) 
                                        and not(starts-with(@href, 'https://www.youtube.com/c/PublicationsOffice')) 
                                        and not(starts-with(@href, 'https://www.instagram.com')) 
                                        and not(starts-with(@href, 'https://ec.europa.eu')) 
                                        and not(starts-with(@href, 'https://eur-lex.europa.eu')) 
                                        and not(starts-with(@href, 'https://ted.europa.eu/en'))
                                        and not(starts-with(@href, 'https://cordis.europa.eu')) 
                                        and not(starts-with(@href, 'http://europa.eu')) 
                                        and starts-with(@href, 'http')
                                        ]""")


def click_odm_button(page, dimension):

    page.locator(f"//button[@aria-label='Select {dimension[0]}']").click()


def get_links_from_elements(links_elements):

    external_links_tab = []

    num_external_links = links_elements.count()
    for i in range(num_external_links):
        external_links_tab.append(links_elements.nth(i).get_attribute('href'))

    return  external_links_tab


def change_page_table(page, dimension):

    nav_table = page.locator("//nav[starts-with(@aria-label, 'pagination-heading')]")
    num_nav_table = nav_table.count()
    print(f"[i] Number of tables paginators found: {num_nav_table}")
    match dimension[0]:
        case 'Policy':
            current_nav = nav_table.nth(0)
        case 'Portal':
            current_nav = nav_table.nth(1)
        case 'Impact':
            current_nav = nav_table.nth(2)

    print(f"-> Table: {current_nav.get_attribute('aria-label')}")

    # Keep clicking "Next" while the link exists and is visible. This is scoped to the selected paginator to avoid strict-mode issues.
    safety_max_clicks = 200  # safety guard to avoid infinite loops
    clicks = 0
    while True:
        next_link = current_nav.locator("//a[@title='Go to next page']")
        if next_link.count() == 0 or not next_link.first.is_visible():
            print("[i] No 'Next' link found. Stopping pagination.")
            break

        next_link.first.click()
        page.wait_for_timeout(1000)    # Added this timeout to wait the ODM page loads the next page of the table
        clicks += 1
        print(f"[i] Clicked 'Next' ({clicks})")

        # # Allow content to update; adjust as needed for your SPA
        # try:
        #     page.wait_for_load_state("networkidle", timeout=3000)
        # except Exception:
        #     # Fall back to a small delay if networkidle is not reliable in this SPA
        #     page.wait_for_timeout(500)

        if clicks >= safety_max_clicks:
            print("[❌] Reached safety limit for pagination clicks. Stopping to avoid infinite loop.")
            break






def external_links_extractor(page, tab_name):

    match tab_name:
        case 'Recommendations':
            links_elements = retrieve_external_links(page)
            external_links_tab_raw = get_links_from_elements(links_elements)
        case 'Dimensions':
            dimensions = [('Policy', 1), ('Portal', 1), ('Quality', 0), ('Impact', 1)]    # in format: (<dimension>, <is there a table?>) -> is there a table? = 1 if yes, 0 if no

            for dimension in dimensions:
                print(f"[i] Extracting external links for dimension: {dimension[0]}")

                click_odm_button(page, dimension)
                if dimension[1] == 1:
                    change_page_table(page, dimension)

                # TODO: I'm here!!
                links_elements = retrieve_external_links(page)
                external_links_tab_raw = get_links_from_elements(links_elements)
        case 'Country profiles':
            links_elements = retrieve_external_links(page)
            external_links_tab_raw = get_links_from_elements(links_elements)

    print(f"Number of external links found: {len(external_links_tab_raw)}")

    return external_links_tab_raw
    

