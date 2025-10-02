# -*- coding: utf-8 -*-

from src.country_buttons_manager import retrieve_buttons, select_button


def retrieve_external_links(page):
    """
    Locate all external links on the page excluding specific domains.

    Args:
        page (playwright.sync_api.Page): Active Playwright page object used to
            query DOM elements.

    Returns:
        playwright.sync_api.Locator: Locator object containing all anchor elements
            with href attributes that match the filtering criteria (external links
            excluding EU/social media domains).
    """
    return page.locator("""//a[@href and not(starts-with(@href, 'https://data.europa.eu')) 
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
                                     and not(starts-with(@href, 'https://style-guide.europa.eu/'))
                                     and not(starts-with(@href, 'https://www.europa.eu/'))
                                     and starts-with(@href, 'https://') 
                                     or starts-with(@href, 'http://')
                                 ]""")


def click_odm_button(page, dimension):
    """
    Locate and click a dimension button by its aria-label attribute.

    Args:
        page (playwright.sync_api.Page): Active Playwright page object used to
            locate and interact with the button element.
        dimension (tuple or list): Container where the first element (dimension[0])
            is the dimension name used to identify the button (e.g., "Policy",
            "Portal", "Impact").

    Returns:
        None
    """
    page.locator(f"//button[@aria-label='Select {dimension[0]}']").click()


def get_links_from_elements(links_elements):
    """
    Extract href attributes from all link elements in a locator.

    Args:
        links_elements (playwright.sync_api.Locator): Locator object containing
            one or more anchor elements from which to extract href attributes.

    Returns:
        list: List of href attribute values (strings) extracted from each link
            element in the locator.
    """
    external_links_tab = []

    num_external_links = links_elements.count()
    for i in range(num_external_links):
        external_links_tab.append(links_elements.nth(i).get_attribute('href'))

    return  external_links_tab


def links_extractor(page):
    """
    Extract all external link URLs from the current page.

    Args:
        page (playwright.sync_api.Page): Active Playwright page object used to
            query and extract links from the current page content.

    Returns:
        list: List of external link URLs (strings) found on the page, including
            duplicates and unfiltered results.
    """
    links_elements = retrieve_external_links(page)
    external_links_tab_raw = get_links_from_elements(links_elements)

    return external_links_tab_raw



def change_page_table(page, dimension):
    """
    Navigate through paginated table pages and extract links from each page.

    Args:
        page (playwright.sync_api.Page): Active Playwright page object used to
            interact with pagination controls and extract links.
        dimension (tuple or list): Container where the first element (dimension[0])
            is the dimension name used to identify the correct table paginator
            (e.g., "Policy", "Portal", "Impact").

    Returns:
        list: List of external link URLs (strings) extracted from all pages of
            the table, aggregated across all pagination clicks.
    """
    links_raw_tab = []

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

    print(f"[i] Extracting links from the table: {current_nav.get_attribute('aria-label')}")

    # Keep clicking "Next" while the link exists and is visible. This is scoped to the selected paginator to avoid strict-mode issues.
    safety_max_clicks = 200  # safety guard to avoid infinite loops
    clicks = 0
    while True:
        # Extract links of the current page
        links_raw_tab.extend(links_extractor(page))

        next_link = current_nav.locator("//a[@title='Go to next page']")
        if next_link.count() == 0 or not next_link.first.is_visible():
            print("[i] No 'Next' link found. Stopping pagination.")
            break

        next_link.first.click()
        page.wait_for_timeout(1000)    # Added this timeout to wait the ODM page loads the next page of the table
        clicks += 1
        print(f"[i] Clicked 'Next' ({clicks})")
        if clicks >= safety_max_clicks:
            print("[❌] Reached safety limit for pagination clicks. Stopping to avoid infinite loop.")
            break

    return links_raw_tab


