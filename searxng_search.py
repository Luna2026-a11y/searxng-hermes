#!/usr/bin/env python3
"""
SearXNG Backend for Hermes Agent — Optimisé tokens
Recherche web + extraction via instance SearXNG auto-hébergée.
Zéro API key, stdlib uniquement, outputs compacts.
"""

import os
import sys
import json
import re
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError

# ─── Configuration ────────────────────────────────────────────────────────────
SEARXNG_URL = os.environ.get("SEARXNG_URL", "").rstrip("/")
SEARXNG_TIMEOUT = int(os.environ.get("SEARXNG_TIMEOUT", "15"))
SEARXNG_LANGUAGE = os.environ.get("SEARXNG_LANGUAGE", "fr")
SEARXNG_SAFESARCH = int(os.environ.get("SEARXNG_SAFESARCH", "1"))
SEARXNG_MAX_RESULTS = int(os.environ.get("SEARXNG_MAX_RESULTS", "5"))
SEARXNG_EXTRACT_MAX = int(os.environ.get("SEARXNG_EXTRACT_MAX", "5000"))
SEARXNG_EXTRACT_TIMEOUT = int(os.environ.get("SEARXNG_EXTRACT_TIMEOUT", "20"))


class SearXNGClient:
    """Client SearXNG optimisé pour Hermes Agent — outputs compacts, minimum tokens."""

    def __init__(self, url=None, language=None, timeout=None):
        self.url = url or SEARXNG_URL
        self.language = language or SEARXNG_LANGUAGE
        self.timeout = timeout or SEARXNG_TIMEOUT
        if not self.url:
            raise ValueError(
                "SEARXNG_URL non configuré. "
                "Définissez SEARXNG_URL ou passez url= au constructeur."
            )

    # ─── Recherche ────────────────────────────────────────────────────────────
    def search(self, query, limit=None, language=None, time_range=None, categories="general"):
        """
        Recherche SearXNG — retourne un dict compact optimisé pour LLM.

        Format de retour (compatible Hermes web_search_tool) :
        {
            "success": True,
            "data": {
                "web": [
                    {"title": "...", "url": "...", "description": "...", "position": 1},
                    ...
                ]
            }
        }
        """
        limit = limit or SEARXNG_MAX_RESULTS
        language = language or self.language

        params = {
            "q": query,
            "format": "json",
            "language": language,
            "safesearch": SEARXNG_SAFESARCH,
            "categories": categories,
        }
        if time_range:
            params["time_range"] = time_range

        url = f"{self.url}/search?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Hermes-SearXNG/1.0")
        req.add_header("Accept", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            raise Exception(f"SearXNG HTTP {e.code}: {e.reason}")
        except URLError as e:
            raise Exception(f"SearXNG connexion: {e.reason}")
        except json.JSONDecodeError:
            raise Exception("SearXNG: réponse JSON invalide")

        web_results = []
        for i, r in enumerate(data.get("results", [])[:limit]):
            # Compact : on garde seulement ce qui est utile au LLM
            entry = {
                "title": r.get("title", "").strip(),
                "url": r.get("url", ""),
                "description": r.get("content", "").strip()[:200],  # Troncature anti-token
                "position": i + 1,
            }
            # Skip les résultats vides
            if entry["url"]:
                web_results.append(entry)

        return {"success": True, "data": {"web": web_results}}

    # ─── Extraction ───────────────────────────────────────────────────────────
    def extract(self, urls, max_length=None):
        """
        Extraction de contenu web — HTML nettoyé en texte compact.

        Pas de依赖 externe (no beautifulsoup, no readability, no firecrawl).
        Utilise urllib + regex pour un nettoyage basique mais efficace.

        Format de retour (compatible Hermes web_extract_tool) :
        {
            "success": True,
            "pages": [
                {"url": "...", "title": "...", "content": "...", "success": True},
                ...
            ]
        }
        """
        max_length = max_length or SEARXNG_EXTRACT_MAX
        if isinstance(urls, str):
            urls = [urls]

        pages = []
        for target_url in urls:
            try:
                req = urllib.request.Request(target_url)
                req.add_header("User-Agent",
                    "Mozilla/5.0 (compatible; Hermes-SearXNG/1.0)")
                with urllib.request.urlopen(req, timeout=SEARXNG_EXTRACT_TIMEOUT) as resp:
                    html = resp.read().decode("utf-8", errors="replace")

                # Extraction du titre
                title_match = re.search(
                    r"<title[^>]*>(.*?)</title>", html,
                    re.DOTALL | re.IGNORECASE
                )
                title = title_match.group(1).strip() if title_match else target_url

                # Nettoyage HTML → texte
                text = html
                # Supprimer scripts, styles, nav, footer, header
                for tag in ("script", "style", "nav", "footer", "header", "aside", "noscript"):
                    text = re.sub(
                        rf"<{tag}[^>]*>.*?</{tag}>", "", text,
                        flags=re.DOTALL | re.IGNORECASE
                    )
                # Supprimer balises HTML
                text = re.sub(r"<[^>]+>", " ", text)
                # Nettoyer les entités HTML courantes
                text = (text.replace("&amp;", "&").replace("&lt;", "<")
                            .replace("&gt;", ">").replace("&quot;", '"')
                            .replace("&#39;", "'").replace("&nbsp;", " "))
                # Nettoyer les espaces
                text = re.sub(r"\s+", " ", text).strip()
                # Troncature intelligente : on garde le début (intro) + un peu de milieu
                if len(text) > max_length:
                    half = max_length // 2
                    text = text[:half] + "\n\n[...contenu tronqué...]\n\n" + text[-half:]

                pages.append({
                    "url": target_url,
                    "title": title,
                    "content": text,
                    "success": True,
                })
            except Exception as e:
                pages.append({
                    "url": target_url,
                    "error": str(e)[:200],
                    "success": False,
                })

        return {"success": any(p.get("success") for p in pages), "pages": pages}

    # ─── Format CLI ───────────────────────────────────────────────────────────
    def format_search(self, results):
        """Format lisible pour le CLI."""
        if not results.get("data", {}).get("web"):
            return "Aucun résultat trouvé."

        lines = [f"🔍 {len(results['data']['web'])} résultat(s)\n"]
        for r in results["data"]["web"]:
            lines.append(f"{r['position']}. **{r['title']}**")
            lines.append(f"   {r['url']}")
            if r.get("description"):
                lines.append(f"   {r['description']}")
            lines.append("")
        return "\n".join(lines)

    def format_extract(self, result):
        """Format lisible pour extraction CLI."""
        lines = []
        for page in result.get("pages", []):
            if page.get("success"):
                lines.append(f"# {page['title']}\n")
                lines.append(page["content"])
            else:
                lines.append(f"❌ {page['url']}: {page.get('error', 'Unknown')}")
            lines.append("\n---\n")
        return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="SearXNG Backend pour Hermes Agent — Optimisé tokens"
    )
    parser.add_argument("query", nargs="?", help="Requête de recherche")
    parser.add_argument("--extract", nargs="+", metavar="URL",
                        help="Extraire le contenu d'URL(s)")
    parser.add_argument("--language", default="fr", help="Code langue (défaut: fr)")
    parser.add_argument("--time-range", choices=["day", "week", "month", "year"],
                        help="Filtrer par période")
    parser.add_argument("--limit", type=int, default=5, help="Nombre max de résultats")
    parser.add_argument("--categories", default="general",
                        help="Catégories: general, images, videos, etc.")
    parser.add_argument("--json", action="store_true",
                        help="Sortie JSON brute (pour intégration Hermes)")
    parser.add_argument("--url", help="URL instance SearXNG (override SEARXNG_URL)")

    args = parser.parse_args()

    if not args.query and not args.extract:
        parser.error("Spécifiez une requête ou --extract URL")

    client = SearXNGClient(url=args.url)

    if args.extract:
        result = client.extract(args.extract)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(client.format_extract(result))
    else:
        result = client.search(
            args.query,
            limit=args.limit,
            language=args.language,
            time_range=args.time_range,
            categories=args.categories,
        )
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(client.format_search(result))


if __name__ == "__main__":
    main()