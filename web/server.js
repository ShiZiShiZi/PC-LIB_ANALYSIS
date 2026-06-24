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
const harmonyCaps = require('../scripts/harmony_caps');   // HarmonyOS PC 目标能力画像（读/同步/人工策展）

const ROOT = path.resolve(__dirname, '..');         // project root (holds .claude/)
const PUBLIC = path.join(__dirname, 'public');
const REPOS = path.join(ROOT, 'repos');
const RUNS = path.join(ROOT, 'runs');
const SETTINGS_FILE = path.join(ROOT, '.panel-settings.json');
const TAGS_FILE = path.join(ROOT, '.panel-library-tags.json');   // per-library 来源标签注册表
const AGENT_FILE = '.claude/agents/pc-lib-analyzer.md';
const RESOLVE_AGENT_DIR = path.join(ROOT, '.resolve-agent');   // scratch for repo-resolver job results
const PORT = process.env.PORT || 8765;
const isWindows = process.platform === 'win32';

const DEFAULT_PROMPT =
  'Analyze the PC open-source software project (a third-party library OR an application) ' +
  'checked out at {repoPath}. First decide library.kind (library/application/...). Follow the ' +
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

// Previous DEFAULT_PROMPT values. A persisted settings.promptTemplate that exactly
// matches one of these is a stale default (it predates a DEFAULT_PROMPT change — e.g.
// the "library OR application" rewrite), so loadSettings() auto-upgrades it to the
// current DEFAULT_PROMPT. A genuinely user-customized template never matches and is
// left untouched. When you change DEFAULT_PROMPT, append the OLD string here.
const LEGACY_PROMPTS = [
  // pre-"library OR application" default (said "Analyze the PC third-party library …")
  'Analyze the PC third-party library checked out at {repoPath}. Follow the method ' +
  'and JSON output contract in {agentFile} and the skills it references. The source ' +
  'is already cloned — do NOT clone again. Run the deterministic code-metrics script ' +
  'with `--out {metricsPath}`, reason through every dimension (function summary, ' +
  'license, dependencies, native/platform API), and write the final report to ' +
  '{reportPath}. Conform to references/report_schema.json. ' +
  '语言要求：function_summary 里所有自然语言字段（summary、每个 category 的 name 与 ' +
  'description、domain、target_users）以及 library.one_liner 必须用简体中文书写；' +
  'SPDX 许可证标识、编程语言名、依赖包名等专有名词保持原文。' +
  'IMPORTANT: write the report, metrics, and ALL intermediate/scratch files inside ' +
  'the project (under the run directory) — never use /tmp or any path outside the ' +
  'project, because the headless runner auto-rejects external directories and the ' +
  'run will abort. Finish with a short digest.',
];

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
  recursiveAfterAnalyze: false,   // auto-start recursive dep analysis after a manual analyze
};

// codegraph is optional: probe once at startup. The analyze prompt only mentions
// codegraph when it is BOTH installed and enabled in settings; otherwise the
// agent falls back to grep/Read.
let codegraphAvailable = false;
execFile('codegraph', ['--version'], { shell: isWindows, timeout: 5000 }, (err) => {
  codegraphAvailable = !err;
  console.log(`  codegraph: ${codegraphAvailable ? 'available' : 'not found (analyses fall back to grep)'}`);
});

// Build (or refresh) the codegraph structural index for a checkout so analysis can
// query it. Runs `init -i` the first time (creates .codegraph/), `sync` afterwards.
// No-op when codegraph isn't available or is disabled. onLog(line) streams progress.
const codegraphIndexing = new Set();   // repoPath currently being (re)indexed — dedupe
function ensureCodegraphIndex(repoPath, onLog) {
  if (!codegraphAvailable || !settings.useCodegraph) return;
  if (!repoPath || !fs.existsSync(repoPath) || codegraphIndexing.has(repoPath)) return;
  const initialized = fs.existsSync(path.join(repoPath, '.codegraph'));
  const args = initialized ? ['sync', repoPath] : ['init', '-i', repoPath];
  const log = (s) => { if (onLog) onLog(s); else console.log(`  codegraph: ${s}`); };
  codegraphIndexing.add(repoPath);
  log(`${initialized ? 'sync' : 'init -i'} ${path.relative(ROOT, repoPath)}…`);
  execFile('codegraph', args, { cwd: ROOT, timeout: 600000, maxBuffer: 16 * 1024 * 1024 }, (err) => {
    codegraphIndexing.delete(repoPath);
    log(err ? `index failed: ${String(err.message || err).split('\n')[0]}` : `index ready (${path.relative(ROOT, repoPath)})`);
  });
}

for (const d of [REPOS, RUNS, RESOLVE_AGENT_DIR]) fs.mkdirSync(d, { recursive: true });

// ---- 分组（工作空间隔离）-------------------------------------------------
// Libraries live under repos/<group>/<name> and runs/<group>/<name>/<ts>. The
// top level of repos/ and runs/ holds GROUP dirs (not libs). 'default' always exists.
const GROUP_RE = /^[A-Za-z0-9._-]{1,64}$/;
const safeGroup = (g) => (g && GROUP_RE.test(g) ? g : 'default');
const repoDir = (group, name) => path.join(REPOS, safeGroup(group), name);
const runLibDir = (group, name) => path.join(RUNS, safeGroup(group), name);
function listGroups() {
  const set = new Set(['default']);
  for (const base of [REPOS, RUNS]) {
    try { for (const d of fs.readdirSync(base, { withFileTypes: true }))
      if (d.isDirectory() && !d.name.startsWith('.')) set.add(d.name); } catch (_) {}
  }
  return ['default', ...[...set].filter((g) => g !== 'default').sort()];
}
function ensureGroupDirs(group) {
  const g = safeGroup(group);
  for (const base of [REPOS, RUNS]) fs.mkdirSync(path.join(base, g), { recursive: true });
  return g;
}
// One-time migration: pre-grouping layout had repos/<name> & runs/<name> at top level.
// Move them under default/ and re-key the tags file. Idempotent (skips once default/ exists).
function migrateToGroups() {
  for (const base of [REPOS, RUNS]) {
    const def = path.join(base, 'default');
    if (fs.existsSync(def)) continue;                 // already migrated for this base
    let entries = [];
    try { entries = fs.readdirSync(base, { withFileTypes: true }); } catch (_) { continue; }
    const libs = entries.filter((d) => d.isDirectory() && !d.name.startsWith('.') && d.name !== 'default');
    if (!libs.length) { fs.mkdirSync(def, { recursive: true }); continue; }
    fs.mkdirSync(def, { recursive: true });
    for (const d of libs) {
      try { fs.renameSync(path.join(base, d.name), path.join(def, d.name)); } catch (_) {}
    }
    console.log(`  migrated ${libs.length} entries under ${path.basename(base)}/ → default/`);
  }
  // re-key tags { "<name>": [...] } → { "default/<name>": [...] } when not already group-keyed
  try {
    if (fs.existsSync(TAGS_FILE)) {
      const t = JSON.parse(fs.readFileSync(TAGS_FILE, 'utf8'));
      if (t && typeof t === 'object' && Object.keys(t).some((k) => !k.includes('/'))) {
        const out = {};
        for (const [k, v] of Object.entries(t)) out[k.includes('/') ? k : `default/${k}`] = v;
        fs.writeFileSync(TAGS_FILE, JSON.stringify(out, null, 2));
      }
    }
  } catch (_) {}
}
migrateToGroups();

