#!/usr/bin/env node
/**
 * pc-lib-analysis — control panel backend (Node stdlib only, zero deps).
 *
 * Serves the UI and exposes an API to: list/clone library repos (batch +
 * concurrent), launch opencode analyses (batch + concurrency-limited queue),
 * stream live opencode I/O over SSE, persist each run's log + report, read past
 * runs back, and manage panel settings.
 *
 * Run:  node web/server.js   (or npm start)  ->  http://localhost:8765
 */
'use strict';

const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');
const url = require('url');
const crypto = require('crypto');
const { spawn, execFile } = require('child_process');
const resolve = require('./resolve');
const harmonyMirror = require('./harmony-mirror');

const ROOT = path.resolve(__dirname, '..');         // project root (holds .claude/)
const PUBLIC = path.join(__dirname, 'public');
const REPOS = path.join(ROOT, 'repos');
const RUNS = path.join(ROOT, 'runs');
const SETTINGS_FILE = path.join(ROOT, '.panel-settings.json');
const AGENT_FILE = '.claude/agents/pc-lib-analyzer.md';
const RESOLVE_AGENT_DIR = path.join(ROOT, '.resolve-agent');   // scratch for repo-resolver job results
const PORT = process.env.PORT || 8765;

const DEFAULT_PROMPT =
  'Analyze the PC third-party library checked out at {repoPath}. Follow the ' +
  'method and JSON output contract in {agentFile} and the skills it references. ' +
  'The source is already cloned — do NOT clone again. Do NOT spawn sub-agents or use the ' +
  '`task` tool — do all evidence-gathering yourself in this single session (codegraph + ' +
  'Grep/Glob/Read) so every step streams to the live log. {codegraphHint}Run the deterministic ' +
  'code-metrics script with `--out {metricsPath}`, reason through every dimension ' +
  '(function summary, license, dependencies, native/platform API), and write the ' +
  'final report to {reportPath}. Conform to references/report_schema.json. ' +
  '语言要求：function_summary 里所有自然语言字段（summary、每个 category 的 name 与 ' +
  'description、domain、target_users）以及 library.one_liner 必须用简体中文书写；' +
  'SPDX 许可证标识、编程语言名、依赖包名等专有名词保持原文。' +
  'IMPORTANT: write the report, metrics, and ALL intermediate/scratch files inside ' +
  'the project (under the run directory) — never use /tmp or any path outside the ' +
  'project, because the headless runner auto-rejects external directories and the ' +
  'run will abort. Finish with a short digest.';

const DEFAULT_SETTINGS = {
  model: '',
  opencodeCmd: 'opencode run',
  promptTemplate: DEFAULT_PROMPT,
  maxConcurrent: 3,
  printLogs: false,
  thinking: true,
  useCodegraph: true,
  pruneGitAfterAnalyze: true,
  enableNetworkResolve: true,
  enableHarmonyMirror: true,
  enableAgentResolve: true,
};

// codegraph is optional: probe once at startup. The analyze prompt only mentions
// codegraph when it is BOTH installed and enabled in settings; otherwise the
// agent falls back to grep/Read.
let codegraphAvailable = false;
execFile('codegraph', ['--version'], { timeout: 5000 }, (err) => {
  codegraphAvailable = !err;
  console.log(`  codegraph: ${codegraphAvailable ? 'available' : 'not found (analyses fall back to grep)'}`);
});

for (const d of [REPOS, RUNS, RESOLVE_AGENT_DIR]) fs.mkdirSync(d, { recursive: true });

let settings = loadSettings();
function loadSettings() {
  try { return { ...DEFAULT_SETTINGS, ...JSON.parse(fs.readFileSync(SETTINGS_FILE, 'utf8')) }; }
  catch { return { ...DEFAULT_SETTINGS }; }
}
function saveSettings(patch) {
  settings = { ...settings, ...patch };
  if (!(settings.maxConcurrent >= 1)) settings.maxConcurrent = 1;
  try { fs.writeFileSync(SETTINGS_FILE, JSON.stringify(settings, null, 2)); } catch (_) {}
  pumpAnalyze();
  return settings;
}

// ---------------------------------------------------------------- job registry
/** @type {Map<string, Job>} */
const jobs = new Map();

class Job {
  constructor(type, meta) {
    this.id = crypto.randomBytes(6).toString('hex');
    this.type = type;                 // 'clone' | 'analyze'
    this.meta = meta;                 // { name, model, argv, runDir, reportPath, prompt }
    this.status = 'running';          // queued | running | done | error
    this.exitCode = null;
    this.startedAt = new Date().toISOString();
    this.endedAt = null;
    this.events = [];
    this.clients = new Set();
    this.onDone = null;
    jobs.set(this.id, this);
  }
  setStatus(s) { this.status = s; this.emit('status', { status: s }); }
  emit(event, data) {
    const payload = { event, data, t: new Date().toISOString() };
    this.events.push(payload);
    if (this.events.length > 5000) this.events.shift();
    const frame = `event: ${event}\ndata: ${JSON.stringify(payload)}\n\n`;
    for (const res of this.clients) { try { res.write(frame); } catch (_) {} }
    if (this.logStream && (event === 'log' || event === 'input' || event === 'end'))
      this.logStream.write(JSON.stringify(payload) + '\n');
  }
  log(stream, text) { this.emit('log', { stream, text }); }
  end(code) {
    // exit 0 but no report (analyze) is an incomplete run, not success.
    const reportAvailable = this.meta.reportPath ? fs.existsSync(this.meta.reportPath) : false;
    if (code === 0 && this.type === 'analyze' && !reportAvailable) this.status = 'error';
    else this.status = code === 0 ? 'done' : 'error';
    this.exitCode = code;
    this.endedAt = new Date().toISOString();
    if (this.type === 'analyze' && this.status === 'done' && settings.pruneGitAfterAnalyze)
      this.pruneGit();
    this.emit('end', { code, status: this.status, reportAvailable });
    if (this.logStream) this.logStream.end();
    this.persistMeta();
    if (this.onDone) this.onDone();
    setTimeout(() => { for (const r of this.clients) { try { r.end(); } catch (_) {} } }, 250);
  }
  pruneGit() {
    const gitDir = path.join(REPOS, this.meta.name, '.git');
    try {
      if (fs.existsSync(gitDir)) {
        fs.rmSync(gitDir, { recursive: true, force: true });
        this.log('stdout', `[prune] 已删除 repos/${this.meta.name}/.git 以回收磁盘`);
      }
    } catch (e) { this.log('stderr', `[prune] 删除 .git 失败：${e.message}`); }
  }
  persistMeta() {
    if (!this.meta.runDir) return;
    const m = { id: this.id, type: this.type, status: this.status, exitCode: this.exitCode,
      startedAt: this.startedAt, endedAt: this.endedAt, ...this.meta };
    try { fs.writeFileSync(path.join(this.meta.runDir, 'meta.json'), JSON.stringify(m, null, 2)); } catch (_) {}
  }
}

