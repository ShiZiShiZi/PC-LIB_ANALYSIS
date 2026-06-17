'use strict';
const $ = (id) => document.getElementById(id);
const api = (p, opts) => fetch(p, opts).then((r) => r.json());

let selectedRepo = null;
let currentReport = null;   // { name, run }
let es = null;              // EventSource

// ---------------------------------------------------------------- boot
init();
async function init() {
  bindUI();
  await refreshState();
  loadModels();
}

async function refreshState() {
  try {
    const s = await api('/api/state');
    $('conn').classList.add('ok');
    if (!$('opencodeCmd').value) $('opencodeCmd').value = s.defaults.opencodeCmd;
    if (!$('prompt').value) $('prompt').value = s.defaults.promptTemplate;
    renderRepos(s.repos);
    renderRuns(s.runs);
  } catch (e) { $('conn').classList.remove('ok'); }
}

async function loadModels() {
  try {
    const { models } = await api('/api/models');
    $('modelList').innerHTML = models.map((m) => `<option value="${m}">`).join('');
  } catch (_) {}
}

function bindUI() {
  $('cloneBtn').onclick = doClone;
  $('analyzeBtn').onclick = doAnalyze;
  $('testBtn').onclick = doTestModel;
  $('rawBtn').onclick = () => { $('rawJson').classList.toggle('hidden'); $('report').classList.toggle('hidden'); };
  $('dlBtn').onclick = downloadReport;
}

// ---------------------------------------------------------------- repo list
function renderRepos(repos) {
  const el = $('repoList');
  el.innerHTML = repos.length ? '' : '<div class="hint">尚无克隆的库</div>';
  for (const name of repos) {
    const div = document.createElement('div');
    div.className = 'item' + (name === selectedRepo ? ' sel' : '');
    div.innerHTML = `<span>📦 ${name}</span>`;
    div.onclick = () => selectRepo(name);
    el.appendChild(div);
  }
}
function selectRepo(name) {
  selectedRepo = name;
  $('analyzeBtn').disabled = false;
  $('selInfo').textContent = `将分析：repos/${name}`;
  document.querySelectorAll('#repoList .item').forEach((i) =>
    i.classList.toggle('sel', i.textContent.includes(name)));
}

function renderRuns(runs) {
  const el = $('runList');
  el.innerHTML = runs.length ? '' : '<div class="hint">暂无历史</div>';
  for (const r of runs) {
    const div = document.createElement('div');
    div.className = 'item';
    div.innerHTML = `<span><span class="dot ${r.status}"></span>${r.name}</span>` +
      `<small>${(r.model || '').split('/').pop() || ''} · ${fmtTime(r.startedAt)}</small>`;
    div.onclick = () => loadRun(r);
    el.appendChild(div);
  }
}

// ---------------------------------------------------------------- actions
async function doClone() {
  const url = $('gitUrl').value.trim();
  if (!url) return alert('请输入 Git URL');
  clearConsole();
  setBadge('running', 'cloning');
  const res = await api('/api/clone', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, ref: $('gitRef').value.trim() || undefined, overwrite: $('overwrite').checked }) });
  if (res.error) { sysLine('✖ ' + res.error); setBadge('error', 'error'); return; }
  subscribe(res.jobId, { onEnd: () => refreshState() });
}

async function doTestModel() {
  const model = $('model').value.trim();
  const span = $('testResult');
  if (!model) { span.className = 'hint err'; span.textContent = '请先填模型'; return; }
  span.className = 'hint'; span.textContent = '测试中…';
  try {
    const r = await api('/api/testmodel?model=' + encodeURIComponent(model));
    span.className = 'hint ' + (r.ok ? 'ok' : 'err');
    span.textContent = r.ok ? `✅ 可用 (${r.ms}ms) · ${r.output}` : `❌ ${r.error}`;
  } catch (e) { span.className = 'hint err'; span.textContent = '❌ ' + e.message; }
}

async function doAnalyze() {
  if (!selectedRepo) return;
  clearConsole();
  $('report').innerHTML = '<p class="muted">分析进行中…</p>';
  currentReport = null; $('dlBtn').disabled = $('rawBtn').disabled = true;
  setBadge('running', 'analyzing');
  const res = await api('/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: selectedRepo, model: $('model').value.trim() || undefined,
      agent: $('agent').value.trim() || undefined,
      opencodeCmd: $('opencodeCmd').value, promptTemplate: $('prompt').value,
      printLogs: $('printLogs').checked || undefined,
    }) });
  if (res.error) { sysLine('✖ ' + res.error); setBadge('error', 'error'); return; }
  const run = res.runDir.split('/').pop();
  subscribe(res.jobId, { onEnd: (d) => { refreshState(); if (d.reportAvailable) loadReport(res.name, run); } });
}

