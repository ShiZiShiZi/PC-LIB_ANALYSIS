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
const path = require('path');
const url = require('url');
const crypto = require('crypto');
const { spawn, execFile } = require('child_process');

const ROOT = path.resolve(__dirname, '..');         // project root (holds .claude/)
const PUBLIC = path.join(__dirname, 'public');
const REPOS = path.join(ROOT, 'repos');
const RUNS = path.join(ROOT, 'runs');
const SETTINGS_FILE = path.join(ROOT, '.panel-settings.json');
const AGENT_FILE = '.claude/agents/pc-lib-analyzer.md';
const PORT = process.env.PORT || 8765;

const DEFAULT_PROMPT =
  'Analyze the PC third-party library checked out at {repoPath}. Follow the ' +
  'method and JSON output contract in {agentFile} and the skills it references. ' +
  'The source is already cloned — do NOT clone again. Run the deterministic ' +
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
};

for (const d of [REPOS, RUNS]) fs.mkdirSync(d, { recursive: true });

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
    this.emit('end', { code, status: this.status, reportAvailable });
    if (this.logStream) this.logStream.end();
    this.persistMeta();
    if (this.onDone) this.onDone();
    setTimeout(() => { for (const r of this.clients) { try { r.end(); } catch (_) {} } }, 250);
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
    out.push({ name, run: ts, status: meta.status || 'unknown', model: meta.model,
      startedAt: meta.startedAt || ts, endedAt: meta.endedAt,
      reportAvailable: fs.existsSync(path.join(runDir, 'report.json')) });
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
      prodCode: r.code_metrics && r.code_metrics.production && r.code_metrics.production.code,
      testCases: r.tests && r.tests.test_cases,
      license: r.license && r.license.spdx,
      analyzedAt: r.library && r.library.analyzed_at,
    };
  } catch { return null; }
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
    return {
      name, cloned: repos.has(name), runCount: runs.length,
      latest, active: activeJobFor(name),
      summary: latest && latest.reportAvailable ? reportSummary(name, latest.run) : null,
    };
  });
}

// ---------------------------------------------------------------- clone
function startClone({ url: gitUrl, ref, overwrite }) {
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
  pipeProcess(job, spawn('git', args, { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] }));
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

  const prompt = (opts.promptTemplate || settings.promptTemplate || DEFAULT_PROMPT)
    .replaceAll('{repoPath}', `repos/${name}`)
    .replaceAll('{agentFile}', AGENT_FILE)
    .replaceAll('{reportPath}', path.relative(ROOT, reportPath))
    .replaceAll('{metricsPath}', path.relative(ROOT, path.join(runDir, 'metrics.json')))
    .replaceAll('{name}', name);

  const base = (opts.opencodeCmd || settings.opencodeCmd).trim().split(/\s+/);
  const model = opts.model || settings.model;
  const argv = [...base];
  if (model) argv.push('-m', model);
  if (opts.agent) argv.push('--agent', opts.agent);
  argv.push('--format', 'json');
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
      return send(res, 200, { settings, defaults: DEFAULT_SETTINGS });
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

    if (req.method === 'GET' && pathname === '/api/report') {
      const file = path.join(RUNS, query.name || '', query.run || '', 'report.json');
      if (!file.startsWith(RUNS) || !fs.existsSync(file)) return send(res, 404, { error: 'report not found' });
      return send(res, 200, fs.readFileSync(file, 'utf8'));
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
