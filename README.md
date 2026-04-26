[🇫🇷 Lire en français](README.fr.md)

# SearXNG Backend for Hermes Agent

Token-optimized SearXNG connector for Hermes Agent — web search and content extraction through your own SearXNG instance, zero API keys, compact outputs.

## 📊 Benchmark & Comparison

**[→ Full Benchmark Results & Backend Comparison on BookStack](https://namel.fr/bookstack/books/web-search-backend-benchmark-searxng-hermes-vs-paid-apis)**

Real measurements — SearXNG-Hermes vs Firecrawl, Tavily, Exa, Parallel. Token savings, latency, features, privacy, pricing. Zero hype, all numbers verified.

### Quick numbers (measured)

| | SearXNG-Hermes | Firecrawl | Tavily | Exa | Parallel |
|---|---|---|---|---|---|
| Cost | **$0** (unlimited) | $16–83/1k | ~$8/1k | ~$7/1k | ~$5/1k |
| Search latency | ~1s | 2–5s | 1–3s | 0.18–1s | <5s |
| Extract latency | **~0.2s** | 3–10s | 2–5s | ~1s | <3s |
| Tokens/search | **418** (compact) | ~800–1500 | ~800–1200 | ~600–1000 | ~400–800 |
| Privacy | **100% local** | Cloud | Cloud | Cloud | Cloud |

## 🎯 Why this repo?

Hermes Agent uses paid web backends (Firecrawl, Tavily, Exa, Parallel) for `web_search` and `web_extract`. This repo provides a **free SearXNG alternative**:

- ✅ **Zero API keys** — uses your existing SearXNG instance
- ✅ **Token-optimized** — compact results, no raw HTML
- ✅ **Standalone** — works as a Hermes skill or CLI script
- ✅ **Python stdlib only** — no external dependencies

**Prerequisite:** a SearXNG instance with JSON format enabled (`settings.yml` → `search.formats: [html, json]`).

## 📦 What's included

| File | Description |
|------|-------------|
| `searxng_search.py` | Full Python backend (search + extract), compact outputs |
| `searxng_search.mjs` | Node.js alternative |
| `searx-search` | Bash wrapper for quick CLI usage |
| `SKILL.md` | Hermes Agent skill — install in 30 seconds |

## 🚀 Quick Start (Hermes Agent)

### Option 1: Skill (recommended)

```bash
# Copy the skill to your Hermes directory
mkdir -p ~/.hermes/skills/
cp SKILL.md ~/.hermes/skills/searxng-backend.md
```

Then in `~/.hermes/config.yaml`:

```yaml
web:
  backend: searxng
  searxng_url: https://your-searxng-instance.example.com
```

### Option 2: Standalone script

```bash
# Set your SearXNG instance URL
export SEARXNG_URL="https://your-searxng-instance.example.com"

# Search
python3 searxng_search.py "dragon ball z villains"

# Extract a web page
python3 searxng_search.py --extract "https://example.com/article"
```

## ⚡ Token Optimizations

This backend is designed to **minimize token consumption**:

1. **Search results**: titles + URLs + 1-2 sentence snippets (no HTML)
2. **Page extraction**: HTML → clean text, smart truncation (beginning + end)
3. **Structured JSON**: directly parseable, no verbose markdown
4. **Configurable limit**: `limit=5` by default (not 20 useless results)

### Compact output example

```json
{
  "success": true,
  "data": {
    "web": [
      {"title": "Dragon Ball Z Villains Wiki", "url": "https://...", "description": "Complete list of DBZ villains..."},
      {"title": "Frieza - Dragon Ball Encyclopedia", "url": "https://...", "description": "Frieza is the emperor..."}
    ]
  }
}
```

vs. raw HTML that burns 2000+ tokens for the same information.

## 🔧 Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SEARXNG_URL` | Your SearXNG instance URL | *(required)* |
| `SEARXNG_TIMEOUT` | Request timeout (seconds) | `15` |
| `SEARXNG_LANGUAGE` | Language code | `fr` |
| `SEARXNG_SAFESARCH` | Safe search level (0=off, 3=strict) | `1` |
| `SEARXNG_MAX_RESULTS` | Max results per search | `5` |
| `SEARXNG_EXTRACT_MAX` | Max extraction size (chars) | `5000` |

## 🔗 Python Module Usage

```python
from searxng_search import SearXNGClient

client = SearXNGClient(url="https://your-searxng-instance.example.com")

# Search
results = client.search("dragon ball z villains", limit=5)
for r in results["data"]["web"]:
    print(f"{r['title']}: {r['url']}")

# Extract
page = client.extract("https://example.com/article")
print(page["content"][:500])
```

## 📋 CLI Output Format

```
🔍 5 résultat(s)

1. **Dragon Ball Z Villains Wiki**
   https://dragonball.fandom.com/wiki/Villains
   Complete list of all major villains in Dragon Ball Z...

2. **Frieza - Dragon Ball Encyclopedia**
   https://en.wikipedia.org/wiki/Frieza
   Frieza is the emperor of Universe 7...
```

## ⚠️ Troubleshooting

### `Connection refused`
- Check that your SearXNG URL is correct
- Verify the instance is reachable: `curl -s "https://your-instance.com/search?q=test&format=json" | head -20`
- Make sure JSON format is enabled in `settings.yml`

### `Invalid JSON response`
- JSON format is not enabled in SearXNG
- Add `- json` to `search.formats` in `settings.yml`

## 📝 License

MIT — Do whatever you want.

## 🙏 Credits

- [SearXNG](https://searxng.org/) — Privacy-respecting metasearch engine
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — Open source AI agent
- Inspired by [searxng-openclaw](https://github.com/gamersalpha/searxng-openclaw) — SearXNG bridge for OpenClaw