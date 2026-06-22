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
  // dynamic-lib provenance
  self_build: '本仓构建产物', bundled: '仓内自带', third_party: '第三方',
};
// locality (本地/远端/系统) derived from acquisition — single source of truth
const ACQ_LOCALITY = {
  vendored: 'local', prebuilt_binary: 'local',
  fetchcontent: 'remote', download_build: 'remote', submodule: 'remote', package_manager: 'remote',
  system: 'system',
};
const LOCALITY_LABELS = { local: '本地', remote: '远端', system: '系统', runtime: '运行时加载', unknown: '来源未知' };
const LOCALITY_CLS = { local: 'done', remote: 'running', system: 'queued', runtime: 'error', unknown: 'gray' };
// short language names for binding chips (avoid the verbose "库" suffix)
const BIND_LABELS = { python: 'Python', java: 'Java', nodejs: 'Node', cpp: 'C++', dotnet: 'C#/.NET', rust: 'Rust', go: 'Go', other: '其他' };
const bindingChips = (bindings, primary) => (bindings || [])
  .filter((b) => b && b !== primary)
  .map((b) => `<span class="chip bind-chip">+${esc(BIND_LABELS[b] || b)}</span>`).join('');
// native_api group category — by portability
const CAT_LABELS = { standard: '标准', platform: '平台特有', system: '系统内核', ffi: 'FFI', hardware: '硬件' };
const CAT_CLS = { standard: 'done', platform: 'running', system: 'error', ffi: 'queued', hardware: 'gray' };
const CAT_ORDER = ['standard', 'platform', 'system', 'hardware', 'ffi'];
const CAT_LEGEND = {
  standard: '语言标准库/运行时，跨平台', platform: '某 OS 专有(Win32 / POSIX-only 等)',
  system: '内核/系统调用层(syscall/ioctl//proc/注册表)', hardware: 'GPU/SIMD/加速器', ffi: '互操作桥(ctypes/JNI/N-API)',
};
const PLAT_LABELS = { windows: 'Windows', posix: 'POSIX', linux: 'Linux', macos: 'macOS', portable: '跨平台', unknown: '' };
// harmony_adaptation (dim 9) — closed axes
const FEAS_LABELS = { feasible: '可行', feasible_with_effort: '可行（需投入）', hard: '困难', infeasible: '不可行' };
const FEAS_CLS = { feasible: 'done', feasible_with_effort: 'running', hard: 'sev-major', infeasible: 'error' };
const DIFF_LABELS = { low: '低', medium: '中', high: '高', very_high: '很高' };
const DIFF_CLS = { low: 'done', medium: 'running', high: 'sev-major', very_high: 'error' };
const SEV_LABELS = { blocker: '阻塞', major: '主要', minor: '次要' };
const SEV_CLS = { blocker: 'error', major: 'sev-major', minor: 'gray' };

// HarmonyOS-PC mirror adaptation status (already-ported packages), cached client-side.
const harmonyMemo = new Map();   // `${eco}:${name}` -> {adapted, source}
async function harmonyStatus(eco, names) {
  const k = (n) => `${eco || ''}:${n}`;
  const need = [...new Set(names)].filter((n) => !harmonyMemo.has(k(n)));
  if (need.length) {
    try {
      const r = await api(`/api/harmony-status?ecosystem=${enc(eco || '')}&names=${enc(need.join(','))}`);
      const res = (r && r.results) || {};
      need.forEach((n) => harmonyMemo.set(k(n), res[n] || { adapted: false }));
    } catch { need.forEach((n) => harmonyMemo.set(k(n), { adapted: false })); }
  }
  const out = {};
  names.forEach((n) => (out[n] = harmonyMemo.get(k(n)) || { adapted: false }));
  return out;
}
// Append a 🟢 已鸿蒙化 badge to any element carrying data-hname/data-heco (once).
async function decorateHarmonyBadges(scope) {
  const els = [...(scope || document).querySelectorAll('[data-hname]:not([data-hdone])')];
  if (!els.length) return;
  const byEco = new Map();
  els.forEach((el) => { const e = el.dataset.heco || ''; if (!byEco.has(e)) byEco.set(e, []); byEco.get(e).push(el); });
  for (const [eco, group] of byEco) {
    const st = await harmonyStatus(eco, group.map((el) => el.dataset.hname));
    group.forEach((el) => {
      el.dataset.hdone = '1';
      const s = st[el.dataset.hname];
      if (s && s.adapted) {
        const b = document.createElement('span');
        b.className = 'badge harmony'; b.textContent = '🟢 已鸿蒙化'; b.title = s.source || '';
        el.appendChild(b);
      }
    });
  }
}

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
  else if (hash === '/observations') renderObservations();
  else if (hash === '/pending-deps') renderPendingDeps();
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
  setHeader('<a class="btn" href="#/pending-deps">📦 待分析依赖</a>' +
            '<a class="btn" href="#/observations">🔭 模型观察</a>' +
            '<button class="btn" id="hExport">⬇ 导出 Excel</button>' +
            '<button class="btn" id="hSettings">⚙ 系统设置</button>' +
            '<button class="btn primary" id="hClone">＋ 克隆库</button>');
  $('#hExport').onclick = () => {
    const q = selected.size ? '?names=' + encodeURIComponent([...selected].join(',')) : '';
    window.location = '/api/export' + q;
  };
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
      <div class="filter">
        <select id="statusFilter">
          <option value="">全部状态</option>
          <option value="analyzed">已分析</option>
          <option value="failed">失败</option>
          <option value="unanalyzed">未分析</option>
          <option value="uncloned">未克隆</option>
          <option value="active">进行中</option>
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
  $('#statusFilter').onchange = () => { page = 1; renderList(); };
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
  const stf = ($('#statusFilter') ? $('#statusFilter').value : '');
  const filtered = libsCache.filter((l) => {
    const matchesSearch = !q || l.name.toLowerCase().includes(q) ||
      ((l.summary && l.summary.oneLiner) || '').toLowerCase().includes(q);
    const matchesEco = !eco || (l.summary && l.summary.ecosystem === eco);
    const matchesStatus = !stf || statusKey(l) === stf;
    return matchesSearch && matchesEco && matchesStatus;
  });
  // 默认排序：最近一次分析时间倒序；无分析时间者按添加（克隆）时间。
  const sortKey = (l) => (l.analyzedAt != null ? l.analyzedAt : (l.addedAt != null ? l.addedAt : 0));
  return filtered.sort((a, b) => sortKey(b) - sortKey(a));
}

