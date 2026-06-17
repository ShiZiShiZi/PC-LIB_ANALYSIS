#!/usr/bin/env node
/**
 * pc-lib-analysis — control panel backend (Node stdlib only, zero deps).
 *
 * Serves the UI and exposes a small API to: list/clone library repos, launch an
 * opencode analysis of a single library, stream the live opencode I/O over SSE,
 * persist every run's log + report, and read past runs back.
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
const AGENT_FILE = '.claude/agents/pc-lib-analyzer.md';
const PORT = process.env.PORT || 8765;

const DEFAULT_OPENCODE_CMD = 'opencode run';
const DEFAULT_PROMPT =
  'Analyze the PC third-party library checked out at {repoPath}. Follow the ' +
  'method and JSON output contract in {agentFile} and the skills it references. ' +
  'The source is already cloned — do NOT clone again. Run the deterministic ' +
  'code-metrics script, reason through every dimension (function summary, ' +
  'license, dependencies, native/platform API), and write the final report to ' +
  '{reportPath}. Conform to references/report_schema.json. Finish with a short digest.';

for (const d of [REPOS, RUNS]) fs.mkdirSync(d, { recursive: true });

// ---------------------------------------------------------------- job registry
/** @type {Map<string, Job>} */
const jobs = new Map();

class Job {
  constructor(type, meta) {
    this.id = crypto.randomBytes(6).toString('hex');
    this.type = type;                 // 'clone' | 'analyze'
    this.meta = meta;                 // { name, model, argv, runDir, reportPath }
    this.status = 'running';          // running | done | error
    this.exitCode = null;
    this.startedAt = new Date().toISOString();
    this.endedAt = null;
    this.events = [];                 // replay buffer
    this.clients = new Set();         // SSE responses
    jobs.set(this.id, this);
  }
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
    this.status = code === 0 ? 'done' : 'error';
    this.exitCode = code;
    this.endedAt = new Date().toISOString();
    this.emit('end', { code, status: this.status,
      reportAvailable: this.meta.reportPath ? fs.existsSync(this.meta.reportPath) : false });
    if (this.logStream) this.logStream.end();
    this.persistMeta();
    setTimeout(() => { for (const r of this.clients) { try { r.end(); } catch (_) {} } }, 250);
  }
  persistMeta() {
    if (!this.meta.runDir) return;
    const m = { id: this.id, type: this.type, status: this.status,
      exitCode: this.exitCode, startedAt: this.startedAt, endedAt: this.endedAt,
      ...this.meta };
    try { fs.writeFileSync(path.join(this.meta.runDir, 'meta.json'),
      JSON.stringify(m, null, 2)); } catch (_) {}
  }
}

