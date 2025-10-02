# -*- coding: utf-8 -*-
"""
Utility functions to clean/filter retrieved external links against the
source-of-truth manifesto (ODM_external_links_manifesto.json).

Goals
- Keep only links that both (a) were retrieved from the website and (b) belong
  to the specified tab according to the manifesto.
- Provide optional finer filtering for the Dimensions tab by level (Policy, Portal, Impact).

Usage examples
--------------
from src.links_cleaner import clean_links_for_tab

retrieved = [
    "https://example.com/a",
    "https://data.public.lu/en/pages/governance/",
]
cleaned = clean_links_for_tab(
    retrieved_links=retrieved,
    tab_name="Country profiles",
    manifest_path="ODM_external_links_manifesto.json",
)

Design notes
- URL normalization is applied before matching: trim spaces, lower-case scheme
  and host, and remove a trailing slash (except if URL is domain-only).
- Functions accept either a loaded manifest dict or a path for convenience.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Union
from urllib.parse import urlsplit, urlunsplit

Manifest = Dict[str, List[Dict[str, str]]]


# -------------------------
# URL normalization helpers
# -------------------------

def _normalize_url(url: str) -> str:
    """Normalize a URL for robust comparison.

    - Strip surrounding spaces
    - Lowercase scheme and netloc (host)
    - Remove redundant trailing slash on path (keep slash if root only)

    This avoids false mismatches due to trivial formatting differences.
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

    # Remove a trailing slash only if not the sole root path
    if path.endswith("/") and path != "/":
        path = path.rstrip("/")

    return urlunsplit((scheme, netloc, path, parts.query, parts.fragment))


# -------------------------
# Manifest loading/indexing
# -------------------------

def _load_manifest_from_path(path: Union[str, Path]) -> Manifest:
    """
    Load and validate the manifest JSON file from the specified path.

    Args:
        path (Union[str, Path]): File path to the manifest JSON file, either as a
            string or Path object.

    Returns:
        Manifest: Dictionary containing manifest data with tab names as keys
            ("Recommendations", "Dimensions", "Country profiles") and lists of
            link entries as values.

    Raises:
        ValueError: If the manifest is not a valid JSON object or is missing
            required tab keys.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Basic shape validation
    if not isinstance(data, dict):
        raise ValueError("Manifest must be a JSON object with top-level keys.")
    for key in ("Recommendations", "Dimensions", "Country profiles"):
        if key not in data:
            raise ValueError(f"Manifest missing required key: {key}")
    return data  # type: ignore[return-value]


def _build_index(manifest: Manifest) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """
    Build lookup indexes from the manifest for efficient URL filtering.

    Args:
        manifest (Manifest): Dictionary containing tab names as keys and lists of
            link entries (with "url" and "level" fields) as values.

    Returns:
        Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]: A tuple containing:
            - tab_index: Mapping of tab name to set of normalized URLs for that tab
            - dimensions_by_level: Mapping of dimension level names (e.g., "Policy",
              "Portal", "Impact") to sets of normalized URLs for that level
    """
    tab_index: Dict[str, Set[str]] = {"Recommendations": set(), "Dimensions": set(), "Country profiles": set()}
    dimensions_by_level: Dict[str, Set[str]] = {}

    for tab_name in ("Recommendations", "Dimensions", "Country profiles"):
        entries = manifest.get(tab_name, [])
        urls = set()
        for entry in entries:
            url = entry.get("url") if isinstance(entry, dict) else None
            if not url:
                continue
            urls.add(_normalize_url(url))

            # Build level index for Dimensions
            if tab_name == "Dimensions":
                level = entry.get("level") if isinstance(entry, dict) else None
                if level:
                    lvl_set = dimensions_by_level.setdefault(level, set())
                    lvl_set.add(_normalize_url(url))
        tab_index[tab_name] = urls

    return tab_index, dimensions_by_level


# -------------------------
# Public API
# -------------------------

def clean_links_for_tab(retrieved_links, tab_name, manifest_or_path= None):
    """Return only links that belong to the given tab per the manifesto.

    Args:
        retrieved_links: Links collected from the website for a tab (raw).
        tab_name: One of "Recommendations", "Dimensions", "Country profiles".
        manifest_or_path: Optional manifest dict or path to ODM_external_links_manifesto.json.
                          If omitted, defaults to a file named ODM_external_links_manifesto.json in repo root.

    Returns:
        A list preserving the order of the first occurrence found in retrieved_links,
        filtered to those present in the manifesto for the requested tab.
    """
    if manifest_or_path is None:
        manifest_or_path = Path("ODM_external_links_manifesto.json")

    manifest: Manifest
    if isinstance(manifest_or_path, (str, Path)):
        manifest = _load_manifest_from_path(manifest_or_path)
    else:
        manifest = manifest_or_path

    tab_index, _ = _build_index(manifest)

    if tab_name not in tab_index:
        raise ValueError(
            f"[❌] Invalid tab_name '{tab_name}'. Expected one of: Recommendations, Dimensions, Country profiles"
        )

    allowed = tab_index[tab_name]

    seen: Set[str] = set()
    result: List[str] = []
    for url in retrieved_links:
        if url is None:
            continue
        nurl = _normalize_url(url)
        if nurl in allowed and nurl not in seen:
            seen.add(nurl)
            result.append(url)  # return as originally retrieved

    return result


def clean_links_for_dimensions(retrieved_links, level, manifest_or_path=None):
    """Return only links that belong to a specific Dimensions level.

    Args:
        retrieved_links: Links collected under Dimensions.
        level: e.g., "Policy", "Portal", "Impact" (case-sensitive as in manifest).
        manifest_or_path: Manifest dict or path.

    Returns:
        Order-preserving filtered list.
    """
    if manifest_or_path is None:
        manifest_or_path = Path("ODM_external_links_manifesto.json")

    manifest: Manifest    # Manifest just says “manifest will be a Manifest-typed object,” aiding static analysis without changing runtime behavior.
    if isinstance(manifest_or_path, (str, Path)):
        manifest = _load_manifest_from_path(manifest_or_path)
    else:
        manifest = manifest_or_path

    _, by_level = _build_index(manifest)
    allowed = by_level.get(level, set())

    seen: Set[str] = set()
    result: List[str] = []
    for url in retrieved_links:
        if url is None:
            continue
        nurl = _normalize_url(url)
        if nurl in allowed and nurl not in seen:
            seen.add(nurl)
            result.append(url)
    return result


__all__ = [
    "clean_links_for_tab",
    "clean_links_for_dimensions",
]