// Stable status bucket for filtering (aligns with libStatus()).
function statusKey(lib) {
  if (lib.active) return 'active';
  if (!lib.cloned) return 'uncloned';
  if (lib.latest) return lib.latest.status === 'error' ? 'failed' : 'analyzed';
  return 'unanalyzed';
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
        <td>${s.ecosystem ? `<span class="chip eco-chip">${esc(ECO_LABELS[s.ecosystem] || s.ecosystem)}</span>` : '—'}${bindingChips(s.bindings, s.ecosystem)}</td>
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

// ===========================================================================
//  PENDING DEPENDENCIES (level 1.5) — 未分析的「三方库依赖的三方库」
// ===========================================================================
let pdepCloneableOnly = false;
let pdepHideAdapted = false;        // 只看未鸿蒙化
const pdepUrlEdits = {};            // key -> user-typed URL (survives polling re-render)
let pdepItems = [];                 // last-rendered items (for 一键填充全部)
const pdepKey = (it) => `${it.ecosystem || ''}|${it.name}`;

// Resolve one dep's repo URL online; fill its input + pdepUrlEdits on hit.
// Returns the resolved url or null. `btn` (optional) gets a transient busy state.
async function resolveDepUrl(eco, name, key, btn) {
  if (btn) { btn.disabled = true; btn.textContent = '…'; }
  let r;
  try { r = await api(`/api/resolve-repo?ecosystem=${enc(eco || '')}&name=${enc(name)}`); }
  catch { r = null; }
  if (btn) { btn.disabled = false; btn.textContent = '🔎'; }
  if (r && r.disabled) { toast('联网解析已在设置中关闭', 'err'); return null; }
  if (r && r.url) {
    pdepUrlEdits[key] = r.url;
    const inp = $(`input.pdep-url[data-key="${cssAttr(key)}"]`);
    if (inp) inp.value = r.url;
    return r.url;
  }
  return null;
}

async function renderPendingDeps() {
  setHeader('<a class="btn ghost" href="#/">← 返回库列表</a>');
  $('#app').innerHTML = `<div class="detail-head"><h1>📦 待分析依赖库</h1></div>
    <p class="muted">已分析库所依赖、但自身尚未被分析的三方库，跨所有库聚合。把某个依赖「加入分析列表」即克隆入库；克隆完成后就地点「分析」。分析完成后它会自动从此列表消失。</p>
    <div class="toolbar">
      <label class="pdep-toggle"><input type="checkbox" id="pdepCloneable" ${pdepCloneableOnly ? 'checked' : ''} /> 只看可克隆（有候选仓库 URL / 远端来源）</label>
      <label class="pdep-toggle"><input type="checkbox" id="pdepHideAdapted" ${pdepHideAdapted ? 'checked' : ''} /> 只看未鸿蒙化</label>
      <span id="pdepHarmonySummary" class="muted"></span>
      <button class="btn sm" id="pdepResolveAll">🔎 一键填充全部</button>
      <button class="btn sm" id="pdepRefresh">刷新</button>
    </div>
    <div id="pdeps"><p class="muted">加载中…</p></div>`;
  $('#pdepCloneable').onchange = (e) => { pdepCloneableOnly = e.target.checked; loadPendingDeps(); };
  $('#pdepHideAdapted').onchange = (e) => { pdepHideAdapted = e.target.checked; loadPendingDeps(); };
  $('#pdepResolveAll').onclick = resolveAllPendingDeps;
  $('#pdepRefresh').onclick = loadPendingDeps;
  await loadPendingDeps();
  const timer = setInterval(loadPendingDeps, 4000);
  view.cleanup = () => clearInterval(timer);
}

async function loadPendingDeps() {
  const box = $('#pdeps');
  if (!box) return;
  // Don't clobber a URL the user is actively typing.
  if (document.activeElement && document.activeElement.classList && document.activeElement.classList.contains('pdep-url')) return;
  let data, libs;
  try { [data, { libraries: libs }] = await Promise.all([api('/api/pending-deps'), api('/api/libraries')]); }
  catch { box.innerHTML = '<div class="hint err">加载失败</div>'; return; }
  const libMap = {};
  (libs || []).forEach((l) => { libMap[l.name] = l; });
  let items = data.items || [];
  if (pdepCloneableOnly) items = items.filter((it) => it.candidateUrl || it.locality === 'remote');
  pdepItems = items;
  if (!items.length) {
    box.innerHTML = `<div class="empty">${pdepCloneableOnly ? '没有带候选仓库 URL 的待分析依赖。' : '暂无待分析依赖。分析更多库后，它们的依赖会出现在这里。'}</div>`;
    return;
  }
  // group by ecosystem
  const byEco = {};
  items.forEach((it) => { (byEco[it.ecosystem || 'other'] = byEco[it.ecosystem || 'other'] || []).push(it); });
  box.innerHTML = Object.entries(byEco).map(([eco, list]) => `
    <div class="card" style="margin-bottom:12px">
      <div class="section-title">${esc(ECO_LABELS[eco] || eco)} (${list.length})</div>
      ${list.map((it) => pdepRowHtml(it, libMap)).join('')}
    </div>`).join('');
  // wire actions
  $$('[data-pdep-clone]', box).forEach((b) => b.onclick = () => {
    const key = b.dataset.pdepClone;
    const input = box.querySelector(`input.pdep-url[data-key="${cssAttr(key)}"]`);
    promoteDep(input ? input.value.trim() : '', key);
  });
  $$('[data-pdep-analyze]', box).forEach((b) => b.onclick = () => analyzeOne(b.dataset.pdepAnalyze));
  $$('[data-pdep-resolve]', box).forEach((b) => b.onclick = async () => {
    const url = await resolveDepUrl(b.dataset.eco, b.dataset.name, b.dataset.pdepResolve, b);
    toast(url ? `已填充：${url}` : '未找到仓库地址，请手动填写', url ? 'ok' : 'err');
  });
  $$('input.pdep-url', box).forEach((inp) => inp.oninput = () => { pdepUrlEdits[inp.dataset.key] = inp.value; });
  decoratePendingHarmony(box);
}

// 已鸿蒙化: badge each row, show "X/Y 已鸿蒙化" summary, optionally hide adapted rows.
async function decoratePendingHarmony(box) {
  await decorateHarmonyBadges(box);
  const items = pdepItems || [];
  const adapted = items.filter((it) => {
    const s = harmonyMemo.get(`${it.ecosystem || ''}:${it.name}`);
    return s && s.adapted;
  }).length;
  const sum = $('#pdepHarmonySummary');
  if (sum) sum.textContent = adapted ? `🟢 ${adapted}/${items.length} 依赖已鸿蒙化` : '';
  if (pdepHideAdapted) {
    box.querySelectorAll('.pdep-name[data-hname]').forEach((el) => {
      const s = harmonyMemo.get(`${el.dataset.heco || ''}:${el.dataset.hname}`);
      const row = el.closest('.pdep-row');
      if (row && s && s.adapted) row.style.display = 'none';
    });
  }
}

// 一键填充全部: resolve repo URLs for every un-cloned row that has no URL yet,
// with a small concurrency pool so we don't fan out to registries all at once.
async function resolveAllPendingDeps() {
  const btn = $('#pdepResolveAll');
  const targets = (pdepItems || []).filter((it) => {
    const key = pdepKey(it);
    const hasUrl = (pdepUrlEdits[key] != null ? pdepUrlEdits[key] : it.candidateUrl) || '';
    return !it.cloned && !it.active && !hasUrl;
  });
  if (!targets.length) return toast('没有需要填充的依赖', 'ok');
  if (btn) btn.disabled = true;
  let done = 0, hit = 0, i = 0;
  const worker = async () => {
    while (i < targets.length) {
      const it = targets[i++];
      const url = await resolveDepUrl(it.ecosystem, it.name, pdepKey(it), null);
      done++; if (url) hit++;
      if (btn) btn.textContent = `🔎 解析中 ${done}/${targets.length}`;
    }
  };
  await Promise.all(Array.from({ length: Math.min(4, targets.length) }, worker));
  if (btn) { btn.disabled = false; btn.textContent = '🔎 一键填充全部'; }
  toast(`已解析 ${hit}/${targets.length} 个仓库地址`, hit ? 'ok' : 'err');
}

function pdepRowHtml(it, libMap) {
  const key = pdepKey(it);
  const eco = it.ecosystem ? `<span class="chip eco-chip">${esc(ECO_LABELS[it.ecosystem] || it.ecosystem)}</span>` : '';
  const loc = it.locality ? `<span class="badge ${LOCALITY_CLS[it.locality] || 'gray'}">${LOCALITY_LABELS[it.locality] || it.locality}</span>` : '';
  const scopes = (it.scopes || []).filter((s) => s && s !== 'runtime').map((s) => `<span class="tag">${esc(s)}</span>`).join('');
  const acq = it.acquisition ? `<span class="tag acq">${esc(ACQ_LABELS[it.acquisition] || it.acquisition)}</span>` : '';
  const seen = new Set();
  const deps = (it.dependents || []).filter((d) => !seen.has(d.lib) && seen.add(d.lib))
    .map((d) => `<a href="#/lib/${enc(d.lib)}" title="${esc(d.purpose || '')}">${esc(d.lib)}</a>`).join('、');
  const purpose = (it.dependents || []).map((d) => d.purpose).find(Boolean) || '';
  // action area depends on clone/analyze state
  const lib = it.repoName ? libMap[it.repoName] : null;
  const analyzed = lib && lib.latest && lib.latest.reportAvailable;
  const active = it.active || (lib && lib.active);
  let action;
  if (active) {
    action = `<span class="muted">处理中…</span> <a class="btn sm ghost" href="#/lib/${enc(it.repoName)}">查看</a>`;
  } else if (analyzed) {
    action = `<a class="btn sm ghost" href="#/lib/${enc(it.repoName)}">已分析 →</a>`;
  } else if (lib && lib.cloned) {
    action = `<span class="badge gray" title="已克隆，待分析">已入库</span> <button class="btn sm primary" data-pdep-analyze="${esc(it.repoName)}">分析</button>`;
  } else {
    const url = pdepUrlEdits[key] != null ? pdepUrlEdits[key] : (it.candidateUrl || '');
    action = `<input class="pdep-url" type="text" data-key="${esc(key)}" value="${esc(url)}" placeholder="Git URL" />
      <button class="btn sm" data-pdep-resolve="${esc(key)}" data-eco="${esc(it.ecosystem || '')}" data-name="${esc(it.name)}" title="联网查询仓库地址">🔎</button>
      <button class="btn sm primary" data-pdep-clone="${esc(key)}">加入列表</button>`;
  }
  return `<div class="pdep-row">
    <div class="pdep-info">
      <div class="pdep-name" data-hname="${esc(it.name)}" data-heco="${esc(it.ecosystem || '')}"><b>${esc(it.name)}</b> ${eco} ${loc} ${scopes} ${acq}</div>
      <div class="muted pdep-meta">被 ${it.count} 个库依赖：${deps || '—'}${purpose ? ` · ${esc(purpose)}` : ''}</div>
    </div>
    <div class="pdep-act">${action}</div>
  </div>`;
}

// escape a string for use inside a [data-...="..."] attribute selector
function cssAttr(s) { return String(s).replace(/["\\]/g, '\\$&'); }

async function promoteDep(url, key) {
  if (!url) return toast('请输入 Git URL', 'err');
  let r;
  try { r = await api('/api/clone', { method: 'POST', headers: JSONH, body: JSON.stringify({ urls: [url] }) }); }
  catch { return toast('克隆请求失败', 'err'); }
  const job = (r.jobs || [])[0];
  if (job && job.jobId) {
    toast(`已开始克隆 ${job.name || url}`, 'ok');
    delete pdepUrlEdits[key];
    loadPendingDeps();
  } else {
    toast((job && job.error) || '克隆失败', 'err');
  }
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
    <label><input id="sPruneGit" type="checkbox" ${s.pruneGitAfterAnalyze ? 'checked' : ''} /> 分析完成后删除 repos/&lt;库&gt;/.git 省磁盘 <span class="hint" style="display:inline">（重新分析将读不到 commit）</span></label>
    <label><input id="sNetResolve" type="checkbox" ${s.enableNetworkResolve ? 'checked' : ''} /> 待分析依赖页允许联网解析仓库地址 <span class="hint" style="display:inline">（PyPI/npm/crates/Maven，C/C++ 走 GitHub 搜索）</span></label>
    <label><input id="sHarmonyMirror" type="checkbox" ${s.enableHarmonyMirror ? 'checked' : ''} /> 联网检测依赖是否已鸿蒙化 <span class="hint" style="display:inline">（OpenHarmony PC 镜像，有 ohos wheel 即已移植）</span></label>
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
      useCodegraph: $('#sCodegraph').checked, pruneGitAfterAnalyze: $('#sPruneGit').checked,
      enableNetworkResolve: $('#sNetResolve').checked, enableHarmonyMirror: $('#sHarmonyMirror').checked,
      promptTemplate: $('#sPrompt').value }) });
    closeModal(); toast('设置已保存', 'ok');
  };
}