function pipeProcess(job, child) {
  const wire = (stream, src) => {
    let buf = '';
    src.setEncoding('utf8');
    src.on('data', (chunk) => {
      buf += chunk;
      let idx;
      while ((idx = buf.indexOf('\n')) >= 0) { job.log(stream, buf.slice(0, idx)); buf = buf.slice(idx + 1); }
    });
    src.on('end', () => { if (buf.length) job.log(stream, buf); });
  };
  wire('stdout', child.stdout);
  wire('stderr', child.stderr);
  child.on('error', (err) => { job.log('stderr', `[spawn error] ${err.message}`); job.end(127); });
  child.on('close', (code) => job.end(code == null ? -1 : code));
}

// ---------------------------------------------------------------- helpers
function send(res, code, body, headers = {}) {
  const data = typeof body === 'string' ? body : JSON.stringify(body);
  res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', ...headers });
  res.end(data);
}
function readBody(req) {
  return new Promise((resolve) => {
    let b = '';
    req.on('data', (c) => (b += c));
    req.on('end', () => { try { resolve(b ? JSON.parse(b) : {}); } catch { resolve({}); } });
  });
}
function repoNameFromUrl(u) {
  const base = u.replace(/\/+$/, '').split('/').pop() || 'repo';
  return base.replace(/\.git$/i, '').replace(/[^A-Za-z0-9._-]/g, '_');
}
// Turn a pasted *web* URL into a clonable git URL. Users often paste browser URLs
// (esp. GitLab `…/-/tree/main`, subgroup paths, or a bare repo URL with no `.git`),
// which `git clone` can't use. Known hosts get cleaned; unknown hosts pass through.
const KNOWN_GIT_HOSTS = /^(?:www\.)?(github\.com|gitlab\.com|gitee\.com|gitcode\.(?:com|net)|bitbucket\.org|codeberg\.org)$/i;
function normalizeCloneUrl(raw) {
  let u = String(raw || '').trim();
  if (!u) return u;
  u = u.split('#')[0].replace(/\?.*$/, '');
  const scp = u.match(/^[\w.-]+@([\w.-]+):(.+)$/);          // git@host:owner/repo(.git)
  if (scp) u = `https://${scp[1]}/${scp[2]}`;
  u = u.replace(/^git:\/\//i, 'https://').replace(/^ssh:\/\/(?:git@)?/i, 'https://');
  let m;
  try { m = new URL(u); } catch { return u; }
  if (!KNOWN_GIT_HOSTS.test(m.hostname)) return u;           // don't second-guess other hosts
  let p = m.pathname;
  const dash = p.indexOf('/-/');                             // GitLab non-repo separator
  if (dash >= 0) p = p.slice(0, dash);
  else p = p.replace(/\/(?:tree|blob|commits?|releases|tags|raw|wikis?|issues|merge_requests|pulls?)\b.*$/i, '');
  p = p.replace(/\/+$/, '').replace(/\.git$/i, '');
  if (!p || p === '') return u;
  return `https://${m.hostname.replace(/^www\./i, '')}${p}.git`;
}
// Best-effort extraction of a clonable git URL from a dependency's free-text
// `source` / `version` (e.g. "通过 FetchContent 从 https://github.com/x/y.git 获取"
// or a pip `git+https://host/x@ref`). Returns a cleaned URL or null — many deps
// (system libs, registry packages) legitimately have none.
function extractGitUrl(...texts) {
  for (const raw of texts) {
    const t = String(raw || '');
    if (!t) continue;
    // pip/npm style: git+https://...(@ref)
    let m = t.match(/git\+(https?:\/\/[^\s'"<>)]+)/i);
    if (m) return m[1].replace(/@[^/@]+$/, '').replace(/[.,;]+$/, '');
    // explicit .git URL anywhere in the text
    m = t.match(/https?:\/\/[^\s'"<>)]+?\.git\b/i);
    if (m) return m[0];
    // bare URL on a known git host
    m = t.match(/https?:\/\/(?:www\.)?(?:github\.com|gitlab\.com|gitee\.com|bitbucket\.org)\/[^\s'"<>)]+/i);
    if (m) return m[0].replace(/[.,;]+$/, '');
    // "owner/repo" shorthand: the model often writes "GitHub owner/repo …" /
    // "Gitee owner/repo" instead of a full URL — synthesize the canonical URL.
    m = t.match(/\b(github|gitlab|gitee)\b[\s:：/]*([A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+)/i);
    if (m) {
      const host = { github: 'github.com', gitlab: 'gitlab.com', gitee: 'gitee.com' }[m[1].toLowerCase()];
      return `https://${host}/${m[2].replace(/\.git$/i, '').replace(/[.,;]+$/, '')}.git`;
    }
  }
  return null;
}
function listRepos() {
  return fs.readdirSync(REPOS, { withFileTypes: true })
    .filter((d) => d.isDirectory() && !d.name.startsWith('.'))
    .map((d) => d.name).sort();
}
function runsForLib(name) {
  const libDir = path.join(RUNS, name);
  if (!fs.existsSync(libDir) || !fs.statSync(libDir).isDirectory()) return [];
  const out = [];
  for (const ts of fs.readdirSync(libDir)) {
    const runDir = path.join(libDir, ts);
    if (!fs.statSync(runDir).isDirectory()) continue;
    let meta = {};
    try { meta = JSON.parse(fs.readFileSync(path.join(runDir, 'meta.json'), 'utf8')); } catch (_) {}
    const reportAvailable = fs.existsSync(path.join(runDir, 'report.json'));
    // meta.json is written by the server at job end; if it is missing (e.g. the
    // server was stopped mid-run) fall back to report presence for the status.
    out.push({ name, run: ts, status: meta.status || (reportAvailable ? 'done' : 'unknown'),
      model: meta.model, startedAt: meta.startedAt || ts, endedAt: meta.endedAt, reportAvailable });
  }
  return out.sort((a, b) => (a.startedAt < b.startedAt ? 1 : -1));
}
function activeJobFor(name) {
  for (const j of jobs.values())
    if (j.meta.name === name && (j.status === 'running' || j.status === 'queued'))
      return { id: j.id, type: j.type, status: j.status };
  return null;
}
function reportSummary(name, run) {
  try {
    const r = JSON.parse(fs.readFileSync(path.join(RUNS, name, run, 'report.json'), 'utf8'));
    return {
      oneLiner: (r.library && r.library.one_liner) || (r.function_summary && r.function_summary.summary) || '',
      primary: r.languages && r.languages.primary,
      ecosystem: (r.library && r.library.ecosystem) || null,
      bindings: (r.library && r.library.bindings) || [],
      prodCode: r.code_metrics && r.code_metrics.production && r.code_metrics.production.code,
      testCases: r.tests && r.tests.test_cases,
      license: r.license && r.license.spdx,
      analyzedAt: r.library && r.library.analyzed_at,
    };
  } catch { return null; }
}
// run id like "2026-06-21T15-42-06-494Z" isn't valid ISO (time uses '-'); restore it.
function runIdToMs(ts) {
  const iso = String(ts || '').replace(/T(\d\d)-(\d\d)-(\d\d)-(\d\d\d)Z$/, 'T$1:$2:$3.$4Z');
  const ms = Date.parse(iso);
  return Number.isNaN(ms) ? null : ms;
}
function birthtimeMs(p) {
  try { const s = fs.statSync(p); return s.birthtimeMs || s.ctimeMs || null; } catch { return null; }
}
function listLibraries() {
  const repos = new Set(listRepos());
  const names = new Set([...repos]);
  if (fs.existsSync(RUNS))
    for (const n of fs.readdirSync(RUNS))
      try { if (fs.statSync(path.join(RUNS, n)).isDirectory()) names.add(n); } catch (_) {}
  return [...names].sort().map((name) => {
    const runs = runsForLib(name);
    const latest = runs[0] || null;
    const analyzedAt = latest ? (Date.parse(latest.endedAt || latest.startedAt) || runIdToMs(latest.run)) : null;
    const addedAt = (repos.has(name) ? birthtimeMs(path.join(REPOS, name)) : null)
      || birthtimeMs(path.join(RUNS, name));
    return {
      name, cloned: repos.has(name), runCount: runs.length,
      latest, active: activeJobFor(name),
      analyzedAt: analyzedAt || null, addedAt,
      summary: latest && latest.reportAvailable ? reportSummary(name, latest.run) : null,
    };
  });
}

// ---------------------------------------------------------------- dependency tree (offline)
function normName(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]/g, ''); }
// Normalize ecosystem aliases to the report enum so cross-language same-name
// deps (e.g. python 'click' vs another ecosystem's 'click') never collide.
function ecoNorm(s) {
  const e = String(s || '').toLowerCase().trim();
  if (/^(node|nodejs|npm|js|javascript|ts|typescript)$/.test(e)) return 'nodejs';
  if (/^(py|python|pypi)$/.test(e)) return 'python';
  if (/^(c|c\+\+|cpp|cxx|cc)$/.test(e)) return 'cpp';
  if (/^(java|maven|jvm|gradle)$/.test(e)) return 'java';
  if (/^(rust|cargo|crate|crates)$/.test(e)) return 'rust';
  if (/^(go|golang)$/.test(e)) return 'go';
  if (/^(dotnet|net|csharp|nuget)$/.test(e)) return 'dotnet';
  return e;
}
function latestReport(name) {
  const latest = runsForLib(name).find((r) => r.reportAvailable);
  if (!latest) return null;
  try { return JSON.parse(fs.readFileSync(path.join(RUNS, name, latest.run, 'report.json'), 'utf8')); }
  catch { return null; }
}
// Index analyzed libraries by `ecosystem + ':' + normalized(name)`, preferring the
// report's package_name over the repo dir name. Keys that resolve to >1 library
// are flagged ambiguous (we won't auto-link them).
function buildLibIndex(getRep) {
  const index = new Map();
  for (const lib of listLibraries()) {
    if (!lib.latest || !lib.latest.reportAvailable) continue;
    const rep = getRep(lib.name);
    if (!rep) continue;
    const eco = ecoNorm(rep.library && rep.library.ecosystem);
    const pkg = (rep.library && rep.library.package_name) || lib.name;
    for (const nm of new Set([pkg, lib.name])) {
      const key = eco + ':' + normName(nm);
      const cur = index.get(key);
      if (!cur) index.set(key, { libName: lib.name, ambiguous: false });
      else if (cur.libName !== lib.name) cur.ambiguous = true;
    }
  }
  return index;
}
// Companion to buildLibIndex keyed by the analyzed library's REPO identity, so a
// dependency can be matched by its source-URL repo name even when its declared
// `name` differs (e.g. rdkit's dep "AvalonTools" == analyzed repo "ava-formake").
function buildLibUrlIndex(getRep) {
  const index = new Map();
  const add = (key, libName) => {
    const cur = index.get(key);
    if (!cur) index.set(key, { libName, ambiguous: false });
    else if (cur.libName !== libName) cur.ambiguous = true;
  };
  for (const lib of listLibraries()) {
    if (!lib.latest || !lib.latest.reportAvailable) continue;
    const rep = getRep(lib.name);
    if (!rep) continue;
    const eco = ecoNorm(rep.library && rep.library.ecosystem);
    const repoNames = new Set([lib.name]);
    const su = rep.library && rep.library.source_url;
    if (su) repoNames.add(repoNameFromUrl(su));
    for (const rn of repoNames) if (rn) add(eco + ':' + normName(rn), lib.name);
  }
  return index;
}
// Match a dependency to an analyzed library: by ecosystem+name first, then by the
// repo identity resolved from its source URL (mirrors the panel's repoName logic).
function resolveDepLib(d, byName, byRepo) {
  const eco = ecoNorm(d.ecosystem);
  let hit = byName.get(eco + ':' + normName(d.name));
  if (hit) return hit;
  const url = extractGitUrl(d.source, d.version);
  if (url) hit = byRepo.get(eco + ':' + normName(repoNameFromUrl(url)));
  return hit;
}
function buildDepTree(rootName, maxDepth) {
  const repCache = new Map();
  const getRep = (n) => { if (!repCache.has(n)) repCache.set(n, latestReport(n)); return repCache.get(n); };
  const index = buildLibIndex(getRep);
  const urlIndex = buildLibUrlIndex(getRep);
  const seen = new Set([rootName]);
  const expand = (libName, depth) => {
    const rep = getRep(libName);
    const deps = (rep && rep.dependencies && rep.dependencies.dependencies) || [];
    return deps.map((d) => {
      const hit = resolveDepLib(d, index, urlIndex);
      const analyzed = !!hit && !hit.ambiguous && hit.libName !== libName;
      const node = {
        name: d.name, ecosystem: d.ecosystem || null, scope: d.scope || null,
        version: d.version || null, purpose: d.purpose || '',
        acquisition: d.acquisition || null, locality: d.locality || null, source: d.source || '',
        declared_in: Array.isArray(d.declared_in) ? d.declared_in : [],
        analyzed, ambiguous: !!(hit && hit.ambiguous),
        libName: analyzed ? hit.libName : null, children: [],
      };
      if (analyzed && depth < maxDepth && !seen.has(hit.libName)) {
        seen.add(hit.libName);
        node.children = expand(hit.libName, depth + 1);
      }
      return node;
    });
  };
  return expand(rootName, 1);
}

// HarmonyOS porting class (4-way) for the dep-topology page. Prefers the agent's
// explicit harmony_adaptation.porting_class; else derives from the existing dim-9 fields
// so 存量 reports are classified without a re-run.
const PLATFORM_BLOCKER_RE = /win32|x11|xcb|cocoa|coregraphics|iokit|registry|wmi|sysfs|procfs|gpu|cuda|opencl|vulkan|device|driver|kernel|syscall|ioctl|permission|hardware|_api\b|api_unavailable|platform/i;
function derivePortingClass(report) {
  const ha = (report && report.harmony_adaptation) || null;
  if (!ha) return null;
  if (ha.porting_class) return ha.porting_class;          // explicit (agent)
  if (ha.feasibility === 'infeasible') return 'infeasible';
  const blk = Array.isArray(ha.blockers) ? ha.blockers : [];
  const cats = blk.map((b) => String(b.category || '').toLowerCase());
  const hasBlocker = blk.some((b) => b.severity === 'blocker');
  const platformish = cats.some((c) => PLATFORM_BLOCKER_RE.test(c));
  if (hasBlocker || platformish) return 'needs_adaptation';
  const path = String(ha.recommended_path || '').toLowerCase();
  const native = cats.some((c) => /native_dependency|ffi|toolchain|posix/.test(c));
  if (/run_on_ported_runtime/.test(path) && !native) return 'no_adaptation';
  if (native) return 'recompile_only';
  // pure script, no native work, no blockers → nothing to adapt
  return 'no_adaptation';
}

// Runtime-relevant dep (for the topology): runtime/optional (or unscoped), not local.
function isRuntimeDep(d) {
  if (String(d.locality || '').toLowerCase() === 'local') return false;
  const sc = String(d.scope || '').toLowerCase();
  if (sc && !['runtime', 'optional', 'peer'].includes(sc)) return false;
  return true;
}

// Build a runtime-only transitive dependency DAG (nodes + edges) rooted at an analyzed
// library, each node carrying its HarmonyOS status (harmonized / 4 porting classes /
// unanalyzed). harmony_adapted is filled per-node from the shared mirror cache later.
function buildDepTopology(rootName, maxDepth = 6, maxNodes = 300) {
  const repCache = new Map();
  const getRep = (n) => { if (!repCache.has(n)) repCache.set(n, latestReport(n)); return repCache.get(n); };
  const index = buildLibIndex(getRep);
  const urlIndex = buildLibUrlIndex(getRep);
  const nodes = new Map();   // id -> node
  const edges = [];
  const edgeSeen = new Set();
  const rootRep = getRep(rootName);
  const rootEco = ecoNorm(rootRep && rootRep.library && rootRep.library.ecosystem);
  const rootId = 'lib:' + rootName;
  nodes.set(rootId, { id: rootId, label: rootName, ecosystem: rootEco, analyzed: true,
    libName: rootName, isRoot: true });
  const queue = [{ libName: rootName, id: rootId, depth: 0 }];
  while (queue.length) {
    const cur = queue.shift();
    if (cur.depth >= maxDepth || nodes.size >= maxNodes) continue;
    const rep = getRep(cur.libName);
    const deps = (rep && rep.dependencies && rep.dependencies.dependencies) || [];
    for (const d of deps) {
      if (!d || !d.name || !isRuntimeDep(d)) continue;
      const hit = resolveDepLib(d, index, urlIndex);
      const analyzed = !!hit && !hit.ambiguous;
      const id = analyzed ? 'lib:' + hit.libName : 'dep:' + ecoNorm(d.ecosystem) + ':' + normName(d.name);
      if (!nodes.has(id)) {
        if (nodes.size >= maxNodes) continue;
        nodes.set(id, { id, label: d.name, ecosystem: ecoNorm(d.ecosystem), analyzed,
          libName: analyzed ? hit.libName : null,
          harmonyAdaptedStamp: d.harmony_adapted === true });
        if (analyzed && hit.libName !== cur.libName) queue.push({ libName: hit.libName, id, depth: cur.depth + 1 });
      }
      const ek = cur.id + '>' + id;
      if (cur.id !== id && !edgeSeen.has(ek)) { edgeSeen.add(ek); edges.push({ source: cur.id, target: id }); }
    }
  }
  // classify each node
  for (const node of nodes.values()) {
    if (node.analyzed) {
      const rep = getRep(node.libName);
      node.portingClass = derivePortingClass(rep);
      const ha = (rep && rep.harmony_adaptation) || {};
      node.feasibility = ha.feasibility || null;
      node.summary = ha.summary || '';
    }
  }
  return { root: rootName, nodes: [...nodes.values()], edges };
}

// ---------------------------------------------------------------- clone
function startClone({ url: rawUrl, ref, overwrite }) {
  const gitUrl = normalizeCloneUrl(rawUrl);
  const name = repoNameFromUrl(gitUrl);
  const dest = path.join(REPOS, name);
  if (fs.existsSync(dest)) {
    if (!overwrite) throw new Error(`repos/${name} already exists (enable overwrite to re-clone)`);
    fs.rmSync(dest, { recursive: true, force: true });
  }
  const args = ['clone', '--progress', '--depth', '1'];
  if (ref) args.push('--branch', ref);
  args.push(gitUrl, dest);
  const job = new Job('clone', { name, argv: ['git', ...args], url: gitUrl });
  job.emit('input', { argv: job.meta.argv });
  // stdin 'ignore' (EOF): opencode/tools block on an open stdin pipe.
  // GIT_TERMINAL_PROMPT=0: a private/auth-required URL fails fast instead of hanging
  // on a credential prompt the headless clone can never answer.
  pipeProcess(job, spawn('git', args, { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, GIT_TERMINAL_PROMPT: '0' } }));
  return job;
}

// ---------------------------------------------------------------- analyze (queued)
const analyzeQueue = [];
let runningAnalyze = 0;

function createAnalyzeJob(opts) {
  const name = opts.name;
  if (!name || !fs.existsSync(path.join(REPOS, name)))
    throw new Error(`repo not found: repos/${name} (clone it first)`);
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const runDir = path.join(RUNS, name, ts);
  fs.mkdirSync(runDir, { recursive: true });
  const reportPath = path.join(runDir, 'report.json');

  const codegraphOn = codegraphAvailable && (opts.useCodegraph ?? settings.useCodegraph);
  const codegraphHint = codegraphOn
    ? `codegraph is installed and enabled: first build a structural index with ` +
      `\`codegraph index repos/${name}\`, then prefer ` +
      `\`codegraph context/query/callers -p repos/${name} -j\` for the function-summary ` +
      `and native/platform-API dimensions (fall back to grep/Read if any codegraph call fails). `
    : '';
  let prompt = (opts.promptTemplate || settings.promptTemplate || DEFAULT_PROMPT)
    .replaceAll('{codegraphHint}', codegraphHint)
    .replaceAll('{repoPath}', `repos/${name}`)
    .replaceAll('{agentFile}', AGENT_FILE)
    .replaceAll('{reportPath}', path.relative(ROOT, reportPath))
    .replaceAll('{metricsPath}', path.relative(ROOT, path.join(runDir, 'metrics.json')))
    .replaceAll('{name}', name);
  // Robust to stale saved templates that predate the {codegraphHint} placeholder:
  // if codegraph is enabled but the hint didn't land, append it.
  if (codegraphHint && !prompt.includes('codegraph')) prompt = prompt + ' ' + codegraphHint;
  // Always forbid sub-agents (even for stale saved templates): opencode does not stream
  // sub-agent (task tool) sessions, so they black-hole the live log. Keep work inline.
  if (!/sub-agent|`task` tool/.test(prompt))
    prompt = prompt + ' Do NOT spawn sub-agents or use the `task` tool; do all work yourself in this single session.';

  const base = (opts.opencodeCmd || settings.opencodeCmd).trim().split(/\s+/);
  const model = opts.model || settings.model;
  const argv = [...base];
  if (model) argv.push('-m', model);
  if (opts.agent) argv.push('--agent', opts.agent);
  argv.push('--format', 'json');
  if (opts.thinking ?? settings.thinking) argv.push('--thinking');  // stream model reasoning
  if (opts.printLogs ?? settings.printLogs) argv.push('--print-logs');
  argv.push(prompt);

  const job = new Job('analyze', { name, model, runDir, reportPath, argv, prompt });
  job.setStatus('queued');
  analyzeQueue.push(job);
  pumpAnalyze();
  return job;
}

function pumpAnalyze() {
  while (runningAnalyze < settings.maxConcurrent && analyzeQueue.length) {
    const job = analyzeQueue.shift();
    runningAnalyze++;
    job.onDone = () => { runningAnalyze--; pumpAnalyze(); };
    spawnAnalyze(job);
  }
}

function spawnAnalyze(job) {
  job.setStatus('running');
  job.logStream = fs.createWriteStream(path.join(job.meta.runDir, 'run.log.jsonl'), { flags: 'a' });
  job.emit('input', { argv: job.meta.argv, prompt: job.meta.prompt, runDir: path.relative(ROOT, job.meta.runDir) });
  const argv = job.meta.argv;
  pipeProcess(job, spawn(argv[0], argv.slice(1), { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] }));
}

// ---------------------------------------------------------------- agent repo-resolver (queued)
const agentResolveQueue = [];
let runningAgentResolve = 0;
const AGENT_RESOLVE_MAX = 2;

function lsRemoteOk(url, cb) {
  if (!url) return cb(false);
  execFile('git', ['ls-remote', '--heads', url], { timeout: 25000, env: { ...process.env, GIT_TERMINAL_PROMPT: '0' } },
    (err, out) => cb(!err && !!String(out || '').trim()));
}

function createAgentResolveJob(ctx) {
  const eco = ecoNorm(ctx.ecosystem);
  const name = String(ctx.name || '').trim();
  if (!name) throw new Error('name required');
  const job = new Job('resolve', { name, ecosystem: eco });
  job.meta.outFile = path.join(RESOLVE_AGENT_DIR, job.id + '.json');
  job.meta.resolveDone = false;
  // dependent checkouts that actually exist (the agent greps them for the integration point)
  const dependents = (ctx.dependents || []).filter((n) => n && fs.existsSync(path.join(REPOS, n)));
  const ctxLines = [
    `name: ${name}`, `ecosystem: ${eco}`, `scope: ${ctx.scope || ''}`,
    `locality: ${ctx.locality || ''}`, `acquisition: ${ctx.acquisition || ''}`,
    `source: ${ctx.source || ''}`, `purpose: ${ctx.purpose || ''}`,
    `dependent libraries (checkouts to grep): ${dependents.map((n) => 'repos/' + n).join(', ') || '(none cloned locally)'}`,
  ].join('\n');
  const prompt =
    `Resolve the upstream source-repository URL of this third-party dependency. Follow the ` +
    `method and JSON output contract in .claude/agents/repo-resolver.md.\n\nContext:\n${ctxLines}\n\n` +
    `OUT_FILE (write your one-line JSON verdict here, inside the project): ${path.relative(ROOT, job.meta.outFile)}\n` +
    `Do all work yourself in this single session; do NOT spawn sub-agents or use the \`task\` tool.`;
  const base = settings.opencodeCmd.trim().split(/\s+/);
  const argv = [...base];
  if (settings.model) argv.push('-m', settings.model);
  argv.push('--agent', 'repo-resolver', '--format', 'json', prompt);
  job.meta.argv = argv;
  job.setStatus('queued');
  agentResolveQueue.push(job);
  pumpAgentResolve();
  return job;
}

function pumpAgentResolve() {
  while (runningAgentResolve < AGENT_RESOLVE_MAX && agentResolveQueue.length) {
    const job = agentResolveQueue.shift();
    runningAgentResolve++;
    job.onDone = () => { runningAgentResolve--; finishAgentResolve(job); pumpAgentResolve(); };
    job.setStatus('running');
    job.emit('input', { argv: job.meta.argv });
    pipeProcess(job, spawn(job.meta.argv[0], job.meta.argv.slice(1), { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] }));
  }
}

// After the agent exits: read its JSON verdict, verify the URL, cache it, mark done.
function finishAgentResolve(job) {
  let v = null;
  try { v = JSON.parse(fs.readFileSync(job.meta.outFile, 'utf8')); } catch (_) {}
  fs.unlink(job.meta.outFile, () => {});
  if (!v || typeof v !== 'object') {
    job.meta.result = { url: null, source: 'agent', confidence: null, candidates: [], is_system: false,
      reasoning: '解析失败：agent 未产出有效结果' };
    job.meta.resolveDone = true;
    return;
  }
  const result = {
    url: v.is_system ? null : (v.url || null), source: 'agent',
    confidence: v.confidence || null, reasoning: v.reasoning || '',
    is_system: !!v.is_system, candidates: Array.isArray(v.candidates) ? v.candidates : [],
  };
  const done = () => {
    resolve.cachePut(job.meta.ecosystem, job.meta.name, result);
    job.meta.result = result;
    job.meta.resolveDone = true;
  };
  if (result.url) lsRemoteOk(result.url, (ok) => {
    if (!ok) {   // unreachable → demote to a candidate, clear the auto-fill url
      if (!result.candidates.some((c) => (c.url || c) === result.url))
        result.candidates.unshift({ name: result.url, url: result.url });
      result.url = null;
      result.confidence = 'low';
      result.reasoning = (result.reasoning ? result.reasoning + ' ' : '') + '（注：该 URL ls-remote 不可达，已降级为候选）';
    }
    done();
  });
  else done();
}

/** Quick liveness probe for a model: tiny prompt, short timeout. */
function testModel(model, cb) {
  model = model || settings.model;
  if (!model) return cb({ ok: false, error: 'no model specified' });
  const child = spawn('opencode', ['run', '-m', model, 'reply with exactly the word: pong'],
    { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
  let out = '', err = '';
  const t0 = Date.now();
  child.stdout.on('data', (d) => (out += d));
  child.stderr.on('data', (d) => (err += d));
  const killer = setTimeout(() => { try { child.kill(); } catch (_) {} }, 30000);
  child.on('error', (e) => { clearTimeout(killer); cb({ ok: false, error: e.message }); });
  child.on('close', (code) => {
    clearTimeout(killer);
    const ms = Date.now() - t0, stdout = out.trim();
    if (code === 0 && stdout) return cb({ ok: true, ms, output: stdout.slice(0, 200) });
    const firstErr = err.split('\n').map((s) => s.trim())
      .find((s) => s && !/service=/.test(s) && !/^\x1b/.test(s)) || `exit ${code}`;
    cb({ ok: false, ms, error: firstErr.replace(/\x1b\[[0-9;]*m/g, '').slice(0, 240) });
  });
}

// ---------------------------------------------------------------- static
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml' };
function serveStatic(req, res, pathname) {
  const file = path.join(PUBLIC, pathname === '/' ? 'index.html' : pathname);
  if (!file.startsWith(PUBLIC)) return send(res, 403, { error: 'forbidden' });
  fs.readFile(file, (err, data) => {
    if (err) return send(res, 404, { error: 'not found' });
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
    res.end(data);
  });
}

// ---------------------------------------------------------------- server
const server = http.createServer(async (req, res) => {
  const { pathname, query } = url.parse(req.url, true);
  try {
    if (req.method === 'GET' && pathname === '/api/libraries')
      return send(res, 200, { libraries: listLibraries() });

    if (req.method === 'GET' && pathname === '/api/library') {
      const name = query.name;
      if (!name || !fs.existsSync(path.join(RUNS, name)) && !fs.existsSync(path.join(REPOS, name)))
        return send(res, 404, { error: 'unknown library' });
      return send(res, 200, { name, cloned: fs.existsSync(path.join(REPOS, name)),
        runs: runsForLib(name), active: activeJobFor(name) });
    }

    if (req.method === 'GET' && pathname === '/api/jobs')
      return send(res, 200, { jobs: [...jobs.values()].map((j) => ({
        id: j.id, type: j.type, name: j.meta.name, status: j.status,
        startedAt: j.startedAt, exitCode: j.exitCode })) });

    if (req.method === 'GET' && pathname === '/api/settings')
      return send(res, 200, { settings, defaults: DEFAULT_SETTINGS, codegraphAvailable });
    if (req.method === 'POST' && pathname === '/api/settings') {
      const body = await readBody(req);
      return send(res, 200, { settings: saveSettings(body) });
    }

    if (req.method === 'GET' && pathname === '/api/models')
      return execFile('opencode', ['models'], { timeout: 15000 }, (e, out) =>
        send(res, 200, { models: e ? [] : out.split('\n').map((s) => s.trim()).filter(Boolean) }));

    if (req.method === 'GET' && pathname === '/api/testmodel')
      return testModel(query.model, (r) => send(res, 200, r));

    if (req.method === 'POST' && pathname === '/api/clone') {
      const body = await readBody(req);
      const urls = body.urls || (body.url ? [body.url] : []);
      if (!urls.length) return send(res, 400, { error: 'url(s) required' });
      const out = urls.map((u) => {
        try { const j = startClone({ url: u, ref: body.ref, overwrite: body.overwrite });
          return { url: u, jobId: j.id, name: j.meta.name }; }
        catch (e) { return { url: u, error: String(e.message || e) }; }
      });
      return send(res, 200, { jobs: out });
    }

    if (req.method === 'POST' && pathname === '/api/analyze') {
      const body = await readBody(req);
      const names = body.names || (body.name ? [body.name] : []);
      if (!names.length) return send(res, 400, { error: 'name(s) required' });
      const out = names.map((n) => {
        try { const j = createAnalyzeJob({ ...body, name: n });
          return { name: n, jobId: j.id, runDir: path.relative(ROOT, j.meta.runDir), status: j.status }; }
        catch (e) { return { name: n, error: String(e.message || e) }; }
      });
      return send(res, 200, { jobs: out });
    }

    if (req.method === 'GET' && pathname === '/api/stream') {
      const job = jobs.get(query.job);
      if (!job) return send(res, 404, { error: 'unknown job' });
      res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
      res.write('retry: 2000\n\n');
      for (const ev of job.events) res.write(`event: ${ev.event}\ndata: ${JSON.stringify(ev)}\n\n`);
      if (job.status === 'done' || job.status === 'error') { res.end(); return; }
      job.clients.add(res);
      const hb = setInterval(() => { try { res.write(': ping\n\n'); } catch (_) {} }, 15000);
      req.on('close', () => { clearInterval(hb); job.clients.delete(res); });
      return;
    }

    if (req.method === 'GET' && pathname === '/api/observations') {
      // Aggregate meta.observations across all libraries' latest reports (skill 反哺).
      const groups = new Map();   // key: dimension|field|kind|value -> {..., count, libs:Set}
      let total = 0;
      for (const lib of listLibraries()) {
        if (!lib.latest || !lib.latest.reportAvailable) continue;
        const rep = latestReport(lib.name);
        const obs = (rep && rep.meta && rep.meta.observations) || [];
        for (const o of obs) {
          total++;
          const dimension = o.dimension || '其他', field = o.field || '', kind = o.kind || 'gap', value = o.value || '';
          const key = [dimension, field, kind, value].join('|');
          let g = groups.get(key);
          if (!g) { g = { dimension, field, kind, value, rationale: o.rationale || '', count: 0, libs: new Set() }; groups.set(key, g); }
          g.count++; g.libs.add(lib.name);
        }
      }
      const items = [...groups.values()].map((g) => ({ ...g, libs: [...g.libs] }))
        .sort((a, b) => b.count - a.count);
      return send(res, 200, { total, items });
    }

    if (req.method === 'GET' && pathname === '/api/pending-deps') {
      // Aggregate, across every analyzed library, the dependencies that are NOT
      // themselves an analyzed library — the "third-party libs depended on but not
      // yet analyzed". Reuses the same ecosystem+name index as the dep tree.
      const repCache = new Map();
      const getRep = (n) => { if (!repCache.has(n)) repCache.set(n, latestReport(n)); return repCache.get(n); };
      const index = buildLibIndex(getRep);
      const urlIndex = buildLibUrlIndex(getRep);
      const repos = new Set(listRepos());
      const groups = new Map();   // key: eco:normname -> aggregated dep
      for (const lib of listLibraries()) {
        if (!lib.latest || !lib.latest.reportAvailable) continue;
        const rep = getRep(lib.name);
        const deps = (rep && rep.dependencies && rep.dependencies.dependencies) || [];
        for (const d of deps) {
          if (!d || !d.name) continue;
          const eco = ecoNorm(d.ecosystem);
          const key = eco + ':' + normName(d.name);
          if (resolveDepLib(d, index, urlIndex)) continue;   // already an analyzed library (by name or source-URL repo)
          let g = groups.get(key);
          if (!g) {
            g = { name: d.name, ecosystem: d.ecosystem || null, count: 0,
              dependents: [], scopes: new Set(), locality: d.locality || null,
              acquisition: d.acquisition || null, source: d.source || '', candidateUrl: null };
            groups.set(key, g);
          }
          g.count++;
          g.dependents.push({ lib: lib.name, purpose: d.purpose || '', scope: d.scope || null });
          if (d.scope) g.scopes.add(d.scope);
          if (!g.locality && d.locality) g.locality = d.locality;
          if (!g.acquisition && d.acquisition) g.acquisition = d.acquisition;
          if (!g.candidateUrl) g.candidateUrl = extractGitUrl(d.source, d.version);
          if (!g.source && d.source) g.source = d.source;
        }
      }
      const items = [...groups.values()].map((g) => {
        const repoName = g.candidateUrl ? repoNameFromUrl(g.candidateUrl) : null;
        return {
          name: g.name, ecosystem: g.ecosystem, count: g.count,
          dependents: g.dependents, scopes: [...g.scopes],
          locality: g.locality, acquisition: g.acquisition,
          source: g.source, candidateUrl: g.candidateUrl, repoName,
          cloned: !!repoName && repos.has(repoName),
          active: repoName ? activeJobFor(repoName) : null,
        };
      }).sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
      return send(res, 200, { total: items.length, items });
    }

    if (req.method === 'GET' && pathname === '/api/depgraph') {
      const name = query.name;
      if (!name) return send(res, 400, { error: 'name required' });
      if (!latestReport(name)) return send(res, 404, { error: 'no report for library' });
      const depth = Math.min(Math.max(parseInt(query.depth, 10) || 3, 1), 5);
      return send(res, 200, { root: name, depth, tree: buildDepTree(name, depth) });
    }

    if (req.method === 'GET' && pathname === '/api/dep-topology') {
      const name = query.name;
      if (!name) return send(res, 400, { error: 'name required' });
      if (!latestReport(name)) return send(res, 404, { error: 'no report for library' });
      const topo = buildDepTopology(name);
      // per-node 已鸿蒙化: query the OpenHarmony mirror in batch (per ecosystem) when enabled;
      // else fall back to the parent-stamped harmony_adapted flag.
      if (settings.enableHarmonyMirror) {
        const byEco = new Map();
        for (const n of topo.nodes) { if (!byEco.has(n.ecosystem)) byEco.set(n.ecosystem, new Set()); byEco.get(n.ecosystem).add(n.label); }
        for (const [eco, names] of byEco) {
          try { const r = await harmonyMirror.statusFor(eco, [...names]); for (const n of topo.nodes) if (n.ecosystem === eco) n.harmonyAdapted = !!(r.results[n.label] && r.results[n.label].adapted); }
          catch (_) { for (const n of topo.nodes) if (n.ecosystem === eco) n.harmonyAdapted = !!n.harmonyAdaptedStamp; }
        }
      } else {
        for (const n of topo.nodes) n.harmonyAdapted = !!n.harmonyAdaptedStamp;
      }
      // final status per node: harmonized > (analyzed ? porting_class : unanalyzed)
      const counts = {};
      for (const n of topo.nodes) {
        n.status = n.isRoot && !n.harmonyAdapted && n.portingClass ? n.portingClass
          : n.harmonyAdapted ? 'harmonized'
          : n.analyzed ? (n.portingClass || 'unanalyzed')
          : 'unanalyzed';
        delete n.harmonyAdaptedStamp;
        counts[n.status] = (counts[n.status] || 0) + 1;
      }
      return send(res, 200, { ...topo, counts });
    }

    if (req.method === 'GET' && pathname === '/api/report') {
      const file = path.join(RUNS, query.name || '', query.run || '', 'report.json');
      if (!file.startsWith(RUNS) || !fs.existsSync(file)) return send(res, 404, { error: 'report not found' });
      return send(res, 200, fs.readFileSync(file, 'utf8'));
    }

    if (req.method === 'GET' && pathname === '/api/harmony-status') {
      if (!settings.enableHarmonyMirror) return send(res, 200, { disabled: true, results: {} });
      const names = (query.names ? String(query.names).split(',') : []).map((s) => s.trim()).filter(Boolean);
      if (!names.length) return send(res, 200, { results: {}, adaptedCount: 0, total: 0 });
      try {
        const r = await harmonyMirror.statusFor(ecoNorm(query.ecosystem), names);
        return send(res, 200, r);
      } catch (e) {
        return send(res, 200, { results: {}, error: String(e.message || e) });
      }
    }

    if (req.method === 'GET' && pathname === '/api/resolve-repo') {
      if (!query.name) return send(res, 400, { error: 'name required' });
      if (!settings.enableNetworkResolve)
        return send(res, 200, { url: null, disabled: true });
      try {
        const r = await resolve.resolveRepo(ecoNorm(query.ecosystem), query.name);
        return send(res, 200, { name: query.name, ecosystem: query.ecosystem || null, ...r });
      } catch (e) {
        return send(res, 200, { url: null, error: String(e.message || e) });
      }
    }

    if (req.method === 'POST' && pathname === '/api/resolve-repo-agent') {
      if (!settings.enableAgentResolve) return send(res, 200, { disabled: true });
      const body = await readBody(req);
      if (!body.name) return send(res, 400, { error: 'name required' });
      try {
        const job = createAgentResolveJob(body);
        return send(res, 200, { jobId: job.id });
      } catch (e) {
        return send(res, 500, { error: String(e.message || e) });
      }
    }
    if (req.method === 'GET' && pathname === '/api/resolve-repo-agent') {
      const job = jobs.get(query.job);
      if (!job || job.type !== 'resolve') return send(res, 404, { error: 'unknown job' });
      if (job.meta.resolveDone) return send(res, 200, { status: 'done', result: job.meta.result });
      if (job.status === 'error') return send(res, 200, { status: 'error' });
      return send(res, 200, { status: job.status });   // queued | running
    }

    if (req.method === 'GET' && pathname === '/api/export') {
      const tmp = path.join(os.tmpdir(), `pc-lib-export-${Date.now()}.xlsx`);
      const args = [path.join('scripts', 'export_xlsx.py'), '--runs', RUNS, '--out', tmp];
      if (query.names) args.push('--names', String(query.names));
      return execFile('python3', args, { cwd: ROOT, timeout: 120000 }, (err, _o, stderr) => {
        if (err || !fs.existsSync(tmp)) {
          fs.unlink(tmp, () => {});
          return send(res, 500, { error: 'export failed', detail: String(stderr || err || '').slice(0, 2000) });
        }
        let buf;
        try { buf = fs.readFileSync(tmp); } catch (e) { return send(res, 500, { error: 'export read failed', detail: String(e) }); }
        finally { fs.unlink(tmp, () => {}); }
        res.writeHead(200, {
          'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          'Content-Disposition': `attachment; filename="pc-lib-analysis-${new Date().toISOString().slice(0, 10)}.xlsx"`,
          'Content-Length': buf.length,
        });
        res.end(buf);
      });
    }

    if (req.method === 'GET' && pathname === '/api/runlog') {
      const file = path.join(RUNS, query.name || '', query.run || '', 'run.log.jsonl');
      if (!file.startsWith(RUNS) || !fs.existsSync(file)) return send(res, 404, { error: 'log not found' });
      return send(res, 200, fs.readFileSync(file, 'utf8'), { 'Content-Type': 'text/plain; charset=utf-8' });
    }

    if (pathname.startsWith('/api/')) return send(res, 404, { error: 'unknown endpoint' });
    return serveStatic(req, res, pathname);
  } catch (err) {
    return send(res, 400, { error: String(err.message || err) });
  }
});

server.listen(PORT, () => {
  console.log(`pc-lib-analysis control panel → http://localhost:${PORT}`);
  console.log(`  project root: ${ROOT}  ·  max concurrent analyses: ${settings.maxConcurrent}`);
});
