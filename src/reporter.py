# -*- coding: utf-8 -*-
"""
Console reporter for ODM external links.

Generates on-screen reports using the JSON status files produced in link_status
and the source-of-truth ODM_external_links_manifesto.json.

Report contents:
1) Per-tab comparison (Recommendations, Dimensions, Country profiles):
   - Links missing (expected but not retrieved/tested)
   - Links not expected but present (retrieved/tested but not in manifesto)
   - Basic counts to give context
2) Overall HTTP status summary (across all tabs):
   - Total links with status 200, in number and percentage of total tested
   - Total and list of links not working properly (status != 200)

Usage:
   from src.reporter import generate_screen_report
   generate_screen_report(status_dir="link_status", manifest_path="ODM_external_links_manifesto.json")
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urlsplit, urlunsplit

TAB_TO_STATUS_FILE = {
    "Recommendations": "recommendations_link_status.json",
    "Dimensions": "dimensions_link_status.json",
    "Country profiles": "country_profiles_link_status.json",
}


# -------------------------
# URL normalization helper
# -------------------------

def _normalize_url(url: str) -> str:
    """
    Normalize a URL for consistent comparison by standardizing its components.

    Args:
        url (str): The URL string to normalize. Can be None or empty.

    Returns:
        str: Normalized URL with:
            - Whitespace trimmed
            - Scheme and netloc (hostname) lowercased
            - Trailing slash removed from path (except for root path "/")
            - Query and fragment preserved as-is
            Returns empty string if input is None or empty after stripping.
    """
    if url is None:
        return ""
    url = url.strip()
    if not url:
        return url
    parts = urlsplit(url)
    scheme = (parts.scheme or "").lower()
    netloc = (parts.netloc or "").lower()
    path = parts.path or ""
    if path.endswith("/") and path != "/":
        path = path.rstrip("/")
    return urlunsplit((scheme, netloc, path, parts.query, parts.fragment))


# -------------------------
# Manifest helpers
# -------------------------

def _load_manifest(manifest_path: Path) -> Dict[str, List[Dict[str, str]]]:
    """
    Load and validate the manifest JSON file for link reporting.

    Args:
        manifest_path (Path): Path object pointing to the manifest JSON file.

    Returns:
        Dict[str, List[Dict[str, str]]]: Dictionary containing manifest data with
            tab names as keys ("Recommendations", "Dimensions", "Country profiles")
            and lists of link entry dictionaries as values.

    Raises:
        ValueError: If the manifest is missing any of the required tab keys
            ("Recommendations", "Dimensions", "Country profiles").
    """
    with manifest_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # ensure required keys
    for key in ("Recommendations", "Dimensions", "Country profiles"):
        if key not in data:
            raise ValueError(f"Manifest missing required key: {key}")
    return data


def _expected_urls_by_tab(manifest: Dict[str, List[Dict[str, str]]]) -> Dict[str, Set[str]]:
    """
    Extract and normalize expected URLs from the manifest, organized by tab.

    Args:
        manifest (Dict[str, List[Dict[str, str]]]): Manifest dictionary containing
            tab names as keys and lists of link entry dictionaries as values.

    Returns:
        Dict[str, Set[str]]: Dictionary mapping each tab name ("Recommendations",
            "Dimensions", "Country profiles") to a set of normalized URLs expected
            for that tab.
    """
    result: Dict[str, Set[str]] = {"Recommendations": set(), "Dimensions": set(), "Country profiles": set()}
    for tab in result.keys():
        urls = set()
        for entry in manifest.get(tab, []):
            url = entry.get("url") if isinstance(entry, dict) else None
            if not url:
                continue
            urls.add(_normalize_url(url))
        result[tab] = urls
    return result


def _level_lookup_by_tab(manifest: Dict[str, List[Dict[str, str]]]) -> Dict[str, Dict[str, str]]:
    """
    Build a lookup mapping of normalized URLs to their level strings per tab.

    Args:
        manifest (Dict[str, List[Dict[str, str]]]): Manifest dictionary containing
            tab names as keys and lists of link entry dictionaries as values.

    Returns:
        Dict[str, Dict[str, str]]: Nested dictionary mapping tab names to dictionaries
            that map normalized URLs to their level strings. Entries without a level
            are excluded from the mapping.
    """
    result: Dict[str, Dict[str, str]] = {"Recommendations": {}, "Dimensions": {}, "Country profiles": {}}
    for tab in result.keys():
        for entry in manifest.get(tab, []):
            if not isinstance(entry, dict):
                continue
            url = entry.get("url")
            level = entry.get("level")
            if not url:
                continue
            norm = _normalize_url(url)
            if level:
                result[tab][norm] = level
    return result


# -------------------------
# Status file helpers
# -------------------------

def _load_status_items(status_file: Path) -> List[Dict]:
    """
    Load status items from a JSON file.

    Args:
        status_file (Path): Path to the JSON file containing status items.

    Returns:
        List[Dict]: A list of dictionaries representing status items if the file
        exists and contains valid JSON data in list format. Returns an empty list
        if the file does not exist, cannot be parsed, or does not contain a list.
    """
    if not status_file.exists():
        return []
    with status_file.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []
    if isinstance(data, list):
        return data
    return []


def _retrieved_urls_from_status(items: List[Dict]) -> Set[str]:
    """
    Extract and normalize URLs from status items.

    Args:
        items (List[Dict]): A list of dictionaries representing status items,
            each expected to contain a "url" field.

    Returns:
        Set[str]: A set of normalized URLs extracted from the status items.
        Only entries with a valid "url" key are included.
    """
    urls: Set[str] = set()
    for it in items:
        # Use the originally requested URL for set comparisons
        url = it.get("url")
        if url:
            urls.add(_normalize_url(url))
    return urls


# -------------------------
# Pretty printing helpers
# -------------------------

def _print_separator(separator_type: int = 1):
    """
    Print a visual separator line to the console.

    Args:
        separator_type (int, optional): Type of separator to print.
            - 1: Prints a line of '=' characters (default).
            - 2: Prints a line of '-' characters.

    Returns:
        None
    """
    match separator_type:
        case 1:
            print("=" * 70)
        case 2:
            print("-" * 70)


def _print_centered(title: str):
    """
    Print a string centered within a fixed console width.

    Args:
        title (str): The text to display centered.

    Returns:
        None
    """
    width = 70
    pad = max(0, (width - len(title)) // 2)
    print(" " * pad + title)


# -------------------------
# HTTP status pretty labels
# -------------------------

def _status_label(status) -> str:
    """Return a short label with icon for a given HTTP status.

    Handles both int and string-like inputs. Falls back to a generic label.
    """
    # Normalize to int when possible
    if isinstance(status, int):
        code = status
    else:
        try:
            code = int(str(status))
        except Exception:
            code = None

    labels = {
        100: "⏩ Continue",
        101: "🔁 Switching Protocols",
        102: "⏳ Processing",
        200: "✅ OK",
        201: "✨ Created",
        202: "📨 Accepted",
        203: "ℹ️ Non-authoritative Information",
        300: "🔀 Multiple Choices",
        301: "🔁 Moved Permanently",
        302: "🔀 Found (Temporary Redirect)",
        303: "👀 See Other",
        304: "🗄️ Not Modified",
        400: "❌ Bad Request",
        401: "🔒 Unauthorized",
        402: "💳 Payment Required",
        403: "🚫 Forbidden",
        404: "❌ Not Found",
        500: "⚠️ Internal Server Error",
        501: "🧩 Not Implemented",
        502: "🧱 Bad Gateway",
        503: "⏳ Service Unavailable",
        504: "⌛ Gateway Timeout",
    }

    if code in labels:
        return f" - {labels[code]}"
    return " - ❓ Other status"


# -------------------------
# Public API
# -------------------------
# Constants
ORDERED_TABS = ("Recommendations", "Dimensions", "Country profiles")


def _aggregate_tab_data(status_dir_p: Path, expected_by_tab: Dict[str, Set[str]]) -> tuple[Dict[str, Dict], List[Dict]]:
    """
    Aggregate per-tab statistics and collect all status items.

    Args:
        status_dir_p (Path): Path to the directory containing status JSON files.
        expected_by_tab (Dict[str, Set[str]]): Mapping of tab names to sets of
            expected normalized URLs.

    Returns:
        tuple[Dict[str, Dict], List[Dict]]:
            - Dict[str, Dict]: Per-tab statistics including:
                * expected_count (int): Number of expected URLs for the tab.
                * retrieved_count (int): Number of retrieved URLs for the tab.
                * missing (List[str]): Expected URLs not found in retrieved data.
                * unexpected (List[str]): Retrieved URLs not present in expected data.
                * ok_200 (int): Count of items with HTTP status code 200.
                * nok (int): Count of items with non-200 HTTP status codes.
                * ok_pct (float): Percentage of items with status code 200.
                * items (List[Dict]): Raw list of status item dictionaries.
            - List[Dict]: Combined list of all status items across tabs.
    """
    per_tab_data: Dict[str, Dict] = {}
    all_status_items: List[Dict] = []

    for tab, filename in TAB_TO_STATUS_FILE.items():
        status_path = status_dir_p / filename
        items = _load_status_items(status_path)
        all_status_items.extend(items)

        expected_set = expected_by_tab.get(tab, set())
        retrieved_set = _retrieved_urls_from_status(items)

        # HTTP OK / NOK counts per tab
        ok_200 = sum(1 for it in items if it.get("status_code") == 200)
        nok = sum(1 for it in items if it.get("status_code") != 200)
        ok_pct = (ok_200 / len(items) * 100) if len(items) > 0 else 0.0

        # Differences vs manifesto
        missing = sorted(expected_set - retrieved_set)
        unexpected = sorted(retrieved_set - expected_set)

        per_tab_data[tab] = {
            "expected_count": len(expected_set),
            "retrieved_count": len(retrieved_set),
            "missing": missing,
            "unexpected": unexpected,
            "ok_200": ok_200,
            "nok": nok,
            "ok_pct": ok_pct,
            "items": items,
        }

    return per_tab_data, all_status_items


def _print_summary_table(per_tab_data: Dict[str, Dict]) -> None:
    """
    Print a formatted summary table of link statistics per tab.

    Args:
        per_tab_data (Dict[str, Dict]): Dictionary mapping tab names to statistics
            dictionaries. Each statistics dictionary is expected to contain:
                * expected_count (int): Number of expected URLs.
                * retrieved_count (int): Number of retrieved URLs.
                * missing (List[str]): List of missing expected URLs.
                * unexpected (List[str]): List of unexpected retrieved URLs.
                * ok_200 (int): Count of items with HTTP status code 200.
                * nok (int): Count of items with non-200 status codes.
                * ok_pct (float): Percentage of items with status code 200.

    Returns:
        None
    """
    print("\n🔔Summary of links per tab (totals):")
    _print_separator()
    header = f"{'Tab':<20} | {'Expected':>8} | {'Retrieved':>9} | {'Missing':>7} | {'Unexpected':>11} | {'✅ 200 OK':>6} | {'❌ Not 200':>5} | {'% of OK':>5}"
    print(header)
    print("-" * len(header))

    for tab in ORDERED_TABS:
        data = per_tab_data.get(tab, {})
        print(
            f"{tab:<20} | "
            f"{data.get('expected_count', 0):>8} | "
            f"{data.get('retrieved_count', 0):>9} | "
            f"{len(data.get('missing', [])):>7} | "
            f"{len(data.get('unexpected', [])):>11} | "
            f"{data.get('ok_200', 0):>9} | "
            f"{data.get('nok', 0):>11} | "
            f"{data.get('ok_pct', 0.0):>5.1f}%"
        )


def _print_missing_links(per_tab_data: Dict[str, Dict]) -> None:
    """
    Print a detailed list of missing links for each tab.

    Args:
        per_tab_data (Dict[str, Dict]): Dictionary mapping tab names to statistics
            dictionaries. Each statistics dictionary may contain a "missing" key
            with a list of expected URLs that were not retrieved.

    Returns:
        None

    Notes:
        - The function prints directly to the console.
        - If no missing links are found across all tabs, a message indicating this
          is displayed.
    """
    print("\n❌ Missing links (expected but not retrieved), by tab:")
    _print_separator()
    had_any = False

    for tab in ORDERED_TABS:
        missing = per_tab_data.get(tab, {}).get("missing", [])
        if missing:
            had_any = True
            print(f"{tab}: {len(missing)} missing")
            for u in missing:
                print(f"  - {u}")

    if not had_any:
        print("No missing links across tabs.")


def _print_unexpected_links(per_tab_data: Dict[str, Dict]) -> None:
    """
    Print a detailed list of unexpected links for each tab.

    Args:
        per_tab_data (Dict[str, Dict]): Dictionary mapping tab names to statistics
            dictionaries. Each statistics dictionary may contain an "unexpected" key
            with a list of retrieved URLs that were not part of the expected set.

    Returns:
        None

    Notes:
        - The function prints directly to the console.
        - If no unexpected links are found across all tabs, a message indicating this
          is displayed.
    """
    print("\n❌ Not expected but present links (retrieved but not in manifesto), by tab:")
    _print_separator()
    had_any = False

    for tab in ORDERED_TABS:
        unexpected = per_tab_data.get(tab, {}).get("unexpected", [])
        if unexpected:
            had_any = True
            print(f"{tab}: {len(unexpected)} unexpected")
            for u in unexpected:
                print(f"  - {u}")

    if not had_any:
        print("No unexpected links across tabs.")


def _group_non_working_links_by_status(per_tab_data: Dict[str, Dict]) -> Dict[object, Dict[str, List[Dict]]]:
    """
    Group non-working links (status codes other than 200) by HTTP status code,
    and further organize them by tab.

    Args:
        per_tab_data (Dict[str, Dict]): Dictionary mapping tab names to statistics
            dictionaries. Each statistics dictionary may contain an "items" key
            with a list of status item dictionaries. Each item is expected to have
            a "status_code" field.

    Returns:
        Dict[object, Dict[str, List[Dict]]]: Nested dictionary where:
            - Keys are HTTP status codes (other than 200).
            - Values are dictionaries mapping tab names to lists of status item
              dictionaries with that status code.
    """
    non_working_by_status: Dict[object, Dict[str, List[Dict]]] = {}

    for tab, filename in TAB_TO_STATUS_FILE.items():
        items = per_tab_data.get(tab, {}).get("items", [])
        for it in items:
            status_code = it.get("status_code")
            if status_code != 200:
                bucket = non_working_by_status.setdefault(status_code, {})
                bucket.setdefault(tab, []).append(it)

    return non_working_by_status


def _status_sort_key(k):
    """
    Generate a sort key for HTTP status codes, placing numeric codes first
    in ascending order, followed by non-numeric codes.

    Args:
        k (Any): The status code to generate a sort key for. Can be an int
            or any other type.

    Returns:
        tuple: A tuple suitable for sorting, where numeric codes come first
        (0, k) and non-numeric codes come afterward (1, str(k)).
    """
    return (0, k) if isinstance(k, int) else (1, str(k))


def _print_non_working_links(per_tab_data: Dict[str, Dict], level_lookup: Dict[str, Dict[str, str]]) -> None:
    """
    Print a detailed report of links that are not working properly
    (HTTP status code other than 200), organized by status and tab.

    Args:
        per_tab_data (Dict[str, Dict]): Dictionary mapping tab names to statistics
            dictionaries. Each statistics dictionary may contain an "items" key
            with a list of status item dictionaries, each expected to have
            "url", "status_code", "method_used", and optionally "error".
        level_lookup (Dict[str, Dict[str, str]]): Nested dictionary mapping tab names
            to normalized URLs to their corresponding level strings. Used to
            display the level of each link.

    Returns:
        None

    Notes:
        - The function prints directly to the console.
        - Links are grouped first by HTTP status code (sorted using _status_sort_key),
          then by tab (following ORDERED_TABS).
        - If all links have status 200, a message indicating this is displayed.
        - The function relies on helper functions: _group_non_working_links_by_status,
          _status_sort_key, _status_label, _normalize_url, and _print_separator.
    """
    print("\n️‍⛓️‍💥 Links not working properly (status other than 200):")
    _print_separator()

    non_working_by_status = _group_non_working_links_by_status(per_tab_data)

    if non_working_by_status:
        for status in sorted(non_working_by_status.keys(), key=_status_sort_key):
            status_icon = _status_label(status)
            print(f"Status {status}{status_icon}:")
            tabs_map = non_working_by_status[status]

            for tab in ORDERED_TABS:
                rows = tabs_map.get(tab, [])
                if not rows:
                    continue
                print(f"  [{tab}] {len(rows)} link(s):")
                for it in rows:
                    url = it.get("url")
                    method = it.get("method_used")
                    err = it.get("error")
                    lvl = level_lookup.get(tab, {}).get(_normalize_url(url), "Unknown")
                    print(f"    - {url} (level={lvl}, method={method}, error={err})")
            _print_separator(2)
    else:
        print("All tested links returned status 200.")


def _collect_unique_problematic_links(all_status_items: List[Dict]) -> Dict[str, Dict[str, object]]:
    """
    Collect and deduplicate problematic links (status code not 200) across all tabs.

    Args:
        all_status_items (List[Dict]): List of status item dictionaries. Each item
            is expected to have at least a "url" and "status_code", and optionally
            "method_used" and "error".

    Returns:
        Dict[str, Dict[str, object]]: Dictionary mapping normalized URLs to a dictionary
        containing:
            - status_code (object): HTTP status code of the problematic link.
            - method (object): Method used for the request, if available.
            - error (object): Error message or description, if available.
            - display_url (str): Original URL as it appeared in the input list.

    Notes:
        - Only links with a status code other than 200 are included.
        - If multiple entries exist for the same normalized URL, missing details
          (status_code, method, error) are filled from subsequent entries.
        - The function is robust to malformed items and silently skips them.
    """
    info_by_url: Dict[str, Dict[str, object]] = {}

    for it in all_status_items:
        try:
            status_code = it.get("status_code")
            if status_code != 200:
                raw_url = it.get("url")
                if not raw_url:
                    continue
                norm = _normalize_url(raw_url)
                entry = info_by_url.get(norm)
                method = it.get("method_used")
                err = it.get("error")

                if entry is None:
                    info_by_url[norm] = {
                        "status_code": status_code,
                        "method": method,
                        "error": err,
                        "display_url": raw_url,
                    }
                else:
                    # Fill missing details if the first stored entry lacks them
                    if entry.get("status_code") in (None, "") and status_code is not None:
                        entry["status_code"] = status_code
                    if (not entry.get("method")) and method:
                        entry["method"] = method
                    if (not entry.get("error")) and err:
                        entry["error"] = err
        except Exception:
            # Be robust to any malformed item
            continue

    return info_by_url


def _print_unique_problematic_links(info_by_url: Dict[str, Dict[str, object]]) -> None:
    """
    Print a summary of unique links that have issues (HTTP status codes not 200).

    Args:
        info_by_url (Dict[str, Dict[str, object]]): Dictionary mapping normalized URLs
            to dictionaries containing information about problematic links, including:
                - status_code (object): HTTP status code of the link.
                - method (object): HTTP method used, if available.
                - error (object): Error message or description, if available.
                - display_url (str): Original URL as it appeared in the input list.

    Returns:
        None

    Notes:
        - The function prints directly to the console.
        - If there are no problematic links, a message indicating this is displayed.
        - Links are printed sorted by their normalized URL.
    """
    print("\n🧭 Unique links with issues (HTTP status not 200):")
    _print_separator()

    if info_by_url:
        print(f"Total: {len(info_by_url)} unique link(s) with issues")
        for norm_url in sorted(info_by_url.keys()):
            entry = info_by_url[norm_url]
            display_url = entry.get("display_url") or norm_url
            status_code = entry.get("status_code")
            method = entry.get("method")
            err = entry.get("error")
            print(f"  - {display_url} (http status={status_code}, method={method}, error={err})")
    else:
        print("No problematic links found.")


def generate_screen_report(status_dir: str = "link_status",
                           manifest_path: str = "ODM_external_links_manifesto.json") -> None:
    """
    Generate a comprehensive console report of external link status based on a manifest
    and previously recorded status files.

    Args:
        status_dir (str, optional): Path to the directory containing JSON status files
            for each tab. Defaults to "link_status".
        manifest_path (str, optional): Path to the JSON manifest file containing
            expected external links. Defaults to "ODM_external_links_manifesto.json".

    Returns:
        None

    Notes:
        - The function prints directly to the console and does not return any values.
        - If the manifest file does not exist, a message is printed and the function
          exits early.
        - The report includes:
            1. Summary table of links per tab.
            2. Detailed list of missing links.
            3. Detailed list of unexpected links.
            4. Links not working properly (status codes other than 200), grouped
               by status and tab.
            5. Unique problematic links across all tabs.
        - Relies on helper functions: _load_manifest, _expected_urls_by_tab,
          _level_lookup_by_tab, _aggregate_tab_data, _print_summary_table,
          _print_missing_links, _print_unexpected_links, _print_non_working_links,
          _collect_unique_problematic_links, _print_unique_problematic_links,
          _print_separator, and _print_centered.
    """
    status_dir_p = Path(status_dir)
    manifest_p = Path(manifest_path)

    if not manifest_p.exists():
        print(f"[❌] Manifest not found at: {manifest_p}")
        return

    manifest = _load_manifest(manifest_p)
    expected_by_tab = _expected_urls_by_tab(manifest)
    level_lookup = _level_lookup_by_tab(manifest)

    print()
    _print_separator()
    _print_centered("📊 ODM External Links Report")
    _print_separator()

    # Aggregate per-tab data first
    per_tab_data, all_status_items = _aggregate_tab_data(status_dir_p, expected_by_tab)

    # Print all report sections
    _print_summary_table(per_tab_data)
    _print_missing_links(per_tab_data)
    _print_unexpected_links(per_tab_data)
    _print_non_working_links(per_tab_data, level_lookup)

    info_by_url = _collect_unique_problematic_links(all_status_items)
    _print_unique_problematic_links(info_by_url)

    print()


__all__ = [
    "generate_screen_report",
]