// ===========================================================================
//  OBSERVATIONS (skill 反哺)
// ===========================================================================
const OBS_KIND_LABELS = { new_value: '新造值', gap: '盲区', ambiguity: '歧义' };
const OBS_KIND_CLS = { new_value: 'done', gap: 'running', ambiguity: 'queued' };
async function renderObservations() {
  setHeader('<a class="btn ghost" href="#/">← 返回库列表</a>');
  $('#app').innerHTML = `<div class="detail-head"><h1>🔭 模型观察 / 词表反哺</h1></div>
    <p class="muted">模型在分析中自造的取值、发现的盲区与分类歧义，跨所有库聚合。高频项可考虑提拔进对应 skill 的推荐取值。</p>
    <div id="obs"><p class="muted">加载中…</p></div>`;
  let data;
  try { data = await api('/api/observations'); } catch { $('#obs').innerHTML = '<div class="hint err">加载失败</div>'; return; }
  if (!data.items || !data.items.length) {
    $('#obs').innerHTML = '<div class="empty">暂无观察记录。重新分析库后，模型遇到新场景会记录在这里。</div>';
    return;
  }
  // group by dimension
  const byDim = {};
  data.items.forEach((it) => { (byDim[it.dimension] = byDim[it.dimension] || []).push(it); });
  $('#obs').innerHTML = Object.entries(byDim).map(([dim, items]) => `
    <div class="card" style="margin-bottom:12px">
      <div class="section-title">${esc(dim)} (${items.length})</div>
      <table class="obstable"><thead><tr><th>类型</th><th>字段</th><th>值</th><th class="c-num">次数</th><th>样本库</th><th>说明</th></tr></thead>
      <tbody>${items.map((it) => `<tr>
        <td><span class="badge ${OBS_KIND_CLS[it.kind] || 'gray'}">${OBS_KIND_LABELS[it.kind] || it.kind}</span></td>
        <td><code>${esc(it.field || '—')}</code></td>
        <td>${it.value ? `<code>${esc(it.value)}</code>` : '—'}</td>
        <td class="c-num">${it.count}</td>
        <td>${(it.libs || []).map((n) => `<a href="#/lib/${enc(n)}">${esc(n)}</a>`).join('、')}</td>
        <td class="muted">${esc(it.rationale || '')}</td></tr>`).join('')}</tbody></table>
    </div>`).join('');
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
  // heartbeat: surface liveness when the stream goes quiet (e.g. a long codegraph/Bash step)
  let lastEvt = Date.now(), hbEl = null;
  const bump = () => { lastEvt = Date.now(); if (hbEl) { hbEl.remove(); hbEl = null; } };
  const hbTimer = setInterval(() => {
    const idle = Date.now() - lastEvt;
    if (idle < 20000) return;
    const c = $('#console'); if (!c) return;
    if (!hbEl) { hbEl = document.createElement('div'); hbEl.className = 'ln sys'; c.appendChild(hbEl); }
    hbEl.textContent = `…仍在运行（已静默 ${Math.round(idle / 1000)}s，主 agent 可能在执行长任务）`;
    c.scrollTop = c.scrollHeight;
  }, 5000);
  const stopHb = () => { clearInterval(hbTimer); if (hbEl) { hbEl.remove(); hbEl = null; } };
  es = new EventSource('/api/stream?job=' + jobId);
  es.addEventListener('input', (e) => { bump(); const d = JSON.parse(e.data).data; metaLine('$ ' + (d.argv ? d.argv.join(' ') : '')); });
  es.addEventListener('status', (e) => { bump(); const d = JSON.parse(e.data).data; setDStatus(d.status); sysLine('状态：' + statusZh(d.status)); });
  es.addEventListener('log', (e) => { bump(); const { stream, text } = JSON.parse(e.data).data; renderLog(text, stream); });
  es.addEventListener('end', (e) => {
    stopHb();
    const d = JSON.parse(e.data).data;
    sysLine(`— 进程结束，退出码 ${d.code}（${statusZh(d.status)}）—`);
    setDStatus(d.status);
    if (es) { es.close(); es = null; }
    if (onEnd) onEnd(d);
  });
  es.onerror = () => {};
  view.cleanup = () => { stopHb(); if (es) { es.close(); es = null; } };
}

