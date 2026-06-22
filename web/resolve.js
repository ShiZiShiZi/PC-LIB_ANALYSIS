/**
 * resolve.js — zero-dependency repository-URL resolver for the pending-deps page.
 *
 * Given a dependency's (ecosystem, name) it queries that ecosystem's public
 * package registry over HTTPS (Node stdlib only) and returns a clonable git URL.
 * Results (including misses) are cached on disk (.resolve-cache.json, gitignored)
 * to stay polite to registries and make repeat lookups near-free.
 *
 *   resolveRepo(ecoCanon, name) -> Promise<{ url, source, confidence, candidates }>
 *
 * ecoCanon is the normalized ecosystem from server.js ecoNorm():
 *   python | nodejs | rust | go | java | cpp | c | dotnet | <raw>
 */
'use strict';

const https = require('https');
const fs = require('fs');
const path = require('path');

const UA = 'pc-lib-analysis/1.0 (+repo-resolver)';
const TIMEOUT = 8000;
const VCS_HOSTS = /(github\.com|gitlab\.com|gitee\.com|gitcode\.(?:com|net)|bitbucket\.org|sourceforge\.net|codeberg\.org)/i;

const CACHE_FILE = path.join(__dirname, '..', '.resolve-cache.json');
const CACHE_TTL_MS = 7 * 24 * 3600 * 1000;
let cache = null;

function loadCache() {
  if (cache) return cache;
  try { cache = JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8')); }
  catch { cache = {}; }
  return cache;
}
function saveCache() {
  try { fs.writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 0)); } catch (_) {}
}

// ── tiny HTTPS GET (text), one redirect hop, timeout ────────────────────────
function httpText(url, redirects = 1) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, { headers: { 'User-Agent': UA, Accept: '*/*' } }, (res) => {
      const { statusCode, headers } = res;
      if (statusCode >= 300 && statusCode < 400 && headers.location && redirects > 0) {
        res.resume();
        const next = new URL(headers.location, url).toString();
        return resolve(httpText(next, redirects - 1));
      }
      if (statusCode < 200 || statusCode >= 300) {
        res.resume();
        return reject(new Error(`HTTP ${statusCode} for ${url}`));
      }
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (c) => (body += c));
      res.on('end', () => resolve(body));
    });
    req.on('error', reject);
    req.setTimeout(TIMEOUT, () => req.destroy(new Error('timeout')));
  });
}
async function httpJson(url) { return JSON.parse(await httpText(url)); }

