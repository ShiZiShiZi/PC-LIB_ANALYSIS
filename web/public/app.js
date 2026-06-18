'use strict';
// ---- tiny helpers ---------------------------------------------------------
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const enc = encodeURIComponent;
const JSONH = { 'Content-Type': 'application/json' };
const api = (p, opts) => fetch(p, opts).then((r) => r.json());
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const num = (n) => (n == null ? 0 : n).toLocaleString();
const fmtTime = (s) => { try { return new Date(s).toLocaleString('zh-CN', { hour12: false }); } catch { return s || ''; } };
const ECO_LABELS = {
  python: 'Python库',
  java: 'Java库',
  nodejs: 'Node.js库',
  cpp: 'C++库',
  rust: 'Rust库',
  go: 'Go库',
  dotnet: '.NET库',
  other: '其他库',
};
const statusZh = (s) => ({ running: '运行中', queued: '排队中', done: '完成', error: '失败', unknown: '未知' }[s] || s);
// dependency acquisition labels (how the build obtains each dep)
const ACQ_LABELS = {
  system: '系统/find_package', vendored: '内嵌源码', fetchcontent: 'FetchContent',
  download_build: '下载源码编译', submodule: 'git 子模块', package_manager: '包管理器',
  prebuilt_binary: '预编译二进制', unknown: '获取方式未知',
};
// locality (本地/远端/系统) derived from acquisition — single source of truth
const ACQ_LOCALITY = {
  vendored: 'local', prebuilt_binary: 'local',
  fetchcontent: 'remote', download_build: 'remote', submodule: 'remote', package_manager: 'remote',
  system: 'system',
};
const LOCALITY_LABELS = { local: '本地', remote: '远端', system: '系统', unknown: '来源未知' };
const LOCALITY_CLS = { local: 'done', remote: 'running', system: 'queued', unknown: 'gray' };

function setHeader(html) { $('#headerActions').innerHTML = html; }
function toast(msg, kind = '') {
  const t = document.createElement('div');
  t.className = 'toast ' + kind; t.textContent = msg;
  $('#toasts').appendChild(t);
  setTimeout(() => t.remove(), 5000);
}
function showModal(html) {
  const root = $('#modalRoot');
  root.innerHTML = `<div class="modal-bg"><div class="modal">${html}</div></div>`;
  $('.modal-bg', root).onclick = (e) => { if (e.target.classList.contains('modal-bg')) closeModal(); };
  $$('[data-close]', root).forEach((b) => (b.onclick = closeModal));
}
function closeModal() { $('#modalRoot').innerHTML = ''; }
async function loadModelsInto(sel) {
  try { const { models } = await api('/api/models'); $(sel).innerHTML = models.map((m) => `<option value="${esc(m)}">`).join(''); } catch (_) {}
}

// ---- router ---------------------------------------------------------------
let view = { cleanup: null };
let es = null;
function navigate() {
  if (view.cleanup) { try { view.cleanup(); } catch (_) {} view.cleanup = null; }
  if (es) { es.close(); es = null; }
  const hash = location.hash.slice(1) || '/';
  if (hash.startsWith('/lib/')) renderDetail(decodeURIComponent(hash.slice(5)));
  else renderDashboard();
}
window.addEventListener('hashchange', navigate);
navigate();

// ===========================================================================
//  DASHBOARD (level 1)
// ===========================================================================
let libsCache = [];
const selected = new Set();
let page = 1;
const PAGE_SIZE = 15;

async function renderDashboard() {
  setHeader('<button class="btn" id="hSettings">⚙ 系统设置</button>' +
            '<button class="btn primary" id="hClone">＋ 克隆库</button>');
  $('#hSettings').onclick = openSettings;
  $('#hClone').onclick = openCloneModal;

  $('#app').innerHTML = `
    <div class="toolbar">
      <div class="search"><input id="search" type="text" placeholder="搜索库名 / 描述…" /></div>
      <div class="filter">
        <select id="ecoFilter">
          <option value="">全部生态</option>
          ${Object.entries(ECO_LABELS).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('')}
        </select>
      </div>
      <button class="btn sm primary" id="batchAnalyze" disabled>分析选中</button>
      <button class="btn sm" id="refreshBtn">刷新</button>
    </div>
    <div id="jobsStrip" class="jobs-strip"></div>
    <div id="list"></div>
    <div id="pager" class="pager"></div>`;

  $('#refreshBtn').onclick = loadDash;
  $('#search').oninput = () => { page = 1; renderList(); };
  $('#ecoFilter').onchange = () => { page = 1; renderList(); };
  $('#batchAnalyze').onclick = batchAnalyze;

  await loadDash();
  const timer = setInterval(loadDash, 3000);
  view.cleanup = () => clearInterval(timer);
}