let settings = loadSettings();
function loadSettings() {
  let s;
  try { s = { ...DEFAULT_SETTINGS, ...JSON.parse(fs.readFileSync(SETTINGS_FILE, 'utf8')) }; }
  catch { return { ...DEFAULT_SETTINGS }; }
  // Auto-heal a stale persisted promptTemplate: if it exactly matches a known former
  // default, upgrade it to the current DEFAULT_PROMPT and rewrite the file so the
  // panel stops running the outdated prompt. User-customized templates never match.
  if (typeof s.promptTemplate === 'string' &&
      LEGACY_PROMPTS.some((p) => p.trim() === s.promptTemplate.trim())) {
    s.promptTemplate = DEFAULT_PROMPT;
    try { fs.writeFileSync(SETTINGS_FILE, JSON.stringify(s, null, 2)); } catch (_) {}
    console.log('  settings: upgraded a stale promptTemplate to the current default');
  }
  return s;
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
// Notified after every job ends (clone/analyze/resolve). The recursion driver
// subscribes here instead of fighting pumpAnalyze for job.onDone (which it owns).
const jobEndListeners = new Set();

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
    for (const fn of jobEndListeners) { try { fn(this); } catch (_) {} }
    setTimeout(() => { for (const r of this.clients) { try { r.end(); } catch (_) {} } }, 250);
  }
  pruneGit() {
    const gitDir = path.join(repoDir(this.meta.group, this.meta.name), '.git');
    try {
      if (fs.existsSync(gitDir)) {
        fs.rmSync(gitDir, { recursive: true, force: true });
        this.log('stdout', `[prune] 已删除 ${path.relative(ROOT, gitDir)} 以回收磁盘`);
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
function listRepos(group) {
  try {
    return fs.readdirSync(path.join(REPOS, safeGroup(group)), { withFileTypes: true })
      .filter((d) => d.isDirectory() && !d.name.startsWith('.'))
      .map((d) => d.name).sort();
  } catch { return []; }
}
function runsForLib(name, group) {
  const libDir = runLibDir(group, name);
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
function activeJobFor(name, group) {
  const g = safeGroup(group);
  for (const j of jobs.values())
    if (j.meta.name === name && safeGroup(j.meta.group) === g && (j.status === 'running' || j.status === 'queued'))
      return { id: j.id, type: j.type, status: j.status };
  return null;
}
function reportSummary(name, run, group) {
  try {
    const r = JSON.parse(fs.readFileSync(path.join(runLibDir(group, name), run, 'report.json'), 'utf8'));
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
// ---- per-library 来源标签 (主软件=primary / 被动依赖=passive) -----------------
// Persisted in .panel-library-tags.json as { "<lib>": ["primary","passive"], ... }.
// A lib can hold both; writes are union (addLibTag) so manual-clone + recursion compose.
const TAG_VALUES = ['primary', 'passive'];
function loadTags() {
  try { const t = JSON.parse(fs.readFileSync(TAGS_FILE, 'utf8')); return t && typeof t === 'object' ? t : {}; }
  catch { return {}; }
}
function saveTags(tags) {
  try { fs.writeFileSync(TAGS_FILE, JSON.stringify(tags, null, 2)); } catch (_) {}
}
const tagKey = (group, name) => `${safeGroup(group)}/${name}`;
function addLibTag(name, group, tag) {
  if (!name || !TAG_VALUES.includes(tag)) return;
  const tags = loadTags();
  const k = tagKey(group, name);
  const set = new Set(tags[k] || []);
  set.add(tag);
  tags[k] = [...set];
  saveTags(tags);
}
function setLibTags(name, group, list) {
  const tags = loadTags();
  const k = tagKey(group, name);
  const clean = [...new Set((Array.isArray(list) ? list : []).filter((t) => TAG_VALUES.includes(t)))];
  if (clean.length) tags[k] = clean; else delete tags[k];
  saveTags(tags);
  return clean;
}

function listLibraries(group) {
  const g = safeGroup(group);
  const repos = new Set(listRepos(g));
  const names = new Set([...repos]);
  const runsBase = path.join(RUNS, g);
  if (fs.existsSync(runsBase))
    for (const n of fs.readdirSync(runsBase))
      try { if (fs.statSync(path.join(runsBase, n)).isDirectory()) names.add(n); } catch (_) {}
  const allTags = loadTags();
  return [...names].sort().map((name) => {
    const runs = runsForLib(name, g);
    const latest = runs[0] || null;
    const analyzedAt = latest ? (Date.parse(latest.endedAt || latest.startedAt) || runIdToMs(latest.run)) : null;
    const addedAt = (repos.has(name) ? birthtimeMs(repoDir(g, name)) : null)
      || birthtimeMs(runLibDir(g, name));
    return {
      name, group: g, cloned: repos.has(name), runCount: runs.length,
      latest, active: activeJobFor(name, g),
      analyzedAt: analyzedAt || null, addedAt, tags: allTags[tagKey(g, name)] || [],
      summary: latest && latest.reportAvailable ? reportSummary(name, latest.run, g) : null,
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
function latestReport(name, group) {
  const g = safeGroup(group);
  const latest = runsForLib(name, g).find((r) => r.reportAvailable);
  if (!latest) return null;
  try { return JSON.parse(fs.readFileSync(path.join(runLibDir(g, name), latest.run, 'report.json'), 'utf8')); }
  catch { return null; }
}
// Index analyzed libraries by `ecosystem + ':' + normalized(name)`, preferring the
// report's package_name over the repo dir name. Keys that resolve to >1 library
// are flagged ambiguous (we won't auto-link them).
function buildLibIndex(getRep, group) {
  const index = new Map();
  for (const lib of listLibraries(group)) {
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
function buildLibUrlIndex(getRep, group) {
  const index = new Map();
  const add = (key, libName) => {
    const cur = index.get(key);
    if (!cur) index.set(key, { libName, ambiguous: false });
    else if (cur.libName !== libName) cur.ambiguous = true;
  };
  for (const lib of listLibraries(group)) {
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
function buildDepTree(rootName, maxDepth, group) {
  const g = safeGroup(group);
  const repCache = new Map();
  const getRep = (n) => { if (!repCache.has(n)) repCache.set(n, latestReport(n, g)); return repCache.get(n); };
  const index = buildLibIndex(getRep, g);
  const urlIndex = buildLibUrlIndex(getRep, g);
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

// HarmonyOS porting class (5-way) for the dep-topology page. Prefers the agent's
// explicit harmony_adaptation.porting_class; else derives from the existing dim-9 fields
// so 存量 reports are classified without a re-run.
const PLATFORM_BLOCKER_RE = /win32|x11|xcb|cocoa|coregraphics|iokit|registry|wmi|sysfs|procfs|gpu|cuda|opencl|vulkan|device|driver|kernel|syscall|ioctl|permission|hardware|_api\b|api_unavailable|platform/i;
function derivePortingClass(report) {
  const ha = (report && report.harmony_adaptation) || null;
  if (!ha) return null;
  if (ha.porting_class) return ha.porting_class;          // explicit (agent) — incl. new 5-way values
  if (ha.feasibility === 'infeasible') return 'infeasible';
  const unadaptable = Array.isArray(ha.unadaptable_apis) ? ha.unadaptable_apis : [];
  const blk = Array.isArray(ha.blockers) ? ha.blockers : [];
  // Prefer the structured closed signal blockers[].adaptability over open-vocab category regex.
  const hasStructured = blk.some((b) => b.adaptability);
  if (unadaptable.length || blk.some((b) => b.adaptability === 'unadaptable')) return 'needs_adaptation_partial';
  if (blk.some((b) => b.severity === 'blocker' || b.adaptability === 'partial')) return 'needs_adaptation_full';
  const cats = blk.map((b) => String(b.category || '').toLowerCase());
  const native = cats.some((c) => /native_dependency|ffi|toolchain|posix/.test(c));
  // Legacy fallback: open-vocab category regex, only when no structured adaptability is present.
  if (!hasStructured && cats.some((c) => PLATFORM_BLOCKER_RE.test(c))) return 'needs_adaptation_full';
  const path = String(ha.recommended_path || '').toLowerCase();
  if (/run_on_ported_runtime/.test(path) && !native) return 'no_adaptation';
  if (native) return 'recompile_only';
  // pure script, no native work, no blockers → nothing to adapt
  return 'no_adaptation';
}

// ---- difficulty level (5-tier) + effort person-days -----------------------
// effort.level is DERIVED (not an independent model axis) from porting_class (floor)
// × person_days (magnitude bucket), take-higher — keeps it self-consistent with the
// porting class while adding the "how much" the class alone can't express, and the
// numeric person_days aggregates up the dep tree.
const LEVEL_RANK = { very_low: 0, low: 1, medium: 2, high: 3, very_high: 4 };
const RANK_LEVEL = ['very_low', 'low', 'medium', 'high', 'very_high'];
const CLASS_LEVEL_FLOOR = { no_adaptation: 0, recompile_only: 1, needs_adaptation_full: 2,
  needs_adaptation: 3, needs_adaptation_partial: 3, infeasible: 4 };
function daysBucket(daysHi) {            // person-days (upper bound) → level rank
  const d = Number(daysHi);
  if (!(d > 2)) return 0;
  if (d <= 5) return 1;
  if (d <= 15) return 2;
  if (d <= 40) return 3;
  return 4;
}
function deriveDifficultyLevel(portingClass, personDaysHi) {
  if (!portingClass) return null;
  const floor = portingClass in CLASS_LEVEL_FLOOR ? CLASS_LEVEL_FLOOR[portingClass] : 0;
  return RANK_LEVEL[Math.max(floor, daysBucket(personDaysHi))];
}
// person-days [lo,hi] for a dim-9 block, deriving from legacy XS..XL / difficulty when absent.
const TSHIRT_DAYS = { XS: [0, 2], S: [2, 5], M: [5, 15], L: [15, 40], XL: [40, 80] };
const DIFF_DAYS = { low: [0, 5], medium: [5, 15], high: [15, 40], very_high: [40, 80] };
function effortDays(ha) {
  if (!ha) return null;
  const e = ha.effort;
  if (e && Array.isArray(e.person_days) && e.person_days.length === 2) {
    const lo = Number(e.person_days[0]), hi = Number(e.person_days[1]);
    if (Number.isFinite(lo) && Number.isFinite(hi)) return [lo, hi];
  }
  if (ha.effort_estimate && TSHIRT_DAYS[ha.effort_estimate]) return TSHIRT_DAYS[ha.effort_estimate].slice();
  if (ha.overall_difficulty && DIFF_DAYS[ha.overall_difficulty]) return DIFF_DAYS[ha.overall_difficulty].slice();
  return null;
}
// confidence ordinal for min-propagation up the tree.
const CONF_RANK = { low: 0, medium: 1, high: 2 };
const RANK_CONF = ['low', 'medium', 'high'];
const FEAS_FOR_CLASS = { no_adaptation: 'feasible', recompile_only: 'feasible_with_effort',
  needs_adaptation_full: 'feasible_with_effort', needs_adaptation: 'hard',
  needs_adaptation_partial: 'hard', infeasible: 'infeasible' };

// Serve-time normalize (mutates report.harmony_adaptation): fill the derived effort.level,
// person_days (from legacy if missing), feasibility consistency, and stable ids — so 存量
// reports gain the new structured fields without a re-run.
function normalizeHarmony(report) {
  const ha = report && report.harmony_adaptation;
  if (!ha || typeof ha !== 'object') return report;
  const cls = derivePortingClass(report);
  if (cls && !ha.porting_class) ha.porting_class = cls;
  if (cls && !ha.feasibility) ha.feasibility = FEAS_FOR_CLASS[cls] || null;
  const days = effortDays(ha);
  ha.effort = ha.effort && typeof ha.effort === 'object' ? ha.effort : {};
  if (days && !(Array.isArray(ha.effort.person_days) && ha.effort.person_days.length === 2))
    ha.effort.person_days = days;
  ha.effort.level = deriveDifficultyLevel(cls, days ? days[1] : 0);   // always server-derived
  const tag = (arr, p) => Array.isArray(arr) && arr.forEach((it, i) => { if (it && typeof it === 'object' && !it.id) it.id = `${p}:${i + 1}`; });
  tag(ha.target_assumptions, 'ta'); tag(ha.unadaptable_apis, 'ua'); tag(ha.blockers, 'bk');
  return report;
}

// Deterministic consistency check — returns 中文 warnings for the panel.
function validateHarmony(report) {
  const ha = report && report.harmony_adaptation;
  if (!ha || typeof ha !== 'object') return [];
  const w = [];
  const cls = ha.porting_class || derivePortingClass(report);
  if (cls && ha.feasibility && FEAS_FOR_CLASS[cls] && ha.feasibility !== FEAS_FOR_CLASS[cls])
    w.push(`feasibility(${ha.feasibility}) 与 porting_class(${cls}) 不自洽，应为 ${FEAS_FOR_CLASS[cls]}`);
  const ua = Array.isArray(ha.unadaptable_apis) ? ha.unadaptable_apis : [];
  const blk = Array.isArray(ha.blockers) ? ha.blockers : [];
  const ta = Array.isArray(ha.target_assumptions) ? ha.target_assumptions : [];
  if (ua.length && !['needs_adaptation_partial', 'needs_adaptation', 'infeasible'].includes(cls))
    w.push(`unadaptable_apis 非空但 porting_class=${cls}（应为 needs_adaptation_partial 或 infeasible）`);
  const ids = new Set([...ta, ...ua, ...blk].map((x) => x && x.id).filter(Boolean));
  for (const b of blk) for (const r of [...(b.caused_by || []), ...(b.manifests_as || [])])
    if (!ids.has(r)) w.push(`blocker ${b.id || b.issue || ''} 的引用 ${r} 不存在（悬空引用）`);
  for (const u of ua) for (const r of (u.caused_by || [])) if (!ids.has(r)) w.push(`unadaptable_api ${u.id || u.api || ''} 的 caused_by ${r} 不存在`);
  for (const a of ta) if (a && a.required && a.target_status === 'unavailable') {
    const refed = [...blk, ...ua].some((x) => (x.caused_by || []).includes(a.id));
    if (!refed) w.push(`target_assumption ${a.id || a.capability || ''} 为 required+unavailable 但无对应 blocker/unadaptable_api`);
  }
  if (ta.some((a) => a && a.required && a.target_status === 'unknown') && ha.confidence === 'high')
    w.push('存在 required 且 unknown 的目标假设，confidence 不应为 high');
  return w;
}

// ---- bottom-up adaptation rollup (serve-time, API-granular) ----------------
// worst-wins lattice over porting classes. Legacy `needs_adaptation` ≡ partial.
const CLASS_RANK = { no_adaptation: 0, recompile_only: 1, needs_adaptation_full: 2,
  needs_adaptation: 3, needs_adaptation_partial: 3, infeasible: 4 };
const RANK_CLASS = ['no_adaptation', 'recompile_only', 'needs_adaptation_full', 'needs_adaptation_partial', 'infeasible'];
const rankOf = (cls) => (cls in CLASS_RANK ? CLASS_RANK[cls] : 0);
const classOfRank = (r) => RANK_CLASS[Math.min(Math.max(r, 0), 4)];
// normalize a symbol for cross-library matching: lowercase + also keep the last
// segment after a . / :: / -> so numpy.ndarray ~ ndarray, cv::Mat ~ mat.
function symKeys(s) {
  const low = String(s || '').toLowerCase().trim();
  if (!low) return [];
  const tail = low.split(/::|->|\./).pop();
  return tail && tail !== low ? [low, tail] : [low];
}
const addDays = (a, b) => !a ? (b ? b.slice() : null) : !b ? a.slice() : [a[0] + b[0], a[1] + b[1]];

// Compute each node's EFFECTIVE adaptation class from its own class + its analyzed
// children's, where a child's un-adaptable APIs only block the parent if the parent
// actually calls them (used_symbols ∩ child.unadaptable public_entry). Falls back to
// dependency scope when used_symbols is absent. Mutates topo.nodes in place.
function rollupAdaptation(topo) {
  const byId = new Map(topo.nodes.map((n) => [n.id, n]));
  const out = new Map();   // id -> [{edge fields}]
  for (const e of topo.edges) { if (!out.has(e.source)) out.set(e.source, []); out.get(e.source).push(e); }
  // a node's own class for rollup purposes (harmonized ⇒ already ported ⇒ no work)
  const selfClassOf = (n) => n.harmonyAdapted ? 'no_adaptation'
    : !n.analyzed ? 'unanalyzed'
    : (n.selfClass || 'no_adaptation');
  const state = new Map();  // 0/undef unvisited, 1 visiting, 2 done
  const memo = new Map();
  // a node's own person-days for rollup (harmonized ⇒ already ported ⇒ 0 work)
  const selfDaysOf = (n) => n.harmonyAdapted ? [0, 0] : (n.effortDays || null);
  const selfConfOf = (n) => n.harmonyAdapted ? 2 : (n.confidence in CONF_RANK ? CONF_RANK[n.confidence] : 1);
  const eff = (id) => {
    const n = byId.get(id);
    if (!n) return { rank: null, uncertain: false };
    if (state.get(id) === 2) return memo.get(id);
    const self = selfClassOf(n);
    if (state.get(id) === 1)   // cycle: use this node's own class only, no deeper recursion
      return self === 'unanalyzed' ? { rank: null, uncertain: true } : { rank: rankOf(self), uncertain: false, days: selfDaysOf(n), confRank: selfConfOf(n) };
    state.set(id, 1);
    // harmonized ⇒ official OHOS build already subsumes its deps → sealed leaf, no roll-up
    if (n.harmonyAdapted) { const r = { rank: 0, uncertain: false, blockingChildren: [], days: [0, 0], confRank: 2 }; state.set(id, 2); memo.set(id, r); return r; }
    if (self === 'unanalyzed') { const r = { rank: null, uncertain: true }; state.set(id, 2); memo.set(id, r); return r; }
    let worst = rankOf(self), uncertain = false;
    let days = selfDaysOf(n), confRank = selfConfOf(n);
    const blockingChildren = [];
    for (const e of (out.get(id) || [])) {
      const child = byId.get(e.target);
      if (!child) continue;
      const ce = eff(e.target);
      if (ce.rank == null) { uncertain = true; confRank = Math.min(confRank, 1); continue; }   // child unknown → can't lower, marks uncertain
      uncertain = uncertain || ce.uncertain;
      // child's un-adaptable surface (public entry preferred, api fallback)
      const unAdaptKeys = new Set();
      for (const u of (child.unadaptableApis || [])) for (const k of symKeys(u.public_entry || u.api)) unAdaptKeys.add(k);
      const used = Array.isArray(e.usedSymbols) ? e.usedSymbols : [];
      const usedKeys = new Set(); for (const s of used) for (const k of symKeys(s)) usedKeys.add(k);
      const hit = [...usedKeys].filter((k) => unAdaptKeys.has(k));
      let contrib;
      if (unAdaptKeys.size === 0) contrib = ce.rank;                 // child fully adaptable → inherit its (low) class
      else if (hit.length) contrib = ce.rank;                       // parent hits the un-adaptable part → full child class
      else if (used.length) contrib = Math.min(ce.rank, CLASS_RANK.recompile_only); // uses child but not the bad part
      else {                                                        // unknown usage → scope fallback
        const sc = String(e.scope || '').toLowerCase();
        contrib = (sc === 'optional' || sc === 'peer') ? Math.min(ce.rank, CLASS_RANK.recompile_only) : ce.rank;
      }
      if (contrib > rankOf(self)) blockingChildren.push({
        child: child.label, libName: child.libName || null,
        childClass: classOfRank(ce.rank), contribClass: classOfRank(contrib),
        viaSymbols: hit, basis: hit.length ? 'used_api' : (used.length ? 'used_other' : 'scope') });
      if (contrib > worst) worst = contrib;
      // accumulate the child's subtree effort + confidence when it contributes porting work
      if (contrib > 0) { days = addDays(days, ce.days); confRank = Math.min(confRank, ce.confRank == null ? 1 : ce.confRank); }
    }
    const r = { rank: worst, uncertain, blockingChildren, days, confRank };
    state.set(id, 2); memo.set(id, r);
    return r;
  };
  for (const n of topo.nodes) {
    const r = eff(n.id);
    // self-view difficulty level (from the node's own class + own effort)
    n.level = deriveDifficultyLevel(n.selfClass, n.effortDays ? n.effortDays[1] : 0);
    if (!n.analyzed && !n.harmonyAdapted) { n.rollupClass = null; n.rollupUncertain = false; n.rollupEffort = null; n.rollupConfidence = null; n.rollupLevel = null; continue; }
    n.rollupClass = r.rank == null ? null : classOfRank(r.rank);
    n.rollupUncertain = !!r.uncertain;
    n.blockingChildren = r.blockingChildren || [];
    n.rollupEffort = r.days || null;
    n.rollupConfidence = r.confRank == null ? null : RANK_CONF[r.confRank];
    n.rollupLevel = deriveDifficultyLevel(n.rollupClass, r.days ? r.days[1] : 0);
  }
  return topo;
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
function buildDepTopology(rootName, group, maxDepth = 6, maxNodes = 300) {
  const g = safeGroup(group);
  const repCache = new Map();
  const getRep = (n) => { if (!repCache.has(n)) repCache.set(n, latestReport(n, g)); return repCache.get(n); };
  const index = buildLibIndex(getRep, g);
  const urlIndex = buildLibUrlIndex(getRep, g);
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
      if (cur.id !== id && !edgeSeen.has(ek)) {
        edgeSeen.add(ek);
        edges.push({ source: cur.id, target: id,
          usedSymbols: Array.isArray(d.used_symbols) ? d.used_symbols : [],
          scope: d.scope || null });
      }
    }
  }
  // classify each node (self porting class + the un-adaptable API surface for rollup)
  for (const node of nodes.values()) {
    if (node.analyzed) {
      const rep = getRep(node.libName);
      node.portingClass = node.selfClass = derivePortingClass(rep);
      const ha = (rep && rep.harmony_adaptation) || {};
      node.feasibility = ha.feasibility || null;
      node.summary = ha.summary || '';
      node.unadaptableApis = Array.isArray(ha.unadaptable_apis) ? ha.unadaptable_apis : [];
      node.effortDays = effortDays(ha);
      node.confidence = ha.confidence || null;
    }
  }
  return { root: rootName, nodes: [...nodes.values()], edges };
}

// ---------------------------------------------------------------- clone
function startClone({ url: rawUrl, ref, overwrite, tag, group }) {
  const gitUrl = normalizeCloneUrl(rawUrl);
  const name = repoNameFromUrl(gitUrl);
  const g = ensureGroupDirs(group);
  const dest = repoDir(g, name);
  if (fs.existsSync(dest)) {
    if (!overwrite) throw new Error(`repos/${g}/${name} already exists (enable overwrite to re-clone)`);
    fs.rmSync(dest, { recursive: true, force: true });
  }
  const args = ['clone', '--progress', '--depth', '1'];
  if (ref) args.push('--branch', ref);
  args.push(gitUrl, dest);
  // 来源标签：默认主软件；递归/待分析依赖传 'passive'。end 回调里克隆成功才落库。
  const job = new Job('clone', { name, group: g, argv: ['git', ...args], url: gitUrl, tag: TAG_VALUES.includes(tag) ? tag : 'primary' });
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
  const group = safeGroup(opts.group);
  const repoPathAbs = repoDir(group, name);
  if (!name || !fs.existsSync(repoPathAbs))
    throw new Error(`repo not found: ${path.relative(ROOT, repoPathAbs)} (clone it first)`);
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const runDir = path.join(runLibDir(group, name), ts);
  fs.mkdirSync(runDir, { recursive: true });
  const reportPath = path.join(runDir, 'report.json');
  const repoRel = path.relative(ROOT, repoPathAbs);   // repos/<group>/<name>

  const codegraphOn = codegraphAvailable && (opts.useCodegraph ?? settings.useCodegraph);
  // Index is pre-built by the server (at clone, and as a safety-net below) — tell the
  // agent to USE it rather than re-build it.
  if (codegraphOn) ensureCodegraphIndex(repoPathAbs);
  const codegraphHint = codegraphOn
    ? `codegraph is installed and the structural index for ${repoRel} is pre-built by ` +
      `\`codegraph init\`: prefer \`codegraph context/query/callers -p ${repoRel} -j\` for the ` +
      `function-summary and native/platform-API dimensions (fall back to grep/Read if any codegraph call fails). `
    : '';
  let prompt = (opts.promptTemplate || settings.promptTemplate || DEFAULT_PROMPT)
    .replaceAll('{codegraphHint}', codegraphHint)
    .replaceAll('{repoPath}', repoRel)
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
  // Robust to stale/custom templates that predate "库 vs 应用" support: if the prompt
  // still frames the target as only a library, remind that it may be an application.
  if (/third-party library/i.test(prompt) && !/library\.kind|application/i.test(prompt))
    prompt = prompt + ' 注意：被分析对象可能是库或应用——请先判定 library.kind（library/application/...）再按对应口径分析。';

  const base = (opts.opencodeCmd || settings.opencodeCmd).trim().split(/\s+/);
  const model = opts.model || settings.model;
  const argv = [...base];
  if (model) argv.push('-m', model);
  if (opts.agent) argv.push('--agent', opts.agent);
  argv.push('--format', 'json');
  if (opts.thinking ?? settings.thinking) argv.push('--thinking');  // stream model reasoning
  if (opts.printLogs ?? settings.printLogs) argv.push('--print-logs');
  argv.push(prompt);

  const job = new Job('analyze', { name, group, model, runDir, reportPath, argv, prompt,
    recursionSession: opts.recursionSession || null });
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
  pipeProcess(job, spawn(argv[0], argv.slice(1), { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'], shell: isWindows }));
}

// ---------------------------------------------------------------- recursive analysis (sessions)
// Drive the "analyze a library, then recursively clone+analyze its runtime deps"
// loop. System / no-source libs are leaves (not recursed). Level-triggered: every
// tick() recomputes the frontier from on-disk state (repos/ + runs/ reports) and
// advances each dep one step, so it dedupes identically to the dep-topology page,
// never re-analyzes an already-analyzed lib, and survives a server restart.
const recursionSessions = new Map();   // id -> RecursionSession
const CLONE_MAX = 3;                   // cap concurrent clones a session launches
const TERMINAL = new Set(['analyzed', 'leaf_system', 'leaf_prebuilt', 'leaf_interface',
  'leaf_no_source', 'ambiguous', 'failed', 'capped']);
const ACTIVE = new Set(['pending', 'resolving', 'resolved', 'cloning', 'analyzing']);

class RecursionSession {
  constructor(root, opts = {}) {
    this.id = crypto.randomBytes(6).toString('hex');
    this.root = root;
    this.group = safeGroup(opts.group);       // 递归始终在根软件所在分组内进行
    this.opts = {
      maxDepth: Math.min(Math.max(parseInt(opts.maxDepth, 10) || 6, 1), 8),
      maxNodes: Math.min(Math.max(parseInt(opts.maxNodes, 10) || 150, 1), 500),
    };
    this.status = 'running';                  // running | stopped | done
    this.decisions = new Map();               // depKey -> decision
    this.events = [];
    this.clients = new Set();
    this.createdAt = new Date().toISOString();
    this._changed = false;
  }

  _set(dec, state, reason, libName) {
    if (dec.state !== state || (reason !== undefined && dec.reason !== reason)) this._changed = true;
    dec.state = state;
    if (reason !== undefined) dec.reason = reason;
    if (libName) dec.libName = libName;
  }
  _inflightClones() { let n = 0; for (const d of this.decisions.values()) if (d.state === 'cloning') n++; return n; }
  _workCount() { let n = 0; for (const d of this.decisions.values()) if (['cloning', 'analyzing', 'analyzed'].includes(d.state)) n++; return n; }

  // Resolve a clonable repo URL for a dep (async, fire-and-forget → re-ticks).
  async _resolve(dec, d) {
    dec.resolving = true;
    this._set(dec, 'resolving');
    this._flush();
    let url = extractGitUrl(d.source, d.version);
    let leaf = null;
    if (!url && settings.enableNetworkResolve) {
      try {
        const r = await resolve.resolveRepo(ecoNorm(d.ecosystem), d.name);
        if (r && (r.interface || r.is_system)) leaf = 'leaf_interface';
        else if (r && r.url) url = r.url;
      } catch (_) {}
    }
    dec.resolving = false;
    if (this.status !== 'running') return;
    if (url) { dec.url = url; dec.repoName = repoNameFromUrl(url); this._set(dec, 'resolved'); }
    else if (leaf) this._set(dec, 'leaf_interface', '系统/接口库，无单一源码仓库');
    else this._set(dec, 'leaf_no_source', '解析不出仓库 URL，需人工解析');
    this._flush();
    this.tick();
  }

  // Advance one dependency by a single step based on current disk state.
  _advance(dec, d, repos) {
    if (TERMINAL.has(dec.state)) return;
    if (dec.ambiguous) return this._set(dec, 'ambiguous', '匹配到多个已分析库，需人工确认');
    if (d.locality === 'system' || d.acquisition === 'system')
      return this._set(dec, 'leaf_system', '系统库（find_package/预装），无源码');
    if (d.acquisition === 'prebuilt_binary')
      return this._set(dec, 'leaf_prebuilt', '预编译二进制，无源码');

    // need a repo URL first
    if (!dec.repoName) {
      if (dec.state !== 'resolving') this._resolve(dec, d);   // async; re-ticks
      return;
    }
    const repoName = dec.repoName;
    // already analyzed?
    if (latestReport(repoName, this.group)) return this._set(dec, 'analyzed', '', repoName);

    const cloned = repos.has(repoName) || fs.existsSync(repoDir(this.group, repoName));
    // a clone/analyze job we launched may have just ended — react to its outcome
    if (dec.state === 'analyzing') {
      const j = jobs.get(dec.jobId);
      if (j && (j.status === 'running' || j.status === 'queued')) return;   // still going
      return this._set(dec, 'failed', '分析未产出 report.json');
    }
    if (dec.state === 'cloning') {
      const j = jobs.get(dec.jobId);
      if (j && (j.status === 'running' || j.status === 'queued')) return;   // still going
      if (!cloned) return this._set(dec, 'failed', '克隆失败');
      // cloned ok → fall through to start analyze
    }

    if (!cloned) {
      if ((dec.cloneAttempts || 0) >= 1) return this._set(dec, 'failed', '克隆失败');
      if (this._inflightClones() >= CLONE_MAX) return;            // slot busy → retry next tick
      if (this._workCount() >= this.opts.maxNodes) return this._set(dec, 'capped', '达到节点上限');
      try {
        const job = startClone({ url: dec.url, tag: 'passive', group: this.group });
        job.meta.recursionSession = this.id;
        dec.jobId = job.id; dec.cloneAttempts = (dec.cloneAttempts || 0) + 1;
        this._set(dec, 'cloning', '克隆中');
      } catch (e) {
        if (!fs.existsSync(repoDir(this.group, repoName))) this._set(dec, 'failed', '克隆出错: ' + e.message);
      }
      return;
    }
    // cloned but not analyzed → start analyze (queued under maxConcurrent)
    if ((dec.analyzeAttempts || 0) >= 1) return this._set(dec, 'failed', '分析失败');
    if (this._workCount() >= this.opts.maxNodes) return this._set(dec, 'capped', '达到节点上限');
    try {
      const job = createAnalyzeJob({ name: repoName, group: this.group, recursionSession: this.id });
      dec.jobId = job.id; dec.analyzeAttempts = (dec.analyzeAttempts || 0) + 1;
      this._set(dec, 'analyzing', '分析中');
    } catch (e) { this._set(dec, 'failed', '分析启动失败: ' + e.message); }
  }

  // Recompute the frontier from disk and advance every pending dependency once.
  tick() {
    if (this.status !== 'running') return;
    this._changed = false;
    const repCache = new Map();
    const getRep = (n) => { if (!repCache.has(n)) repCache.set(n, latestReport(n, this.group)); return repCache.get(n); };
    const index = buildLibIndex(getRep, this.group);
    const urlIndex = buildLibUrlIndex(getRep, this.group);
    const repos = new Set(listRepos(this.group));

    // BFS over analyzed reports → collect unanalyzed runtime deps + their depth.
    const seen = new Set([this.root]);
    const frontier = new Map();   // depKey -> { d, depth, ambiguous }
    const queue = [{ libName: this.root, depth: 0 }];
    while (queue.length) {
      const cur = queue.shift();
      if (cur.depth >= this.opts.maxDepth) continue;
      const rep = getRep(cur.libName);
      const deps = (rep && rep.dependencies && rep.dependencies.dependencies) || [];
      for (const d of deps) {
        if (!d || !d.name || !isRuntimeDep(d)) continue;
        const hit = resolveDepLib(d, index, urlIndex);
        if (hit && !hit.ambiguous) {                       // analyzed → recurse into it
          if (!seen.has(hit.libName)) { seen.add(hit.libName); queue.push({ libName: hit.libName, depth: cur.depth + 1 }); }
          continue;
        }
        const depKey = ecoNorm(d.ecosystem) + ':' + normName(d.name);
        const prev = frontier.get(depKey);
        if (!prev || cur.depth + 1 < prev.depth)
          frontier.set(depKey, { d, depth: cur.depth + 1, ambiguous: !!(hit && hit.ambiguous) });
      }
    }

    // advance each frontier dependency
    for (const [depKey, f] of frontier) {
      let dec = this.decisions.get(depKey);
      if (!dec) {
        dec = { key: depKey, name: f.d.name, ecosystem: ecoNorm(f.d.ecosystem),
          depth: f.depth, state: 'pending', reason: '', ambiguous: f.ambiguous };
        this.decisions.set(depKey, dec);
        this._changed = true;
      } else { dec.depth = Math.min(dec.depth, f.depth); dec.ambiguous = dec.ambiguous || f.ambiguous; }
      this._advance(dec, f.d, repos);
    }
    // reconcile in-flight decisions that completed but left the frontier
    for (const dec of this.decisions.values()) {
      if (TERMINAL.has(dec.state)) continue;
      if (dec.repoName && latestReport(dec.repoName, this.group)) this._set(dec, 'analyzed', '', dec.repoName);
    }
    // done when nothing is active anymore
    if (![...this.decisions.values()].some((d) => ACTIVE.has(d.state))) {
      if (this.status === 'running') { this.status = 'done'; this._changed = true; }
    }
    this._flush();
  }

  stop() { if (this.status === 'running') { this.status = 'stopped'; this.emit('update', this.snapshot()); } }

  _counts() {
    const c = {};
    for (const d of this.decisions.values()) c[d.state] = (c[d.state] || 0) + 1;
    return c;
  }
  snapshot() {
    return {
      id: this.id, root: this.root, group: this.group, status: this.status, opts: this.opts,
      createdAt: this.createdAt, counts: this._counts(),
      decisions: [...this.decisions.values()]
        .sort((a, b) => a.depth - b.depth || a.name.localeCompare(b.name))
        .map((d) => ({ name: d.name, ecosystem: d.ecosystem, depth: d.depth, state: d.state,
          reason: d.reason || '', repoName: d.repoName || null, libName: d.libName || null, url: d.url || null })),
    };
  }
  _flush() { if (this._changed) { this._changed = false; this.emit('update', this.snapshot()); } }
  emit(event, data) {
    const payload = { event, data, t: new Date().toISOString() };
    this.events.push(payload);
    if (this.events.length > 2000) this.events.shift();
    const frame = `event: ${event}\ndata: ${JSON.stringify(payload)}\n\n`;
    for (const res of this.clients) { try { res.write(frame); } catch (_) {} }
  }
}

function startRecursionSession(root, opts = {}) {
  const s = new RecursionSession(root, opts);
  recursionSessions.set(s.id, s);
  // keep memory bounded — drop oldest finished sessions
  if (recursionSessions.size > 30) {
    const old = [...recursionSessions.values()].filter((x) => x.status !== 'running')
      .sort((a, b) => (a.createdAt < b.createdAt ? -1 : 1))[0];
    if (old) recursionSessions.delete(old.id);
  }
  s.tick();
  return s;
}

// Level-trigger: re-tick every running session after any job ends, and optionally
// auto-start recursion after a user-initiated analyze (one not already part of a session).
jobEndListeners.add((job) => {
  // 克隆成功 → 落来源标签（union，脏失败不留标签）+ 预建 codegraph 索引（你建议的"clone 之后执行"）
  if (job.type === 'clone' && job.status === 'done' && job.meta.name) {
    const rp = repoDir(job.meta.group, job.meta.name);
    if (fs.existsSync(rp)) {
      addLibTag(job.meta.name, job.meta.group, job.meta.tag || 'primary');
      ensureCodegraphIndex(rp, (s) => { try { job.log('stdout', `[codegraph] ${s}`); } catch (_) {} });
    }
  }
  for (const s of recursionSessions.values()) if (s.status === 'running') s.tick();
  if (job.type === 'analyze' && job.status === 'done' && !job.meta.recursionSession
      && settings.recursiveAfterAnalyze) {
    const root = job.meta.name, group = safeGroup(job.meta.group);
    if (latestReport(root, group)
        && ![...recursionSessions.values()].some((s) => s.root === root && safeGroup(s.group) === group && s.status === 'running'))
      startRecursionSession(root, { group });
  }
});

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
  const group = safeGroup(ctx.group);
  if (!name) throw new Error('name required');
  const job = new Job('resolve', { name, ecosystem: eco, group });
  job.meta.outFile = path.join(RESOLVE_AGENT_DIR, job.id + '.json');
  job.meta.resolveDone = false;
  // dependent checkouts that actually exist (the agent greps them for the integration point)
  const dependents = (ctx.dependents || []).filter((n) => n && fs.existsSync(repoDir(group, n)));
  const ctxLines = [
    `name: ${name}`, `ecosystem: ${eco}`, `scope: ${ctx.scope || ''}`,
    `locality: ${ctx.locality || ''}`, `acquisition: ${ctx.acquisition || ''}`,
    `source: ${ctx.source || ''}`, `purpose: ${ctx.purpose || ''}`,
    `dependent libraries (checkouts to grep): ${dependents.map((n) => path.relative(ROOT, repoDir(group, n))).join(', ') || '(none cloned locally)'}`,
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
    pipeProcess(job, spawn(job.meta.argv[0], job.meta.argv.slice(1), { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'], shell: isWindows }));
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
    { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'], shell: isWindows });
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
    if (req.method === 'GET' && pathname === '/api/groups')
      return send(res, 200, { groups: listGroups() });
    if (req.method === 'POST' && pathname === '/api/groups') {
      const body = await readBody(req);
      const g = String(body.group || '').trim();
      if (!GROUP_RE.test(g)) return send(res, 400, { error: '分组名仅允许字母/数字/._- 且不超过 64 字符' });
      ensureGroupDirs(g);
      return send(res, 200, { groups: listGroups(), created: g });
    }

    if (req.method === 'GET' && pathname === '/api/libraries')
      return send(res, 200, { group: safeGroup(query.group), groups: listGroups(), libraries: listLibraries(query.group) });

    if (req.method === 'GET' && pathname === '/api/library') {
      const name = query.name;
      const g = safeGroup(query.group);
      if (!name || !fs.existsSync(runLibDir(g, name)) && !fs.existsSync(repoDir(g, name)))
        return send(res, 404, { error: 'unknown library' });
      return send(res, 200, { name, group: g, cloned: fs.existsSync(repoDir(g, name)),
        runs: runsForLib(name, g), active: activeJobFor(name, g) });
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
      return execFile('opencode', ['models'], { shell: isWindows, timeout: 15000 }, (e, out) =>
        send(res, 200, { models: e ? [] : out.split('\n').map((s) => s.trim()).filter(Boolean) }));

    if (req.method === 'GET' && pathname === '/api/testmodel')
      return testModel(query.model, (r) => send(res, 200, r));

    if (req.method === 'POST' && pathname === '/api/clone') {
      const body = await readBody(req);
      const urls = body.urls || (body.url ? [body.url] : []);
      if (!urls.length) return send(res, 400, { error: 'url(s) required' });
      const out = urls.map((u) => {
        try { const j = startClone({ url: u, ref: body.ref, overwrite: body.overwrite, tag: body.tag, group: body.group });
          return { url: u, jobId: j.id, name: j.meta.name }; }
        catch (e) { return { url: u, error: String(e.message || e) }; }
      });
      return send(res, 200, { jobs: out });
    }

    if (req.method === 'POST' && pathname === '/api/library-tags') {
      const body = await readBody(req);
      if (!body.name) return send(res, 400, { error: 'name required' });
      return send(res, 200, { name: body.name, group: safeGroup(body.group), tags: setLibTags(body.name, body.group, body.tags) });
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
      // 词表反哺跨所有分组聚合（与具体分组无关）
      for (const grp of listGroups()) for (const lib of listLibraries(grp)) {
        if (!lib.latest || !lib.latest.reportAvailable) continue;
        const rep = latestReport(lib.name, grp);
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
      const pg = safeGroup(query.group);
      const repCache = new Map();
      const getRep = (n) => { if (!repCache.has(n)) repCache.set(n, latestReport(n, pg)); return repCache.get(n); };
      const index = buildLibIndex(getRep, pg);
      const urlIndex = buildLibUrlIndex(getRep, pg);
      const repos = new Set(listRepos(pg));
      const groups = new Map();   // key: eco:normname -> aggregated dep
      for (const lib of listLibraries(pg)) {
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
          active: repoName ? activeJobFor(repoName, pg) : null,
        };
      }).sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
      return send(res, 200, { group: pg, total: items.length, items });
    }

    if (req.method === 'GET' && pathname === '/api/depgraph') {
      const name = query.name;
      const g = safeGroup(query.group);
      if (!name) return send(res, 400, { error: 'name required' });
      if (!latestReport(name, g)) return send(res, 404, { error: 'no report for library' });
      const depth = Math.min(Math.max(parseInt(query.depth, 10) || 3, 1), 5);
      return send(res, 200, { root: name, group: g, depth, tree: buildDepTree(name, depth, g) });
    }

    if (req.method === 'GET' && pathname === '/api/dep-topology') {
      const name = query.name;
      const g = safeGroup(query.group);
      if (!name) return send(res, 400, { error: 'name required' });
      if (!latestReport(name, g)) return send(res, 404, { error: 'no report for library' });
      const topo = buildDepTopology(name, g);
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
      // bottom-up roll-up: each node's effective class incl. the deps it actually uses
      rollupAdaptation(topo);
      // status per node, two views — self (本体) and rollup (含依赖综合).
      // harmonized > (analyzed ? class : unanalyzed); root keeps its own class.
      const statusFor = (n, cls) => n.isRoot && !n.harmonyAdapted && cls ? cls
        : n.harmonyAdapted ? 'harmonized'
        : n.analyzed ? (cls || 'unanalyzed')
        : 'unanalyzed';
      const counts = {}, rollupCounts = {};
      for (const n of topo.nodes) {
        n.status = statusFor(n, n.portingClass);
        n.rollupStatus = statusFor(n, n.rollupClass);
        delete n.harmonyAdaptedStamp;
        counts[n.status] = (counts[n.status] || 0) + 1;
        rollupCounts[n.rollupStatus] = (rollupCounts[n.rollupStatus] || 0) + 1;
      }
      return send(res, 200, { ...topo, counts, rollupCounts });
    }

    if (req.method === 'POST' && pathname === '/api/recurse') {
      const body = await readBody(req);
      const name = body.name;
      const g = safeGroup(body.group);
      if (!name) return send(res, 400, { error: 'name required' });
      if (!latestReport(name, g)) return send(res, 404, { error: 'root library not analyzed yet' });
      const existing = [...recursionSessions.values()].find((s) => s.root === name && safeGroup(s.group) === g && s.status === 'running');
      if (existing) return send(res, 200, { sessionId: existing.id, existing: true });
      const s = startRecursionSession(name, { ...body, group: g });
      return send(res, 200, { sessionId: s.id });
    }

    if (req.method === 'GET' && pathname === '/api/recurse/stream') {
      const s = recursionSessions.get(query.session);
      if (!s) return send(res, 404, { error: 'unknown session' });
      res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
      res.write('retry: 2000\n\n');
      res.write(`event: update\ndata: ${JSON.stringify({ event: 'update', data: s.snapshot() })}\n\n`);
      if (s.status !== 'running') { res.end(); return; }
      s.clients.add(res);
      const hb = setInterval(() => { try { res.write(': ping\n\n'); } catch (_) {} }, 15000);
      req.on('close', () => { clearInterval(hb); s.clients.delete(res); });
      return;
    }

    if (req.method === 'POST' && pathname === '/api/recurse/stop') {
      const body = await readBody(req);
      const s = recursionSessions.get(body.session);
      if (!s) return send(res, 404, { error: 'unknown session' });
      s.stop();
      return send(res, 200, { status: s.status });
    }

    if (req.method === 'GET' && pathname === '/api/recurse') {
      if (query.session) {
        const s = recursionSessions.get(query.session);
        if (!s) return send(res, 404, { error: 'unknown session' });
        return send(res, 200, s.snapshot());
      }
      const sessions = [...recursionSessions.values()]
        .sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1))
        .map((s) => ({ id: s.id, root: s.root, group: s.group, status: s.status, counts: s._counts(), createdAt: s.createdAt }));
      return send(res, 200, { sessions });
    }

    if (req.method === 'GET' && pathname === '/api/report') {
      const file = path.join(runLibDir(query.group, query.name || ''), query.run || '', 'report.json');
      if (!file.startsWith(RUNS) || !fs.existsSync(file)) return send(res, 404, { error: 'report not found' });
      let rep;
      try { rep = JSON.parse(fs.readFileSync(file, 'utf8')); }
      catch (_) { return send(res, 200, fs.readFileSync(file, 'utf8')); }   // malformed → raw passthrough
      // serve-time: fill derived dim-9 fields (effort.level/person_days/ids/feasibility) and
      // attach consistency warnings, so 存量 reports gain structured data without a re-run.
      normalizeHarmony(rep);
      const hw = validateHarmony(rep);
      if (hw.length) rep.meta = { ...(rep.meta || {}), harmony_warnings: hw };
      return send(res, 200, rep);
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

    if (req.method === 'GET' && pathname === '/api/harmony-caps') {
      try { return send(res, 200, harmonyCaps.load()); }
      catch (e) { return send(res, 500, { error: String(e.message || e) }); }
    }
    if (req.method === 'POST' && pathname === '/api/harmony-caps/sync') {
      if (!settings.enableHarmonyMirror) return send(res, 200, { disabled: true });
      try { const summary = await harmonyCaps.sync(); return send(res, 200, { ...summary, caps: harmonyCaps.load() }); }
      catch (e) { return send(res, 500, { error: String(e.message || e) }); }
    }
    if (req.method === 'POST' && pathname === '/api/harmony-caps/row') {
      const body = await readBody(req);
      if (!body.id) return send(res, 400, { error: 'id required' });
      try { const row = harmonyCaps.patchRow(body.id, { status: body.status, source: body.source, note: body.note }); return send(res, 200, { row, caps: harmonyCaps.load() }); }
      catch (e) { return send(res, 400, { error: String(e.message || e) }); }
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
      const g = safeGroup(query.group);
      const tmp = path.join(os.tmpdir(), `pc-lib-export-${Date.now()}.xlsx`);
      const args = [path.join('scripts', 'export_xlsx.py'), '--runs', path.join(RUNS, g), '--out', tmp];
      if (query.names) args.push('--names', String(query.names));
      return execFile(isWindows ? 'python' : 'python3', args, { cwd: ROOT, shell: isWindows, timeout: 120000 }, (err, _o, stderr) => {
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
      const file = path.join(runLibDir(query.group, query.name || ''), query.run || '', 'run.log.jsonl');
      if (!file.startsWith(RUNS) || !fs.existsSync(file)) return send(res, 404, { error: 'log not found' });
      return send(res, 200, fs.readFileSync(file, 'utf8'), { 'Content-Type': 'text/plain; charset=utf-8' });
    }

    if (pathname.startsWith('/api/')) return send(res, 404, { error: 'unknown endpoint' });
    return serveStatic(req, res, pathname);
  } catch (err) {
    return send(res, 400, { error: String(err.message || err) });
  }
});

// Export pure dim-9 derivation helpers for unit testing; only listen when run directly.
if (require.main === module) {
  server.listen(PORT, () => {
    console.log(`PC 开源软件分析 control panel → http://localhost:${PORT}`);
    console.log(`  project root: ${ROOT}  ·  max concurrent analyses: ${settings.maxConcurrent}`);
  });
} else {
  module.exports = { derivePortingClass, deriveDifficultyLevel, effortDays, normalizeHarmony,
    validateHarmony, rollupAdaptation, buildDepTopology };
}
