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
from typing import Dict, Iterable, List, Tuple, Set
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
    with manifest_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # ensure required keys
    for key in ("Recommendations", "Dimensions", "Country profiles"):
        if key not in data:
            raise ValueError(f"Manifest missing required key: {key}")
    return data


def _expected_urls_by_tab(manifest: Dict[str, List[Dict[str, str]]]) -> Dict[str, Set[str]]:
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
    """Build mapping per tab: normalized URL -> level string.

    If an entry has no level, it will not be added to the map (lookups will miss
    and be handled as Unknown later).
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

    match separator_type:
        case 1:
            print("=" * 70)
        case 2:
            print("-" * 70)


def _print_centered(title: str):
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

def generate_screen_report(status_dir: str = "link_status", manifest_path: str = "ODM_external_links_manifesto.json") -> None:
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

    # 1) Total summary for links per tab (table)
    print("\n🔔Summary of links per tab (totals):")
    _print_separator()
    header = f"{'Tab':<20} | {'Expected':>8} | {'Retrieved':>9} | {'Missing':>7} | {'Unexpected':>11} | {'✅ 200 OK':>6} | {'❌ Not 200':>5} | {'% of OK':>5}"
    print(header)
    print("-" * len(header))
    for tab in ("Recommendations", "Dimensions", "Country profiles"):
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

    # 2) Separate detailed lists (not table)
    # Missing links
    print("\n❌ Missing links (expected but not retrieved), by tab:")
    _print_separator()
    had_any = False
    for tab in ("Recommendations", "Dimensions", "Country profiles"):
        missing = per_tab_data.get(tab, {}).get("missing", [])
        if missing:
            had_any = True
            print(f"{tab}: {len(missing)} missing")
            for u in missing:
                print(f"  - {u}")
            # _print_separator()
    if not had_any:
        print("No missing links across tabs.")

    # Unexpected links
    print("\n❌ Not expected but present links (retrieved but not in manifesto), by tab:")
    _print_separator()
    had_any = False
    for tab in ("Recommendations", "Dimensions", "Country profiles"):
        unexpected = per_tab_data.get(tab, {}).get("unexpected", [])
        if unexpected:
            had_any = True
            print(f"{tab}: {len(unexpected)} unexpected")
            for u in unexpected:
                print(f"  - {u}")
    if not had_any:
        print("No unexpected links across tabs.")

    # Not working links (HTTP status != 200)
    print("\n️‍⛓️‍💥 Links not working properly (status other than 200):")
    _print_separator()

    # Group non-200 links first by HTTP status, then by tab
    non_working_by_status: Dict[object, Dict[str, List[Dict]]] = {}
    for tab, filename in TAB_TO_STATUS_FILE.items():
        items = per_tab_data.get(tab, {}).get("items", [])
        for it in items:
            status_code = it.get("status_code")
            if status_code != 200:
                bucket = non_working_by_status.setdefault(status_code, {})
                bucket.setdefault(tab, []).append(it)

    if non_working_by_status:
        # Sort statuses: numeric first ascending, then non-numeric/string-like
        def _status_sort_key(k):
            return (0, k) if isinstance(k, int) else (1, str(k))

        for status in sorted(non_working_by_status.keys(), key=_status_sort_key):
            status_icon = _status_label(status)
            print(f"Status {status}{status_icon}:")
            tabs_map = non_working_by_status[status]
            # Print tabs in a consistent order
            for tab in ("Recommendations", "Dimensions", "Country profiles"):
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

    # _print_separator()
    print()


__all__ = [
    "generate_screen_report",
]
