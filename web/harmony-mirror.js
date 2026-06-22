/**
 * harmony-mirror.js — is a third-party package already adapted to HarmonyOS PC?
 *
 * Two source kinds (see HARMONY_MIRRORS):
 *  - Python ('simple'): the mirror is a full PyPI proxy, so mere presence ≠ ported.
 *    The real signal is a native `ohos` wheel (numpy ships `*-ohos_aarch64.whl`). The
 *    mirror has NO listable root (it 404s), so we probe each package page on demand:
 *    GET <simple>/<name>/ : 200 AND contains an `ohos` wheel ⇒ adapted.
 *  - C/C++ ('list'): the OpenHarmony cmd-pkgs README lists every prebuilt package in
 *    its install commands (`sh -s -- <name> <ver>`); membership (with name variants)
 *    ⇒ adapted.
 * Both kinds cache to .harmony-mirror-cache.json — per-package for 'simple', and
 * the per-package result (.harmony-mirror-cache.json). Single source of truth
 * shared by the web panel (server require()s this) and the analyzer agent (via
 * scripts/harmony_adapted.js).
 *
 * Zero-dependency: Node https. TLS works in Node even where the system Python
 * cert store does not.
 */
'use strict';

const https = require('https');
const fs = require('fs');
const path = require('path');

// ecosystem (canonical, per server ecoNorm) -> how to check the OpenHarmony PC source.
//  - kind 'simple': PEP 503 per-package probe (PyPI mirror; ohos wheel ⇒ adapted).
//  - kind 'list'  : one README listing all prebuilt packages; membership ⇒ adapted.
const HARMONY_MIRRORS = {
  python: { kind: 'simple', url: 'https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple/' },
  cpp: { kind: 'list', url: 'https://raw.gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/raw/main/README.md', listKey: 'cpp' },
  c: { kind: 'list', url: 'https://raw.gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/raw/main/README.md', listKey: 'cpp' },
};
const MIRROR_LABEL = {
  python: 'OpenHarmony PC PyPI 镜像 (pypi.cnb.cool/OpenHarmonyPCDeveloper)',
  cpp: 'OpenHarmony PC C/C++ 预编译包 (gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs)',
  c: 'OpenHarmony PC C/C++ 预编译包 (gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs)',
};

const CACHE_FILE = path.join(__dirname, '..', '.harmony-mirror-cache.json');
const CACHE_TTL_MS = 3 * 24 * 3600 * 1000;
const TIMEOUT = 8000;
const MAX_CONCURRENCY = 5;
let cache = null;   // { "eco:normname": { adapted, ts } }

// PEP 503 normalized project name.
function normalize(name) {
  return String(name || '').replace(/[-_.]+/g, '-').trim().toLowerCase();
}

function loadCache() {
  if (cache) return cache;
  try { cache = JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8')); } catch { cache = {}; }
  return cache;
}
function saveCache() {
  try { fs.writeFileSync(CACHE_FILE, JSON.stringify(cache)); } catch (_) {}
}

// GET returning { status, body } (does NOT throw on 4xx — 404 is a real answer).
function httpGet(url, redirects = 1) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, { headers: { 'User-Agent': 'pc-lib-analysis/1.0' } }, (res) => {
      const { statusCode, headers } = res;
      if (statusCode >= 300 && statusCode < 400 && headers.location && redirects > 0) {
        res.resume();
        return resolve(httpGet(new URL(headers.location, url).toString(), redirects - 1));
      }
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (c) => (body += c));
      res.on('end', () => resolve({ status: statusCode, body }));
    });
    req.on('error', reject);
    req.setTimeout(TIMEOUT, () => req.destroy(new Error('timeout')));
  });
}

// 'simple' strategy: probe one package page; returns boolean or null (error/unknown).
async function probe(cfg, name) {
  const url = cfg.url + normalize(name) + '/';
  let r;
  try { r = await httpGet(url); } catch { return null; }
  if (r.status === 404) return false;
  if (r.status < 200 || r.status >= 300) return null;
  // The mirror is a full PyPI proxy (most packages are plain upstream passthrough).
  // The HarmonyOS-port signal is a native `ohos` wheel (e.g. *-ohos_aarch64.whl);
  // pure passthrough packages have none. So require an ohos artifact.
  return /ohos/i.test(r.body);
}

