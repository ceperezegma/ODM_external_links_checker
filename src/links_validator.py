# -*- coding: utf-8 -*-
"""
HTTP status checker utilities for external links.

Focus:
- Test HTTP status for each retrieved external link.
- Save results in a structured JSON format alongside the tested link.

Design:
- Try a HEAD request first for speed; if it fails or returns 405/400-range atypicals, fallback to GET.
- Follow redirects and record the final URL.
- Handle timeouts, SSL, and network errors gracefully.
- Support concurrency with ThreadPoolExecutor for performance.

Public API:
- check_links_status(links, max_workers=12, timeout=10, verify_ssl=True) -> List[Dict]
- save_statuses(statuses, output_path) -> None
- check_and_save_link_statuses_by_tab(links_by_tab, output_dir, ...) -> Dict[tab, output_file]
"""
from __future__ import annotations

import json
import ssl
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# -----------------------------
# Core single-link status check
# -----------------------------

def _now_iso() -> str:
    """
    Get the current UTC timestamp in ISO 8601 format.

    Args:
        None

    Returns:
        str: Current UTC datetime as an ISO 8601 formatted string.
    """
    return datetime.now(timezone.utc).isoformat()


def _build_ssl_context(verify_ssl: bool) -> ssl.SSLContext:
    """
    Create an SSL context with optional certificate verification.

    Args:
        verify_ssl (bool): Whether to verify SSL certificates. If True, creates
            a default context with standard certificate verification. If False,
            disables hostname checking and certificate verification.

    Returns:
        ssl.SSLContext: Configured SSL context for HTTPS requests.
    """
    if verify_ssl:
        return ssl.create_default_context()
    # Unverified (not recommended for production, but useful if needed)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _request(url: str, method: str, timeout: int, ctx: ssl.SSLContext, user_agent: str) -> Tuple[int, str, str]:
    """
    Perform a single HTTP/HTTPS request and return response details.

    Args:
        url (str): Target URL to request.
        method (str): HTTP method to use (e.g., "HEAD", "GET").
        timeout (int): Request timeout in seconds.
        ctx (ssl.SSLContext): SSL context for HTTPS requests.
        user_agent (str): User-Agent header value to send with the request.

    Returns:
        Tuple[int, str, str]: A tuple containing:
            - status_code: HTTP status code (int)
            - final_url: Final URL after following redirects (str)
            - reason: HTTP status reason phrase (str)
    """

    headers = {"User-Agent": user_agent, "Accept": "*/*"}
    req = Request(url=url, method=method, headers=headers)
    start = time.perf_counter()
    try:
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            # urllib follows redirects; geturl() returns the final URL
            status = getattr(resp, "status", 200)
            reason = getattr(resp, "reason", "OK")
            final_url = resp.geturl()
            _ = resp.read(0)  # avoid downloading body for HEAD/GET minimal
    except HTTPError as e:
        # HTTPError is both an exception and file-like response. It contains status.
        status = getattr(e, "code", None) or 0
        reason = getattr(e, "reason", str(e)) or "HTTPError"
        final_url = getattr(e, "url", url) or url
    end = time.perf_counter()
    # Return status, final_url, and reason. Elapsed will be measured outside.
    return status, final_url, reason