// ---- console --------------------------------------------------------------
const shownTools = new Set();   // dedupe tool_use lines by callID (reset per console clear)
function clearConsole() { const c = $('#console'); if (c) c.innerHTML = ''; shownTools.clear(); }
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
      const id = p.callID || p.id || '';
      const status = s.status || 'running';
      const raw = (s.input && s.input.description) || s.title || (s.input ? JSON.stringify(s.input) : '');
      const label = String(raw).slice(0, 100);
      // errors: always surface once
      if (status === 'error') {
        if (id && shownTools.has('err:' + id)) return null;
        if (id) shownTools.add('err:' + id);
        return { text: `🔧 ${p.tool}${label ? ' · ' + label : ''} ✖`, cls: 'stderr' };
      }
      // otherwise show one line at first sighting (running → liveness for long tools)
      if (id && shownTools.has('seen:' + id)) return null;
      if (id) shownTools.add('seen:' + id);
      const mark = status === 'completed' ? '' : ' · 运行中…';
      return { text: `🔧 ${p.tool}${label ? ' · ' + label : ''}${mark}`, cls: 'tool' };
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
    <b>生态</b><span>${lib.ecosystem ? `<span class="chip eco-chip">${esc(ECO_LABELS[lib.ecosystem] || lib.ecosystem)}</span>` : '—'}${bindingChips(lib.bindings, lib.ecosystem)}</span>
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
    const hasSplit = langs.some((l) => l.production || l.test || l.example);
    const seg = (n, cls, label) => (n && n.code)
      ? `<span class="bar ${cls}" style="width:${100 * n.code / max}%" title="${label} ${num(n.code)} 行 / ${num(n.files)} 文件"></span>` : '';
    const rows = langs.slice(0, 8).map((l) => {
      const bar = hasSplit
        ? `<span class="barwrap">${seg(l.production, 'prod', '生产')}${seg(l.test, 'test', '测试')}${seg(l.example, 'example', '样例')}</span>`
        : `<span class="bar" style="width:${Math.max(3, 100 * l.code / max)}%"></span>`;
      return `<div class="barrow"><span>${esc(l.language)}</span><span>${bar}</span><span>${num(l.code)} (${l.pct}%)</span></div>`;
    }).join('');
    const legend = hasSplit
      ? `<div class="lang-legend"><span><span class="bar prod"></span> 生产</span><span><span class="bar test"></span> 测试</span><span><span class="bar example"></span> 样例</span></div>`
      : '';
    parts.push(sec('语言分布', legend + rows));
  }

  parts.push(sec('测试', `<div class="kv">
    <b>测试文件</b><span>${num(t.test_files)}</span>
    <b>测试用例</b><span>${num(t.test_cases)}</span>
    <b>框架</b><span>${(t.frameworks || []).map((f) => `<span class="chip">${esc(f)}</span>`).join('') || '—'}</span></div>`));

  const hasDeps = dep.count != null || (dep.dependencies || []).length;
  const dynlibs = na.dynamic_libraries || [];
  if (hasDeps || dynlibs.length) {
    const items = (dep.dependencies || []).slice(0, 40).map((d) =>
      `<span class="chip" data-hname="${esc(d.name)}" data-heco="${esc(d.ecosystem || '')}" title="${esc(d.purpose || '')}">${esc(d.name)}${d.scope && d.scope !== 'runtime' ? ` ·${esc(d.scope)}` : ''}</span>`).join('');
    const treePart = hasDeps
      ? `<div class="subtitle">依赖关系（面板内连接，离线）</div>
         <div class="deptree" id="depTree"><p class="muted">加载依赖关系…</p></div>`
      : '';
    const dynPart = dynlibs.length
      ? `<div class="subtitle">运行时动态加载库 (${dynlibs.length})</div><div class="deptree">${dynlibs.map(dynDepRow).join('')}</div>`
      : '';
    const auxN = (dep.dependencies || []).filter((d) =>
      ['build', 'test', 'dev'].includes(String(d.scope || '').toLowerCase())).length;
    const runN = dep.count != null ? dep.count : ((dep.dependencies || []).length - auxN);
    const depTitle = (auxN ? `依赖 (${runN} 运行时 · ${auxN} 开发/测试/构建)` : `依赖 (${runN})`)
      + ' <span id="depHarmonyCount" class="muted"></span>';
    parts.push(sec(depTitle,
      (hasDeps ? (items || '<span class="muted">无</span>') : '') +
      (dep.notes ? `<p class="hint">${esc(dep.notes)}</p>` : '') + treePart + dynPart));
  }

  if ((na.groups || []).length || na.summary) {
    const sortedGroups = (na.groups || []).slice().sort((a, b) =>
      (CAT_ORDER.indexOf(a.category) + 1 || 99) - (CAT_ORDER.indexOf(b.category) + 1 || 99));
    const groups = sortedGroups.map((g) => {
      const cat = g.category ? `<span class="badge ${CAT_CLS[g.category] || 'gray'}">${CAT_LABELS[g.category] || g.category}</span> ` : '';
      const plat = g.platform && PLAT_LABELS[g.platform] ? `<span class="tag">${PLAT_LABELS[g.platform]}</span>` : '';
      const head = `<div class="apigroup-h">${cat}<b>${esc(g.type)}</b> ${plat}</div>`;
      // new per-API table; fall back to old flat symbols for legacy reports
      if ((g.apis || []).length) {
        const rows = g.apis.map((a) => {
          const loc = (a.evidence || []).slice(0, 3).map(esc).join('、');
          const more = (a.evidence || []).length > 3 ? ` <span class="muted" title="${esc((a.evidence || []).join(', '))}">…</span>` : '';
          const cnt = (a.count != null) ? ` <span class="api-cnt" title="调用次数">×${num(a.count)}</span>` : '';
          return `<tr><td class="api-n"><code>${esc(a.name)}</code>${cnt}${a.conditional ? ' <span class="tag">#ifdef</span>' : ''}</td>
            <td>${esc(a.purpose || '')}</td><td class="api-loc">${loc || '—'}${more}</td></tr>`;
        }).join('');
        return `${head}<table class="apitable"><thead><tr><th>API</th><th>用途</th><th>调用位置</th></tr></thead><tbody>${rows}</tbody></table>`;
      }
      const syms = (g.symbols || []).map(esc).join(', ');
      return `${head}<div class="cat"><span class="syms">${syms || '<i class="muted">—</i>'}</span></div>`;
    }).join('');
    const legend = `<div class="api-legend">${CAT_ORDER.filter((c) => sortedGroups.some((g) => g.category === c))
      .map((c) => `<span><span class="badge ${CAT_CLS[c]}">${CAT_LABELS[c]}</span> ${esc(CAT_LEGEND[c])}</span>`).join('')}</div>`;
    parts.push(sec('系统 / 平台 API 调用', `<p>${esc(na.summary || '')}</p>${legend}${groups}` +
      (dynlibs.length ? `<p class="hint">运行时动态加载库见「依赖」区。</p>` : '') +
      (na.platform_dependence ? `<p class="hint">平台依赖：${esc(na.platform_dependence)}</p>` : '')));
  }

  // 外部交互面 (runtime_surface)
  const rs = r.runtime_surface || {};
  const surfRow = (label, arr, fmt) => {
    const items = (arr || []).map(fmt).join('');
    return items ? `<div class="subtitle">${label}</div>${items}` : '';
  };
  const surfItem = (main, purpose, evidence) =>
    `<div class="surf"><b>${esc(main)}</b>${purpose ? ` — <span>${esc(purpose)}</span>` : ''}` +
    `${(evidence || []).length ? ` <span class="muted" title="${esc(evidence.join(', '))}">📄</span>` : ''}</div>`;
  if ((rs.network || []).length || (rs.filesystem || []).length || (rs.env_vars || []).length ||
      (rs.subprocess || []).length || (rs.devices || []).length || rs.summary) {
    parts.push(sec('外部交互面', `${rs.summary ? `<p>${esc(rs.summary)}</p>` : ''}` +
      surfRow('环境变量', rs.env_vars, (e) => surfItem(e.name, e.purpose, e.evidence)) +
      surfRow('网络', rs.network, (e) => surfItem(e.detail, e.purpose, e.evidence)) +
      surfRow('文件系统', rs.filesystem, (e) => surfItem(e.detail, e.purpose, e.evidence)) +
      surfRow('子进程', rs.subprocess, (e) => surfItem(e.command, e.purpose, e.evidence)) +
      surfRow('设备', rs.devices, (e) => surfItem(e.detail, e.purpose, e.evidence))));
  }

  // 构建与平台 (build_env)
  const be = r.build_env || {};
  if (be.language_standard || be.build_system || be.runtime_version ||
      (be.platforms || []).length || (be.compiler_extensions || []).length || be.notes) {
    const plats = (be.platforms || []).map((p) =>
      `<span class="chip" title="${esc((p.evidence || []).join(', '))}">${esc(p.os || '')}${p.arch ? ' / ' + esc(p.arch) : ''}</span>`).join('');
    const exts = (be.compiler_extensions || []).map((e) => surfItem(e.detail, e.purpose, e.evidence)).join('');
    parts.push(sec('构建与平台', `<div class="kv">
      <b>语言标准</b><span>${esc(be.language_standard || '—')}</span>
      <b>运行时版本</b><span>${esc(be.runtime_version || '—')}</span>
      <b>构建系统</b><span>${esc(be.build_system || '—')}</span></div>` +
      (plats ? `<div class="subtitle">支持平台</div>${plats}` : '') +
      (exts ? `<div class="subtitle">编译器特有扩展</div>${exts}` : '') +
      (be.notes ? `<p class="hint">${esc(be.notes)}</p>` : '')));
  }

  // 鸿蒙适配评估 (harmony_adaptation, dim 9)
  const ha = r.harmony_adaptation || {};
  if (ha.feasibility || ha.summary || (ha.blockers || []).length ||
      ha.recommended_path || (ha.key_tasks || []).length) {
    const feasBadge = ha.feasibility
      ? `<span class="badge ${FEAS_CLS[ha.feasibility] || 'gray'}">${FEAS_LABELS[ha.feasibility] || esc(ha.feasibility)}</span>` : '—';
    const diffBadge = ha.overall_difficulty
      ? `<span class="badge ${DIFF_CLS[ha.overall_difficulty] || 'gray'}">${DIFF_LABELS[ha.overall_difficulty] || esc(ha.overall_difficulty)}</span>` : '—';
    const blockRows = (ha.blockers || []).map((b) => {
      const sev = b.severity
        ? `<span class="badge ${SEV_CLS[b.severity] || 'gray'}">${SEV_LABELS[b.severity] || esc(b.severity)}</span>` : '';
      const status = b.harmony_status ? `<span class="tag">${esc(b.harmony_status)}</span>` : '';
      const cat = b.category ? ` <code>${esc(b.category)}</code>` : '';
      const src = b.source_dimension ? ` <span class="muted">·${esc(b.source_dimension)}</span>` : '';
      const ev = (b.evidence || []).slice(0, 3).map(esc).join('、');
      const more = (b.evidence || []).length > 3
        ? ` <span class="muted" title="${esc((b.evidence || []).join(', '))}">…</span>` : '';
      return `<tr><td class="api-n">${sev}${cat}${src}</td>
        <td><b>${esc(b.issue || '')}</b>${b.remediation ? `<br><span class="muted">${esc(b.remediation)}</span>` : ''}</td>
        <td class="api-loc">${status}${ev ? `<div>${ev}${more}</div>` : ''}</td></tr>`;
    }).join('');
    const blockers = blockRows
      ? `<div class="subtitle">移植阻碍点</div><table class="apitable"><thead><tr><th>严重度 / 类别</th><th>问题与改造建议</th><th>鸿蒙状态 / 证据</th></tr></thead><tbody>${blockRows}</tbody></table>`
      : '';
    const compat = (ha.compatible || []).map((c) => surfItem(c.aspect, c.note, c.evidence)).join('');
    const tasks = (ha.key_tasks || []).length
      ? `<div class="subtitle">关键工作项</div><ul class="ha-tasks">${ha.key_tasks.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>` : '';
    parts.push(sec('鸿蒙适配评估', `<div class="kv">
      <b>可行性</b><span>${feasBadge}</span>
      <b>整体难度</b><span>${diffBadge}</span>
      <b>工作量</b><span>${ha.effort_estimate ? esc(ha.effort_estimate) : '—'}</span>
      <b>推荐路径</b><span>${ha.recommended_path ? `<code>${esc(ha.recommended_path)}</code>` : '—'}</span>
      <b>目标平台</b><span>${esc(ha.target || '—')}</span></div>` +
      (ha.summary ? `<p>${esc(ha.summary)}</p>` : '') +
      blockers +
      (compat ? `<div class="subtitle">可平滑移植</div>${compat}` : '') +
      tasks +
      (ha.notes ? `<p class="hint">${esc(ha.notes)}</p>` : '')));
  }

  const warn = (r.meta || {}).warnings || [];
  if (warn.length) parts.push(sec('警告', warn.map((w) => `<div class="cat">⚠ ${esc(w)}</div>`).join('')));

  el.innerHTML = parts.join('');
  depHlKey = null;
  el.onclick = depHighlightHandler;   // delegated click-to-highlight for dep tags
  if (hasDeps) loadDepTree(curReport && curReport.name);
  decorateHarmonyBadges(el).then(() => updateDepHarmonyCount(r));
}