// 'list' strategy: fetch the cmd-pkgs README once, harvest every prebuilt package
// name from its install commands (`sh -s -- <name> <version>`), cache as a Set.
async function adaptedList(cfg, refresh = false) {
  const c = loadCache();
  const cacheKey = `_list:${cfg.listKey}`;
  const entry = c[cacheKey];
  if (!refresh && entry && Date.now() - (entry.ts || 0) < CACHE_TTL_MS) return new Set(entry.names || []);
  let r;
  try { r = await httpGet(cfg.url); } catch { return entry ? new Set(entry.names) : null; }
  if (!r || r.status < 200 || r.status >= 300) return entry ? new Set(entry.names) : null;
  const names = new Set();
  const re = /sh\s+-s\s+--\s+([a-z0-9._+-]+)/gi;
  let m;
  while ((m = re.exec(r.body))) names.add(m[1].toLowerCase());
  c[cacheKey] = { names: [...names], ts: Date.now() };
  saveCache();
  return names;
}

// C/C++ dep names rarely match the list verbatim; try a few harmless variants.
function nameVariants(name) {
  const n = normalize(name);
  const v = new Set([n]);
  v.add(n.replace(/^lib/, ''));     // libpng -> png
  v.add('lib' + n);                 // png -> libpng
  v.add(n.replace(/\d+$/, ''));     // eigen3 -> eigen, sqlite3 -> sqlite
  v.delete('');
  return [...v];
}

// adapted bool for one package, with disk cache (null results are not cached).
async function isAdapted(ecoCanon, name, refresh = false) {
  const eco = String(ecoCanon || '').toLowerCase();
  const cfg = HARMONY_MIRRORS[eco];
  if (!cfg) return false;
  const c = loadCache();
  const key = `${eco}:${normalize(name)}`;
  const hit = c[key];
  if (!refresh && hit && Date.now() - (hit.ts || 0) < CACHE_TTL_MS) return hit.adapted;
  let res;
  if (cfg.kind === 'list') {
    const set = await adaptedList(cfg, refresh);
    res = set === null ? null : nameVariants(name).some((v) => set.has(v));
  } else {
    res = await probe(cfg, name);
  }
  if (res === null) return hit ? hit.adapted : false;   // keep stale on transient error
  c[key] = { adapted: res, ts: Date.now() };
  saveCache();
  return res;
}

// Resolve many names with bounded concurrency.
async function _mapLimited(items, fn) {
  const out = new Array(items.length);
  let i = 0;
  const workers = Array.from({ length: Math.min(MAX_CONCURRENCY, items.length || 1) }, async () => {
    while (i < items.length) { const idx = i++; out[idx] = await fn(items[idx], idx); }
  });
  await Promise.all(workers);
  return out;
}

// { ecosystem, source, results: {name:{adapted,source}}, adaptedCount, total }
async function statusFor(ecoCanon, names, refresh = false) {
  const eco = String(ecoCanon || '').toLowerCase();
  const src = MIRROR_LABEL[eco] || null;
  const flags = await _mapLimited(names, (nm) => isAdapted(eco, nm, refresh));
  const results = {};
  let adaptedCount = 0;
  names.forEach((nm, k) => {
    const hit = !!flags[k];
    if (hit) adaptedCount++;
    results[nm] = { adapted: hit, source: hit ? src : null };
  });
  return { ecosystem: eco, source: src, results, adaptedCount, total: names.length };
}

// Stamp dependencies[].harmony_adapted into a report.json in place (Phase 2 / agent).
async function stampReport(reportPath) {
  const rep = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
  const deps = ((rep.dependencies || {}).dependencies) || [];
  await _mapLimited(deps, async (d) => {
    if (!d || !d.name) return;
    const eco = String(d.ecosystem || '').toLowerCase();
    const hit = await isAdapted(eco, d.name);
    d.harmony_adapted = hit;
    d.harmony_adapted_source = hit ? (MIRROR_LABEL[eco] || null) : null;
  });
  const stamped = deps.filter((d) => d && d.harmony_adapted).length;
  fs.writeFileSync(reportPath, JSON.stringify(rep, null, 2));
  return { stamped, total: deps.length };
}

module.exports = { isAdapted, statusFor, stampReport, normalize, HARMONY_MIRRORS, MIRROR_LABEL };
