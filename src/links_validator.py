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
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# -----------------------------
# Core single-link status check
# -----------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_ssl_context(verify_ssl: bool) -> ssl.SSLContext:
    if verify_ssl:
        return ssl.create_default_context()
    # Unverified (not recommended for production, but useful if needed)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _request(url: str, method: str, timeout: int, ctx: ssl.SSLContext, user_agent: str) -> Tuple[int, str, str]:
    """Perform a single HTTP(S) request and return (status_code, final_url, reason).

    Follows redirects automatically via urllib.
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
    """Check a single link with HEAD then GET fallback.

    Returns a dict with:
    - url: original URL
    - final_url: URL after redirects (if any)
    - status_code: int or None
    - ok: bool (True if 200-399)
    - method_used: 'HEAD' or 'GET'
    - error: str or None
    - elapsed_ms: float
    - checked_at: ISO8601 UTC timestamp
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
    """Check a collection of links concurrently and return the structured results list."""
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
    """Save statuses to a JSON file (list of objects)."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(statuses, f, ensure_ascii=False, indent=2)


def check_and_save_link_statuses_by_tab(
    links_by_tab: Dict[str, Iterable[str]],
    output_dir: Path | str = "link_status",
    max_workers: int = 12,
    timeout: int = 10,
    verify_ssl: bool = True,
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