// ---------------------------------------------------------------- SSE
function subscribe(jobId, { onEnd } = {}) {
  if (es) es.close();
  es = new EventSource('/api/stream?job=' + jobId);
  es.addEventListener('input', (e) => {
    const d = JSON.parse(e.data).data;
    metaLine('$ ' + (d.argv ? d.argv.join(' ') : ''));
    if (d.prompt) sysLine('prompt → ' + d.prompt);
  });
  es.addEventListener('log', (e) => {
    const { stream, text } = JSON.parse(e.data).data;
    renderLog(text, stream);
  });
  es.addEventListener('end', (e) => {
    const d = JSON.parse(e.data).data;
    setBadge(d.status, `${d.status} (exit ${d.code})`);
    sysLine(`— 进程结束，退出码 ${d.code} —`);
    es.close(); es = null;
    onEnd && onEnd(d);
  });
  es.onerror = () => { sysLine('（连接中断）'); };
}

// ---------------------------------------------------------------- console
function clearConsole() { $('console').innerHTML = ''; }
function appendLine(text, cls) {
  const div = document.createElement('div');
  div.className = 'ln ' + (cls || '');
  div.textContent = text;
  $('console').appendChild(div);
  if ($('autoscroll').checked) $('console').scrollTop = $('console').scrollHeight;
}
const logLine = (t, stream) => appendLine(t, stream === 'stderr' ? 'stderr' : '');
const sysLine = (t) => appendLine(t, 'sys');
const metaLine = (t) => appendLine(t, 'meta');

// Render a raw log line: parse opencode --format json events into readable
// lines; fall back to raw text (git progress, plain output, errors).
function renderLog(text, stream) {
  if (stream === 'stderr') { if (/\bservice=/.test(text)) return; return logLine(text, 'stderr'); }
  const t = (text || '').trim();
  if (t.startsWith('{') && t.endsWith('}')) {
    try { const r = formatEvent(JSON.parse(t)); if (r === null) return; if (r) return appendLine(r.text, r.cls); }
    catch (_) { /* not an event line */ }
  }
  if (t) logLine(text, 'stdout');
}
function formatEvent(ev) {
  const p = ev.part || {};
  switch (ev.type) {
    case 'text': return p.text ? { text: p.text, cls: '' } : null;
    case 'tool_use': {
      const s = p.state || {};
      if (s.status && s.status !== 'completed' && s.status !== 'error') return null; // skip running deltas
      const label = s.title || (s.input ? JSON.stringify(s.input).slice(0, 100) : '');
      return { text: `🔧 ${p.tool}${label ? ' · ' + label : ''}${s.status === 'error' ? ' ✖' : ''}`, cls: 'meta' };
    }
    case 'error': return { text: '✖ ' + (p.message || ev.message || JSON.stringify(ev).slice(0, 200)), cls: 'stderr' };
    case 'step_start': case 'step_finish': return null;
    default: return null;
  }
}
function setBadge(status, label) {
  const b = $('jobBadge');
  b.textContent = label; b.className = 'badge ' + (status || '');
}

// ---------------------------------------------------------------- report
async function loadRun(r) {
  clearConsole();
  setBadge(r.status, r.status);
  // replay persisted log
  try {
    const txt = await fetch(`/api/runlog?name=${r.name}&run=${r.run}`).then((x) => x.text());
    txt.trim().split('\n').forEach((line) => {
      try {
        const ev = JSON.parse(line);
        if (ev.event === 'input') metaLine('$ ' + (ev.data.argv || []).join(' '));
        else if (ev.event === 'log') renderLog(ev.data.text, ev.data.stream);
        else if (ev.event === 'end') sysLine(`— exit ${ev.data.code} —`);
      } catch (_) {}
    });
  } catch (_) {}
  if (r.reportAvailable) loadReport(r.name, r.run);
  else { $('report').innerHTML = '<p class="muted">该次运行无报告。</p>'; }
}

async function loadReport(name, run) {
  try {
    const txt = await fetch(`/api/report?name=${name}&run=${run}`).then((x) => x.text());
    const obj = JSON.parse(txt);
    currentReport = { name, run, obj };
    renderReport(obj);
    $('rawJson').textContent = JSON.stringify(obj, null, 2);
    $('dlBtn').disabled = $('rawBtn').disabled = false;
  } catch (e) { $('report').innerHTML = `<p class="muted">报告解析失败：${e.message}</p>`; }
}

