# SearXNG Backend pour Hermes Agent

Connecteur SearXNG optimisé pour Hermes Agent — recherche web et extraction de contenu via une instance SearXNG, sans API key, avec outputs compacts pour économiser les tokens.

## 🎯 Pourquoi ce repo ?

Hermes Agent utilise des backends web payants (Firecrawl, Tavily, Exa, Parallel) pour `web_search` et `web_extract`. Ce repo fournit un **backend SearXNG alternatif gratuit** :

- ✅ **Zéro API key** — utilise votre instance SearXNG existante
- ✅ **Optimisé tokens** — résultats compacts, pas de HTML brut
- ✅ **Standalone** — fonctionne comme skill Hermes ou script CLI
- ✅ **Stdlib Python** — zéro dépendance externe

**Prérequis :** une instance SearXNG accessible avec le format JSON activé (`settings.yml` → `search.formats: [html, json]`).

## 📦 Ce qui est inclus

| Fichier | Description |
|---------|-------------|
| `searxng_search.py` | Backend SearXNG complet (search + extract), outputs compacts |
| `searxng_search.mjs` | Version Node.js alternatif |
| `searx-search` | Wrapper bash pour usage CLI rapide |
| `SKILL.md` | Skill Hermes — installation en 30 secondes |

## 🚀 Installation rapide (Hermes Agent)

### Méthode 1 : Skill (recommandée)

```bash
# Copier le skill dans votre dossier Hermes
mkdir -p ~/.hermes/skills/
cp SKILL.md ~/.hermes/skills/searxng-backend.md
```

Puis dans `~/.hermes/config.yaml` :

```yaml
web:
  backend: searxng
  searxng_url: https://votre-instance.searxng.fr
```

### Méthode 2 : Script standalone

```bash
# Configurer l'URL de votre instance
export SEARXNG_URL="https://votre-instance.searxng.fr"

# Rechercher
python3 searxng_search.py "dragon ball z villains"

# Extraire une page
python3 searxng_search.py --extract "https://example.com/article"
```

## ⚡ Optimisations tokens Hermes

Le backend est conçu pour **minimiser la consommation de tokens** :

1. **Résultats de recherche** : titres + URLs + 1-2 phrases d'extrait (pas de HTML)
2. **Extraction de page** : nettoyage HTML → texte brut, troncature intelligente
3. **Structuré JSON** : parsing direct, pas de markdown verbeux
4. **Limite configurable** : `limit=5` par défaut (pas 20 résultats inutiles)

### Exemple de sortie compacte

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

vs. HTML brut qui consomme 2000+ tokens pour le même résultat.

## 🔧 Configuration

| Variable | Description | Défaut |
|----------|-------------|--------|
| `SEARXNG_URL` | URL de votre instance SearXNG | *(obligatoire)* |
| `SEARXNG_TIMEOUT` | Timeout requêtes (secondes) | `15` |
| `SEARXNG_LANGUAGE` | Code langue | `fr` |
| `SEARXNG_SAFESARCH` | Filtrage (0=off, 3=strict) | `1` |
| `SEARXNG_MAX_RESULTS` | Résultats max par recherche | `5` |
| `SEARXNG_EXTRACT_MAX` | Taille max extraction (caractères) | `5000` |

## 🔗 Utilisation comme module Python

```python
from searxng_search import SearXNGClient

client = SearXNGClient(url="https://votre-instance.searxng.fr")

# Recherche
results = client.search("dragon ball z villains", limit=5)
for r in results["data"]["web"]:
    print(f"{r['title']}: {r['url']}")

# Extraction
page = client.extract("https://example.com/article")
print(page["content"][:500])
```

## 📋 Format de sortie CLI

```
🔍 5 résultat(s) trouvé(s)

1. **Dragon Ball Z Villains Wiki**
   https://dragonball.fandom.com/wiki/Villains
   Complete list of all major villains in Dragon Ball Z...

2. **Frieza - Dragon Ball Encyclopedia**
   https://en.wikipedia.org/wiki/Frieza
   Frieza is the emperor of Universe 7...
```

## ⚠️ Dépannage

### `Connexion refusée`
- Vérifiez que l'URL SearXNG est correcte
- Vérifiez que l'instance est accessible : `curl -s "https://votre-instance.com/search?q=test&format=json" | head -20`
- Vérifiez que le format JSON est activé dans `settings.yml`

### `Invalid JSON response`
- Le format JSON n'est pas activé dans SearXNG
- Ajoutez `- json` dans `search.formats` dans `settings.yml`

## 📝 Licence

MIT — Faites-en ce que vous voulez.

## 🙏 Crédits

- [SearXNG](https://searxng.org/) — Meta-moteur de recherche respectueux de la vie privée
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — Agent IA open source
- Inspiré de [searxng-openclaw](https://github.com/gamersalpha/searxng-openclaw) — Bridge SearXNG pour OpenClaw