// "X/Y 已鸿蒙化" in the dependency section title, from the cached status.
function updateDepHarmonyCount(r) {
  const span = $('#depHarmonyCount'); if (!span) return;
  const deps = ((r.dependencies || {}).dependencies) || [];
  if (!deps.length) return;
  const adapted = deps.filter((d) => {
    const s = harmonyMemo.get(`${d.ecosystem || ''}:${d.name}`);
    return s && s.adapted;
  }).length;
  span.textContent = adapted ? `· 🟢 ${adapted}/${deps.length} 已鸿蒙化` : '';
}

// ---- click-to-highlight dependency tags -----------------------------------
let depHlKey = null;
function applyDepHighlight(scope, key) {
  scope.querySelectorAll('.deptree li.leaf, .deptree summary, .dynlib').forEach((row) => {
    row.classList.remove('hl-on', 'hl-dim');
    if (key) row.classList.add(row.querySelector(`[data-hl="${key}"]`) ? 'hl-on' : 'hl-dim');
  });
  scope.querySelectorAll('[data-hl]').forEach((b) => b.classList.toggle('hl-badge-on', !!key && b.dataset.hl === key));
}
function depHighlightHandler(e) {
  const scope = $('#report'); if (!scope) return;
  const b = e.target.closest('[data-hl]');
  if (!b) { if (depHlKey) { depHlKey = null; applyDepHighlight(scope, null); } return; }
  e.preventDefault();
  depHlKey = (depHlKey === b.dataset.hl) ? null : b.dataset.hl;
  applyDepHighlight(scope, depHlKey);
}