function downloadReport() {
  if (!currentReport) return;
  const blob = new Blob([JSON.stringify(currentReport.obj, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${currentReport.name}.report.json`;
  a.click();
}

function renderReport(r) {
  const el = $('report');
  el.classList.remove('hidden'); $('rawJson').classList.add('hidden');
  const parts = [];
  const sec = (title, inner) => `<div class="rsec"><h3>${title}</h3>${inner}</div>`;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

  // header
  const lib = r.library || {};
  parts.push(sec('概览', `<div class="kv">
    <b>名称</b><span>${esc(lib.name)}</span>
    <b>一句话</b><span>${esc(lib.one_liner || (r.function_summary || {}).summary || '')}</span>
    <b>主语言</b><span>${esc((r.languages || {}).primary)}</span>
    <b>许可证</b><span>${esc((r.license || {}).spdx)} <small>(${esc((r.license || {}).confidence)})</small></span>
    <b>来源</b><span>${esc(lib.source_url)}</span></div>`));

  // function summary
  const fs = r.function_summary || {};
  if (fs.summary || fs.categories) {
    const cats = (fs.categories || []).map((c) =>
      `<div class="cat"><b>${esc(c.name)}</b> — <span>${esc(c.description)}</span></div>`).join('');
    parts.push(sec('功能总结 & 分类', `<p>${esc(fs.summary)}</p>${cats}` +
      (fs.domain ? `<p class="hint">领域：${esc(fs.domain)} · 目标用户：${esc(fs.target_users || '')}</p>` : '')));
  }

  // code metrics
  const cm = r.code_metrics || {};
  if (cm.production) {
    parts.push(sec('代码量', `<div class="metrics-grid">
      <div class="m"><b>${num(cm.production.code)}</b><span>生产代码</span></div>
      <div class="m"><b>${num(cm.test.code)}</b><span>测试代码</span></div>
      <div class="m"><b>${num(cm.example.code)}</b><span>样例代码</span></div></div>
      <p class="hint">总计 ${num((cm.total || {}).code)} 行代码 · 计数工具 ${esc(cm.tool)}</p>`));
  }

  // languages bars
  const langs = (r.languages || {}).breakdown || [];
  if (langs.length) {
    const max = Math.max(...langs.map((l) => l.code), 1);
    parts.push(sec('语言分布', langs.slice(0, 8).map((l) =>
      `<div class="barrow"><span>${esc(l.language)}</span>` +
      `<span><span class="bar" style="width:${Math.max(2, 100 * l.code / max)}%"></span></span>` +
      `<span>${num(l.code)} (${l.pct}%)</span></div>`).join('')));
  }

  // tests
  const t = r.tests || {};
  parts.push(sec('测试', `<div class="kv">
    <b>测试文件</b><span>${num(t.test_files)}</span>
    <b>测试用例</b><span>${num(t.test_cases)}</span>
    <b>框架</b><span>${(t.frameworks || []).map((f) => `<span class="chip">${esc(f)}</span>`).join(' ') || '—'}</span></div>`));

  // dependencies
  const dep = r.dependencies || {};
  if (dep.dependencies || dep.count != null) {
    const items = (dep.dependencies || []).slice(0, 30).map((d) =>
      `<span class="chip" title="${esc(d.purpose || '')}">${esc(d.name)}${d.scope && d.scope !== 'runtime' ? ` ·${esc(d.scope)}` : ''}</span>`).join(' ');
    parts.push(sec(`依赖 (${dep.count != null ? dep.count : (dep.dependencies || []).length})`,
      items || '<span class="muted">无</span>' + (dep.notes ? `<p class="hint">${esc(dep.notes)}</p>` : '')));
  }

  // native api
  const na = r.native_api || {};
  if (na.groups || na.summary) {
    const groups = (na.groups || []).map((g) =>
      `<div class="cat"><b>${esc(g.type)}</b> <span>${(g.symbols || []).slice(0, 10).map(esc).join(', ')}</span></div>`).join('');
    parts.push(sec('底层 / 平台 API', `<p>${esc(na.summary || '')}</p>${groups}` +
      (na.platform_dependence ? `<p class="hint">平台依赖：${esc(na.platform_dependence)}</p>` : '')));
  }

  // warnings
  const warn = (r.meta || {}).warnings || [];
  if (warn.length) parts.push(sec('警告', warn.map((w) => `<div class="cat">⚠ ${esc(w)}</div>`).join('')));

  el.innerHTML = parts.join('');
}

// ---------------------------------------------------------------- util
function num(n) { return (n == null ? 0 : n).toLocaleString(); }
function fmtTime(s) { try { return new Date(s).toLocaleString(); } catch { return s; } }
