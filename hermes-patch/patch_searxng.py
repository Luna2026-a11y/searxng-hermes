#!/usr/bin/env python3
"""
Re-apply SearXNG patch to Hermes web_tools.py after an update.

Run this script after each `hermes update` to restore the SearXNG backend.
Usage: python3 ~/.hermes/scripts/patch_searxng.py
"""

import sys
import os

WEB_TOOLS_PATH = os.path.expanduser("~/.hermes/hermes-agent/tools/web_tools.py")

def check_already_patched(content: str) -> bool:
    """Check if SearXNG is already integrated."""
    return '"searxng"' in content and "_searxng_search" in content

def patch_backend_detection(content: str) -> str:
    """Add searxng to _get_backend() valid backends."""
    # Already has searxng in valid backends?
    if '"searxng")' in content or '"searxng",)' in content:
        # Check the tuple
        old = 'if configured in ("parallel", "firecrawl", "tavily", "exa"):'
        new = 'if configured in ("parallel", "firecrawl", "tavily", "exa", "searxng"):'
        content = content.replace(old, new)
    
    # Add auto-detection for SearXNG (before firecrawl fallback)
    autodetect_marker = '    # SearXNG: auto-detect from env or config (no API key needed)'
    if autodetect_marker not in content:
        old = '    return "firecrawl"  # default (backward compat)'
        new = '''    # SearXNG: auto-detect from env or config (no API key needed)
    searxng_url = os.getenv("SEARXNG_URL") or _load_web_config().get("searxng_url")
    if searxng_url:
        return "searxng"

    return "firecrawl"  # default (backward compat)'''
        content = content.replace(old, new)
    
    return content

def patch_backend_available(content: str) -> str:
    """Add searxng to _is_backend_available()."""
    if 'backend == "searxng":' in content and '_is_backend_available' not in content:
        return content  # Already patched
    
    # Add before "return False"
    old = '    return False\n\n\n# ─── Firecrawl Client'
    new = '''    if backend == "searxng":
        return bool(os.getenv("SEARXNG_URL") or _load_web_config().get("searxng_url"))
    return False


# ─── Firecrawl Client'''
    content = content.replace(old, new)
    return content

def add_searxng_functions(content: str) -> str:
    """Add SearXNG client functions if not present."""
    if "_searxng_search" in content:
        return content  # Already present
    
    searxng_code = '''
# ─── SearXNG Client ──────────────────────────────────────────────────────────

def _get_searxng_url() -> str:
    """Return the SearXNG instance URL from env or config."""
    url = os.getenv("SEARXNG_URL") or _load_web_config().get("searxng_url") or ""
    return url.strip().rstrip("/")


def _searxng_search(query: str, limit: int = 5) -> dict:
    """Search via SearXNG JSON API. Returns normalized web search results."""
    import urllib.parse
    searxng_url = _get_searxng_url()
    if not searxng_url:
        raise ValueError("SEARXNG_URL not configured. Set SEARXNG_URL env var or web.searxng_url in config.yaml")

    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "language": "fr",
    })
    search_url = f"{searxng_url}/search?{params}"

    ssl_verify = not _has_env("SEARXNG_SSL_VERIFY") or os.getenv("SEARXNG_SSL_VERIFY", "").lower() not in ("false", "0", "no")

    logger.info("SearXNG search: '%s' (limit: %d)", query, limit)
    response = httpx.get(search_url, timeout=30, verify=ssl_verify)
    response.raise_for_status()
    data = response.json()

    web_results = []
    for i, item in enumerate(data.get("results", [])[:limit]):
        web_results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("description") or item.get("content", ""),
            "position": i + 1,
        })

    return {"success": True, "data": {"web": web_results}}


def _searxng_extract(urls: List[str]) -> List[Dict[str, Any]]:
    """Extract content from URLs via SearXNG (uses direct HTTP fetch + HTML parsing)."""
    import re as _re
    import html as _html_mod

    documents: List[Dict[str, Any]] = []
    for url in urls:
        try:
            ssl_verify = not _has_env("SEARXNG_SSL_VERIFY") or os.getenv("SEARXNG_SSL_VERIFY", "").lower() not in ("false", "0", "no")

            resp = httpx.get(url, timeout=30, verify=ssl_verify, follow_redirects=True)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            if "html" not in content_type and "text" not in content_type:
                documents.append({
                    "url": url,
                    "title": "",
                    "content": "[Unsupported content type: {}]".format(content_type),
                    "raw_content": resp.text[:500],
                    "metadata": {"sourceURL": url},
                })
                continue

            raw_html = resp.text

            # Remove scripts, styles, nav, footer, header
            raw_html = _re.sub(r'<script[^>]*>.*?</script>', '', raw_html, flags=_re.DOTALL | _re.IGNORECASE)
            raw_html = _re.sub(r'<style[^>]*>.*?</style>', '', raw_html, flags=_re.DOTALL | _re.IGNORECASE)
            raw_html = _re.sub(r'<nav[^>]*>.*?</nav>', '', raw_html, flags=_re.DOTALL | _re.IGNORECASE)
            raw_html = _re.sub(r'<footer[^>]*>.*?</footer>', '', raw_html, flags=_re.DOTALL | _re.IGNORECASE)
            raw_html = _re.sub(r'<header[^>]*>.*?</header>', '', raw_html, flags=_re.DOTALL | _re.IGNORECASE)

            # Extract title
            title_match = _re.search(r'<title[^>]*>(.*?)</title>', raw_html, _re.DOTALL | _re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else ""

            # Convert HTML to text
            text = raw_html
            text = _re.sub(r'<(br|p|div|h[1-6]|li|tr)[^>]*>', '\n', text, flags=_re.IGNORECASE)
            text = _re.sub(r'<[^>]+>', '', text)
            text = _html_mod.unescape(text)
            text = _re.sub(r'\n\s*\n', '\n\n', text)
            text = _re.sub(r'[ \t]+', ' ', text)
            text = text.strip()

            # Truncate very long content
            if len(text) > 50000:
                text = text[:50000] + "\n... [truncated]"

            documents.append({
                "url": url,
                "title": title,
                "content": text,
                "raw_content": text,
                "metadata": {"sourceURL": url, "title": title},
            })
        except Exception as e:
            documents.append({
                "url": url,
                "title": "",
                "content": "",
                "raw_content": "",
                "error": str(e),
                "metadata": {"sourceURL": url},
            })

    return documents

'''
    # Insert before _firecrawl_backend_help_suffix
    marker = "def _firecrawl_backend_help_suffix"
    if marker in content:
        idx = content.find(marker)
        content = content[:idx] + searxng_code + content[idx:]
    
    return content