def remove_duplicates_tab(external_links_tab_raw):
 """
     Returns a new list containing only the first occurrence of each element from
     external_links_tab_raw, preserving order and skipping None values.
 """
 seen = set()
 external_links_tab_clean = []
 for item in external_links_tab_raw:
     if item is None:
         continue
     if item not in seen:
         seen.add(item)
         external_links_tab_clean.append(item)

 return external_links_tab_clean


def links_extractor_countries(page, country_buttons, countries):
    """
    Remove duplicate URLs from a list while preserving order and filtering out None values.

    Args:
        external_links_tab_raw (list): List of URLs that may contain duplicates
            and None values.

    Returns:
        list: Deduplicated list of URLs with only the first occurrence of each
            unique URL preserved in original order, with None values excluded.
    """
    links_raw_tab= []

    num_countries = len(country_buttons)
    for i in range(num_countries):
        select_button(page, country_buttons[i], countries[i])
        print(f"[i] Extracting external links for country: {countries[i][0]}")

        links_raw_tab.extend(links_extractor(page))

    return links_raw_tab


# -----------------------------------------------
# Core function for links extraction across ODM
#-----------------------------------------------
def external_links_extractor(page, tab_name):
    """
    Extract and deduplicate external links from a specific ODM tab.

    Args:
        page (playwright.sync_api.Page): Active Playwright page object used to
            interact with the tab content and extract links.
        tab_name (str): Name of the tab to extract links from. Must be one of:
            "Recommendations", "Dimensions", or "Country profiles".

    Returns:
        list: Deduplicated list of external link URLs (strings) extracted from
            the specified tab, with None values removed and order preserved.
    """
    external_links_tab_raw = []

    match tab_name:
        case 'Recommendations':
            external_links_tab_raw.extend(links_extractor(page))
        case 'Dimensions':
            dimensions = [('Policy', 1), ('Portal', 1), ('Quality', 0), ('Impact', 1)]    # in format: (<dimension>, <is there a table?>) -> is there a table? = 1 if yes, 0 if no

            for dimension in dimensions:
                print(f"[i] Extracting external links for dimension: {dimension[0]}")

                click_odm_button(page, dimension)
                if dimension[1] == 1:
                    external_links_tab_raw.extend(change_page_table(page, dimension))
        case 'Country profiles':
            countries = combined = [
                ('Albania', 'AL'),
                ('Austria', 'AT'),
                ('Belgium', 'BE'),
                ('Bosnia and Herzegovina', 'BA'),
                ('Bulgaria', 'BG'),
                ('Croatia', 'HR'),
                ('Cyprus', 'CY'),
                ('Czechia', 'CZ'),
                ('Denmark', 'DK'),
                ('Estonia', 'EE'),
                ('Finland', 'FI'),
                ('France', 'FR'),
                ('Germany', 'DE'),
                ('Greece', 'EL'),
                ('Hungary', 'HU'),
                ('Iceland', 'IS'),
                ('Ireland', 'IE'),
                ('Italy', 'IT'),
                ('Latvia', 'LV'),
                ('Lithuania', 'LT'),
                ('Luxembourg', 'LU'),
                ('Malta', 'MT'),
                ('Netherlands', 'NL'),
                ('Norway', 'NO'),
                ('Poland', 'PL'),
                ('Portugal', 'PT'),
                ('Romania', 'RO'),
                ('Serbia', 'RS'),
                ('Slovakia', 'SK'),
                ('Slovenia', 'SI'),
                ('Spain', 'ES'),
                ('Sweden', 'SE'),
                ('Switzerland', 'CH'),
                ('Ukraine', 'UA')]

            country_buttons = retrieve_buttons(page, countries)

            external_links_tab_raw.extend(links_extractor_countries(page, country_buttons, countries))

    external_links_clean =  remove_duplicates_tab(external_links_tab_raw)
    print(f"[i] Number of external links found: {len(external_links_tab_raw)}")

    return external_links_clean
    