async function loadDash() {
  try {
    const [{ libraries }, { jobs }] = await Promise.all([api('/api/libraries'), api('/api/jobs')]);
    libsCache = libraries;
    renderJobsStrip(jobs);
    renderList();
  } catch (_) {}
}

function visibleLibs() {
  const q = ($('#search') ? $('#search').value : '').trim().toLowerCase();
  const eco = ($('#ecoFilter') ? $('#ecoFilter').value : '');
  return libsCache.filter((l) => {
    const matchesSearch = !q || l.name.toLowerCase().includes(q) ||
      ((l.summary && l.summary.oneLiner) || '').toLowerCase().includes(q);
    const matchesEco = !eco || (l.summary && l.summary.ecosystem === eco);
    return matchesSearch && matchesEco;
  });
}

function libStatus(lib) {
  if (lib.active) return lib.active.type === 'clone'
    ? { cls: 'running', label: '克隆中' }
    : { cls: lib.active.status, label: lib.active.status === 'queued' ? '排队中' : '分析中' };
  if (!lib.cloned) return { cls: 'gray', label: '未克隆' };
  if (lib.latest) return { cls: lib.latest.status, label: lib.latest.status === 'done' ? '已分析' : (lib.latest.status === 'error' ? '失败' : '未知') };
  return { cls: 'gray', label: '未分析' };
}

function renderList() {
  const box = $('#list'); if (!box) return;
  const libs = visibleLibs();
  if (!libs.length) {
    box.innerHTML = '<div class="empty">还没有库。点击右上角「＋ 克隆库」开始。</div>';
    $('#pager').innerHTML = ''; updateBatchBtn(); return;
  }
  const pages = Math.max(1, Math.ceil(libs.length / PAGE_SIZE));
  page = Math.min(page, pages);
  const slice = libs.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const visCloned = libs.filter((l) => l.cloned).map((l) => l.name);
  const allSel = visCloned.length && visCloned.every((n) => selected.has(n));

  box.innerHTML = `<table class="libtable">
    <thead><tr>
      <th class="c-chk"><input type="checkbox" id="selAll" ${allSel ? 'checked' : ''} title="全选/取消" /></th>
      <th>名称</th><th class="c-st">状态</th><th>生态</th><th>语言</th>
      <th class="c-num">生产代码</th><th class="c-num">测试</th><th>协议</th><th class="c-act">操作</th>
    </tr></thead><tbody>${slice.map((lib) => {
      const st = libStatus(lib); const s = lib.summary || {};
      return `<tr data-name="${esc(lib.name)}">
        <td class="c-chk"><input type="checkbox" data-sel="${esc(lib.name)}" ${selected.has(lib.name) ? 'checked' : ''} ${lib.cloned ? '' : 'disabled'} /></td>
        <td><a class="lname" href="#/lib/${enc(lib.name)}">${esc(lib.name)}</a>
            <div class="lsub">${esc(s.oneLiner || (lib.cloned ? '尚未分析' : '尚未克隆'))}</div></td>
        <td class="c-st"><span class="badge ${st.cls}">${st.label}</span></td>
        <td>${s.ecosystem ? `<span class="chip eco-chip">${esc(ECO_LABELS[s.ecosystem] || s.ecosystem)}</span>` : '—'}</td>
        <td>${s.primary ? `<span class="chip lang-chip">${esc(s.primary)}</span>` : '—'}</td>
        <td class="c-num">${s.prodCode != null ? num(s.prodCode) : '—'}</td>
        <td class="c-num">${s.testCases != null ? num(s.testCases) : '—'}</td>
        <td>${esc(s.license || '—')}</td>
        <td class="c-act">
          <a class="btn sm ghost" href="#/lib/${enc(lib.name)}">详情</a>
          <button class="btn sm primary" data-act="analyze" data-name="${esc(lib.name)}" ${lib.active || !lib.cloned ? 'disabled' : ''}>分析</button>
        </td></tr>`;
    }).join('')}</tbody></table>`;

  $('#selAll').onchange = () => {
    visCloned.forEach((n) => (allSel ? selected.delete(n) : selected.add(n)));
    renderList();
  };
  $$('[data-sel]', box).forEach((cb) => cb.onchange = () => {
    cb.checked ? selected.add(cb.dataset.sel) : selected.delete(cb.dataset.sel);
    updateBatchBtn();
  });
  $$('[data-act="analyze"]', box).forEach((b) => b.onclick = () => analyzeOne(b.dataset.name));

  $('#pager').innerHTML = `
    <button class="btn sm" id="pPrev" ${page <= 1 ? 'disabled' : ''}>‹ 上一页</button>
    <span class="pinfo">第 ${page} / ${pages} 页 · 共 ${libs.length} 个库</span>
    <button class="btn sm" id="pNext" ${page >= pages ? 'disabled' : ''}>下一页 ›</button>`;
  $('#pPrev').onclick = () => { if (page > 1) { page--; renderList(); } };
  $('#pNext').onclick = () => { if (page < pages) { page++; renderList(); } };
  updateBatchBtn();
}

