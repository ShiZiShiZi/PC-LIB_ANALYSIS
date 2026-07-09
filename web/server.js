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
  '{monorepoNote}' +
  'The source is already cloned — do NOT clone again. Do NOT spawn sub-agents or use the ' +
  '`task` tool — do all evidence-gathering yourself in this single session (codegraph + ' +
  'Grep/Glob/Read) so every step streams to the live log. {codegraphHint}{harmonySkillsHint}' +
  'Run the deterministic ' +
  'code-metrics script with `--out {metricsPath}`, then reason through every dimension ' +
  '(function summary, license, dependencies, native/platform API). ' +
  'OUTPUT INCREMENTALLY: as you finish each dimension, immediately `Write` its block to ' +
  '{runDir}/blocks/<name>.json (filename = top-level report key, content = that block\'s JSON ' +
  'value) — do NOT accumulate everything for one giant final write, and do NOT emit ' +
  'languages/code_metrics/tests (the script splices those from metrics.json). When every block ' +
  'is written, assemble the report by running `python3 scripts/assemble_report.py --run-dir ' +
  '{runDir}` — it splices the metrics fragment, validates required keys, and ATOMICALLY writes ' +
  '{reportPath}. Do NOT hand-write {reportPath}; see {agentFile} for the block mapping. ' +
  'Conform to references/report_schema.json. ' +
  '语言要求：function_summary 里所有自然语言字段（summary、每个 category 的 name 与 ' +
  'description、domain、target_users）以及 library.one_liner 必须用简体中文书写；' +
  'SPDX 许可证标识、编程语言名、依赖包名等专有名词保持原文。' +
  'IMPORTANT: write the report, metrics, and ALL intermediate/scratch files inside ' +
  'the project (under the run directory) — never use /tmp or any path outside the ' +
  'project, because the headless runner auto-rejects external directories and the ' +
  'run will abort. ' +
  'When reading source files, always use relative paths from the project root ' +
  '(e.g., {repoPath}/pyproject.toml) or paths already returned by a prior tool result — ' +
  'do NOT construct absolute paths manually, as self-built absolutes are frequently wrong ' +
  'and will be rejected. Finish with a short digest.';

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
  // pre-"relative-path read" default (lacked the "do NOT construct absolute paths" warning)
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
  'run will abort. Finish with a short digest.',
  // pre-monorepo default (lacked the {monorepoNote} placeholder)
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
  'run will abort. ' +
  'When reading source files, always use relative paths from the project root ' +
  '(e.g., {repoPath}/pyproject.toml) or paths already returned by a prior tool result — ' +
  'do NOT construct absolute paths manually, as self-built absolutes are frequently wrong ' +
  'and will be rejected. Finish with a short digest.',
  // pre-block-streaming default (one giant final Write; predates the incremental
  // blocks/ + assemble_report.py flow)
  'Analyze the PC open-source software project (a third-party library OR an application) ' +
  'checked out at {repoPath}. First decide library.kind (library/application/...). Follow the ' +
  'method and JSON output contract in {agentFile} and the skills it references. ' +
  '{monorepoNote}' +
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
  'run will abort. ' +
  'When reading source files, always use relative paths from the project root ' +
  '(e.g., {repoPath}/pyproject.toml) or paths already returned by a prior tool result — ' +
  'do NOT construct absolute paths manually, as self-built absolutes are frequently wrong ' +
  'and will be rejected. Finish with a short digest.',
  // pre-{harmonySkillsHint} default (lacked the HarmonyOS doc-skills placeholder)
  'Analyze the PC open-source software project (a third-party library OR an application) ' +
  'checked out at {repoPath}. First decide library.kind (library/application/...). Follow the ' +
  'method and JSON output contract in {agentFile} and the skills it references. ' +
  '{monorepoNote}' +
  'The source is already cloned — do NOT clone again. Do NOT spawn sub-agents or use the ' +
  '`task` tool — do all evidence-gathering yourself in this single session (codegraph + ' +
  'Grep/Glob/Read) so every step streams to the live log. {codegraphHint}Run the deterministic ' +
  'code-metrics script with `--out {metricsPath}`, then reason through every dimension ' +
  '(function summary, license, dependencies, native/platform API). ' +
  'OUTPUT INCREMENTALLY: as you finish each dimension, immediately `Write` its block to ' +
  '{runDir}/blocks/<name>.json (filename = top-level report key, content = that block\'s JSON ' +
  'value) — do NOT accumulate everything for one giant final write, and do NOT emit ' +
  'languages/code_metrics/tests (the script splices those from metrics.json). When every block ' +
  'is written, assemble the report by running `python3 scripts/assemble_report.py --run-dir ' +
  '{runDir}` — it splices the metrics fragment, validates required keys, and ATOMICALLY writes ' +
  '{reportPath}. Do NOT hand-write {reportPath}; see {agentFile} for the block mapping. ' +
  'Conform to references/report_schema.json. ' +
  '语言要求：function_summary 里所有自然语言字段（summary、每个 category 的 name 与 ' +
  'description、domain、target_users）以及 library.one_liner 必须用简体中文书写；' +
  'SPDX 许可证标识、编程语言名、依赖包名等专有名词保持原文。' +
  'IMPORTANT: write the report, metrics, and ALL intermediate/scratch files inside ' +
  'the project (under the run directory) — never use /tmp or any path outside the ' +
  'project, because the headless runner auto-rejects external directories and the ' +
  'run will abort. ' +
  'When reading source files, always use relative paths from the project root ' +
  '(e.g., {repoPath}/pyproject.toml) or paths already returned by a prior tool result — ' +
  'do NOT construct absolute paths manually, as self-built absolutes are frequently wrong ' +
  'and will be rejected. Finish with a short digest.',
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
  enableHarmonyDocSkills: true,   // 分析时提示使用 opencode 全局鸿蒙文档 skill（存在才生效）
  recompileLocPerDay: 3000,       // 工作量分项 recompile = recompile_reuse 桶 LOC ÷ 此速率（行/天）
  adaptationLocPerDay: 500,       // 工作量分项 api_adaptation = needs_adaptation 桶 LOC ÷ 此速率（行/天）
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

