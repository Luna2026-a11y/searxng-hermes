---
name: searxng-backend
description: Backend SearXNG pour Hermes Agent — recherche web et extraction via instance auto-hébergée, outputs compacts optimisés tokens.
category: devops
---

# SearXNG Backend pour Hermes Agent

Backend SearXNG alternatif pour les web tools Hermes — remplace Firecrawl/Tavily/Exa avec une instance auto-hébergée gratuite.

## Installation

1. Avoir une instance SearXNG avec le format JSON activé (`settings.yml` → `search.formats: [html, json]`)
2. Configurer dans `~/.hermes/config.yaml` :

```yaml
web:
  backend: searxng
  searxng_url: https://votre-instance.searxng.fr
```

Ou via variable d'environnement : `export SEARXNG_URL=https://votre-instance.searxng.fr`

3. Placer `searxng_search.py` dans un accès de l'agent (ex: `~/.hermes/scripts/`)

## Utilisation depuis Hermes

```python
from searxng_search import SearXNGClient

client = SearXNGClient()

# Recherche compacte (5 résultats, ~200 tokens au lieu de ~2000)
results = client.search("dragon ball z villains", limit=5)

# Extraction de page (HTML nettoyé, troncature intelligente)
page = client.extract("https://example.com/article")
```

## CLI rapide

```bash
# Recherche
python3 searxng_search.py "votre recherche" --json

# Extraction
python3 searxng_search.py --extract https://example.com --json
```

## Optimisations tokens

- Résultats recherche : titre + URL + 200 chars max d'extrait
- Extraction : HTML → texte, suppression nav/footer/scripts, troncature début+fin
- JSON structuré : parsable directement, pas de markdown verbeux
- 5 résultats par défaut (pas 20 inutiles)