function updateBatchBtn() {
  const b = $('#batchAnalyze'); if (!b) return;
  const n = selected.size;
  b.disabled = n === 0;
  b.textContent = n ? `分析选中 (${n})` : '分析选中';
}

function renderJobsStrip(jobs) {
  const strip = $('#jobsStrip'); if (!strip) return;
  const active = jobs.filter((j) => j.status === 'running' || j.status === 'queued');
  if (!active.length) { strip.innerHTML = ''; return; }
  strip.innerHTML = `<div class="card"><div class="section-title">进行中的任务 (${active.length})</div>` +
    active.map((j) => `<div class="jobline">
      <span class="spin"></span>
      <span class="jname">${esc(j.name)}</span>
      <span class="badge ${j.status}">${j.type === 'clone' ? '克隆' : '分析'} · ${statusZh(j.status)}</span>
      <span class="spacer"></span>
      <a href="#/lib/${enc(j.name)}">查看 →</a></div>`).join('') + '</div>';
}

async function analyzeOne(name) {
  const r = await api('/api/analyze', { method: 'POST', headers: JSONH, body: JSON.stringify({ name }) });
  if (r.jobs && r.jobs[0] && r.jobs[0].jobId) location.hash = '#/lib/' + enc(name);
  else toast((r.jobs && r.jobs[0] && r.jobs[0].error) || '启动失败', 'err');
}

async function batchAnalyze() {
  const names = [...selected];
  if (!names.length) return;
  const r = await api('/api/analyze', { method: 'POST', headers: JSONH, body: JSON.stringify({ names }) });
  const ok = (r.jobs || []).filter((j) => j.jobId);
  const err = (r.jobs || []).filter((j) => j.error);
  toast(`已提交 ${ok.length} 个分析任务` + (err.length ? `，${err.length} 个失败` : ''), err.length ? 'err' : 'ok');
  selected.clear();
  loadDash();
}