// HarmonyOS doc skills（可选）：opencode 全局 skills，让分析 agent 把目标侧事实
// （@ohos API 是否存在 / ohos.permission.* 精确名 / SysCap）查官方文档而非凭模型记忆。
// 启动时探测一次；prompt 仅在「目录存在 且 settings.enableHarmonyDocSkills」时提及
//（探针已验证：headless 下 opencode 内置 skill 工具默认放行、skill 目录外部读可用）。
const HARMONY_DOC_SKILLS = ['harmonyos-sdk-api-lookup', 'harmonyos-docs-lookup'].filter((n) => {
  try { return fs.existsSync(path.join(os.homedir(), '.config', 'opencode', 'skills', n, 'SKILL.md')); }
  catch (_) { return false; }
});
if (HARMONY_DOC_SKILLS.length)
  console.log(`  harmony doc skills: ${HARMONY_DOC_SKILLS.join(', ')}`);

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
  // Only a TRUE pre-grouping layout migrates: if EITHER base already has default/,
  // the tree is group-keyed — its top-level dirs are GROUPS, and moving them under
  // default/ would swallow whole workspaces (e.g. after someone deletes an empty
  // repos/default/). One-time and global, not per-base.
  const migrated = [REPOS, RUNS].some((b) => fs.existsSync(path.join(b, 'default')));
  for (const base of [REPOS, RUNS]) {
    const def = path.join(base, 'default');
    if (migrated) { fs.mkdirSync(def, { recursive: true }); continue; }
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
  if (!(Number(settings.recompileLocPerDay) > 0)) settings.recompileLocPerDay = DEFAULT_SETTINGS.recompileLocPerDay;
  if (!(Number(settings.adaptationLocPerDay) > 0)) settings.adaptationLocPerDay = DEFAULT_SETTINGS.adaptationLocPerDay;
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
// Canonical, OWNER-qualified repo identity used as the strongest cross-ecosystem
// join key: `host/owner[/subgroup…]/repo` (lowercased). HOST-AGNOSTIC — keeps the
// full path so GitLab subgroups / googlesource single-segment / self-hosted all
// work. Returns null (→ caller falls back to name keys, never force-links) for
// URLs that are NOT a trustworthy repo: non-http(s)/scp, package registries &
// download sites, release artifacts, or a bare homepage with `.git` tacked on.
const _REGISTRY_HOSTS = /^(?:www\.)?(?:pypi\.org|files\.pythonhosted\.org|registry\.npmjs\.org|npmjs\.com|crates\.io|static\.crates\.io|repo\d*\.maven\.org|repo\.maven\.apache\.org|search\.maven\.org|rubygems\.org|nuget\.org|pkg\.go\.dev|proxy\.golang\.org|anaconda\.org|conda\.anaconda\.org)$/i;
const _ARTIFACT_RE = /\.(?:tar\.(?:gz|bz2|xz|zst)|tgz|tbz2?|txz|zip|whl|crate|gem|jar|7z|rar)$/i;
function canonicalRepoKey(url, subpath) {
  let u = String(url || '').trim();
  if (!u) return null;
  u = u.replace(/^git\+/i, '');
  const scp = u.match(/^[\w.-]+@([\w.-]+):(.+)$/);          // git@host:owner/repo(.git)
  if (scp) u = `https://${scp[1]}/${scp[2]}`;
  u = u.replace(/^git:\/\//i, 'https://').replace(/^ssh:\/\/(?:git@)?/i, 'https://')
       .replace(/^http:\/\//i, 'https://');
  u = u.split('#')[0].replace(/\?.*$/, '');
  let m;
  try { m = new URL(u); } catch { return null; }
  if (!/^https:$/i.test(m.protocol)) return null;
  const host = m.hostname.replace(/^www\./i, '').toLowerCase();
  if (_REGISTRY_HOSTS.test(host)) return null;              // a registry, not a repo
  if (_ARTIFACT_RE.test(m.pathname)) return null;           // a release artifact
  let p = m.pathname;
  const dash = p.indexOf('/-/');                            // GitLab non-repo separator
  if (dash >= 0) p = p.slice(0, dash);
  else p = p.replace(/\/(?:tree|blob|commits?|releases?|tags?|raw|wikis?|issues?|merge_requests|pulls?|src|browse)\b.*$/i, '');
  p = p.replace(/\/+$/, '').replace(/^\/+/, '').replace(/\.git$/i, '');
  if (!p) return null;                                       // bare homepage (e.g. foo.sourceforge.net[.git])
  const key = `${host}/${p.toLowerCase()}`;
  // monorepo subunit: a subpath discriminator keeps two subdirs of one repo distinct
  // (else e.g. .../tree/main/components/cronet and .../base collapse to the same key).
  const sp = String(subpath || '').replace(/\/+$/, '').replace(/^\/+/, '').toLowerCase();
  return sp ? `${key}#${sp}` : key;
}
// A set of `eco:variant` name keys for fuzzy same-name matching: handles lib-prefix
// (libpng↔png), version suffix (zlib-1.3↔zlib), and artifact-ish names.
function nameKeys(eco, name) {
  const out = new Set();
  let base = String(name || '').trim().toLowerCase();
  base = base.replace(_ARTIFACT_RE, '').replace(/[-_.]?v?\d[\d.]*$/, '');  // drop trailing version
  const variants = new Set();
  const add = (s) => { const n = normName(s); if (n) variants.add(n); };
  add(base);
  add(base.replace(/^lib/, ''));      // libpng → png
  add('lib' + base.replace(/^lib/, '')); // png → libpng
  for (const v of variants) out.add(eco + ':' + v);
  return out;
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
// Parse a pasted web URL into { gitUrl, ref, subpath } — supports monorepo subdir
// URLs like github.com/owner/repo/tree/<ref>/<sub/dir> (and /blob/), GitLab
// /-/tree/<ref>/<path>. gitUrl reuses normalizeCloneUrl (repo root). ref/subpath are
// undefined for a plain repo URL. NB: the first segment after tree/blob is taken as
// the ref, so a branch containing '/' is ambiguous — the panel's explicit subpath
// field is the fallback for that case.
function parseRepoUrl(raw) {
  const gitUrl = normalizeCloneUrl(raw);
  let ref, subpath;
  const u = String(raw || '').trim().split('#')[0].replace(/\?.*$/, '');
  let m;
  try { m = new URL(u); } catch { return { gitUrl, ref, subpath }; }
  if (!KNOWN_GIT_HOSTS.test(m.hostname)) return { gitUrl, ref, subpath };
  const dash = m.pathname.indexOf('/-/');                    // GitLab
  const hay = dash >= 0 ? m.pathname.slice(dash + 3) : m.pathname;
  const withPath = hay.match(/(?:^|\/)(?:tree|blob)\/([^/]+)\/(.+)$/i);
  const refOnly = hay.match(/(?:^|\/)(?:tree|blob)\/([^/]+)\/?$/i);
  if (withPath) { ref = decodeURIComponent(withPath[1]); subpath = withPath[2]; }
  else if (refOnly) { ref = decodeURIComponent(refOnly[1]); }
  if (subpath) subpath = decodeURIComponent(subpath).replace(/\/+$/, '').replace(/^\/+/, '') || undefined;
  return { gitUrl, ref, subpath };
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
    // dim-9 鸿蒙适配结论（serve-time 派生，口径同 /api/report 的 normalizeHarmony）：
    // 仪表盘徽章按 5 档 effective_class 上色；overall = 是否可适配总判。
    const ha = r.harmony_adaptation || null;
    const portingClass = ha ? effectivePortingClass(r) : null;   // 5-way effective_class for the badge
    const overall = (ha && ha.adaptation_assessment && ha.adaptation_assessment.overall) || overallForEffective(portingClass);
    const personDays = effortDays(ha);
    const difficultyLevel = portingClass
      ? deriveDifficultyLevel(portingClass, personDays ? personDays[1] : 0) : null;
    return {
      oneLiner: (r.library && r.library.one_liner) || (r.function_summary && r.function_summary.summary) || '',
      primary: r.languages && r.languages.primary,
      ecosystem: (r.library && r.library.ecosystem) || null,
      bindings: (r.library && r.library.bindings) || [],
      prodCode: r.code_metrics && r.code_metrics.production && r.code_metrics.production.code,
      testCases: r.tests && r.tests.test_cases,
      license: r.license && r.license.spdx,
      licenseCategory: deriveLicenseCategory(r),
      subpath: (r.library && r.library.source_subpath) || null,
      analyzedAt: r.library && r.library.analyzed_at,
      portingClass, difficultyLevel, personDays, overall,
      functionalViability: (ha && ha.functional_viability) || null,   // 快照口径（详情页才 caps live 回投）
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
    // monorepo 子目录：即使尚未分析，也从 .identity.json 暴露 subpath 供 L1 chip 显示。
    const ident = repos.has(name) ? readIdentity(g, name) : null;
    return {
      name, group: g, cloned: repos.has(name), runCount: runs.length,
      latest, active: activeJobFor(name, g), subpath: (ident && ident.subpath) || null,
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
// Read the per-library identity record (handle ↔ {url, canonicalKey, ecosystem}),
// written by startClone. Lets even un-analyzed libs join by source-URL. null if none.
function readIdentity(group, handle) {
  try { return JSON.parse(fs.readFileSync(path.join(repoDir(group, handle), '.identity.json'), 'utf8')); }
  catch { return null; }
}
function writeIdentity(group, handle, url, subpath, ref) {
  try {
    fs.writeFileSync(path.join(repoDir(group, handle), '.identity.json'),
      JSON.stringify({ handle, url: url || null, canonicalKey: canonicalRepoKey(url, subpath),
        subpath: subpath || null, ref: ref || null }, null, 2));
  } catch (_) {}
}
// Does an existing handle point to the SAME upstream repo as (url, ckey)? Uses the
// identity record; a legacy checkout without one is treated as "same" so we never
// disturb pre-existing handles.
function sameRepoHandle(group, handle, url, ckey) {
  const id = readIdentity(group, handle);
  if (!id) return true;
  if (ckey && id.canonicalKey) return id.canonicalKey === ckey;
  if (url && id.url) return id.url === url;
  return true;
}
// Choose a collision-safe storage handle: reuse the base name when free or it's the
// same repo; otherwise qualify with the owner (zlib → zlib__madler), then number.
function pickCloneHandle(group, base, url, ckey) {
  const free = (h) => !fs.existsSync(repoDir(group, h)) || sameRepoHandle(group, h, url, ckey);
  if (free(base)) return base;
  const owner = ckey ? (ckey.split('/')[1] || '').replace(/[^A-Za-z0-9._-]/g, '_') : '';
  const qualified = owner ? `${base}__${owner}` : `${base}-2`;
  if (free(qualified)) return qualified;
  let n = 2;
  while (!free(`${base}-${n}`)) n++;
  return `${base}-${n}`;
}
// Unified, multi-key identity index over analyzed libraries in a group:
//   byUrl : canonicalRepoKey(source_url|identity.url)         → strongest join key
//   byName: eco:variant (package_name/handle/repo-basename/aliases, via nameKeys)
// A key resolving to >1 library is flagged ambiguous (we won't auto-link it).
function buildIdentityIndex(getRep, group) {
  const byUrl = new Map(), byName = new Map();
  const add = (map, key, libName) => {
    if (!key) return;
    const cur = map.get(key);
    if (!cur) map.set(key, { libName, ambiguous: false });
    else if (cur.libName !== libName) cur.ambiguous = true;
  };
  for (const lib of listLibraries(group)) {
    if (!lib.latest || !lib.latest.reportAvailable) continue;
    const rep = getRep(lib.name);
    if (!rep) continue;
    const L = rep.library || {};
    const eco = ecoNorm(L.ecosystem);
    // URL keys: report source_url + the clone-time identity record (covers pre/odd cases).
    // Monorepo subunit: fold its subpath into the key so two subdirs of one repo stay
    // distinct (and a plain repo-root dep URL doesn't false-match a subunit).
    const ident = readIdentity(group, lib.name);
    const sub = L.source_subpath || (ident && ident.subpath) || null;
    for (const u of [L.source_url, ident && ident.url]) add(byUrl, canonicalRepoKey(u, sub), lib.name);
    // Name keys: package_name, handle, source_url basename, declared aliases / import names
    const names = [L.package_name, lib.name];
    if (L.source_url) names.push(repoNameFromUrl(L.source_url));
    for (const a of [].concat(L.aliases || [], L.import_names || [])) names.push(a);
    for (const nm of names) for (const k of nameKeys(eco, nm)) add(byName, k, lib.name);
  }
  return { byUrl, byName };
}
// Match a dependency to an analyzed library. URL identity FIRST (owner-qualified,
// cross-ecosystem, robust), falling back to ecosystem+name variants. The dep's repo
// URL is taken from its own source text, its model-emitted source_repo (L3), or the
// panel's resolve cache — so a dep whose NAME differs from the repo still links.
function resolveDepLib(d, idx) {
  const eco = ecoNorm(d.ecosystem);
  const cached = resolve.cacheGet(eco, d.name);
  const url = extractGitUrl(d.source, d.version) || d.source_repo || (cached && cached.url);
  const urlKey = canonicalRepoKey(url);
  if (urlKey) { const hit = idx.byUrl.get(urlKey); if (hit) return hit; }
  for (const nm of [d.name, d.registry_name]) {
    if (!nm) continue;
    for (const k of nameKeys(eco, nm)) { const hit = idx.byName.get(k); if (hit) return hit; }
  }
  return null;
}
function buildDepTree(rootName, maxDepth, group) {
  const g = safeGroup(group);
  const repCache = new Map();
  const getRep = (n) => { if (!repCache.has(n)) repCache.set(n, latestReport(n, g)); return repCache.get(n); };
  const idx = buildIdentityIndex(getRep, g);
  const seen = new Set([rootName]);
  const expand = (libName, depth) => {
    const rep = getRep(libName);
    const deps = (rep && rep.dependencies && rep.dependencies.dependencies) || [];
    return deps.map((d) => {
      const hit = resolveDepLib(d, idx);
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

// ---- license category (5-way strict closed axis) --------------------------
// Map an SPDX id / license name to one of 5 categories so 存量 reports gain
// license.category without a re-run. The model's explicit value always wins;
// this is only a fallback. Recognized-but-unmapped → null (leave to the model).
// Order matters: strong before weak (both contain "gpl"-ish text), commercial
// and copyleft before permissive.
const LICENSE_CATEGORY_RULES = [
  { cat: 'strong_copyleft', re: /\b(agpl|affero|\bgpl|gnu\s*general\s*public|gnu\s*gpl|eupl|osl-|open\s*software\s*license|sleepycat|cecill(?!-c|-b)|gpl-[123])/i },
  { cat: 'weak_copyleft', re: /\b(lgpl|lesser\s*general\s*public|mpl|mozilla\s*public|epl-|eclipse\s*public|cddl|common\s*development|cpl-|common\s*public\s*license|ms-rl|cecill-c)/i },
  { cat: 'commercial', re: /\b(sspl|busl|bsl-1\.1|business\s*source|elastic-2|\belv2\b|commons-clause|proprietary|commercial|all\s*rights\s*reserved|\beula\b)/i },
  { cat: 'permissive', re: /\b(mit\b|mit-0|bsd|apache|isc\b|zlib|libpng|boost|bsl-1\.0|unlicense|0bsd|cc0|wtfpl|python-2|\bpsf\b|x11|ncsa|postgresql|artistic)/i },
];
function deriveLicenseCategory(report) {
  const lic = (report && report.license) || null;
  if (!lic || typeof lic !== 'object') return null;
  if (lic.category) return lic.category;                     // explicit (model) wins
  const spdx = String(lic.spdx == null ? '' : lic.spdx).trim();
  const name = String(lic.name == null ? '' : lic.name).trim();
  const hay = (spdx + ' ' + name).trim();
  const noAssert = !spdx || /^(noassertion|unknown|none|null)$/i.test(spdx);
  if (!hay) return 'undeclared';
  for (const rule of LICENSE_CATEGORY_RULES) if (rule.re.test(hay)) return rule.cat;
  if (noAssert) return 'undeclared';
  return null;                                               // recognized but unmapped
}
// serve-time backfill — only when the model didn't supply category.
// serve-time repair for the double-nested dim-8 conflation: a weaker model can
// write the combined {runtime_surface:{…}, build_env:{…}} object into BOTH
// blocks, so report.runtime_surface / report.build_env end up nested one level
// too deep and render empty. Deterministically unwrap so 存量 reports display
// correctly without a re-run (mirrors assemble_report.py's unwrap_conflated_dim8).
const DIM8_KEYS = {
  runtime_surface: ['summary', 'network', 'filesystem', 'env_vars', 'subprocess', 'devices', 'services'],
  build_env: ['language_standard', 'runtime_version', 'build_system', 'compiler_extensions',
              'platforms', 'entry_points', 'packaging', 'notes'],
};
function normalizeDim8(report) {
  if (!report || typeof report !== 'object') return report;
  for (const [key, ownKeys] of Object.entries(DIM8_KEYS)) {
    const val = report[key];
    if (!val || typeof val !== 'object' || Array.isArray(val)) continue;
    if (ownKeys.some((k) => k in val)) continue;          // already correctly-keyed
    const inner = val[key];
    if (inner && typeof inner === 'object' && !Array.isArray(inner) && ownKeys.some((k) => k in inner))
      report[key] = inner;
  }
  return report;
}

function normalizeLicense(report) {
  if (!report || !report.license || typeof report.license !== 'object') return report;
  if (!report.license.category) {
    const c = deriveLicenseCategory(report);
    if (c) report.license.category = c;
  }
  return report;
}
// consistency check — model category vs the SPDX-derived one.
function validateLicense(report) {
  const lic = report && report.license;
  if (!lic || typeof lic !== 'object' || !lic.category) return [];
  const derived = deriveLicenseCategory({ license: { spdx: lic.spdx, name: lic.name } });
  if (derived && derived !== lic.category)
    return [['license_category_mismatch', W_ACT,
      `license.category(${lic.category}) 与依据 SPDX(${lic.spdx || '—'}) 派生的性质(${derived}) 不一致，请核对`]];
  return [];
}

// Serve-time shape tolerance for dim-12 code_partition. The agent occasionally emits synonym
// keys (bucket total_loc / module dir|module|name / note) instead of the schema's loc/path/reason,
// which rendered as blank module names + 0 LOC and broke the LOC-reconciliation warning. Coerce to
// canonical in place (never overwriting an existing canonical value) so 存量 reports render/tally
// correctly without a re-run — same pattern as normalizeHarmony/normalizeLicense.
function normalizeCodePartition(report) {
  const cp = report && report.code_partition;
  if (!cp || typeof cp !== 'object' || !Array.isArray(cp.buckets)) return report;
  for (const b of cp.buckets) {
    if (!b || typeof b !== 'object') continue;
    const mods = Array.isArray(b.modules) ? b.modules : [];
    for (const m of mods) {
      if (!m || typeof m !== 'object') continue;
      if (m.path == null) m.path = m.dir != null ? m.dir : (m.module != null ? m.module : m.name);
      if (m.reason == null && m.note != null) m.reason = m.note;
    }
    if (b.loc == null) {
      if (b.total_loc != null) b.loc = b.total_loc;
      else {                                              // backfill bucket loc from module locs
        const s = mods.reduce((a, m) => a + (Number(m && m.loc) || 0), 0);
        if (s > 0) b.loc = s;
      }
    }
  }
  return report;
}

// HarmonyOS porting class (5-way) for the dep-topology page. Prefers the agent's
// explicit harmony_adaptation.porting_class; else derives from the existing dim-9 fields
// so 存量 reports are classified without a re-run.
const PLATFORM_BLOCKER_RE = /win32|x11|xcb|cocoa|coregraphics|iokit|registry|wmi|sysfs|procfs|gpu|cuda|opencl|vulkan|device|driver|kernel|syscall|ioctl|permission|hardware|_api\b|api_unavailable|platform/i;
// A granular un-adaptability signal = the single source of truth for "some USED functionality
// has no HarmonyOS equivalent": dim-9 unadaptable_apis, or a blocker explicitly marked
// adaptability:'unadaptable'. (code_partition's unadaptable bucket is NOT used here — it's the
// less-authoritative, more error-prone dim; its ↔ dim-9 mismatch is left to validateReport.)
function hasUnadaptableSignal(ha) {
  if (!ha || typeof ha !== 'object') return false;
  if (Array.isArray(ha.unadaptable_apis) && ha.unadaptable_apis.length) return true;
  if (Array.isArray(ha.blockers) && ha.blockers.some((b) => b && b.adaptability === 'unadaptable')) return true;
  return false;
}
// Total LOC in the dim-12 code_partition needs_adaptation bucket(s). normalizeCodePartition runs
// before normalizeHarmony so bucket.class/.loc are already canonicalized here.
function needsAdaptationLoc(report) {
  const cp = report && report.code_partition;
  if (!cp || !Array.isArray(cp.buckets)) return 0;
  return cp.buckets.reduce((a, b) => a + (b && b.class === 'needs_adaptation' ? (Number(b.loc) || 0) : 0), 0);
}
// Should a dim-12 needs_adaptation bucket override cls UP to needs_adaptation? recompile_only
// (C/C++) definitionally means "zero source change", so ANY needs_adaptation module contradicts it →
// always override. no_adaptation (ported-runtime langs like Go/Rust/Python) legitimately tolerates
// trivial cross-compile platform branches (GOOS/cfg files that recompile unchanged), so require the
// bucket to be MATERIAL (≥5% of production code) before overriding — otherwise dim-12 over-bucketing
// of a few scattered platform lines wrongly upgrades a genuinely no-adaptation library. Returns the
// target class or null (leave cls as-is).
const NEEDS_ADAPTATION_MATERIAL_PCT = 0.05;
function needsAdaptationOverride(report, cls) {
  if (cls !== 'no_adaptation' && cls !== 'recompile_only') return null;
  const need = needsAdaptationLoc(report);
  if (need <= 0) return null;
  if (cls === 'recompile_only') return 'needs_adaptation';
  const prod = Number(report && report.code_metrics && report.code_metrics.production
    && report.code_metrics.production.code) || 0;
  return prod > 0 && need >= NEEDS_ADAPTATION_MATERIAL_PCT * prod ? 'needs_adaptation' : null;
}
// Legacy (pre-v4) 5-value porting_class → new 3-value axis; applied to the model pick when
// upgrading 存量 reports. The core/platform split is re-derived from unadaptable_apis[].functionality_class.
const LEGACY_PCLASS_MAP = { needs_adaptation_full: 'needs_adaptation',
  needs_adaptation_partial: 'needs_adaptation', infeasible: 'needs_adaptation' };
function collapseLegacyPclass(v) { return (v && LEGACY_PCLASS_MAP[v]) || v; }
// Hard invariant: a non-empty un-adaptability signal, or a dim-12 needs_adaptation bucket, means
// the class is AT LEAST needs_adaptation — no_adaptation/recompile_only assert "zero source change"
// and thus contradict it. Clamp UP (never down). Applied to BOTH the agent's explicit porting_class
// and the fallback derivation, so a self-contradictory report can't reach the panel/topology.
const CLAMPABLE_PORTING_CLASSES = new Set(['no_adaptation', 'recompile_only']);
function reconcilePortingClass(report, ha, cls) {
  if (!cls) return cls;
  if (CLAMPABLE_PORTING_CLASSES.has(cls) && hasUnadaptableSignal(ha)) return 'needs_adaptation';
  const na = needsAdaptationOverride(report, cls);
  if (na) return na;
  return cls;
}
function derivePortingClass(report) {
  const ha = (report && report.harmony_adaptation) || null;
  if (!ha) return null;
  let cls;
  if (ha.porting_class) {
    cls = collapseLegacyPclass(ha.porting_class);         // explicit (agent) — collapse legacy 5-way
  } else {
    const unadaptable = Array.isArray(ha.unadaptable_apis) ? ha.unadaptable_apis : [];
    const blk = Array.isArray(ha.blockers) ? ha.blockers : [];
    if (unadaptable.length
        || blk.some((b) => b.adaptability === 'unadaptable' || b.adaptability === 'partial')
        || blk.some((b) => b.severity === 'blocker')) {
      cls = 'needs_adaptation';
    } else {
      const cats = blk.map((b) => String(b.category || '').toLowerCase());
      const native = cats.some((c) => /native_dependency|ffi|toolchain|posix/.test(c));
      if (cats.some((c) => PLATFORM_BLOCKER_RE.test(c))) cls = 'needs_adaptation';
      else if (native) cls = 'recompile_only';
      else cls = 'no_adaptation';                         // pure script, no native work, no blockers
    }
  }
  return reconcilePortingClass(report, ha, cls);
}

// ---- adaptation_assessment: two-dimensional (core vs platform-difference) derivation -------
// 5-way effective_class (topology color + difficulty floor + rollup rank) worst→best order.
const LEGACY_FUNC_CLASS_DEFAULT_CORE = 'core';
const LEGACY_FUNC_CLASS_DEFAULT_PLATFORM = 'platform_specific';
function funcClassDefault(legacyPclass) {
  return legacyPclass === 'infeasible' ? LEGACY_FUNC_CLASS_DEFAULT_CORE : LEGACY_FUNC_CLASS_DEFAULT_PLATFORM;
}
// Derive harmony_adaptation.adaptation_assessment from porting_class + the (model-tagged or
// legacy-defaulted) unadaptable_apis[].functionality_class. Returns the 5-way effective_class used
// for the effort.level floor. Mutates ha in place. Byte-mirror of report_normalize.derive_adaptation_assessment.
function deriveAdaptationAssessment(report, ha, legacyPclass) {
  const cls = ha.porting_class;
  const coreIds = [], platIds = [];
  const uas = Array.isArray(ha.unadaptable_apis) ? ha.unadaptable_apis : [];
  for (const u of uas) {
    if (!u || typeof u !== 'object') continue;
    let fc = u.functionality_class;
    if (u.functionality_class_defaulted) {
      fc = funcClassDefault(legacyPclass);                // previously defaulted → re-derive, stay flagged
      u.functionality_class = fc;
    } else if (fc === 'core' || fc === 'platform_specific') {
      // model-provided
    } else {
      fc = funcClassDefault(legacyPclass);                // newly missing → backfill + flag provenance
      u.functionality_class = fc;
      u.functionality_class_defaulted = true;
    }
    (fc === 'core' ? coreIds : platIds).push(u.id);
  }
  const core = coreIds.filter(Boolean);
  const plat = platIds.filter(Boolean);
  let effective;
  if (cls === 'needs_adaptation') {
    if (core.length) effective = 'needs_adaptation_core_partial';
    else if (plat.length) effective = 'needs_adaptation_platform_partial';
    else effective = 'needs_adaptation';
  } else {
    effective = cls || 'no_adaptation';
  }
  const overall = effective === 'needs_adaptation_core_partial' ? 'core_blocked'
    : effective === 'needs_adaptation_platform_partial' ? 'adaptable_with_tailoring'
      : 'adaptable';
  ha.adaptation_assessment = {
    effective_class: effective,
    overall,
    core: { adaptable: !core.length, unadaptable: core },
    platform_specific: { adaptable: !plat.length, unadaptable: plat },
  };
  return effective;
}
// functional_viability: target-side "运行前提是否满足" verdict (mirror of report_normalize.derive_functional_viability).
// Orthogonal to porting_class/adaptation_assessment — worst-wins over required target_assumptions:
// unavailable→blocked_external > unknown→unverified > partial→viable_with_work > (all available/none)→viable.
const VIABILITY_RANK = { viable: 0, viable_with_work: 1, unverified: 2, blocked_external: 3 };
const STATUS_TO_VIABILITY = { unavailable: 'blocked_external', unknown: 'unverified', partial: 'viable_with_work', available: 'viable' };
function deriveFunctionalViability(ha) {
  let worst = 'viable';
  const ta = (ha && Array.isArray(ha.target_assumptions)) ? ha.target_assumptions : [];
  for (const a of ta) {
    if (!a || typeof a !== 'object' || !a.required) continue;
    const v = STATUS_TO_VIABILITY[a.target_status] || 'viable';
    if (VIABILITY_RANK[v] > VIABILITY_RANK[worst]) worst = v;
  }
  return worst;
}
// overall 是否可适配 verdict as a pure function of the 5-way effective_class (matches
// deriveAdaptationAssessment) — for deriving it on raw/unnormalized reports (topology/summary).
function overallForEffective(effectiveClass) {
  if (effectiveClass === 'needs_adaptation_core_partial') return 'core_blocked';
  if (effectiveClass === 'needs_adaptation_platform_partial') return 'adaptable_with_tailoring';
  return effectiveClass ? 'adaptable' : null;
}
// The 5-way effective_class for a report (topology/rollup): prefer the persisted derivation, else compute.
function effectivePortingClass(report) {
  const ha = (report && report.harmony_adaptation) || null;
  if (!ha) return null;
  if (ha.adaptation_assessment && ha.adaptation_assessment.effective_class) return ha.adaptation_assessment.effective_class;
  const cls = derivePortingClass(report);
  const clone = { ...ha, porting_class: cls };
  return deriveAdaptationAssessment(report, clone, ha.porting_class_model || ha.porting_class);
}

// ---- difficulty level (5-tier) + effort person-days -----------------------
// effort.level is DERIVED (not an independent model axis) from the 5-way effective_class (floor)
// × person_days (magnitude bucket), take-higher — keeps it self-consistent with the porting class
// while adding the "how much" the class alone can't express, and the numeric person_days aggregates up.
const LEVEL_RANK = { very_low: 0, low: 1, medium: 2, high: 3, very_high: 4 };
const RANK_LEVEL = ['very_low', 'low', 'medium', 'high', 'very_high'];
// floor keyed by the derived 5-way effective_class (NOT the 3-value porting_class).
const CLASS_LEVEL_FLOOR = { no_adaptation: 0, recompile_only: 1, needs_adaptation: 2,
  needs_adaptation_platform_partial: 3, needs_adaptation_core_partial: 4 };
function daysBucket(daysHi) {            // person-days (upper bound) → level rank
  const d = Number(daysHi);
  if (!(d > 2)) return 0;
  if (d <= 5) return 1;
  if (d <= 15) return 2;
  if (d <= 40) return 3;
  return 4;
}
function deriveDifficultyLevel(effectiveClass, personDaysHi) {
  if (!effectiveClass) return null;
  const floor = effectiveClass in CLASS_LEVEL_FLOOR ? CLASS_LEVEL_FLOOR[effectiveClass] : 0;
  return RANK_LEVEL[Math.max(floor, daysBucket(personDaysHi))];
}
// person-days [lo,hi] for a dim-9 block (the model's single effort axis).
function effortDays(ha) {
  if (!ha) return null;
  const e = ha.effort;
  if (e && Array.isArray(e.person_days) && e.person_days.length === 2) {
    const lo = Number(e.person_days[0]), hi = Number(e.person_days[1]);
    if (Number.isFinite(lo) && Number.isFinite(hi)) return [lo, hi];
  }
  return null;
}
// confidence ordinal for min-propagation up the tree.
const CONF_RANK = { low: 0, medium: 1, high: 2 };
const RANK_CONF = ['low', 'medium', 'high'];

// Report normalization is now single-sourced in scripts/report_normalize.py and persisted at
// assemble time (report.json is born normalized + stamped with meta.normalized_version). The JS
// functions below are the byte-identical MIRROR (a full-corpus parity test asserts they agree),
// kept only to upgrade legacy/older-stamp reports at serve time without a re-run. Bump BOTH this
// constant and report_normalize.NORMALIZED_VERSION together when the derivation logic changes.
// v2: consistency warnings carry a stable {code, class}; the model's self-review may dismiss an
// `actionable` one (meta.harmony_warnings_dismissed → meta.harmony_warnings_reviewed).
// v3: effort.breakdown recompile/api_adaptation derived from code_partition LOC at configurable
// rates, and effort.person_days total = Σ breakdown when itemized.
// v4: dim-9 refactor — feasibility/recommended_path removed; porting_class collapsed to 3 values;
// unadaptable_apis[].functionality_class drives a derived adaptation_assessment {effective_class,
// overall, core, platform_specific}; effort.level floor keyed by effective_class.
const NORMALIZED_VERSION = 5;
const W_ACT = 'actionable';   // model self-review may FIX (with evidence) or DISMISS as false positive
const W_INFO = 'info';        // deterministic audit note — never dismissible

// Effort-breakdown derivation (mirror of report_normalize.py). recompile / api_adaptation are
// derived from code_partition LOC ÷ configurable rate (settings.recompileLocPerDay /
// adaptationLocPerDay, defaults in DEFAULT_SETTINGS which MUST match the Python defaults).
const DERIVED_COMPONENTS = ['recompile', 'api_adaptation'];
function bucketLoc(report, cls) {
  const cp = report && report.code_partition;
  if (!cp || !Array.isArray(cp.buckets)) return 0;
  return cp.buckets.reduce((a, b) => a + ((b && b.class === cls) ? (Number(b.loc) || 0) : 0), 0);
}
function round1(x) {   // round half-up to 1 decimal; JS numbers drop a trailing .0 (3 not 3.0)
  const n = Number(x);
  return Number.isFinite(n) ? Math.round(Math.max(n, 0) * 10) / 10 : 0;
}
function sumBreakdown(bd) {
  let lo = 0, hi = 0, any = false;
  for (const b of bd) {
    const pd = b && Array.isArray(b.person_days) && b.person_days.length === 2 ? b.person_days : null;
    if (pd && Number.isFinite(Number(pd[0])) && Number.isFinite(Number(pd[1]))) { lo += Number(pd[0]); hi += Number(pd[1]); any = true; }
  }
  return any ? [lo, hi] : null;
}
function applyDerivedComponent(bd, comp, loc, rate, zhLabel) {
  loc = Number(loc) || 0;
  if (loc <= 0 || rate <= 0) return;
  let d = round1(loc / rate);
  if (!(d > 0)) d = 0.1;
  const pd = [d, d];
  const basis = `${zhLabel} ${Math.trunc(loc)} 行 ÷ ${Math.trunc(rate)} 行/天`;
  const existing = bd.find((b) => b && b.component === comp);
  if (existing) { existing.person_days = pd; existing.basis = basis; return; }
  bd.push({ component: comp, person_days: pd, basis });
}

// Serve-time normalize (mutates report.harmony_adaptation): fill the derived effort.level,
// person_days (from breakdown / legacy), adaptation_assessment (two-dimensional core/platform +
// 5-way effective_class + overall verdict), and stable ids — so 存量 reports gain the new
// structured fields without a re-run. Byte-mirror of report_normalize.normalize_harmony.
function normalizeHarmony(report) {
  const ha = report && report.harmony_adaptation;
  if (!ha || typeof ha !== 'object') return report;
  // base = the model's ORIGINAL pick (may be a legacy 5-value); preserved in porting_class_model
  // and read from there on re-normalization so the value stays re-derivable after overwrites.
  const base = ('porting_class_model' in ha) ? ha.porting_class_model : (ha.porting_class || null);
  ha.porting_class_model = base;
  const cls = derivePortingClass(report);                 // reconciled 3-value — may clamp the agent value up
  if (cls) {
    // Compare the COLLAPSED legacy base (not the raw 5-value) so a pure v3→v4 collapse isn't flagged
    // as a model contradiction; only a real clamp-up (recompile_only → needs_adaptation) records an adjustment.
    const collapsedBase = base ? collapseLegacyPclass(base) : base;
    if (collapsedBase && collapsedBase !== cls) ha.porting_class_adjusted = { from: collapsedBase, to: cls };
    ha.porting_class = cls;
  }
  // dropped in v4: feasibility / recommended_path
  delete ha.feasibility;
  delete ha.recommended_path;
  ha.effort = ha.effort && typeof ha.effort === 'object' ? ha.effort : {};
  const tag = (arr, p) => Array.isArray(arr) && arr.forEach((it, i) => { if (it && typeof it === 'object' && !it.id) it.id = `${p}:${i + 1}`; });
  tag(ha.target_assumptions, 'ta'); tag(ha.unadaptable_apis, 'ua'); tag(ha.blockers, 'bk');
  // target_status_model: persist the model's authored target_status once per assumption (the *_model
  // pattern) so the serve-time caps re-projection can overwrite target_status from live caps while
  // staying re-derivable. Mirror of report_normalize.normalize_harmony.
  if (Array.isArray(ha.target_assumptions))
    for (const a of ha.target_assumptions) if (a && typeof a === 'object' && !('target_status_model' in a)) a.target_status_model = (a.target_status ?? null);
  // confidence: a required + unknown target assumption deterministically caps confidence at medium.
  // Persist the model value once for idempotent re-derivation; restore when the cap no longer applies.
  if (!('confidence_model' in ha)) ha.confidence_model = (ha.confidence ?? null);
  const reqUnknown = (Array.isArray(ha.target_assumptions) ? ha.target_assumptions : [])
    .some((a) => a && typeof a === 'object' && a.required && a.target_status === 'unknown');
  const confM = ha.confidence_model;
  if (confM != null) ha.confidence = (reqUnknown && confM === 'high') ? 'medium' : confM;
  const meta = (report && typeof report.meta === 'object' && report.meta) ? report.meta : null;
  if (meta) {
    if (!('confidence_overall_model' in meta)) meta.confidence_overall_model = (meta.confidence_overall ?? null);
    const mc = meta.confidence_overall_model;
    if (mc != null) meta.confidence_overall = (reqUnknown && mc === 'high') ? 'medium' : mc;
  }
  // functional_viability: target-side "运行前提是否满足" verdict, orthogonal to porting_class.
  ha.functional_viability = deriveFunctionalViability(ha);
  // Two-dimensional (core vs platform-difference) assessment + 5-way effective_class. Needs the ua
  // ids assigned above; legacy default for functionality_class keys off the raw pick.
  const effective = deriveAdaptationAssessment(report, ha, base);
  // required_permissions: default missing harmony_status to unknown so the panel/xlsx
  // and confidence logic treat an unstated permission conservatively.
  if (Array.isArray(ha.required_permissions))
    for (const p of ha.required_permissions) if (p && typeof p === 'object' && !p.harmony_status) p.harmony_status = 'unknown';
  // Effort breakdown + total (mirror report_normalize.normalize_harmony). recompile /
  // api_adaptation are derived from code_partition LOC; only touch a model-provided breakdown
  // (never synthesise one) so re-normalization is idempotent and no-breakdown reports keep the
  // model's holistic person_days. total = Σ breakdown when itemized (decision Q1).
  const eff = ha.effort;
  const bd = Array.isArray(eff.breakdown) ? eff.breakdown : null;
  const hadBreakdown = Array.isArray(bd) && bd.length > 0;
  const modelDays = effortDays(ha);
  let total;
  if (hadBreakdown) {
    const rec = Number(settings.recompileLocPerDay) > 0 ? Number(settings.recompileLocPerDay) : 3000;
    const adp = Number(settings.adaptationLocPerDay) > 0 ? Number(settings.adaptationLocPerDay) : 500;
    applyDerivedComponent(bd, 'recompile', bucketLoc(report, 'recompile_reuse'), rec, '重编译复用');
    applyDerivedComponent(bd, 'api_adaptation', bucketLoc(report, 'needs_adaptation'), adp, '需适配');
    const s = sumBreakdown(bd);
    total = s !== null ? s : modelDays;
  } else {
    total = modelDays;
  }
  if (total) eff.person_days = [round1(total[0]), round1(total[1])];
  const pd = eff.person_days;
  eff.level = deriveDifficultyLevel(effective, Array.isArray(pd) && pd.length === 2 ? pd[1] : 0);
  // critical_dependencies: default a missing order to the array position (1-based).
  if (Array.isArray(ha.critical_dependencies))
    ha.critical_dependencies.forEach((c, i) => { if (c && typeof c === 'object' && !(Number(c.order) >= 1)) c.order = i + 1; });
  return report;
}

// Deterministic consistency check — returns 中文 warnings for the panel.
function validateHarmony(report) {
  const ha = report && report.harmony_adaptation;
  if (!ha || typeof ha !== 'object') return [];
  const w = [];
  const cls = ha.porting_class || derivePortingClass(report);
  // transparency: normalizeHarmony clamped a self-contradictory model porting_class UP to needs_adaptation
  // (recompile_only/no_adaptation + an unadaptable signal or a dim-12 needs_adaptation bucket).
  if (ha.porting_class_adjusted && ha.porting_class_adjusted.from !== ha.porting_class_adjusted.to) {
    w.push(['pclass_adjusted', W_INFO,
      `porting_class 模型原判 ${ha.porting_class_adjusted.from}，但代码分区(dim-12)存在需适配模块或不可适配 API/阻碍点，已按"不矛盾"校正为 ${ha.porting_class_adjusted.to}`]);
  }
  // soft hint (human-review only, not auto-clamped): recompile_only is definitionally the C/C++
  // NDK-rebuild class; a managed/ported-runtime lib (Go/Java/Python/JS/TS) with NO native surface
  // marked recompile_only is almost certainly a mis-file for no_adaptation.
  const eco = String((report.library && report.library.ecosystem) || '').toLowerCase();
  const managedEco = ['go', 'python', 'java', 'javascript', 'nodejs', 'node', 'typescript'].includes(eco);
  const na = report.native_api || {};
  const nativeSurface = (Array.isArray(na.dynamic_libraries) && na.dynamic_libraries.length)
    || (Array.isArray(na.groups) && na.groups.some((g) => g && ['ffi', 'platform', 'system', 'hardware'].includes(g.category)))
    || (Array.isArray(report.library && report.library.bindings) && report.library.bindings.length);
  if (cls === 'recompile_only' && managedEco && !nativeSurface)
    w.push(['recompile_no_native', W_INFO,
      `porting_class=recompile_only 但主生态为 ${eco}（已移植运行时）且无原生调用面，疑似应为 no_adaptation`]);
  const ua = Array.isArray(ha.unadaptable_apis) ? ha.unadaptable_apis : [];
  const blk = Array.isArray(ha.blockers) ? ha.blockers : [];
  const ta = Array.isArray(ha.target_assumptions) ? ha.target_assumptions : [];
  if (ua.length && cls !== 'needs_adaptation')
    w.push(['ua_pclass', W_INFO, `unadaptable_apis 非空但 porting_class=${cls}（应为 needs_adaptation）`]);
  for (const u of ua) {
    // functionality_class is backfilled by normalize; flag ones the MODEL omitted so the self-review
    // can tag core vs platform-difference with evidence (the default may be wrong).
    if (u && u.functionality_class_defaulted)
      w.push([`ua_func_class_defaulted:${u.id || u.api || ''}`, W_ACT,
        `unadaptable_api ${u.id || u.api || ''} 未标 functionality_class，已默认按 ${u.functionality_class} 归类——请据实标 core/platform_specific`]);
  }
  const ids = new Set([...ta, ...ua, ...blk].map((x) => x && x.id).filter(Boolean));
  const arr = (v) => (Array.isArray(v) ? v : []);   // a malformed string ref must not spread to chars
  for (const b of blk) for (const r of [...arr(b.caused_by), ...arr(b.manifests_as)])
    if (!ids.has(r)) w.push([`blocker_ref:${b.id || b.issue || ''}:${r}`, W_ACT, `blocker ${b.id || b.issue || ''} 的引用 ${r} 不存在（悬空引用）`]);
  for (const u of ua) for (const r of arr(u.caused_by)) if (!ids.has(r)) w.push([`ua_ref:${u.id || u.api || ''}:${r}`, W_ACT, `unadaptable_api ${u.id || u.api || ''} 的 caused_by ${r} 不存在`]);
  for (const a of ta) if (a && a.required && a.target_status === 'unavailable') {
    const refed = [...blk, ...ua].some((x) => (x.caused_by || []).includes(a.id));
    if (!refed) w.push([`ta_unref:${a.id || a.capability || ''}`, W_ACT, `target_assumption ${a.id || a.capability || ''} 为 required+unavailable 但无对应 blocker/unadaptable_api`]);
  }
  const reqUnknown = ta.some((a) => a && a.required && a.target_status === 'unknown');
  if (reqUnknown && ha.confidence_model === 'high')
    w.push(['confidence_capped_unknown', W_INFO, '存在 required 且 unknown 的目标假设，confidence 已由 high 确定性下调至 medium']);
  else if (reqUnknown && ha.confidence === 'high')
    w.push(['conf_high_unknown', W_ACT, '存在 required 且 unknown 的目标假设，confidence 不应为 high']);
  const perms = Array.isArray(ha.required_permissions) ? ha.required_permissions : [];
  for (const p of perms) if (p && p.harmony_status === 'unavailable' && !blk.length)
    w.push([`perm_unavail_noblocker:${p.permission || ''}`, W_ACT, `required_permission ${p.permission || ''} 为 unavailable 但无对应 blocker`]);
  return w;
}

// Cross-dimension consistency — catches model omissions/contradictions between
// capability_profile ↔ native_api ↔ dependencies ↔ dim-9. Conservative (only
// high-confidence signals) to avoid noise. Returns 中文 warnings.
// leading word-boundary only — library names often concatenate (Qt6Widgets, libGLESv2, cudart)
const CAP_SIGNALS = [
  // NB: avoid broad OS-API tokens (e.g. win32 = whole Windows API, mostly non-GUI) → false positives
  { key: 'gui', re: /\b(qt|pyqt|pyside|gtk|wxwidget|imgui|tkinter|electron|swing|javafx|\bswt\b|wpf|winui)/i },
  { key: 'rendering_3d', re: /\b(opengl|libgl|gles|egl|vulkan|directx|d3d1[12]|dxgi|webgpu)/i },
  { key: 'media', re: /\b(ffmpeg|libav|gstreamer|portaudio|libasound|pulseaudio|x264|openh264|libvpx|v4l2|avfoundation)/i },
  { key: 'hardware', re: /\b(cuda|nvcc|opencl|libusb|termios|bluez|npu|fpga)/i },
];
// cloud-vendor signals — from dep names, dynamic libs, and hard-coded network hosts.
// If a vendor SDK/domain shows up but cloud_services didn't flag it → likely 漏判.
const CLOUD_SIGNALS = [
  { vendor: 'google_firebase', re: /\b(firebase|firebaseio\.com|firebaseapp\.com|firebasestorage)/i },
  { vendor: 'aws', re: /\b(boto3|botocore|aws-sdk|aws-amplify|amazonaws\.com|awssdk)/i },
  { vendor: 'gcp', re: /\b(google-cloud|googleapis\.com|@google-cloud)/i },
  { vendor: 'azure', re: /\b(azure-|@azure\/|\.azure\.com|azurewebsites)/i },
  { vendor: 'alibaba_cloud', re: /\b(aliyun|aliyuncs\.com|@alicloud)/i },
  { vendor: 'tencent_cloud', re: /\b(tencentcloud|myqcloud\.com|tencentcloudapi)/i },
  { vendor: 'supabase', re: /\b(supabase)/i },
  { vendor: 'sentry', re: /\b(sentry-sdk|@sentry\/|sentry-native|sentry\.io)/i },
];
function validateReport(report) {
  if (!report || typeof report !== 'object') return [];
  const w = [];
  const cap = report.capability_profile || {};
  const scen = Array.isArray(cap.scenarios) ? cap.scenarios : [];
  const presentKeys = new Set(scen.filter((s) => s && s.present).map((s) => s.key));
  // collect the names/types that hint at a scenario, from deps + dynamic libs + api groups
  const na = report.native_api || {};
  const names = [
    ...((report.dependencies && report.dependencies.dependencies) || []).map((d) => d && d.name),
    ...((na.dynamic_libraries || []).map((d) => d && d.name)),
    ...((na.groups || []).map((g) => g && g.type)),
  ].filter(Boolean);
  // include a lib-stripped variant so a leading `lib`/path prefix doesn't hide the token
  const hay = names.flatMap((n) => [n, String(n).replace(/^lib/i, '')]).join('  ');
  for (const sig of CAP_SIGNALS) {
    if (sig.re.test(hay) && !presentKeys.has(sig.key))
      w.push([`cap_miss:${sig.key}`, W_ACT, `依赖/native_api 出现 ${sig.key} 强信号，但 capability_profile 未标记该场景（可能漏判）`]);
  }
  // present scenario without evidence
  for (const s of scen) if (s && s.present && !((s.evidence || []).length))
    w.push([`scenario_no_evidence:${s.key}`, W_ACT, `能力画像场景 ${s.key} present 但缺 evidence`]);
  // dangling permission → scenario
  const ha = report.harmony_adaptation || {};
  for (const p of (ha.required_permissions || []))
    if (p && p.source_capability && p.source_capability !== 'cloud_services' && !presentKeys.has(p.source_capability))
      w.push([`perm_dangling_cap:${p.permission || ''}`, W_ACT, `required_permission ${p.permission || ''} 的 source_capability=${p.source_capability} 不在已标记场景中`]);
  // present+unsupported scenario not reflected in dim-9
  const blk = Array.isArray(ha.blockers) ? ha.blockers : [];
  const ta = Array.isArray(ha.target_assumptions) ? ha.target_assumptions : [];
  const dimText = JSON.stringify([blk, ta, ha.unadaptable_apis || []]).toLowerCase();
  for (const s of scen) if (s && s.present && ['unavailable', 'partial'].includes(s.harmony_status)
      && !dimText.includes(String(s.key).toLowerCase()) && (blk.length + ta.length) === 0)
    w.push([`scenario_no_dim9:${s.key}`, W_ACT, `场景 ${s.key} 鸿蒙状态为 ${s.harmony_status} 但 dim-9 无对应阻碍/假设（可能漏登记）`]);
  // cloud service omission — vendor SDK/domain present in deps/network but cloud_services missed it
  const cs = report.cloud_services || {};
  const csvc = Array.isArray(cs.services) ? cs.services : [];
  const csVendors = new Set(csvc.map((s) => s && s.vendor).filter(Boolean));
  const netText = JSON.stringify(report.runtime_surface && report.runtime_surface.network || []);
  const cloudHay = (hay + '  ' + netText).toLowerCase();
  for (const sig of CLOUD_SIGNALS)
    if (sig.re.test(cloudHay) && !csVendors.has(sig.vendor))
      w.push([`cloud_miss:${sig.vendor}`, W_ACT, `依赖/网络出现 ${sig.vendor} 云服务强信号，但 cloud_services 未标记该厂商（可能漏判）`]);
  // cloud present but dim-9 has no INTERNET permission
  if (cs.present && csvc.length) {
    const perms = JSON.stringify(ha.required_permissions || []).toLowerCase();
    if (!perms.includes('internet'))
      w.push(['cloud_no_internet', W_ACT, `cloud_services 涉及云端但 dim-9 未登记 ohos.permission.INTERNET（可能漏登记）`]);
  }
  // dim-12 code_partition ↔ code_metrics ↔ dim-9 consistency
  const cp = report.code_partition || null;
  const cls = ha.porting_class || derivePortingClass(report);
  const uaList = Array.isArray(ha.unadaptable_apis) ? ha.unadaptable_apis : [];
  if (cp && Array.isArray(cp.buckets) && cp.buckets.length) {
    const prodCode = Number(report.code_metrics && report.code_metrics.production
      && report.code_metrics.production.code) || 0;
    const sum = cp.buckets.reduce((a, b) => a + (Number(b && b.loc) || 0), 0);
    if (prodCode > 0 && Math.abs(sum - prodCode) / prodCode > 0.15)
      w.push(['cp_loc_coverage', W_INFO, `代码分区桶 LOC 之和(${sum})与生产代码(${prodCode})偏差超过 15%（覆盖不足或重复计入）`]);
    const unLoc = cp.buckets.filter((b) => b && b.class === 'unadaptable')
      .reduce((a, b) => a + (Number(b.loc) || 0), 0);
    if (unLoc > 0 && cls !== 'needs_adaptation')
      w.push(['cp_unadapt_pclass', W_INFO, `代码分区含 unadaptable 桶(${unLoc} 行)但 porting_class=${cls}（应为 needs_adaptation）`]);
    // Same materiality gate as the reconcile clamp — only flag a genuine contradiction (a Go/Rust
    // no_adaptation lib with a few scattered cross-compile platform lines is NOT flagged).
    if (needsAdaptationOverride(report, cls))
      w.push(['cp_needs_full', W_INFO, `代码分区含 needs_adaptation 桶(${needsAdaptationLoc(report)} 行)但 porting_class=${cls}（应为 needs_adaptation；零源码改动才是 recompile_only）`]);
    if (unLoc > 0 && !uaList.length)
      w.push(['cp_unadapt_no_ua', W_ACT, '代码分区含 unadaptable 桶但 dim-9 unadaptable_apis 为空（漏登记或分桶过严）']);
    if (unLoc === 0 && uaList.length)
      w.push(['ua_no_cp_bucket', W_ACT, 'dim-9 有 unadaptable_apis 但代码分区无 unadaptable 桶（分桶可能漏标）']);
  }
  // effort.breakdown 分项之和应落在 person_days 区间附近
  const eb = ha.effort && Array.isArray(ha.effort.breakdown) ? ha.effort.breakdown : [];
  const days = effortDays(ha);
  if (eb.length && days) {
    let lo = 0, hi = 0;
    for (const b of eb) {
      const pd = b && Array.isArray(b.person_days) && b.person_days.length === 2 ? b.person_days : [0, 0];
      lo += Number(pd[0]) || 0; hi += Number(pd[1]) || 0;
    }
    if (hi < days[0] * 0.7 || lo > days[1] * 1.3)
      w.push(['effort_breakdown', W_INFO, `effort.breakdown 分项之和([${lo}, ${hi}])与 person_days([${days[0]}, ${days[1]}])明显不符`]);
  }
  // critical_dependencies referential integrity
  const cds = Array.isArray(ha.critical_dependencies) ? ha.critical_dependencies : [];
  if (cds.length) {
    const deps = (report.dependencies && report.dependencies.dependencies) || [];
    const depByName = new Map(deps.filter((d) => d && d.name)
      .map((d) => [String(d.name).toLowerCase(), d]));
    const idSet = new Set([...(ha.blockers || []), ...uaList, ...(ha.target_assumptions || [])]
      .map((x) => x && x.id).filter(Boolean));
    for (const c of cds) {
      if (!c || !c.name) continue;
      const dep = depByName.get(String(c.name).toLowerCase());
      if (!dep)
        w.push([`critical_dep_notfound:${c.name}`, W_ACT, `critical_dependencies 的 ${c.name} 在 dependencies 列表中找不到（名称须与 dependencies[].name 一致）`]);
      else if (dep.harmony_adapted === true)
        w.push([`critical_dep_adapted:${c.name}`, W_ACT, `critical_dependencies 列出了已鸿蒙化依赖 ${c.name}（官方源已有移植产物，不应列入关键路径）`]);
      for (const r of (Array.isArray(c.refs) ? c.refs : [])) if (!idSet.has(r))
        w.push([`critical_dep_ref:${c.name}:${r}`, W_ACT, `critical_dependencies ${c.name} 的引用 ${r} 不存在（悬空引用）`]);
    }
  }
  return w;
}

// Mirror of report_normalize.normalize_report's warning block. Runs the three validators
// (which now yield [code, class, message] triples), then applies the model self-review's
// dismissals: an `actionable` warning whose code is listed in meta.harmony_warnings_dismissed
// moves to `reviewed` (with rationale); everything else (incl. all `info` audit notes) stays
// active. Returns {active:[{code,class,message}], reviewed:[{code,message,rationale}]}.
function computeWarnings(report) {
  const raw = [...validateHarmony(report), ...validateReport(report), ...validateLicense(report)];
  const meta = (report && report.meta) || {};
  const dismissed = new Map();
  for (const d of (Array.isArray(meta.harmony_warnings_dismissed) ? meta.harmony_warnings_dismissed : []))
    if (d && d.code) dismissed.set(d.code, d.rationale || '');
  const active = [];
  const reviewed = [];
  for (const [code, cls, message] of raw) {
    if (cls === W_ACT && dismissed.has(code)) reviewed.push({ code, message, rationale: dismissed.get(code) });
    else active.push({ code, class: cls, message });
  }
  return { active, reviewed };
}

// ---- bottom-up adaptation rollup (serve-time, API-granular) ----------------
// worst-wins lattice over the 5-way effective_class (needs_adaptation_core_partial worst).
const CLASS_RANK = { no_adaptation: 0, recompile_only: 1, needs_adaptation: 2,
  needs_adaptation_platform_partial: 3, needs_adaptation_core_partial: 4 };
const RANK_CLASS = ['no_adaptation', 'recompile_only', 'needs_adaptation', 'needs_adaptation_platform_partial', 'needs_adaptation_core_partial'];
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
        viaSymbols: hit, basis: hit.length ? 'used_api' : (used.length ? 'used_other' : 'scope'),
        days: ce.days || null });
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
    n.blockingChildren = (r.blockingChildren || []).slice()
      .sort((a, b) => ((b.days ? b.days[1] : 0) - (a.days ? a.days[1] : 0)));
    n.rollupEffort = r.days || null;
    n.rollupConfidence = r.confRank == null ? null : RANK_CONF[r.confRank];
    n.rollupLevel = deriveDifficultyLevel(n.rollupClass, r.days ? r.days[1] : 0);
  }
  // Serve-time critical path: from each analyzed node, follow the child that
  // contributes the most rollup person-days (needs actual porting work) — the
  // dependency chain porting must clear first. Derived from the memoized rollup,
  // so 存量 reports get it without a re-run; complements the model-emitted
  // harmony_adaptation.critical_dependencies (which also covers unanalyzed deps).
  const nextOnPath = (id) => {
    let best = null, bestHi = -1;
    for (const e of (out.get(id) || [])) {
      const m = memo.get(e.target);
      if (!m || m.rank == null || m.rank <= 0) continue;   // no porting work → not critical
      const hi = m.days ? m.days[1] : 0;
      if (hi > bestHi) { best = e.target; bestHi = hi; }
    }
    return best;
  };
  for (const n of topo.nodes) {
    if (!n.analyzed) { n.criticalPath = []; continue; }
    const path = [], seen = new Set([n.id]);
    let cur = nextOnPath(n.id);
    while (cur && !seen.has(cur) && path.length < 20) {
      seen.add(cur);
      const c = byId.get(cur), m = memo.get(cur) || {};
      path.push({ id: cur, label: c ? c.label : cur, libName: (c && c.libName) || null,
        class: m.rank == null ? null : classOfRank(m.rank), days: m.days || null });
      cur = nextOnPath(cur);
    }
    n.criticalPath = path;
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
  const idx = buildIdentityIndex(getRep, g);
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
      const hit = resolveDepLib(d, idx);
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
      // color/rank by the 5-way effective_class (needs_adaptation core/platform split); the 3-value
      // porting_class is kept separately for reference.
      node.portingClass = node.selfClass = effectivePortingClass(rep);
      const ha = (rep && rep.harmony_adaptation) || {};
      // derive overall from the (possibly computed) effective_class so raw/unnormalized on-disk reports work too
      node.overall = (ha.adaptation_assessment && ha.adaptation_assessment.overall) || overallForEffective(node.selfClass);
      node.adaptationAssessment = ha.adaptation_assessment || null;
      node.summary = ha.summary || '';
      node.unadaptableApis = Array.isArray(ha.unadaptable_apis) ? ha.unadaptable_apis : [];
      node.effortDays = effortDays(ha);
      node.confidence = ha.confidence || null;
    }
  }
  return { root: rootName, nodes: [...nodes.values()], edges };
}

// ---------------------------------------------------------------- clone
function startClone({ url: rawUrl, ref, overwrite, tag, group, subpath }) {
  // Monorepo: parse an optional subdir + branch out of the URL (…/tree/<ref>/<sub>).
  // An explicit `subpath` (panel field) wins over the URL-derived one; likewise ref.
  const parsed = parseRepoUrl(rawUrl);
  const gitUrl = parsed.gitUrl;
  const sub = (subpath && String(subpath).trim()) || parsed.subpath || null;
  const cloneRef = ref || parsed.ref || null;
  const g = ensureGroupDirs(group);
  // Storage handle: the git basename (or the subdir leaf for a monorepo subunit),
  // disambiguated when it collides with a DIFFERENT upstream repo/subpath already in
  // this group (owner-qualified). Same repo+subpath (by identity) keeps its handle.
  const ckey = canonicalRepoKey(gitUrl, sub);
  const baseHandle = sub
    ? (sub.replace(/\/+$/, '').split('/').pop() || repoNameFromUrl(gitUrl)).replace(/[^A-Za-z0-9._-]/g, '_')
    : repoNameFromUrl(gitUrl);
  const name = pickCloneHandle(g, baseHandle, gitUrl, ckey);
  const dest = repoDir(g, name);
  if (fs.existsSync(dest)) {
    if (!overwrite) throw new Error(`repos/${g}/${name} already exists (enable overwrite to re-clone)`);
    fs.rmSync(dest, { recursive: true, force: true });
  }
  const args = ['clone', '--progress', '--depth', '1'];
  // Monorepo subdir: partial + sparse clone so a giant repo (chromium) only fetches
  // the subtree (+ root files via cone mode) instead of the whole GB working tree.
  // The `sparse-checkout set <subpath>` runs in the clone-end listener after checkout.
  if (sub) args.push('--filter=blob:none', '--sparse');
  if (cloneRef) args.push('--branch', cloneRef);
  args.push(gitUrl, dest);
  // 来源标签：默认主软件；递归/待分析依赖传 'passive'。end 回调里克隆成功才落库。
  const job = new Job('clone', { name, group: g, argv: ['git', ...args], url: gitUrl, subpath: sub, ref: cloneRef, tag: TAG_VALUES.includes(tag) ? tag : 'primary' });
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
  // Block-streaming: the agent writes each dimension to <runDir>/blocks/<name>.json as
  // it reasons, then assemble_report.py splices them + metrics into report.json. Pre-create
  // the dir so the agent's Writes never race on a missing parent.
  fs.mkdirSync(path.join(runDir, 'blocks'), { recursive: true });
  const reportPath = path.join(runDir, 'report.json');
  const repoRootRel = path.relative(ROOT, repoPathAbs);   // repos/<group>/<name> (clone root)
  // Monorepo subunit: analyze the subdir, but keep the clone root for git commit /
  // reading root manifests. Non-monorepo: analyzeDir == clone root (unchanged behavior).
  const identity = readIdentity(group, name);
  const sub = identity && identity.subpath ? String(identity.subpath) : null;
  const analyzeDirAbs = sub ? path.join(repoPathAbs, sub) : repoPathAbs;
  const repoRel = path.relative(ROOT, analyzeDirAbs);     // {repoPath} — analysis root

  const codegraphOn = codegraphAvailable && (opts.useCodegraph ?? settings.useCodegraph);
  // Index is pre-built by the server (at clone, and as a safety-net below) — tell the
  // agent to USE it rather than re-build it. For a monorepo subunit, scope to the subdir.
  if (codegraphOn) ensureCodegraphIndex(analyzeDirAbs);
  const codegraphHint = codegraphOn
    ? `codegraph is installed and the structural index for ${repoRel} is pre-built by ` +
      `\`codegraph init\`: prefer \`codegraph context/query/callers -p ${repoRel} -j\` for the ` +
      `function-summary and native/platform-API dimensions (fall back to grep/Read if any codegraph call fails). `
    : '';
  const monorepoNote = sub
    ? `本次分析的是 monorepo（克隆根在 ${repoRootRel}）的子目录 \`${sub}\`。把该子目录当作被分析的库：` +
      `code-metrics、native_api、"实际用到的依赖" 都以子目录（${repoRel}）为范围；可读取克隆根 ${repoRootRel} 下的` +
      `构建/清单文件（DEPS、BUILD.gn、根 package.json/go.mod 等）理解其依赖；git commit 用克隆根 ${repoRootRel}；` +
      `在报告里设置 library.source_subpath="${sub}"、library.monorepo=true，library.source_url 仍为仓库根 URL。 `
    : '';
  const harmonySkillsOn = HARMONY_DOC_SKILLS.length
    && (opts.enableHarmonyDocSkills ?? settings.enableHarmonyDocSkills);
  const harmonySkillsHint = harmonySkillsOn
    ? `鸿蒙文档技能可用：opencode 全局 skill ${HARMONY_DOC_SKILLS.join(' 与 ')} 已安装` +
      '（前者为 API 签名/ohos.permission.* 权限/SysCap 的官方 API 参考，后者为官方开发指南/FAQ）。' +
      '在 dim-9/dim-10 判断鸿蒙等价 API、权限精确名与适配路径时，按 harmony-adaptation SKILL.md 的' +
      '「目标侧 API 事实核查」步骤使用：先用 skill 工具按名加载，再在其返回的文档目录内 Glob/Grep 检索' +
      '（文件名过滤优先，每库 ≤10 次），引用的文档以文件名入 evidence/source。' +
      '注意：文档证明 API 在鸿蒙存在 ≠ PC 形态可用——PC 可用性仍以 references/harmony-pc-capabilities.json 为权威。 '
    : '';
  let prompt = (opts.promptTemplate || settings.promptTemplate || DEFAULT_PROMPT)
    .replaceAll('{codegraphHint}', codegraphHint)
    .replaceAll('{harmonySkillsHint}', harmonySkillsHint)
    .replaceAll('{monorepoNote}', monorepoNote)
    .replaceAll('{repoPath}', repoRel)
    .replaceAll('{repoRoot}', repoRootRel)
    .replaceAll('{agentFile}', AGENT_FILE)
    .replaceAll('{reportPath}', path.relative(ROOT, reportPath))
    .replaceAll('{metricsPath}', path.relative(ROOT, path.join(runDir, 'metrics.json')))
    .replaceAll('{runDir}', path.relative(ROOT, runDir))
    .replaceAll('{name}', name);
  // Robust to stale saved templates that predate {monorepoNote}: append it if a
  // subpath is set but the placeholder didn't land.
  if (monorepoNote && !prompt.includes('source_subpath')) prompt = prompt + ' ' + monorepoNote;
  // Robust to stale/custom templates that predate block-streaming: if the prompt doesn't
  // mention the assemble step, append the incremental-blocks + assemble instruction so the
  // run never falls back to one giant final Write.
  if (!prompt.includes('assemble_report'))
    prompt = prompt + ` 分块流式产出：每算完一个维度立即 Write 到 ${path.relative(ROOT, path.join(runDir, 'blocks'))}/<name>.json`
      + `（文件名=报告顶层键；不要自己产出 languages/code_metrics/tests），全部写完后运行 `
      + `\`python3 scripts/assemble_report.py --run-dir ${path.relative(ROOT, runDir)}\` 组装并原子写 report.json（勿手写 report.json）。`;
  // Robust to stale saved templates that predate the {codegraphHint} placeholder:
  // if codegraph is enabled but the hint didn't land, append it.
  if (codegraphHint && !prompt.includes('codegraph')) prompt = prompt + ' ' + codegraphHint;
  // Robust to stale saved templates that predate the {harmonySkillsHint} placeholder.
  if (harmonySkillsHint && !prompt.includes('harmonyos-sdk-api-lookup'))
    prompt = prompt + ' ' + harmonySkillsHint;
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
  'leaf_no_source', 'leaf_harmonized', 'ambiguous', 'failed', 'capped']);
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
    this.manual = !!opts.manual;              // 手动模式：只展示 frontier，待用户批准才 clone/analyze
    this.autoRoot = !this.manual;             // 非手动 = 从根整树全量自动（保留原行为）
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

  // Check the HarmonyOS-PC mirror for this dep (async, fire-and-forget → re-ticks).
  // A hit seals it as a leaf (no recurse); a miss just flags it so the next tick
  // proceeds to resolve/clone/analyze as usual.
  async _checkHarmonized(dec, d) {
    dec.harmonyChecking = true;
    let adapted = false;
    try { adapted = await harmonyMirror.isAdapted(ecoNorm(d.ecosystem), d.name); } catch (_) {}
    dec.harmonyChecking = false;
    dec.harmonyChecked = true;
    if (this.status !== 'running') return;
    if (adapted) this._set(dec, 'leaf_harmonized', '已鸿蒙化（镜像已提供预编译/ohos 包），无需递归');
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

    // 手动模式门控：未经用户批准的依赖只做免费的本地 URL 预填（供查看/编辑），
    // 不联网、不克隆、不分析——等待 /api/recurse/advance 把 dec.approved 置真。
    if (this.manual && !dec.approved) {
      if (!dec.repoName) {
        const url = extractGitUrl(d.source, d.version);
        if (url) { dec.url = url; dec.repoName = repoNameFromUrl(url); this._set(dec, 'resolved', '待选择'); }
        else this._set(dec, 'pending', '待选择（请填写 Git 地址）');
      }
      return;
    }

    // 已移植到鸿蒙 PC 镜像 → 封闭叶子，不再 resolve/clone/analyze
    // （与 dim-9 rollupAdaptation 把已鸿蒙化依赖当封闭叶子的口径一致）。只在初始 pending
    // 态触发一次，避免影响已在 resolving/cloning/analyzing 的在途决策。
    if (settings.enableHarmonyMirror && dec.state === 'pending'
        && !dec.harmonyChecked && !dec.harmonyChecking) {
      this._checkHarmonized(dec, d);   // async；完成后 re-tick
      return;
    }

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
    const idx = buildIdentityIndex(getRep, this.group);
    const repos = new Set(listRepos(this.group));

    // 已分析子库 → 其引入决策（用于把「递归」批准沿依赖树向下传递）
    const byRepo = new Map();
    for (const dec of this.decisions.values()) if (dec.repoName) byRepo.set(dec.repoName, dec);

    // BFS over analyzed reports → collect unanalyzed runtime deps + their depth.
    // 队列携带 auto：根=autoRoot，子库继承祖先 auto 或该库被「递归」批准的 autoRecurse。
    const seen = new Set([this.root]);
    const frontier = new Map();   // depKey -> { d, depth, ambiguous, auto }
    const queue = [{ libName: this.root, depth: 0, auto: this.autoRoot }];
    while (queue.length) {
      const cur = queue.shift();
      if (cur.depth >= this.opts.maxDepth) continue;
      const rep = getRep(cur.libName);
      const deps = (rep && rep.dependencies && rep.dependencies.dependencies) || [];
      for (const d of deps) {
        if (!d || !d.name || !isRuntimeDep(d)) continue;
        const hit = resolveDepLib(d, idx);
        if (hit && !hit.ambiguous) {                       // analyzed → recurse into it
          if (!seen.has(hit.libName)) {
            seen.add(hit.libName);
            const decL = byRepo.get(hit.libName);
            queue.push({ libName: hit.libName, depth: cur.depth + 1, auto: cur.auto || !!(decL && decL.autoRecurse) });
          }
          continue;
        }
        const depKey = ecoNorm(d.ecosystem) + ':' + normName(d.name);
        const prev = frontier.get(depKey);
        const nd = cur.depth + 1;
        frontier.set(depKey, {
          d: (prev && prev.depth <= nd) ? prev.d : d,
          depth: prev ? Math.min(prev.depth, nd) : nd,
          ambiguous: (prev ? prev.ambiguous : false) || !!(hit && hit.ambiguous),
          auto: (prev ? prev.auto : false) || cur.auto,
        });
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
      if (f.auto && !dec.approved) { dec.approved = true; dec.autoRecurse = true; this._changed = true; }
      this._advance(dec, f.d, repos);
    }
    // reconcile in-flight decisions that completed but left the frontier
    for (const dec of this.decisions.values()) {
      if (TERMINAL.has(dec.state)) continue;
      if (dec.repoName && latestReport(dec.repoName, this.group)) this._set(dec, 'analyzed', '', dec.repoName);
    }
    // done: 手动会话仅当所有依赖都终态（有「待选择」依赖则保持 running、SSE 不关闭，
    // 等用户继续批准）；非手动会话沿用「无活跃即完成」。
    const decs = [...this.decisions.values()];
    const doneNow = this.manual ? decs.every((d) => TERMINAL.has(d.state)) : !decs.some((d) => ACTIVE.has(d.state));
    if (doneNow && this.status === 'running') { this.status = 'done'; this._changed = true; }
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
        .map((d) => ({ key: d.key, name: d.name, ecosystem: d.ecosystem, depth: d.depth, state: d.state,
          reason: d.reason || '', repoName: d.repoName || null, libName: d.libName || null, url: d.url || null,
          approved: !!d.approved, autoRecurse: !!d.autoRecurse })),
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
      const sub = job.meta.subpath || null;
      // Monorepo: expand the sparse set to the target subtree (cone mode also keeps
      // repo-root files, so dependency manifests like DEPS/BUILD.gn come along).
      if (sub) {
        try {
          require('child_process').execFileSync('git', ['-C', rp, 'sparse-checkout', 'set', '--cone', sub],
            { stdio: 'pipe', timeout: 300000 });
          job.log('stdout', `[monorepo] sparse-checkout set ${sub}`);
        } catch (e) {
          job.log('stderr', `[monorepo] sparse-checkout failed（可能服务器不支持 partial clone）：${e.message}`);
        }
      }
      writeIdentity(job.meta.group, job.meta.name, job.meta.url, sub, job.meta.ref);   // 句柄↔上游仓身份(含 subpath)
      // Index only the analyzed subtree for a monorepo subunit (cheaper + scoped).
      const idxPath = sub ? path.join(rp, sub) : rp;
      ensureCodegraphIndex(idxPath, (s) => { try { job.log('stdout', `[codegraph] ${s}`); } catch (_) {} });
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
      // Explicit subpath (panel field) only applies to a single URL — ambiguous for a
      // batch. Each URL's own …/tree/<ref>/<sub> is still parsed inside startClone.
      const explicitSub = urls.length === 1 ? body.subpath : undefined;
      const out = urls.map((u) => {
        try { const j = startClone({ url: u, ref: body.ref, overwrite: body.overwrite, tag: body.tag, group: body.group, subpath: explicitSub });
          return { url: u, jobId: j.id, name: j.meta.name, subpath: j.meta.subpath || undefined }; }
        catch (e) { return { url: u, error: String(e.message || e) }; }
      });
      return send(res, 200, { jobs: out });
    }

    if (req.method === 'POST' && pathname === '/api/library-tags') {
      const body = await readBody(req);
      if (!body.name) return send(res, 400, { error: 'name required' });
      return send(res, 200, { name: body.name, group: safeGroup(body.group), tags: setLibTags(body.name, body.group, body.tags) });
    }

    // 彻底删除一个库：克隆代码 + 全部分析记录 + 来源标签 + 关联的递归会话。
    if (req.method === 'POST' && pathname === '/api/library/delete') {
      const body = await readBody(req);
      const name = body.name;
      const g = safeGroup(body.group);
      if (!name) return send(res, 400, { error: 'name required' });
      if (/[\\/]|\.\./.test(name)) return send(res, 400, { error: 'invalid name' });   // 防目录穿越
      if (activeJobFor(name, g)) return send(res, 409, { error: '该库有进行中的任务，请先停止/等待完成再删除' });
      try {
        fs.rmSync(repoDir(g, name), { recursive: true, force: true });
        fs.rmSync(runLibDir(g, name), { recursive: true, force: true });
      } catch (e) { return send(res, 500, { error: '删除失败: ' + e.message }); }
      setLibTags(name, g, []);                          // 清来源标签（空列表会 delete tags[k]）
      for (const [id, s] of recursionSessions)          // 清以该库为 root 的递归会话
        if (s.root === name && safeGroup(s.group) === g) recursionSessions.delete(id);
      return send(res, 200, { ok: true });
    }

    // 删除单次运行记录（只删该 <ts> 目录，不动库本身、其它运行、标签）。
    if (req.method === 'POST' && pathname === '/api/run/delete') {
      const body = await readBody(req);
      const name = body.name;
      const run = body.run;
      const g = safeGroup(body.group);
      if (!name || !run) return send(res, 400, { error: 'name and run required' });
      if (/[\\/]|\.\./.test(name) || /[\\/]|\.\./.test(run)) return send(res, 400, { error: 'invalid name/run' });   // 防目录穿越
      const runDir = path.join(runLibDir(g, name), run);
      if (!runDir.startsWith(RUNS) || !fs.existsSync(runDir)) return send(res, 404, { error: 'run not found' });
      for (const j of jobs.values())                    // 拦「正在产出的那次运行」（精确到 run 目录）
        if ((j.status === 'running' || j.status === 'queued') && j.meta.runDir &&
            path.resolve(j.meta.runDir) === path.resolve(runDir))
          return send(res, 409, { error: '该运行正在进行中，请先停止/等待完成再删除' });
      try { fs.rmSync(runDir, { recursive: true, force: true }); }
      catch (e) { return send(res, 500, { error: '删除失败: ' + e.message }); }
      return send(res, 200, { ok: true });
    }

    // 将库（代码 + 分析记录 + 标签）迁移到另一个分组。
    if (req.method === 'POST' && pathname === '/api/library/migrate') {
      const body = await readBody(req);
      const name = body.name;
      const fromG = safeGroup(body.fromGroup);
      const toG = safeGroup(body.toGroup);
      if (!name) return send(res, 400, { error: 'name required' });
      if (/[\\/]|\.\./.test(name)) return send(res, 400, { error: 'invalid name' });
      if (fromG === toG) return send(res, 400, { error: 'fromGroup and toGroup must differ' });
      if (activeJobFor(name, fromG)) return send(res, 409, { error: '该库有进行中的任务，请先停止/等待完成再迁移' });
      const srcRepo = repoDir(fromG, name);
      const srcRuns = runLibDir(fromG, name);
      const hasSrcRepo = fs.existsSync(srcRepo);
      const hasSrcRuns = fs.existsSync(srcRuns);
      if (!hasSrcRepo && !hasSrcRuns) return send(res, 404, { error: '源库不存在' });
      const dstRepo = repoDir(toG, name);
      const dstRuns = runLibDir(toG, name);
      if (fs.existsSync(dstRepo) || fs.existsSync(dstRuns))
        return send(res, 409, { error: `目标分组「${toG}」中已存在同名库「${name}」` });
      ensureGroupDirs(toG);
      try {
        if (hasSrcRepo) fs.renameSync(srcRepo, dstRepo);
        if (hasSrcRuns) fs.renameSync(srcRuns, dstRuns);
      } catch (e) { return send(res, 500, { error: '迁移失败: ' + e.message }); }
      // 更新标签 key：fromG/name → toG/name
      const tags = loadTags();
      const oldKey = fromG + '/' + name;
      const newKey = toG + '/' + name;
      if (tags[oldKey] !== undefined) {
        tags[newKey] = tags[oldKey];
        delete tags[oldKey];
        saveTags(tags);
      }
      return send(res, 200, { ok: true, name, fromGroup: fromG, toGroup: toG });
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
      const idx = buildIdentityIndex(getRep, pg);
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
          if (resolveDepLib(d, idx)) continue;   // already an analyzed library (by URL identity or name)
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

    // 手动会话：批准选中的依赖并推进。recurse=true → 该依赖及其子依赖继续自动级联；
    // recurse=false → 仅分析本层；recurseAll=true → 整树转全量自动。
    if (req.method === 'POST' && pathname === '/api/recurse/advance') {
      const body = await readBody(req);
      const s = recursionSessions.get(body.session);
      if (!s) return send(res, 404, { error: 'unknown session' });
      if (body.recurseAll) {
        s.autoRoot = true;
      } else {
        for (const it of (Array.isArray(body.items) ? body.items : [])) {
          const dec = it && s.decisions.get(it.key);
          if (!dec || TERMINAL.has(dec.state)) continue;
          if (it.url) { dec.url = String(it.url).trim(); dec.repoName = repoNameFromUrl(dec.url); }
          if (!dec.url) continue;                       // 无地址不批准
          dec.approved = true;
          dec.autoRecurse = !!body.recurse;
          s._set(dec, 'resolved', body.recurse ? '已批准（递归）' : '已批准（仅本层）');
        }
      }
      if (s.status !== 'running') s.status = 'running';  // 复活已 done 的手动会话
      s.tick();
      return send(res, 200, s.snapshot());
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
      // A report born/migrated through scripts/report_normalize.py carries the current version
      // stamp and is already self-consistent (single source of truth: derived porting_class /
      // feasibility / effort.level + persisted meta.harmony_warnings) — serve as-is. Only
      // legacy/older-stamp reports get the JS mirror at serve time, so 存量 upgrade without a re-run.
      if (!(rep && rep.meta && Number(rep.meta.normalized_version) >= NORMALIZED_VERSION)) {
        normalizeDim8(rep);
        normalizeCodePartition(rep);   // before normalizeHarmony: canonical loc/path feeds LOC对账 + class校正
        normalizeHarmony(rep);
        normalizeLicense(rep);
        const { active, reviewed } = computeWarnings(rep);
        rep.meta = rep.meta && typeof rep.meta === 'object' ? rep.meta : {};
        if (active.length) rep.meta.harmony_warnings = active; else delete rep.meta.harmony_warnings;
        if (reviewed.length) rep.meta.harmony_warnings_reviewed = reviewed; else delete rep.meta.harmony_warnings_reviewed;
      }
      // Serve-time caps re-projection — runs for EVERY report regardless of the version stamp (like
      // the topology rollup). Overwrite each target_assumption.target_status from the LIVE caps (by
      // capability_key; caps is the authoritative target-side source, the model's value kept in
      // target_status_model), then re-derive functional_viability + the required+unknown confidence
      // cap from the projected statuses. So curating a caps row refreshes every dependent report on
      // read — no re-analysis. Graceful degrade: any caps failure serves the report un-reprojected.
      try {
        const ha = rep && rep.harmony_adaptation;
        const ta = ha && Array.isArray(ha.target_assumptions) ? ha.target_assumptions : null;
        if (ta && ta.length) {
          const caps = harmonyCaps.load();
          const statusById = new Map();
          for (const s of (caps && Array.isArray(caps.sections) ? caps.sections : []))
            for (const row of (s && Array.isArray(s.rows) ? s.rows : []))
              if (row && row.id && row.status) statusById.set(row.id, row.status);
          for (const a of ta) {
            if (!a || typeof a !== 'object' || !a.capability_key || !statusById.has(a.capability_key)) continue;
            if (!('target_status_model' in a)) a.target_status_model = (a.target_status ?? null);
            a.target_status = statusById.get(a.capability_key);
          }
          ha.functional_viability = deriveFunctionalViability(ha);
          const reqUnknown = ta.some((a) => a && a.required && a.target_status === 'unknown');
          if (ha.confidence_model != null)
            ha.confidence = (reqUnknown && ha.confidence_model === 'high') ? 'medium' : ha.confidence_model;
          if (rep.meta && rep.meta.confidence_overall_model != null)
            rep.meta.confidence_overall = (reqUnknown && rep.meta.confidence_overall_model === 'high') ? 'medium' : rep.meta.confidence_overall_model;
        }
      } catch (_) { /* caps unavailable → serve report as-is (no re-projection) */ }
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
      try {
        const caps = harmonyCaps.load();
        // 反哺研究优先级：跨所有已分析报告聚合每个目标能力行「被 N 个分析需要」
        // （经 harmony_adaptation.target_assumptions[].capability_key）。遍历范式同 /api/observations。
        const demand = {};   // rowId -> {count, unknown, libs:[]}
        for (const grp of listGroups()) for (const lib of listLibraries(grp)) {
          if (!lib.latest || !lib.latest.reportAvailable) continue;
          const rep = latestReport(lib.name, grp);
          const tas = (rep && rep.harmony_adaptation && rep.harmony_adaptation.target_assumptions) || [];
          const seen = new Set();   // 同一报告对同一行只计一次
          for (const ta of tas) {
            const key = ta && ta.capability_key;
            if (!key || seen.has(key)) continue;
            seen.add(key);
            let d = demand[key]; if (!d) d = demand[key] = { count: 0, unknown: 0, libs: [] };
            d.count++; d.libs.push(lib.name);
            if (ta.target_status === 'unknown') d.unknown++;
          }
        }
        return send(res, 200, { ...caps, demand });
      }
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
    // Create-or-update a caps row (adding its section if absent) — promotes an unknown/caps_gap
    // target assumption into a curated capability. Optional `bind` binds the originating report's
    // assumption to the new row id (capability_key) + resolves its caps_gap observation, so that
    // report refreshes via the serve-time re-projection with no re-analysis (D4). The one place the
    // panel writes back into a report.json — a deliberate human-curation edit (re-analysis-safe:
    // a fresh run self-binds against the now-present caps row).
    if (req.method === 'POST' && pathname === '/api/harmony-caps/add-row') {
      const body = await readBody(req);
      if (!body.sectionId || !body.id) return send(res, 400, { error: 'sectionId and id required' });
      try {
        const { row, created } = harmonyCaps.upsertRow({
          sectionId: body.sectionId, sectionTitle: body.sectionTitle, id: body.id,
          capability: body.capability, status: body.status, source: body.source, note: body.note });
        let bound = false;
        const bind = body.bind;
        if (bind && bind.name && bind.run && bind.ta_id) {
          const file = path.join(runLibDir(bind.group, bind.name), bind.run, 'report.json');
          if (file.startsWith(RUNS) && fs.existsSync(file)) {
            const rep = JSON.parse(fs.readFileSync(file, 'utf8'));
            const ha = rep && rep.harmony_adaptation;
            const ta = ha && Array.isArray(ha.target_assumptions)
              ? ha.target_assumptions.find((a) => a && a.id === bind.ta_id) : null;
            if (ta) {
              if (!('target_status_model' in ta)) ta.target_status_model = (ta.target_status ?? null);
              ta.capability_key = body.id;
              if (body.status) ta.target_status = body.status;
              const gid = String(body.id).toLowerCase();
              if (rep.meta && Array.isArray(rep.meta.observations) && gid.length >= 2)   // resolve the caps_gap proposal
                rep.meta.observations = rep.meta.observations.filter(
                  (o) => !(o && o.kind === 'caps_gap' && String(o.value || '').toLowerCase().includes(gid)));
              const tmp = file + '.tmp';
              fs.writeFileSync(tmp, JSON.stringify(rep, null, 2) + '\n');
              fs.renameSync(tmp, file);
              bound = true;
            }
          }
        }
        return send(res, 200, { row, created, bound, caps: harmonyCaps.load() });
      } catch (e) { return send(res, 400, { error: String(e.message || e) }); }
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
    reconcilePortingClass, hasUnadaptableSignal, normalizeCodePartition,
    deriveAdaptationAssessment, deriveFunctionalViability, effectivePortingClass,
    validateHarmony, validateReport, computeWarnings, rollupAdaptation, buildDepTopology,
    deriveLicenseCategory, normalizeLicense, validateLicense, normalizeDim8,
    parseRepoUrl, canonicalRepoKey, normalizeCloneUrl };
}
