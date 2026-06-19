#!/usr/bin/env python3
# Adapted from knowledge-catalog/okf/src/enrichment_agent/web/fetcher.py +
# tools/web_tools.py  —  Apache-2.0 GoogleCloudPlatform/knowledge-catalog
"""OKF budget-capped web fetcher.

Usage:
  # Register seed URL (depth 0) and create/update state file:
  okf_fetch.py <url> --state <f.json> --seed [--max-pages N] [--max-depth N]
                     [--allowed-host H]... [--allowed-path-prefix P]...
                     [--denied-path-substring S]...

  # Fetch a URL (must have been registered via a seed or a prior fetch):
  okf_fetch.py <url> --state <f.json>

The state file persists budget counters, visited URLs, and depth tracking across
multiple calls (simulates the in-memory WebState in the upstream ADK agent).

Output JSON on stdout:
  success: {url, title, markdown, links, fetched_count, max_pages_budget, depth, max_depth}
  failure: {error, url, fetched_count, max_pages_budget}

Requires: markdownify  (pip install markdownify)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen

_USER_AGENT = "okf-enrichment-agent/0.1 (+https://github.com/GoogleCloudPlatform/knowledge-catalog)"
_MAX_MARKDOWN_BYTES = 40 * 1024
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_HREF_RE = re.compile(r"""href\s*=\s*["']([^"'#\s]+)["']""", re.IGNORECASE)


def _load_state(state_path: Path) -> dict:
    if state_path.exists():
        return json.loads(state_path.read_text(encoding="utf-8"))
    return {
        "allowed_hosts": None,
        "allowed_path_prefixes": None,
        "denied_path_substrings": [],
        "max_pages": 100,
        "max_depth": 2,
        "fetched_count": 0,
        "visited": [],
        "url_depth": {},
    }


def _save_state(state_path: Path, state: dict) -> None:
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _extract_title(html: str) -> str | None:
    m = _TITLE_RE.search(html)
    if not m:
        return None
    raw = re.sub(r"\s+", " ", m.group(1)).strip()
    return raw or None


def _extract_links(html: str, base_url: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in _HREF_RE.finditer(html):
        href = match.group(1).strip()
        if not href:
            continue
        scheme = urlparse(href).scheme.lower()
        if scheme and scheme not in ("http", "https", ""):
            continue
        absolute, _ = urldefrag(urljoin(base_url, href))
        if absolute in seen:
            continue
        seen.add(absolute)
        out.append(absolute)
    return out


def _truncate(text: str, max_bytes: int) -> str:
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore") + "\n\n[...truncated...]"


def _fetch_and_parse(url: str) -> tuple[str | None, str, list[str]]:
    """Returns (title, markdown, links)."""
    try:
        from markdownify import markdownify
    except ImportError:
        raise ImportError("markdownify is required: pip install markdownify")

    req = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "text/html,*/*;q=0.5"})
    try:
        with urlopen(req, timeout=10.0) as resp:
            content_type = resp.headers.get("Content-Type", "")
            final_url = resp.geturl() or url
            body_bytes = resp.read()
    except Exception as e:
        raise OSError(str(e)) from e

    if "html" not in content_type.lower():
        raise OSError(f"non-HTML content-type: {content_type or 'unknown'}")

    charset = "utf-8"
    if "charset=" in content_type.lower():
        charset = content_type.lower().split("charset=", 1)[1].split(";", 1)[0].strip() or "utf-8"
    try:
        html = body_bytes.decode(charset, errors="replace")
    except LookupError:
        html = body_bytes.decode("utf-8", errors="replace")

    title = _extract_title(html)
    links = _extract_links(html, final_url)
    markdown = markdownify(html, heading_style="ATX")
    markdown = _truncate(markdown, _MAX_MARKDOWN_BYTES)
    return title, markdown, links


def main() -> int:
    p = argparse.ArgumentParser(prog="okf_fetch.py")
    p.add_argument("url")
    p.add_argument("--state", required=True, metavar="FILE", help="JSON state file path.")
    p.add_argument("--seed", action="store_true", help="Register URL as depth-0 seed (init/update state).")
    p.add_argument("--max-pages", type=int, default=None)
    p.add_argument("--max-depth", type=int, default=None)
    p.add_argument("--allowed-host", action="append", default=None, metavar="HOST")
    p.add_argument("--allowed-path-prefix", action="append", default=None, metavar="PREFIX")
    p.add_argument("--denied-path-substring", action="append", default=None, metavar="SUB")
    args = p.parse_args()

    state_path = Path(args.state)
    state = _load_state(state_path)

    # Apply CLI overrides (only when initializing or when flags provided)
    if args.max_pages is not None:
        state["max_pages"] = args.max_pages
    if args.max_depth is not None:
        state["max_depth"] = args.max_depth
    if args.allowed_host is not None:
        existing = set(state.get("allowed_hosts") or [])
        existing.update(args.allowed_host)
        state["allowed_hosts"] = sorted(existing)
    if args.allowed_path_prefix is not None:
        existing = set(state.get("allowed_path_prefixes") or [])
        existing.update(args.allowed_path_prefix)
        state["allowed_path_prefixes"] = sorted(existing)
    if args.denied_path_substring is not None:
        existing = set(state.get("denied_path_substrings") or [])
        existing.update(args.denied_path_substring)
        state["denied_path_substrings"] = sorted(existing)

    if args.seed:
        state["url_depth"][args.url] = 0
        # Infer allowed host from seed if not already set
        if state.get("allowed_hosts") is None:
            host = urlparse(args.url).netloc
            if host:
                state["allowed_hosts"] = [host]
        _save_state(state_path, state)

    def _out(obj: dict) -> int:
        json.dump(obj, sys.stdout)
        print()
        return 0

    visited = set(state.get("visited") or [])
    url_depth: dict[str, int] = state.get("url_depth") or {}
    allowed_hosts = state.get("allowed_hosts")
    allowed_prefixes = state.get("allowed_path_prefixes")
    denied_subs = state.get("denied_path_substrings") or []
    max_pages = state.get("max_pages", 100)
    max_depth = state.get("max_depth", 2)
    fetched_count = state.get("fetched_count", 0)

    parsed = urlparse(args.url)

    def _reject(reason: str) -> int:
        return _out({"error": reason, "url": args.url,
                     "fetched_count": fetched_count, "max_pages_budget": max_pages})

    if parsed.scheme not in ("http", "https"):
        return _reject(f"unsupported scheme: {parsed.scheme or '(none)'}")
    if not parsed.netloc:
        return _reject("missing host in URL")
    if allowed_hosts and parsed.netloc not in allowed_hosts:
        return _reject(
            f"host not in allowed list: {parsed.netloc} (allowed: {sorted(allowed_hosts)})"
        )
    path = parsed.path or "/"
    if allowed_prefixes and not any(path.startswith(pr) for pr in allowed_prefixes):
        return _reject(f"path not in allowed prefixes: {path}")
    for bad in denied_subs:
        if bad and bad in path:
            return _reject(f"path matches denied substring: {bad!r}")
    if args.url in visited:
        return _reject("already fetched in this session")
    if fetched_count >= max_pages:
        return _reject("max_pages reached")

    depth = url_depth.get(args.url)
    if depth is None:
        return _reject("URL not reachable from a seed within the crawl graph")
    if depth > max_depth:
        return _reject(f"depth {depth} exceeds max_depth {max_depth}")

    # Perform the fetch
    try:
        title, markdown, links = _fetch_and_parse(args.url)
    except (OSError, ImportError) as e:
        return _reject(f"fetch failed: {e}")

    # Update state
    visited.add(args.url)
    fetched_count += 1
    child_depth = depth + 1
    for link in links:
        url_depth.setdefault(link, child_depth)

    state.update({
        "fetched_count": fetched_count,
        "visited": sorted(visited),
        "url_depth": url_depth,
    })
    _save_state(state_path, state)

    return _out({
        "url": args.url,
        "title": title,
        "markdown": markdown,
        "links": links,
        "fetched_count": fetched_count,
        "max_pages_budget": max_pages,
        "depth": depth,
        "max_depth": max_depth,
    })


if __name__ == "__main__":
    sys.exit(main())