/** Stream a child process line-by-line into a job. */
function pipeProcess(job, child) {
  const wire = (stream, src) => {
    let buf = '';
    src.setEncoding('utf8');
    src.on('data', (chunk) => {
      buf += chunk;
      let idx;
      while ((idx = buf.indexOf('\n')) >= 0) {
        job.log(stream, buf.slice(0, idx));
        buf = buf.slice(idx + 1);
      }
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
function listRuns() {
  const out = [];
  if (!fs.existsSync(RUNS)) return out;
  for (const lib of fs.readdirSync(RUNS)) {
    const libDir = path.join(RUNS, lib);
    if (!fs.statSync(libDir).isDirectory()) continue;
    for (const ts of fs.readdirSync(libDir)) {
      const runDir = path.join(libDir, ts);
      if (!fs.statSync(runDir).isDirectory()) continue;   // skip stray files
      let meta = {};
      try { meta = JSON.parse(fs.readFileSync(path.join(runDir, 'meta.json'), 'utf8')); } catch (_) {}
      out.push({ name: lib, run: ts,
        status: meta.status || 'unknown', model: meta.model,
        startedAt: meta.startedAt || ts,
        reportAvailable: fs.existsSync(path.join(runDir, 'report.json')) });
    }
  }
  return out.sort((a, b) => (a.startedAt < b.startedAt ? 1 : -1));
}

// ---------------------------------------------------------------- actions
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
  const job = new Job('clone', { name, argv: ['git', ...args] });
  job.emit('input', { argv: job.meta.argv });
  // stdin 'ignore' (EOF) — opencode and other tools block on an open stdin pipe.
  pipeProcess(job, spawn('git', args, { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] }));
  return job;
}

function startAnalyze(opts) {
  const name = opts.name;
  if (!name || !fs.existsSync(path.join(REPOS, name)))
    throw new Error(`repo not found: repos/${name} (clone it first)`);
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const runDir = path.join(RUNS, name, ts);
  fs.mkdirSync(runDir, { recursive: true });
  const reportPath = path.join(runDir, 'report.json');

  const prompt = (opts.promptTemplate || DEFAULT_PROMPT)
    .replaceAll('{repoPath}', `repos/${name}`)
    .replaceAll('{agentFile}', AGENT_FILE)
    .replaceAll('{reportPath}', path.relative(ROOT, reportPath))
    .replaceAll('{name}', name);

  const base = (opts.opencodeCmd || DEFAULT_OPENCODE_CMD).trim().split(/\s+/);
  const argv = [...base];
  if (opts.model) argv.push('-m', opts.model);
  if (opts.agent) argv.push('--agent', opts.agent);
  const fmt = opts.format || 'json';            // default: structured streaming events
  if (fmt === 'json') argv.push('--format', 'json');
  if (opts.printLogs) argv.push('--print-logs'); // opt-in: noisy internal INFO logs
  argv.push(prompt);

  const job = new Job('analyze', { name, model: opts.model, runDir, reportPath,
    argv, prompt });
  job.logStream = fs.createWriteStream(path.join(runDir, 'run.log.jsonl'), { flags: 'a' });
  job.emit('input', { argv, prompt, runDir: path.relative(ROOT, runDir) });
  // stdin 'ignore' (EOF): opencode run blocks forever on an open stdin pipe.
  pipeProcess(job, spawn(argv[0], argv.slice(1), { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] }));
  return job;
}

/** Quick liveness probe for a model: tiny prompt, short timeout. */
function testModel(model, cb) {
  if (!model) return cb({ ok: false, error: 'no model specified' });
  const args = ['run', '-m', model, 'reply with exactly the word: pong'];
  const t0 = Date.now();
  const child = spawn('opencode', args, { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
  let out = '', err = '';
  child.stdout.on('data', (d) => (out += d));
  child.stderr.on('data', (d) => (err += d));
  const killer = setTimeout(() => { try { child.kill(); } catch (_) {} }, 30000);
  child.on('error', (e) => { clearTimeout(killer); cb({ ok: false, error: e.message }); });
  child.on('close', (code) => {
    clearTimeout(killer);
    const ms = Date.now() - t0;
    const stdout = out.trim();
    if (code === 0 && stdout) return cb({ ok: true, ms, output: stdout.slice(0, 200) });
    const firstErr = err.split('\n').map((s) => s.trim())
      .find((s) => s && !/service=/.test(s) && !/^\x1b/.test(s)) || `exit ${code}`;
    cb({ ok: false, ms, error: firstErr.replace(/\x1b\[[0-9;]*m/g, '').slice(0, 240) });
  });
}

// ---------------------------------------------------------------- static
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml' };
function serveStatic(req, res, pathname) {
  let file = path.join(PUBLIC, pathname === '/' ? 'index.html' : pathname);
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
    if (req.method === 'GET' && pathname === '/api/state')
      return send(res, 200, { repos: listRepos(), runs: listRuns(),
        defaults: { opencodeCmd: DEFAULT_OPENCODE_CMD, promptTemplate: DEFAULT_PROMPT } });

    if (req.method === 'GET' && pathname === '/api/models')
      return execFile('opencode', ['models'], { timeout: 15000 }, (e, out) =>
        send(res, 200, { models: e ? [] : out.split('\n').map((s) => s.trim()).filter(Boolean) }));

    if (req.method === 'GET' && pathname === '/api/testmodel')
      return testModel(query.model, (r) => send(res, 200, r));

    if (req.method === 'POST' && pathname === '/api/clone') {
      const body = await readBody(req);
      if (!body.url) return send(res, 400, { error: 'url required' });
      const job = startClone(body);
      return send(res, 200, { jobId: job.id, name: job.meta.name });
    }

    if (req.method === 'POST' && pathname === '/api/analyze') {
      const body = await readBody(req);
      const job = startAnalyze(body);
      return send(res, 200, { jobId: job.id, name: job.meta.name,
        runDir: path.relative(ROOT, job.meta.runDir) });
    }

    if (req.method === 'GET' && pathname === '/api/stream') {
      const job = jobs.get(query.job);
      if (!job) return send(res, 404, { error: 'unknown job' });
      res.writeHead(200, { 'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache', Connection: 'keep-alive' });
      res.write('retry: 2000\n\n');
      for (const ev of job.events) res.write(`event: ${ev.event}\ndata: ${JSON.stringify(ev)}\n\n`);
      if (job.status !== 'running') { res.end(); return; }
      job.clients.add(res);
      const hb = setInterval(() => { try { res.write(': ping\n\n'); } catch (_) {} }, 15000);
      req.on('close', () => { clearInterval(hb); job.clients.delete(res); });
      return;
    }

    if (req.method === 'GET' && pathname === '/api/report') {
      const file = path.join(RUNS, query.name || '', query.run || '', 'report.json');
      if (!file.startsWith(RUNS) || !fs.existsSync(file))
        return send(res, 404, { error: 'report not found' });
      return send(res, 200, fs.readFileSync(file, 'utf8'));
    }

    if (req.method === 'GET' && pathname === '/api/runlog') {
      const file = path.join(RUNS, query.name || '', query.run || '', 'run.log.jsonl');
      if (!file.startsWith(RUNS) || !fs.existsSync(file))
        return send(res, 404, { error: 'log not found' });
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
  console.log(`  project root: ${ROOT}`);
});