// ---- clone modal ----------------------------------------------------------
function openCloneModal() {
  showModal(`<h2>克隆库</h2>
    <label>Git 仓库地址（每行一个，支持批量并发克隆）
      <textarea id="mUrls" rows="5" placeholder="https://github.com/owner/lib.git
https://github.com/owner/lib2.git"></textarea></label>
    <div class="row">
      <label class="grow">分支 / Tag（可选，应用于全部）<input id="mRef" type="text" placeholder="main / v1.2.0" /></label>
      <label style="white-space:nowrap"><input id="mOver" type="checkbox" /> 覆盖已存在</label>
    </div>
    <div class="actions"><button class="btn" data-close>取消</button>
      <button class="btn primary" id="mGo">开始克隆</button></div>`);
  $('#mGo').onclick = async () => {
    const urls = $('#mUrls').value.split('\n').map((s) => s.trim()).filter(Boolean);
    if (!urls.length) return toast('请输入至少一个 Git URL', 'err');
    const r = await api('/api/clone', { method: 'POST', headers: JSONH, body: JSON.stringify({
      urls, ref: $('#mRef').value.trim() || undefined, overwrite: $('#mOver').checked }) });
    closeModal();
    const ok = (r.jobs || []).filter((j) => j.jobId);
    const err = (r.jobs || []).filter((j) => j.error);
    toast(`已开始克隆 ${ok.length} 个库` + (err.length ? `，${err.length} 个失败` : ''), err.length ? 'err' : 'ok');
    err.forEach((e) => toast(`${e.url}：${e.error}`, 'err'));
    loadDash();
  };
}

// ---- settings modal -------------------------------------------------------
async function openSettings() {
  const { settings: s, codegraphAvailable: cg } = await api('/api/settings');
  showModal(`<h2>系统设置</h2>
    <label>默认模型 Model
      <div class="row"><input id="sModel" class="grow" type="text" list="modelList" value="${esc(s.model)}" placeholder="provider/model（留空用 opencode 默认）" />
        <datalist id="modelList"></datalist>
        <button class="btn sm" id="sTest">Test</button></div>
      <div id="sTestR" class="hint"></div></label>
    <label>opencode 命令 <input id="sCmd" type="text" value="${esc(s.opencodeCmd)}" /></label>
    <label>最大并发分析数 <input id="sConc" type="number" min="1" max="10" value="${s.maxConcurrent}" /></label>
    <label><input id="sLogs" type="checkbox" ${s.printLogs ? 'checked' : ''} /> 记录 opencode 调试日志（--print-logs）</label>
    <label><input id="sCodegraph" type="checkbox" ${s.useCodegraph ? 'checked' : ''} ${cg ? '' : 'disabled'} /> 启用 codegraph 结构化分析${cg ? '' : '<span class="hint err" style="display:inline"> — 未检测到 codegraph，将回退 grep</span>'}</label>
    <details><summary class="hint" style="cursor:pointer">Prompt 模板（高级）</summary>
      <textarea id="sPrompt" rows="9">${esc(s.promptTemplate)}</textarea>
      <p class="hint">占位符：{repoPath} {agentFile} {reportPath} {metricsPath} {name}</p></details>
    <div class="actions"><button class="btn" data-close>取消</button>
      <button class="btn primary" id="sSave">保存</button></div>`);
  loadModelsInto('#modelList');
  $('#sTest').onclick = async () => {
    const span = $('#sTestR'); span.className = 'hint'; span.textContent = '测试中…';
    const r = await api('/api/testmodel?model=' + enc($('#sModel').value.trim()));
    span.className = 'hint ' + (r.ok ? 'ok' : 'err');
    span.textContent = r.ok ? `✅ 可用 (${r.ms}ms) · ${r.output}` : `❌ ${r.error}`;
  };
  $('#sSave').onclick = async () => {
    await api('/api/settings', { method: 'POST', headers: JSONH, body: JSON.stringify({
      model: $('#sModel').value.trim(), opencodeCmd: $('#sCmd').value.trim(),
      maxConcurrent: Number($('#sConc').value) || 3, printLogs: $('#sLogs').checked,
      useCodegraph: $('#sCodegraph').checked, promptTemplate: $('#sPrompt').value }) });
    closeModal(); toast('设置已保存', 'ok');
  };
}

// ===========================================================================
//  DETAIL (level 2)
// ===========================================================================
let curReport = null;     // {name, run, obj}
let curRun = null;