// ── normalize any repo-ish URL to a clonable https git URL (or null) ────────
function normalizeRepoUrl(raw) {
  if (!raw || typeof raw !== 'string') return null;
  let u = raw.trim();
  if (!u) return null;
  u = u.replace(/^git\+/, '');
  // scp-like git@github.com:owner/repo(.git)
  let m = u.match(/^[\w.-]+@([\w.-]+):(.+)$/);
  if (m) u = `https://${m[1]}/${m[2]}`;
  u = u.replace(/^git:\/\//i, 'https://').replace(/^ssh:\/\/(?:git@)?/i, 'https://');
  u = u.replace(/^http:\/\//i, 'https://');
  u = u.split('#')[0].replace(/\?.*$/, '');
  if (!/^https:\/\//i.test(u)) return null;
  if (!VCS_HOSTS.test(u)) return null;
  // trim github/gitlab deep links to the repo root: host/owner/repo
  m = u.match(/^(https:\/\/[\w.-]+\/[^/]+\/[^/]+?)(?:\.git)?(?:\/(?:tree|blob|releases|issues|wiki|commit|-)\b.*)?\/?$/i);
  let base = m ? m[1] : u.replace(/\/+$/, '');
  base = base.replace(/\.git$/i, '');
  return base + '.git';
}

function pickFromUrls(urls) {
  // urls: array of candidate strings, VCS hosts win, else first https.
  const norm = urls.map(normalizeRepoUrl).filter(Boolean);
  return norm[0] || null;
}

// ── per-ecosystem resolvers ─────────────────────────────────────────────────
async function resolvePython(name) {
  const d = await httpJson(`https://pypi.org/pypi/${encodeURIComponent(name)}/json`);
  const info = d.info || {};
  const pu = info.project_urls || {};
  const ordered = [];
  for (const k of Object.keys(pu)) {
    if (/source|repo|code|github|gitlab|tracker|homepage/i.test(k)) ordered.push(pu[k]);
  }
  const url = pickFromUrls([...ordered, ...Object.values(pu), info.home_page].filter(Boolean));
  return { url, source: 'pypi', confidence: url ? 'high' : null };
}

async function resolveNpm(name) {
  const d = await httpJson(`https://registry.npmjs.org/${encodeURIComponent(name)}`);
  const repo = d.repository;
  const cands = [];
  if (typeof repo === 'string') cands.push(repo);
  else if (repo && repo.url) cands.push(repo.url);
  if (d.homepage) cands.push(d.homepage);
  if (d.bugs && d.bugs.url) cands.push(d.bugs.url);
  const url = pickFromUrls(cands);
  return { url, source: 'npm', confidence: url ? 'high' : null };
}

async function resolveRust(name) {
  const d = await httpJson(`https://crates.io/api/v1/crates/${encodeURIComponent(name)}`);
  const c = d.crate || {};
  const url = pickFromUrls([c.repository, c.homepage].filter(Boolean));
  return { url, source: 'crates.io', confidence: url ? 'high' : null };
}

function resolveGo(name) {
  // A Go module path usually IS the repo: host/owner/repo[/subpkg...]
  const m = String(name).match(/^((?:github\.com|gitlab\.com|gitee\.com|bitbucket\.org|codeberg\.org)\/[^/]+\/[^/]+)/i);
  const url = m ? normalizeRepoUrl('https://' + m[1]) : null;
  return Promise.resolve({ url, source: 'go-module-path', confidence: url ? 'medium' : null });
}

async function resolveJava(name) {
  // name may be "groupId:artifactId" or just the artifact.
  const [maybeG, maybeA] = String(name).split(':');
  const artifact = maybeA || maybeG;
  const q = maybeA ? `g:"${maybeG}" AND a:"${maybeA}"` : `a:"${artifact}"`;
  const search = await httpJson(
    `https://search.maven.org/solrsearch/select?q=${encodeURIComponent(q)}&rows=5&wt=json`);
  const doc = ((search.response || {}).docs || [])[0];
  if (!doc) return { url: null, source: 'maven', confidence: null };
  const g = doc.g, a = doc.a, v = doc.latestVersion || doc.v;
  try {
    const pom = await httpText(
      `https://repo1.maven.org/maven2/${g.replace(/\./g, '/')}/${a}/${v}/${a}-${v}.pom`);
    const scm = pom.match(/<scm>[\s\S]*?<url>([^<]+)<\/url>[\s\S]*?<\/scm>/i)
      || pom.match(/<connection>([^<]*github[^<]*)<\/connection>/i)
      || pom.match(/<url>([^<]*(?:github|gitlab|gitee|bitbucket)[^<]+)<\/url>/i);
    const url = scm ? normalizeRepoUrl(scm[1]) : null;
    return { url, source: 'maven', confidence: url ? 'medium' : null };
  } catch (_) {
    return { url: null, source: 'maven', confidence: null };
  }
}

async function resolveGithubSearch(name) {
  // Last-resort heuristic for C/C++ and unknown ecosystems: search GitHub by name.
  // Unauthenticated: 60 req/h — cached hard. Low confidence; surface candidates.
  const d = await httpJson(
    `https://api.github.com/search/repositories?q=${encodeURIComponent(name)}+in:name&sort=stars&order=desc&per_page=5`);
  const items = (d.items || []);
  const candidates = items.map((it) => normalizeRepoUrl(it.clone_url || it.html_url)).filter(Boolean);
  return { url: candidates[0] || null, source: 'github-search', confidence: candidates[0] ? 'low' : null, candidates };
}

const RESOLVERS = {
  python: resolvePython,
  nodejs: resolveNpm,
  rust: resolveRust,
  go: resolveGo,
  java: resolveJava,
};

async function resolveRepo(ecoCanon, name) {
  const eco = String(ecoCanon || '').toLowerCase();
  const nm = String(name || '').trim();
  const empty = { url: null, source: null, confidence: null, candidates: [] };
  if (!nm) return empty;

  const c = loadCache();
  const key = `${eco}:${nm}`;
  const hit = c[key];
  if (hit && Date.now() - (hit.ts || 0) < CACHE_TTL_MS) {
    return { url: hit.url, source: hit.source, confidence: hit.confidence, candidates: hit.candidates || [], cached: true };
  }

  let out = empty;
  try {
    const fn = RESOLVERS[eco] || resolveGithubSearch;
    let r = await fn(nm);
    // ecosystem registry found nothing → GitHub search fallback (except go).
    if ((!r || !r.url) && fn !== resolveGithubSearch && eco !== 'go') {
      try { const fb = await resolveGithubSearch(nm); if (fb.url) r = fb; } catch (_) {}
    }
    out = { url: (r && r.url) || null, source: r && r.source, confidence: r && r.confidence, candidates: (r && r.candidates) || [] };
  } catch (e) {
    out = { ...empty, error: String(e.message || e) };
  }

  c[key] = { url: out.url, source: out.source, confidence: out.confidence, candidates: out.candidates, ts: Date.now() };
  saveCache();
  return out;
}

module.exports = { resolveRepo, normalizeRepoUrl, httpText };