// ---- dependency tree (offline, /api/depgraph) -----------------------------
async function loadDepTree(name) {
  const box = $('#depTree'); if (!box || !name) return;
  try {
    const { tree } = await api('/api/depgraph?name=' + enc(name));
    box.innerHTML = (tree && tree.length) ? depGroupsHtml(tree) : '<p class="muted">无可连接的依赖关系。</p>';
    decorateHarmonyBadges(box);
  } catch { box.innerHTML = '<p class="muted">依赖关系不可用。</p>'; }
}
// Top level: runtime deps grouped by ecosystem (language); aux deps (build / test /
// dev scope) split into their OWN collapsed groups by scope — a test framework or a
// docs generator isn't a build "toolchain", so don't lump them into one bucket.
const SCOPE_GROUP = { build: '🛠 构建', test: '🧪 测试', dev: '🔧 开发 / 工具' };
function depGroupsHtml(nodes) {
  const grp = (label, ns, open) =>
    `<details class="depgroup"${open ? ' open' : ''}><summary>${label} <span class="muted">(${ns.length})</span></summary>${depTreeHtml(ns)}</details>`;
  const isAux = (n) => Object.prototype.hasOwnProperty.call(SCOPE_GROUP, String(n.scope || '').toLowerCase());
  const aux = nodes.filter(isAux);
  const rest = nodes.filter((n) => !isAux(n));
  const eco = {};
  rest.forEach((n) => { const k = n.ecosystem || 'other'; (eco[k] = eco[k] || []).push(n); });
  let html = Object.entries(eco).map(([k, ns]) => grp(esc(ECO_LABELS[k] || k), ns, true)).join('');
  ['build', 'test', 'dev'].forEach((s) => {
    const ns = aux.filter((n) => String(n.scope || '').toLowerCase() === s);
    if (ns.length) html += grp(SCOPE_GROUP[s], ns, false);
  });
  return html || depTreeHtml(nodes);
}
function depNodeLabel(n) {
  const eco = n.ecosystem ? `<span class="chip eco-chip" data-hl="eco:${esc(n.ecosystem)}">${esc(ECO_LABELS[n.ecosystem] || n.ecosystem)}</span>` : '';
  const ver = n.version ? `<span class="muted">${esc(n.version)}</span>` : '';
  const scope = n.scope && n.scope !== 'runtime' ? `<span class="tag" data-hl="scope:${esc(n.scope)}">${esc(n.scope)}</span>` : '';
  const loc = n.locality || (n.acquisition ? (ACQ_LOCALITY[n.acquisition] || 'unknown') : null);
  const locBadge = loc ? `<span class="badge ${LOCALITY_CLS[loc]}" data-hl="loc:${loc}" title="${esc(ACQ_LABELS[n.acquisition] || n.acquisition)}">${LOCALITY_LABELS[loc]}</span>` : '';
  const acq = n.acquisition ? `<span class="tag acq" data-hl="acq:${esc(n.acquisition)}" title="${esc(n.source || '')}">${esc(ACQ_LABELS[n.acquisition] || n.acquisition)}</span>` : '';
  let tail;
  if (n.analyzed) tail = `<a class="btn sm ghost" href="#/lib/${enc(n.libName)}">跳转 →</a>`;
  else if (n.ambiguous) tail = `<span class="badge gray" title="面板内有多个同名同生态库，未自动连接">歧义</span>`;
  else tail = `<span class="badge gray">未分析</span>`;
  return `<span class="dep-name" data-hname="${esc(n.name)}" data-heco="${esc(n.ecosystem || '')}" title="${esc(n.purpose || '')}">${esc(n.name)}</span> ${ver} ${eco} ${locBadge} ${acq} ${scope} ${tail}`;
}
// runtime dynamically-loaded library, shown in the dependency area as a runtime dep
function dynDepRow(d) {
  const acq = d.acquisition ? `<span class="tag acq">${esc(ACQ_LABELS[d.acquisition] || d.acquisition)}</span>` : '';
  const meta = (d.source) ? `<div class="dep-meta">来源：${esc(d.source)}</div>` : '';
  return `<div class="dynlib">` +
    `<span class="badge ${LOCALITY_CLS.runtime}" data-hl="loc:runtime">${LOCALITY_LABELS.runtime}</span>` +
    `<span class="chip lang-chip">${esc(d.name)}</span>` +
    (d.mechanism ? `<span class="tag">${esc(d.mechanism)}</span>` : '') + acq +
    (d.optional ? `<span class="tag opt">可选</span>` : '') +
    `<span class="dynlib-desc" title="${esc((d.evidence || []).join(', '))}">${esc(d.description || '')}</span></div>` + meta;
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