async function renderDetail(name) {
  setHeader('<a class="btn ghost" href="#/">← 返回库列表</a>');
  $('#app').innerHTML = `
    <div class="detail-head">
      <h1>${esc(name)}</h1>
      <span id="dStatus"></span>
      <span class="spacer"></span>
      <button class="btn sm" id="dTest">Test 模型</button>
      <button class="btn primary sm" id="dAnalyze">重新分析</button>
    </div>
    <div class="cols">
      <div class="stack">
        <div class="card"><div class="section-title">运行历史</div><div id="runs"></div></div>
      </div>
      <div class="stack">
        <div class="card"><div class="section-title">实时 / 运行日志</div><div id="console" class="console"></div></div>
        <div class="card">
          <div class="row" style="justify-content:space-between;margin-bottom:10px">
            <div class="section-title" style="margin:0">分析报告</div>
            <div class="row" style="gap:6px">
              <button class="btn sm ghost" id="rawBtn" disabled>原始 JSON</button>
              <button class="btn sm ghost" id="dlBtn" disabled>下载</button></div>
          </div>
          <div id="report"><p class="muted">选择一次运行以查看报告。</p></div>
          <pre id="rawJson" class="raw hidden"></pre>
        </div>
      </div>
    </div>`;

  $('#dTest').onclick = async () => {
    toast('正在测试默认模型…');
    const r = await api('/api/testmodel?model=');
    toast(r.ok ? `模型可用 (${r.ms}ms)` : `模型不可用：${r.error}`, r.ok ? 'ok' : 'err');
  };
  $('#dAnalyze').onclick = () => reAnalyze(name);
  $('#rawBtn').onclick = () => { $('#rawJson').classList.toggle('hidden'); $('#report').classList.toggle('hidden'); };
  $('#dlBtn').onclick = downloadReport;

  await loadDetail(name);
}

function setDStatus(status) {
  const el = $('#dStatus'); if (el) el.innerHTML = status ? `<span class="badge ${status}">${statusZh(status)}</span>` : '';
}

async function loadDetail(name) {
  const d = await api('/api/library?name=' + enc(name));
  if (d.error) { $('#runs').innerHTML = `<div class="hint err">${esc(d.error)}</div>`; return; }
  renderRuns(name, d.runs, d.active);
  if (d.active) {
    setDStatus(d.active.status);
    subscribe(d.active.id, name, () => loadDetail(name));   // live, reload on end
  } else {
    const latest = d.runs[0];
    setDStatus(latest ? latest.status : '');
    if (latest) loadRun(name, latest.run);
  }
}

function renderRuns(name, runs, active) {
  const box = $('#runs');
  if (!runs.length && !active) { box.innerHTML = '<div class="hint">暂无运行记录，点击「重新分析」。</div>'; return; }
  box.innerHTML = runs.map((r) => `<div class="runrow ${r.run === curRun ? 'sel' : ''}" data-run="${esc(r.run)}">
      <span class="badge ${r.status}">${statusZh(r.status)}</span>
      <span class="ts">${fmtTime(r.startedAt)}</span>
      ${r.reportAvailable ? '<span title="有报告">📄</span>' : ''}</div>`).join('');
  $$('.runrow', box).forEach((row) => row.onclick = () => {
    curRun = row.dataset.run;
    $$('.runrow', box).forEach((x) => x.classList.toggle('sel', x === row));
    loadRun(name, row.dataset.run);
  });
}

async function reAnalyze(name) {
  const r = await api('/api/analyze', { method: 'POST', headers: JSONH, body: JSON.stringify({ name }) });
  const job = r.jobs && r.jobs[0];
  if (!job || !job.jobId) return toast((job && job.error) || '启动失败', 'err');
  toast('已开始分析', 'ok');
  setDStatus(job.status);
  subscribe(job.jobId, name, () => loadDetail(name));
  loadDetail(name);   // refresh run list to include the new run
}

// ---- SSE ------------------------------------------------------------------
function subscribe(jobId, name, onEnd) {
  if (es) es.close();
  clearConsole();
  es = new EventSource('/api/stream?job=' + jobId);
  es.addEventListener('input', (e) => { const d = JSON.parse(e.data).data; metaLine('$ ' + (d.argv ? d.argv.join(' ') : '')); });
  es.addEventListener('status', (e) => { const d = JSON.parse(e.data).data; setDStatus(d.status); sysLine('状态：' + statusZh(d.status)); });
  es.addEventListener('log', (e) => { const { stream, text } = JSON.parse(e.data).data; renderLog(text, stream); });
  es.addEventListener('end', (e) => {
    const d = JSON.parse(e.data).data;
    sysLine(`— 进程结束，退出码 ${d.code}（${statusZh(d.status)}）—`);
    setDStatus(d.status);
    if (es) { es.close(); es = null; }
    if (onEnd) onEnd(d);
  });
  es.onerror = () => {};
  view.cleanup = () => { if (es) { es.close(); es = null; } };
}