def check_link(url: str, timeout: int = 10, verify_ssl: bool = True, user_agent: str = "Mozilla/5.0 (compatible; ODM-LinkChecker/1.0)") -> Dict:
    """
    Check the HTTP status of a single link with automatic fallback from HEAD to GET.

    Args:
        url (str): The URL to check.
        timeout (int, optional): Request timeout in seconds. Defaults to 10.
        verify_ssl (bool, optional): Whether to verify SSL certificates. Defaults to True.
        user_agent (str, optional): User-Agent header value. Defaults to "Mozilla/5.0 (compatible; ODM-LinkChecker/1.0)".

    Returns:
        Dict: Dictionary containing link check results with keys:
            - url: Original URL checked
            - final_url: URL after following redirects
            - status_code: HTTP status code (int or None if error)
            - ok: Boolean indicating if status is 200-399
            - method_used: HTTP method used ('HEAD' or 'GET')
            - error: Error message (str or None if successful)
            - elapsed_ms: Elapsed time in milliseconds
            - checked_at: ISO 8601 UTC timestamp of check
    """
    checked_at = _now_iso()
    ctx = _build_ssl_context(verify_ssl)

    # Try HEAD first
    start = time.perf_counter()
    try:
        status, final_url, reason = _request(url, "HEAD", timeout, ctx, user_agent)
        method_used = "HEAD"
        error = None
        # Some servers return 405/403 to HEAD even though GET works; fallback if so or status < 200
        if status in (400, 401, 402, 403, 404, 405) or status == 0:
            # Fallback to GET
            status, final_url, reason = _request(url, "GET", timeout, ctx, user_agent)
            method_used = "GET"
    except URLError as e:
        # Network-level error; try GET as fallback
        try:
            status, final_url, reason = _request(url, "GET", timeout, ctx, user_agent)
            method_used = "GET"
            error = None
        except Exception as e2:
            end = time.perf_counter()
            return {
                "url": url,
                "final_url": url,
                "status_code": None,
                "ok": False,
                "method_used": "HEAD",
                "error": f"{type(e2).__name__}: {e2}",
                "elapsed_ms": (end - start) * 1000.0,
                "checked_at": checked_at,
            }
    except Exception as e:
        end = time.perf_counter()
        return {
            "url": url,
            "final_url": url,
            "status_code": None,
            "ok": False,
            "method_used": "HEAD",
            "error": f"{type(e).__name__}: {e}",
            "elapsed_ms": (end - start) * 1000.0,
            "checked_at": checked_at,
        }

    end = time.perf_counter()
    ok = 200 <= (status or 0) < 400
    return {
        "url": url,
        "final_url": final_url,
        "status_code": int(status) if status is not None else None,
        "ok": bool(ok),
        "method_used": method_used,
        "error": None,
        "elapsed_ms": (end - start) * 1000.0,
        "checked_at": checked_at,
    }


# ---------------------------------
# Batch checking and JSON persistence
# ---------------------------------

def check_links_status(links: Iterable[str], max_workers: int = 12, timeout: int = 10, verify_ssl: bool = True) -> List[Dict]:
    """
    Check HTTP status of multiple links concurrently with deduplication.

    Args:
        links (Iterable[str]): Collection of URLs to check.
        max_workers (int, optional): Maximum number of concurrent worker threads.
            Defaults to 12.
        timeout (int, optional): Request timeout in seconds for each link.
            Defaults to 10.
        verify_ssl (bool, optional): Whether to verify SSL certificates.
            Defaults to True.

    Returns:
        List[Dict]: List of dictionaries, each containing check results for a link
            with the same structure as returned by check_link().
    """

    # Deduplicate while preserving order
    seen = set()
    deduped: List[str] = []
    for u in links:
        if not u:
            continue
        if u not in seen:
            seen.add(u)
            deduped.append(u)

    results: List[Dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(check_link, url=u, timeout=timeout, verify_ssl=verify_ssl): u for u in deduped}
        for fut in as_completed(future_map):
            try:
                results.append(fut.result())
            except Exception as e:
                u = future_map[fut]
                results.append({
                    "url": u,
                    "final_url": u,
                    "status_code": None,
                    "ok": False,
                    "method_used": None,
                    "error": f"{type(e).__name__}: {e}",
                    "elapsed_ms": None,
                    "checked_at": _now_iso(),
                })
    return results


def save_statuses(statuses: List[Dict], output_path: Path | str) -> None:
    """
    Save link check statuses to a JSON file.

    Args:
        statuses (List[Dict]): List of status dictionaries to save, each containing
            link check results from check_link() or check_links_status().
        output_path (Path | str): File path where the JSON file will be saved.
            Parent directories will be created if they don't exist.

    Returns:
        None
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(statuses, f, ensure_ascii=False, indent=2)


def check_and_save_link_statuses_by_tab(
        links_by_tab: Dict[str, Iterable[str]],
        output_dir: Path | str = "link_status",
        max_workers: int = 12,
        timeout: int = 10,
        verify_ssl: bool = True
) -> Dict[str, str]:
    """Check link statuses per tab and save separate JSON files.

    Args:
        links_by_tab: mapping of tab key -> list of links. Keys are user-defined labels.
        output_dir: directory where status files will be written.

    Returns:
        Mapping of tab key -> output file path (str).
    """
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)

    outputs: Dict[str, str] = {}
    for tab_key, links in links_by_tab.items():
        statuses = check_links_status(links, max_workers=max_workers, timeout=timeout, verify_ssl=verify_ssl)
        out_path = base / f"{tab_key}_link_status.json"
        save_statuses(statuses, out_path)
        outputs[tab_key] = str(out_path)
    return outputs


__all__ = [
    "check_link",
    "check_links_status",
    "save_statuses",
    "check_and_save_link_statuses_by_tab",
]
