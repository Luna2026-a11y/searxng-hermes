#!/usr/bin/env node

/**
 * SearXNG Backend for Hermes Agent — Token-optimized
 * Recherche web + extraction via instance SearXNG auto-hébergée.
 */

import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const https = require('https');
const http = require('http');
const { URL } = require('url');

const SEARXNG_URL = (process.env.SEARXNG_URL || '').replace(/\/+$/, '');
const SEARXNG_LANGUAGE = process.env.SEARXNG_LANGUAGE || 'fr';
const SEARXNG_SAFESARCH = parseInt(process.env.SEARXNG_SAFESARCH || '1');
const SEARXNG_MAX_RESULTS = parseInt(process.env.SEARXNG_MAX_RESULTS || '5');
const SEARXNG_EXTRACT_MAX = parseInt(process.env.SEARXNG_EXTRACT_MAX || '5000');
const SEARXNG_TIMEOUT = parseInt(process.env.SEARXNG_TIMEOUT || '15') * 1000;

class SearXNGClient {
  constructor(url) {
    this.url = url || SEARXNG_URL;
    if (!this.url) throw new Error('SEARXNG_URL non configuré');
  }

  async search(query, options = {}) {
    const {
      limit = SEARXNG_MAX_RESULTS,
      language = SEARXNG_LANGUAGE,
      timeRange = null,
      categories = 'general',
    } = options;

    const url = new URL(`${this.url}/search`);
    url.searchParams.append('q', query);
    url.searchParams.append('format', 'json');
    url.searchParams.append('language', language);
    url.searchParams.append('safesearch', SEARXNG_SAFESARCH);
    url.searchParams.append('categories', categories);
    if (timeRange) url.searchParams.append('time_range', timeRange);

    const data = await this._fetch(url.toString());
    const web = (data.results || []).slice(0, limit).map((r, i) => ({
      title: (r.title || '').trim(),
      url: r.url || '',
      description: (r.content || '').trim().substring(0, 200),
      position: i + 1,
    })).filter(r => r.url);

    return { success: true, data: { web } };
  }

  async extract(urls, maxLen = SEARXNG_EXTRACT_MAX) {
    if (typeof urls === 'string') urls = [urls];
    const pages = await Promise.all(urls.map(async (targetUrl) => {
      try {
        const html = await this._fetchRaw(targetUrl);
        const titleMatch = html.match(/<title[^>]*>(.*?)<\/title>/is);
        const title = titleMatch ? titleMatch[1].trim() : targetUrl;

        let text = html
          .replace(/<(script|style|nav|footer|header|aside|noscript)[^>]*>[\s\S]*?<\/\1>/gi, '')
          .replace(/<[^>]+>/g, ' ')
          .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
          .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;/g, ' ')
          .replace(/\s+/g, ' ').trim();

        if (text.length > maxLen) {
          const half = Math.floor(maxLen / 2);
          text = text.substring(0, half) + '\n\n[...truncated...]\n\n' + text.substring(text.length - half);
        }

        return { url: targetUrl, title, content: text, success: true };
      } catch (e) {
        return { url: targetUrl, error: e.message.substring(0, 200), success: false };
      }
    }));

    return { success: pages.some(p => p.success), pages };
  }

  _fetch(url) {
    return new Promise((resolve, reject) => {
      const proto = url.startsWith('https') ? https : http;
      const req = proto.get(url, { headers: { 'User-Agent': 'Hermes-SearXNG/1.0', 'Accept': 'application/json' } }, (res) => {
        let data = '';
        res.on('data', c => data += c);
        res.on('end', () => { try { resolve(JSON.parse(data)); } catch (e) { reject(new Error('Invalid JSON')); } });
      });
      req.on('error', reject);
      req.setTimeout(SEARXNG_TIMEOUT, () => { req.destroy(); reject(new Error('Timeout')); });
    });
  }

  _fetchRaw(url) {
    return new Promise((resolve, reject) => {
      const proto = url.startsWith('https') ? https : http;
      const req = proto.get(url, { headers: { 'User-Agent': 'Mozilla/5.0 (compatible; Hermes-SearXNG/1.0)' } }, (res) => {
        let data = '';
        res.on('data', c => data += c);
        res.on('end', () => resolve(data));
      });
      req.on('error', reject);
      req.setTimeout(SEARXNG_TIMEOUT, () => { req.destroy(); reject(new Error('Timeout')); });
    });
  }

  formatSearch(results) {
    const web = results?.data?.web;
    if (!web?.length) return 'Aucun résultat trouvé.';
    return `\n🔍 ${web.length} résultat(s)\n\n` +
      web.map(r => `${r.position}. **${r.title}**\n   ${r.url}\n   ${r.description || ''}\n`).join('\n');
  }

  formatExtract(result) {
    return (result.pages || []).map(p =>
      p.success ? `# ${p.title}\n\n${p.content}\n\n---\n` : `❌ ${p.url}: ${p.error}\n---\n`
    ).join('\n');
  }
}

// CLI
async function main() {
  const args = process.argv.slice(2);
  const extractIdx = args.indexOf('--extract');
  const jsonIdx = args.indexOf('--json');

  if (extractIdx !== -1) {
    const urls = args.slice(extractIdx + 1).filter(a => !a.startsWith('--'));
    const client = new SearXNGClient();
    const result = await client.extract(urls);
    console.log(jsonIdx !== -1 ? JSON.stringify(result, null, 2) : client.formatExtract(result));
  } else {
    const query = args.filter(a => !a.startsWith('--')).join(' ');
    if (!query) {
      console.error('Usage: node searxng_search.mjs "recherche" [--json] [--extract URL...]');
      process.exit(1);
    }
    const client = new SearXNGClient();
    const result = await client.search(query);
    console.log(jsonIdx !== -1 ? JSON.stringify(result, null, 2) : client.formatSearch(result));
  }
}

export { SearXNGClient };

if (import.meta.url === `file://${process.argv[1]}`) main();