def patch_search_dispatch(content: str) -> str:
    """Add SearXNG dispatch in web_search_tool()."""
    if 'if backend == "searxng":\n            response_data = _searxng_search' in content:
        return content
    
    old = '''        # Dispatch to the configured backend
        backend = _get_backend()
        if backend == "parallel":'''
    new = '''        # Dispatch to the configured backend
        backend = _get_backend()
        if backend == "searxng":
            response_data = _searxng_search(query, limit)
            debug_call_data["results_count"] = len(response_data.get("data", {}).get("web", []))
            result_json = json.dumps(response_data, indent=2, ensure_ascii=False)
            debug_call_data["final_response_size"] = len(result_json)
            _debug.log_call("web_search_tool", debug_call_data)
            _debug.save()
            return result_json

        if backend == "parallel":'''
    content = content.replace(old, new)
    return content

def patch_extract_dispatch(content: str) -> str:
    """Add SearXNG dispatch in web_extract_tool()."""
    if 'if backend == "searxng":\n                logger.info("SearXNG extract' in content:
        return content
    
    old = '''            backend = _get_backend()

            if backend == "parallel":'''
    new = '''            backend = _get_backend()

            if backend == "searxng":
                logger.info("SearXNG extract: %d URL(s)", len(safe_urls))
                results = _searxng_extract(safe_urls)
            elif backend == "parallel":'''
    content = content.replace(old, new)
    return content

def main():
    print(f"Patching {WEB_TOOLS_PATH}...")
    
    if not os.path.exists(WEB_TOOLS_PATH):
        print(f"ERROR: {WEB_TOOLS_PATH} not found!")
        sys.exit(1)
    
    with open(WEB_TOOLS_PATH, 'r') as f:
        content = f.read()
    
    if check_already_patched(content):
        print("SearXNG already patched. Verifying...")
        # Still apply patches in case partial
    else:
        print("Applying SearXNG patch...")
    
    original = content
    content = patch_backend_detection(content)
    content = patch_backend_available(content)
    content = add_searxng_functions(content)
    content = patch_search_dispatch(content)
    content = patch_extract_dispatch(content)
    
    if content == original:
        print("No changes needed - all patches already applied.")
        return
    
    with open(WEB_TOOLS_PATH, 'w') as f:
        f.write(content)
    
    print("SUCCESS: SearXNG patch applied!")
    print()
    print("To activate, make sure your ~/.hermes/config.yaml has:")
    print("  web:")
    print("    backend: searxng")
    print("    searxng_url: https://searx.portail.namel.fr")

if __name__ == "__main__":
    main()