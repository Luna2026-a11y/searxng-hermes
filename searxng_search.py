#!/usr/bin/env python3
"""
SearXNG Backend for Hermes Agent — Optimisé tokens
Recherche web + extraction via instance SearXNG auto-hébergée.
Zéro API key, stdlib uniquement, outputs compacts.

Formats de recherche:
  compact  — titre + URL + description courte (défaut, ~327 tokens/5 résultats)
  rich     — + date, source, score, thumbnail (~550 tokens/5 résultats)
"""

import os
import sys
import json
import re
import urllib.request
import urllib.parse
import html as html_mod
from urllib.error import URLError, HTTPError

# ─── Configuration ────────────────────────────────────────────────────────────
SEARXNG_URL = os.environ.get("SEARXNG_URL", "").rstrip("/")
SEARXNG_TIMEOUT = int(os.environ.get("SEARXNG_TIMEOUT", "15"))
SEARXNG_LANGUAGE = os.environ.get("SEARXNG_LANGUAGE", "fr")
SEARXNG_SAFESEARCH = int(os.environ.get("SEARXNG_SAFESEARCH", "1"))
SEARXNG_MAX_RESULTS = int(os.environ.get("SEARXNG_MAX_RESULTS", "5"))
SEARXNG_DESC_MAX = int(os.environ.get("SEARXNG_DESC_MAX", "200"))
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
    def search(self, query, limit=None, language=None, time_range=None,
               categories="general", fmt="compact"):
        """
        Recherche SearXNG — retourne un dict optimisé pour LLM.

        Formats:
          compact — titre, url, description tronquée (défaut)
          rich    — + publishedDate, engine, score, thumbnail

        Format de retour (compatible Hermes web_search_tool) :
        {
            "success": True,
            "data": {
                "web": [
                    {"title": "...", "url": "...", "description": "...", "position": 1,
                     "publishedDate": "...", "engine": "...", "score": 6.8, "thumbnail": "..."},
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
            "safesearch": SEARXNG_SAFESEARCH,
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
            desc = html_mod.unescape(r.get("content", "").strip())
            if len(desc) > SEARXNG_DESC_MAX:
                desc = desc[:SEARXNG_DESC_MAX] + "…"

            # Base entry (compact)
            entry = {
                "title": r.get("title", "").strip(),
                "url": r.get("url", ""),
                "description": desc,
                "position": i + 1,
            }

            # Rich format: ajouter métadonnées
            if fmt == "rich":
                if r.get("publishedDate"):
                    entry["publishedDate"] = r["publishedDate"]
                if r.get("engine"):
                    entry["engine"] = r["engine"]
                if r.get("engines"):
                    entry["engines"] = r["engines"]
                if r.get("score"):
                    entry["score"] = r["score"]
                if r.get("thumbnail"):
                    entry["thumbnail"] = r["thumbnail"]

            if entry["url"]:
                web_results.append(entry)

        return {"success": True, "data": {"web": web_results}}

    # ─── Extraction ───────────────────────────────────────────────────────────
    def extract(self, urls, max_length=None):
        """
        Extraction de contenu web — HTML nettoyé en texte compact.

        Pas de dépendance externe (no beautifulsoup, no readability, no firecrawl).
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
                    raw = resp.read()
                    # Try multiple encodings
                    for enc in ("utf-8", "latin-1", "cp1252"):
                        try:
                            html_content = raw.decode(enc)
                            break
                        except (UnicodeDecodeError, ValueError):
                            continue
                    else:
                        html_content = raw.decode("utf-8", errors="replace")

                # Extraction du titre
                title_match = re.search(
                    r"<title[^>]*>(.*?)</title>", html_content,
                    re.DOTALL | re.IGNORECASE
                )
                title = html_mod.unescape(title_match.group(1).strip()) if title_match else target_url

                # Nettoyage HTML → texte
                text = html_content
                for tag in ("script", "style", "nav", "footer", "header", "aside", "noscript"):
                    text = re.sub(
                        rf"<{tag}[^>]*>.*?</{tag}>", "", text,
                        flags=re.DOTALL | re.IGNORECASE
                    )
                text = re.sub(r"<[^>]+>", " ", text)
                text = html_mod.unescape(text)
                text = re.sub(r"\s+", " ", text).strip()

                # Troncature intelligente
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
    def format_search(self, results, fmt="compact"):
        """Format lisible pour le CLI."""
        if not results.get("data", {}).get("web"):
            return "Aucun résultat trouvé."

        web = results["data"]["web"]
        lines = [f"🔍 {len(web)} résultat(s)\n"]

        if fmt == "rich":
            for r in web:
                lines.append(f"{r['position']}. **{r['title']}**")
                lines.append(f"   🔗 {r['url']}")
                if r.get("description"):
                    lines.append(f"   📄 {r['description']}")
                if r.get("publishedDate"):
                    lines.append(f"   📅 {r['publishedDate']}")
                if r.get("engine"):
                    engines = r.get("engines", [r["engine"]])
                    lines.append(f"   🔍 {' | '.join(engines)}")
                if r.get("score"):
                    lines.append(f"   ⭐ {r['score']}")
                if r.get("thumbnail"):
                    lines.append(f"   🖼️ {r['thumbnail'][:80]}…")
                lines.append("")
        else:
            for r in web:
                lines.append(f"{r['position']}. [{r['title']}]({r['url']})")
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
    parser.add_argument("--format", choices=["compact", "rich"], default="compact",
                        help="Format de sortie (compact=défaut, rich=métadonnées)")
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
            fmt=args.format,
        )
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(client.format_search(result, fmt=args.format))


if __name__ == "__main__":
    main()