// ---- console --------------------------------------------------------------
function clearConsole() { const c = $('#console'); if (c) c.innerHTML = ''; }
function appendLine(text, cls) {
  const c = $('#console'); if (!c) return;
  const div = document.createElement('div');
  div.className = 'ln ' + (cls || ''); div.textContent = text;
  c.appendChild(div); c.scrollTop = c.scrollHeight;
}
const logLine = (t, s) => appendLine(t, s === 'stderr' ? 'stderr' : '');
const sysLine = (t) => appendLine(t, 'sys');
const metaLine = (t) => appendLine(t, 'meta');

function renderLog(text, stream) {
  if (stream === 'stderr') { if (/\bservice=/.test(text)) return; return logLine(text, 'stderr'); }
  const t = (text || '').trim();
  if (t.startsWith('{') && t.endsWith('}')) {
    try { const r = formatEvent(JSON.parse(t)); if (r === null) return; if (r) return appendLine(r.text, r.cls); }
    catch (_) {}
  }
  if (t) logLine(text, 'stdout');
}
function formatEvent(ev) {
  const p = ev.part || {};
  switch (ev.type) {
    case 'reasoning': return p.text ? { text: '💭 ' + p.text, cls: 'think' } : null;
    case 'text': return p.text ? { text: p.text, cls: '' } : null;
    case 'tool_use': {
      const s = p.state || {};
      if (s.status && s.status !== 'completed' && s.status !== 'error') return null;
      const label = s.title || (s.input ? JSON.stringify(s.input).slice(0, 100) : '');
      return { text: `🔧 ${p.tool}${label ? ' · ' + label : ''}${s.status === 'error' ? ' ✖' : ''}`, cls: 'tool' };
    }
    case 'error': return { text: '✖ ' + (p.message || ev.message || JSON.stringify(ev).slice(0, 200)), cls: 'stderr' };
    default: return null;
  }
}

// ---- report ---------------------------------------------------------------
async function loadRun(name, run) {
  curRun = run;
  try {
    const txt = await fetch(`/api/report?name=${enc(name)}&run=${enc(run)}`).then((x) => x.text());
    const obj = JSON.parse(txt);
    curReport = { name, run, obj };
    renderReport(obj);
    $('#rawJson').textContent = JSON.stringify(obj, null, 2);
    $('#rawBtn').disabled = $('#dlBtn').disabled = false;
  } catch (_) {
    $('#report').innerHTML = '<p class="muted">本次运行没有报告（可能未完成或失败）。</p>';
    $('#rawBtn').disabled = $('#dlBtn').disabled = true;
  }
  // also replay this run's persisted log if not currently streaming live
  if (!es) {
    try {
      const log = await fetch(`/api/runlog?name=${enc(name)}&run=${enc(run)}`).then((x) => x.text());
      clearConsole();
      log.trim().split('\n').forEach((line) => {
        try { const ev = JSON.parse(line);
          if (ev.event === 'input') metaLine('$ ' + (ev.data.argv || []).join(' '));
          else if (ev.event === 'log') renderLog(ev.data.text, ev.data.stream);
          else if (ev.event === 'end') sysLine(`— 退出码 ${ev.data.code} —`);
        } catch (_) {}
      });
    } catch (_) {}
  }
}

function downloadReport() {
  if (!curReport) return;
  const blob = new Blob([JSON.stringify(curReport.obj, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = `${curReport.name}.report.json`; a.click();
}

function renderReport(r) {
  const el = $('#report'); el.classList.remove('hidden'); $('#rawJson').classList.add('hidden');
  const sec = (title, inner) => `<div class="rsec"><h3>${title}</h3>${inner}</div>`;
  const parts = [];
  const lib = r.library || {}, fs = r.function_summary || {}, cm = r.code_metrics || {},
    t = r.tests || {}, lic = r.license || {}, dep = r.dependencies || {}, na = r.native_api || {};

  parts.push(sec('概览', `<div class="kv">
    <b>名称</b><span>${esc(lib.name)}</span>
    <b>一句话</b><span>${esc(lib.one_liner || fs.summary || '')}</span>
    <b>生态</b><span>${lib.ecosystem ? esc(ECO_LABELS[lib.ecosystem] || lib.ecosystem) : '—'}</span>
    <b>主语言</b><span>${esc((r.languages || {}).primary || '—')}</span>
    <b>许可证</b><span>${esc(lic.spdx || '—')} <span class="muted">(${esc(lic.confidence || '')})</span></span>
    <b>来源</b><span>${esc(lib.source_url || '')}</span></div>`));

  if (fs.summary || (fs.categories || []).length) {
    const cats = (fs.categories || []).map((c) => `<div class="cat"><b>${esc(c.name)}</b> — <span>${esc(c.description)}</span></div>`).join('');
    parts.push(sec('功能总结 & 分类', `<p>${esc(fs.summary)}</p>${cats}` +
      (fs.domain ? `<p class="hint">领域：${esc(fs.domain)}　目标用户：${esc(fs.target_users || '')}</p>` : '')));
  }

  if (cm.production) {
    const mcell = (agg, label) => `<div class="m"><b>${num((agg || {}).code)}</b><span>${label}</span>
      <em class="m-total">共 ${num((agg || {}).total_lines)} 行</em></div>`;
    parts.push(sec('代码量', `<div class="metrics-grid">
      ${mcell(cm.production, '生产代码')}${mcell(cm.test, '测试代码')}
      ${mcell(cm.example, '样例代码')}${mcell(cm.total, '总计')}</div>
      <p class="hint">「代码行」为净代码（不含注释/空行）；「共 N 行」为总物理行。计数工具：${esc(cm.tool || '')}</p>`));
  }

  const langs = (r.languages || {}).breakdown || [];
  if (langs.length) {
    const max = Math.max(...langs.map((l) => l.code), 1);
    parts.push(sec('语言分布', langs.slice(0, 8).map((l) =>
      `<div class="barrow"><span>${esc(l.language)}</span><span><span class="bar" style="width:${Math.max(3, 100 * l.code / max)}%"></span></span><span>${num(l.code)} (${l.pct}%)</span></div>`).join('')));
  }

  parts.push(sec('测试', `<div class="kv">
    <b>测试文件</b><span>${num(t.test_files)}</span>
    <b>测试用例</b><span>${num(t.test_cases)}</span>
    <b>框架</b><span>${(t.frameworks || []).map((f) => `<span class="chip">${esc(f)}</span>`).join('') || '—'}</span></div>`));

  const hasDeps = dep.count != null || (dep.dependencies || []).length;
  if (hasDeps) {
    const items = (dep.dependencies || []).slice(0, 40).map((d) =>
      `<span class="chip" title="${esc(d.purpose || '')}">${esc(d.name)}${d.scope && d.scope !== 'runtime' ? ` ·${esc(d.scope)}` : ''}</span>`).join('');
    parts.push(sec(`依赖 (${dep.count != null ? dep.count : (dep.dependencies || []).length})`,
      (items || '<span class="muted">无</span>') + (dep.notes ? `<p class="hint">${esc(dep.notes)}</p>` : '') +
      `<div class="subtitle">依赖关系（面板内连接，离线）</div>
       <div class="deptree" id="depTree"><p class="muted">加载依赖关系…</p></div>`));
  }

  if ((na.groups || []).length || na.summary || (na.dynamic_libraries || []).length) {
    const groups = (na.groups || []).map((g) => {
      const syms = (g.symbols || []).map(esc).join(', ');
      return `<div class="cat"><b>${esc(g.type)}</b> <span class="syms">${syms || '<i class="muted">—</i>'}</span></div>`;
    }).join('');
    const dyn = (na.dynamic_libraries || []).map((d) =>
      `<div class="dynlib"><span class="chip lang-chip">${esc(d.name)}</span>` +
      (d.mechanism ? `<span class="tag">${esc(d.mechanism)}</span>` : '') +
      (d.optional ? `<span class="tag opt">可选</span>` : '') +
      `<span class="dynlib-desc" title="${esc((d.evidence || []).join(', '))}">${esc(d.description || '')}</span></div>`).join('');
    parts.push(sec('底层 / 平台 API', `<p>${esc(na.summary || '')}</p>${groups}` +
      (dyn ? `<div class="subtitle">动态加载库</div>${dyn}` : '') +
      (na.platform_dependence ? `<p class="hint">平台依赖：${esc(na.platform_dependence)}</p>` : '')));
  }

  const warn = (r.meta || {}).warnings || [];
  if (warn.length) parts.push(sec('警告', warn.map((w) => `<div class="cat">⚠ ${esc(w)}</div>`).join('')));

  el.innerHTML = parts.join('');
  if (hasDeps) loadDepTree(curReport && curReport.name);
}

// ---- dependency tree (offline, /api/depgraph) -----------------------------
async function loadDepTree(name) {
  const box = $('#depTree'); if (!box || !name) return;
  try {
    const { tree } = await api('/api/depgraph?name=' + enc(name));
    box.innerHTML = (tree && tree.length) ? depGroupsHtml(tree) : '<p class="muted">无可连接的依赖关系。</p>';
  } catch { box.innerHTML = '<p class="muted">依赖关系不可用。</p>'; }
}
// Top level: group direct dependencies by ecosystem; each group is collapsible.
function depGroupsHtml(nodes) {
  const groups = {};
  nodes.forEach((n) => { const k = n.ecosystem || 'other'; (groups[k] = groups[k] || []).push(n); });
  return Object.entries(groups).map(([eco, ns]) =>
    `<details class="depgroup" open><summary>${esc(ECO_LABELS[eco] || eco)} <span class="muted">(${ns.length})</span></summary>${depTreeHtml(ns)}</details>`).join('') ||
    depTreeHtml(nodes);
}
function depNodeLabel(n) {
  const eco = n.ecosystem ? `<span class="chip eco-chip">${esc(ECO_LABELS[n.ecosystem] || n.ecosystem)}</span>` : '';
  const ver = n.version ? `<span class="muted">${esc(n.version)}</span>` : '';
  const scope = n.scope && n.scope !== 'runtime' ? `<span class="tag">${esc(n.scope)}</span>` : '';
  const loc = n.acquisition ? (ACQ_LOCALITY[n.acquisition] || 'unknown') : null;
  const locBadge = loc ? `<span class="badge ${LOCALITY_CLS[loc]}" title="${esc(ACQ_LABELS[n.acquisition] || n.acquisition)}">${LOCALITY_LABELS[loc]}</span>` : '';
  const acq = n.acquisition ? `<span class="tag acq" title="${esc(n.source || '')}">${esc(ACQ_LABELS[n.acquisition] || n.acquisition)}</span>` : '';
  let tail;
  if (n.analyzed) tail = `<a class="btn sm ghost" href="#/lib/${enc(n.libName)}">跳转 →</a>`;
  else if (n.ambiguous) tail = `<span class="badge gray" title="面板内有多个同名同生态库，未自动连接">歧义</span>`;
  else tail = `<span class="badge gray">未分析</span>`;
  return `<span class="dep-name" title="${esc(n.purpose || '')}">${esc(n.name)}</span> ${ver} ${eco} ${locBadge} ${acq} ${scope} ${tail}`;
}
function depMetaHtml(n) {
  const bits = [];
  if (n.source) bits.push(`来源：${esc(n.source)}`);
  if (n.declared_in && n.declared_in.length) bits.push(`声明于：${n.declared_in.map(esc).join('、')}`);
  return bits.length ? `<div class="dep-meta">${bits.join(' · ')}</div>` : '';
}
function depTreeHtml(nodes) {
  return '<ul class="tree">' + nodes.map((n) => (n.children && n.children.length)
    ? `<li><details><summary>${depNodeLabel(n)}</summary>${depMetaHtml(n)}${depTreeHtml(n.children)}</details></li>`
    : `<li class="leaf">${depNodeLabel(n)}${depMetaHtml(n)}</li>`).join('') + '</ul>';
}
