'use strict';
// ---- tiny helpers ---------------------------------------------------------
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const enc = encodeURIComponent;
const JSONH = { 'Content-Type': 'application/json' };
const api = (p, opts) => fetch(p, opts).then((r) => r.json());
// 活动分组（工作空间隔离）。所有 group-scoped 的请求带上它。
let activeGroup = localStorage.getItem('activeGroup') || 'default';
const gq = () => 'group=' + enc(activeGroup);                 // for query strings
const withGroup = (obj) => ({ ...obj, group: activeGroup });  // for POST bodies
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const num = (n) => (n == null ? 0 : n).toLocaleString();
const fmtTime = (s) => { try { return new Date(s).toLocaleString('zh-CN', { hour12: false }); } catch { return s || ''; } };
// 时长 ms → 人类可读（1h02m / 2m13s / 45s）。非法/负值返回 ''。
const fmtDuration = (ms) => {
  if (ms == null || !isFinite(ms) || ms < 0) return '';
  const s = Math.round(ms / 1000);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  if (h) return `${h}h${String(m).padStart(2, '0')}m`;
  if (m) return `${m}m${String(sec).padStart(2, '0')}s`;
  return `${sec}s`;
};
// 一次运行的耗时（endedAt - startedAt），任一缺失/非法返回 ''。
const runDuration = (r) => {
  if (!r || !r.startedAt || !r.endedAt) return '';
  return fmtDuration(Date.parse(r.endedAt) - Date.parse(r.startedAt));
};
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
// 来源标签 (主软件=primary / 被动依赖=passive)
const TAG_LABELS = { primary: '主软件', passive: '被动依赖' };
const TAG_CLS = { primary: 'tag-primary', passive: 'tag-passive' };
// library.kind — what the analyzed subject is (library vs application vs ...)
const KIND_LABELS = { library: '库', application: '应用', framework: '框架', tool: '工具',
  cli: '命令行', service: '服务', plugin: '插件', other: '其他' };
const kindLabel = (k) => k ? (KIND_LABELS[k] || k) : null;
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
// adaptation_assessment.overall — 是否可适配总判（派生，替代旧 feasibility）
const OVERALL_LABELS = { adaptable: '可适配', adaptable_with_tailoring: '可适配（部分平台特性需裁剪）', core_blocked: '核心功能不完全可适配' };
const OVERALL_CLS = { adaptable: 'done', adaptable_with_tailoring: 'sev-major', core_blocked: 'error' };
// functional_viability — 运行前提是否满足（目标侧派生轴，与 overall 正交：代码可无需适配但功能受阻于外部前提）
const FV_LABELS = { viable: '前提齐备', viable_with_work: '有条件可用', blocked_external: '功能受阻·依赖外部前提', unverified: '前提未核实' };
const FV_CLS = { viable: 'done', viable_with_work: 'sev-major', blocked_external: 'error', unverified: 'gray' };
// unadaptable_apis[].functionality_class — 功能类别（核心 vs 平台差异）
const FUNC_CLASS_LABELS = { core: '核心功能', platform_specific: '平台差异功能' };
// effort.level — 难度等级（server 派生：effective_class 下限 × person_days 数量级）
const LVL_LABELS = { very_low: '极低', low: '低', medium: '中', high: '高', very_high: '极高' };
const LVL_CLS = { very_low: 'done', low: 'done', medium: 'running', high: 'sev-major', very_high: 'error' };
const CONF_LABELS = { high: '高', medium: '中', low: '低' };
const fmtDays = (pd) => Array.isArray(pd) && pd.length === 2 ? `${pd[0]}–${pd[1]} 人天` : '';
const SEV_LABELS = { blocker: '阻塞', major: '主要', minor: '次要' };
const SEV_CLS = { blocker: 'error', major: 'sev-major', minor: 'gray' };
const ADAPT_LABELS = { adaptable: '可适配', partial: '部分可适配', unadaptable: '不可适配' };
const ADAPT_CLS = { adaptable: 'done', partial: 'sev-major', unadaptable: 'error' };
// target_assumptions[].target_status — HarmonyOS PC 目标能力是否满足
const TGT_LABELS = { available: '已支持', partial: '部分支持', unavailable: '不支持', unknown: '未核实', restricted: '受限' };
const TGT_CLS = { available: 'done', partial: 'running', unavailable: 'error', unknown: 'gray', restricted: 'sev-major' };
// capability_profile (dim 10) — scenario key labels
const CAP_LABELS = { gui: 'GUI 界面', rendering_3d: '3D 渲染', rendering_2d: '2D 绘制', media: '媒体', hardware: '硬件/设备' };
// license.category (dim 5) — 协议性质闭轴 label + color
const LIC_CAT_LABELS = { commercial: '商业协议', strong_copyleft: '强传染协议', weak_copyleft: '弱传染协议', permissive: '友好协议', undeclared: '未声明协议' };
const LIC_CAT_CLS = { commercial: 'sev-major', strong_copyleft: 'error', weak_copyleft: 'running', permissive: 'done', undeclared: 'gray' };
// cloud_services (dim 11) — vendor + category labels
const VENDOR_LABELS = {
  google_firebase: 'Firebase (Google)', aws: 'AWS', gcp: 'Google Cloud', azure: 'Azure',
  alibaba_cloud: '阿里云', tencent_cloud: '腾讯云', huawei_cloud: '华为云', supabase: 'Supabase',
  sentry: 'Sentry', cloudflare: 'Cloudflare', unknown: '未知厂商',
};
const CLOUD_CAT_LABELS = {
  auth: '登录鉴权', cloud_storage: '云存储', database: '云数据库', cloud_functions: '云函数',
  push: '推送', messaging: '消息', analytics: '分析统计', crash_reporting: '崩溃上报',
  remote_config: '远程配置', maps: '地图', ml_ai: 'AI 云推理', ads: '广告', hosting: '托管',
};
// code_partition (dim 12) — 分区桶闭轴 label + color（与拓扑配色系一致）
const PART_META = {
  reuse_direct:    { label: '直接复用', color: '#1f9d55' },
  recompile_reuse: { label: '重编译复用', color: '#0ea5a5' },
  needs_adaptation:{ label: '需适配', color: '#dd7a33' },
  unadaptable:     { label: '无法适配', color: '#d65745' },
};
const PART_ORDER = ['reuse_direct', 'recompile_reuse', 'needs_adaptation', 'unadaptable'];
// effort.breakdown[].component — 推荐集 label（开放词，未知值原样展示）
const EFFORT_COMP_LABELS = {
  recompile: '重编/交叉编译', api_adaptation: '平台 API 适配', gui: 'GUI 改造',
  deps_porting: '依赖移植', build_system: '构建系统', testing_verification: '测试验证', packaging: '打包分发',
};

// dep-topology node status — label + color (HarmonyOS 移植分级 5 档派生 effective_class)
const TOPO_STATUS = {
  harmonized:                          { label: '已鸿蒙化', color: '#1f9d55' },
  no_adaptation:                       { label: '无需适配', color: '#3b6cf6' },
  recompile_only:                      { label: '仅交叉编译', color: '#0ea5a5' },
  needs_adaptation:                    { label: '需适配·全部可适配', color: '#e0a458' },
  needs_adaptation_platform_partial:   { label: '需适配·平台差异有不可适配点', color: '#dd7a33' },
  needs_adaptation_core_partial:       { label: '需适配·核心有不可适配点', color: '#d65745' },
  unanalyzed:                          { label: '未分析', color: '#9aa4b2' },
};
const TOPO_ORDER = ['harmonized', 'no_adaptation', 'recompile_only', 'needs_adaptation', 'needs_adaptation_platform_partial', 'needs_adaptation_core_partial', 'unanalyzed'];
// 移植分级（effective_class）的 5 个取值——用于列表过滤选项；不含拓扑专用的 harmonized/unanalyzed
const PORTING_CLASS_ORDER = ['no_adaptation', 'recompile_only', 'needs_adaptation', 'needs_adaptation_platform_partial', 'needs_adaptation_core_partial'];
const topoStatusMeta = (s) => TOPO_STATUS[s] || { label: s || '未知', color: '#9aa4b2' };
// 移植分级「徽章」配色（仅首页列表 + 报告卡；依赖拓扑图仍用 TOPO_STATUS 图例配色）：
// 无需适配→绿、有不可适配点(核心/平台差异)→红；仅交叉编译/需适配·全部可适配 无键 → 回退原色。
const PCLASS_BADGE_COLOR = {
  no_adaptation: '#1f9d55',
  needs_adaptation_platform_partial: '#d65745',
  needs_adaptation_core_partial: '#d65745',
};
const pclassBadge = (cls) => {
  const m = topoStatusMeta(cls);
  return `<span class="badge" style="background:${PCLASS_BADGE_COLOR[cls] || m.color};color:#fff">${esc(m.label)}</span>`;
};

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
  else if (hash.startsWith('/recursive/')) renderRecursive(decodeURIComponent(hash.slice(11)));
  else if (hash === '/observations') renderObservations();
  else if (hash === '/pending-deps') renderPendingDeps();
  else if (hash === '/harmony-caps') renderHarmonyCaps();
  else if (hash.startsWith('/topology')) renderTopology(hash.startsWith('/topology/') ? decodeURIComponent(hash.slice(10)) : null);
  else renderDashboard();
}
window.addEventListener('hashchange', navigate);
// NOTE: the initial navigate() call lives at the very BOTTOM of this file so that all
// module-level `let`/`const` state (e.g. pdep* below) is initialized before a view
// renders — otherwise loading directly on #/pending-deps hits a TDZ ReferenceError.

// ===========================================================================
//  DASHBOARD (level 1)
// ===========================================================================
let libsCache = [];
const selected = new Set();
let page = 1;
const PAGE_SIZES = [10, 15, 25, 50, 100];
let pageSize = (() => { const v = parseInt(localStorage.getItem('dashPageSize'), 10); return PAGE_SIZES.includes(v) ? v : 15; })();

async function renderDashboard() {
  setHeader('<a class="btn" href="#/pending-deps">📦 待分析依赖</a>' +
            '<a class="btn" href="#/topology">🕸 依赖拓扑</a>' +
            '<a class="btn" href="#/harmony-caps">🧭 鸿蒙目标能力</a>' +
            '<a class="btn" href="#/observations">🔭 模型观察</a>' +
            '<button class="btn" id="hExport">⬇ 导出 Excel(定制表)</button>' +
            '<button class="btn" id="hSettings">⚙ 系统设置</button>' +
            '<button class="btn primary" id="hClone">＋ 克隆库</button>');
  $('#hExport').onclick = () => {
    const q = '?' + gq() + (selected.size ? '&names=' + enc([...selected].join(',')) : '');
    window.location = '/api/export' + q;
  };
  $('#hSettings').onclick = openSettings;
  $('#hClone').onclick = openCloneModal;

  $('#app').innerHTML = `
    <div class="toolbar">
      <div class="filter" title="工作空间分组：克隆/分析/报告按分组隔离">
        <select id="groupSelect"></select>
      </div>
      <button class="btn sm" id="newGroupBtn" title="新建分组">＋ 分组</button>
      <button class="btn sm danger ghost" id="delGroupBtn" title="删除当前分组（连同其下全部库与记录）">🗑 分组</button>
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
      <div class="filter">
        <select id="tagFilter">
          <option value="">全部标签</option>
          <option value="primary">主软件</option>
          <option value="passive">被动依赖</option>
        </select>
      </div>
      <div class="filter">
        <select id="portingFilter">
          <option value="">全部移植分级</option>
          ${PORTING_CLASS_ORDER.map((k) => `<option value="${esc(k)}">${esc(TOPO_STATUS[k].label)}</option>`).join('')}
        </select>
      </div>
      <div class="filter">
        <select id="levelFilter">
          <option value="">全部难度</option>
          ${Object.entries(LVL_LABELS).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('')}
        </select>
      </div>
      <button class="btn sm primary" id="batchAnalyze" disabled>分析选中</button>
      <button class="btn sm" id="batchClone" disabled title="重新克隆选中的「有报告但源码仓已删」的库">克隆选中</button>
      <button class="btn sm" id="batchMigrate" disabled title="把选中的库迁移到另一个分组">迁移选中</button>
      <button class="btn sm" id="refreshBtn">刷新</button>
    </div>
    <div id="jobsStrip" class="jobs-strip"></div>
    <div id="list"></div>
    <div id="pager" class="pager"></div>`;

  $('#refreshBtn').onclick = loadDash;
  $('#search').oninput = () => { page = 1; renderList(); };
  $('#ecoFilter').onchange = () => { page = 1; renderList(); };
  $('#statusFilter').onchange = () => { page = 1; renderList(); };
  $('#tagFilter').onchange = () => { page = 1; renderList(); };
  $('#portingFilter').onchange = () => { page = 1; renderList(); };
  $('#levelFilter').onchange = () => { page = 1; renderList(); };
  $('#batchAnalyze').onclick = batchAnalyze;
  $('#batchClone').onclick = batchClone;
  $('#batchMigrate').onclick = openBatchMigrateModal;
  $('#groupSelect').onchange = () => {
    activeGroup = $('#groupSelect').value || 'default';
    localStorage.setItem('activeGroup', activeGroup);
    selected.clear(); page = 1; loadDash();
  };
  $('#newGroupBtn').onclick = newGroup;
  $('#delGroupBtn').onclick = deleteGroup;

  await loadDash();
  const timer = setInterval(loadDash, 3000);
  view.cleanup = () => clearInterval(timer);
}

function renderGroupSelect(groups) {
  const sel = $('#groupSelect'); if (!sel) return;
  if (!groups.includes(activeGroup)) activeGroup = 'default';
  sel.innerHTML = groups.map((g) => `<option value="${esc(g)}" ${g === activeGroup ? 'selected' : ''}>分组：${esc(g)}</option>`).join('');
  const del = $('#delGroupBtn'); if (del) del.disabled = (activeGroup === 'default');   // default 不可删
}

async function deleteGroup() {
  if (activeGroup === 'default') return toast('default 分组不可删除', 'err');
  if (!confirm(`确认删除分组「${activeGroup}」？\n将删除该分组下的全部库、克隆代码、分析记录与来源标签，不可恢复。`)) return;
  let r;
  try { r = await api('/api/groups/delete', { method: 'POST', headers: JSONH, body: JSON.stringify({ group: activeGroup }) }); }
  catch { return toast('删除失败', 'err'); }
  if (r && r.error) return toast(r.error, 'err');
  const gone = activeGroup;
  activeGroup = 'default';
  localStorage.setItem('activeGroup', activeGroup);
  selected.clear(); page = 1;
  renderGroupSelect(r.groups || ['default']);
  toast(`已删除分组 ${gone}`, 'ok');
  loadDash();
}

async function newGroup() {
  const name = (prompt('新建分组名（字母/数字/._-，≤64）：') || '').trim();
  if (!name) return;
  const r = await api('/api/groups', { method: 'POST', headers: JSONH, body: JSON.stringify({ group: name }) });
  if (r.error) return toast(r.error, 'err');
  activeGroup = r.created || name;
  localStorage.setItem('activeGroup', activeGroup);
  renderGroupSelect(r.groups || [activeGroup]);
  selected.clear(); page = 1; toast(`已创建分组 ${activeGroup}`, 'ok'); loadDash();
}

async function loadDash() {
  try {
    const [libResp, { jobs }] = await Promise.all([api('/api/libraries?' + gq()), api('/api/jobs')]);
    if (libResp.groups) renderGroupSelect(libResp.groups);
    libsCache = libResp.libraries || [];
    renderJobsStrip(jobs);
    renderList();
  } catch (_) {}
}

function visibleLibs() {
  const q = ($('#search') ? $('#search').value : '').trim().toLowerCase();
  const eco = ($('#ecoFilter') ? $('#ecoFilter').value : '');
  const stf = ($('#statusFilter') ? $('#statusFilter').value : '');
  const tag = ($('#tagFilter') ? $('#tagFilter').value : '');
  const pf = ($('#portingFilter') ? $('#portingFilter').value : '');
  const lf = ($('#levelFilter') ? $('#levelFilter').value : '');
  const filtered = libsCache.filter((l) => {
    const matchesSearch = !q || l.name.toLowerCase().includes(q) ||
      ((l.summary && l.summary.oneLiner) || '').toLowerCase().includes(q);
    const matchesEco = !eco || (l.summary && l.summary.ecosystem === eco);
    const matchesStatus = !stf || statusKey(l) === stf;
    const matchesTag = !tag || (l.tags || []).includes(tag);
    const matchesPorting = !pf || (l.summary && l.summary.portingClass === pf);
    const matchesLevel = !lf || (l.summary && l.summary.difficultyLevel === lf);
    return matchesSearch && matchesEco && matchesStatus && matchesTag && matchesPorting && matchesLevel;
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
  const pages = Math.max(1, Math.ceil(libs.length / pageSize));
  page = Math.min(page, pages);
  const slice = libs.slice((page - 1) * pageSize, page * pageSize);
  // 可勾选＝已克隆(可分析) 或 有报告地址的报告-only 库(可重新克隆)；全选只作用于当前分页。
  const selectable = (l) => l.cloned || !!l.cloneUrl;
  const pageSelectable = slice.filter(selectable).map((l) => l.name);
  const allSel = pageSelectable.length && pageSelectable.every((n) => selected.has(n));

  box.innerHTML = `<table class="libtable">
    <thead><tr>
      <th class="c-chk"><input type="checkbox" id="selAll" ${allSel ? 'checked' : ''} title="全选/取消" /></th>
      <th>名称</th><th class="c-st">状态</th><th>生态</th><th>语言</th>
      <th class="c-num">生产代码</th><th class="c-num">测试</th><th>协议</th>
      <th class="c-st">移植分级</th><th class="c-st">运行前提</th><th class="c-st">难度等级</th>
      <th class="c-time">最近分析</th><th class="c-act">操作</th>
    </tr></thead><tbody>${slice.map((lib) => {
      const st = libStatus(lib); const s = lib.summary || {};
      return `<tr data-name="${esc(lib.name)}">
        <td class="c-chk"><input type="checkbox" data-sel="${esc(lib.name)}" ${selected.has(lib.name) ? 'checked' : ''} ${selectable(lib) ? '' : 'disabled'} /></td>
        <td><a class="lname" href="#/lib/${enc(lib.name)}">${esc(lib.name)}</a>
            ${(lib.tags || []).map((t) => `<span class="chip ${TAG_CLS[t] || ''}">${esc(TAG_LABELS[t] || t)}</span>`).join('')}
            ${(lib.subpath || s.subpath) ? `<span class="chip" title="monorepo 子目录">▸ ${esc(lib.subpath || s.subpath)}</span>` : ''}
            <div class="lsub">${esc(s.oneLiner || (lib.cloned ? '尚未分析' : '尚未克隆'))}</div></td>
        <td class="c-st"><span class="badge ${st.cls}">${st.label}</span></td>
        <td>${s.ecosystem ? `<span class="chip eco-chip">${esc(ECO_LABELS[s.ecosystem] || s.ecosystem)}</span>` : '—'}${bindingChips(s.bindings, s.ecosystem)}</td>
        <td>${s.primary ? `<span class="chip lang-chip">${esc(s.primary)}</span>` : '—'}</td>
        <td class="c-num">${s.prodCode != null ? num(s.prodCode) : '—'}</td>
        <td class="c-num">${s.testCases != null ? num(s.testCases) : '—'}</td>
        <td>${esc(s.license || '—')}${s.licenseCategory ? ` <span class="badge ${LIC_CAT_CLS[s.licenseCategory] || 'gray'}">${LIC_CAT_LABELS[s.licenseCategory] || esc(s.licenseCategory)}</span>` : ''}</td>
        <td class="c-st">${s.portingClass ? pclassBadge(s.portingClass) : '—'}</td>
        <td class="c-st">${s.functionalViability ? `<span class="badge ${FV_CLS[s.functionalViability] || 'gray'}">${FV_LABELS[s.functionalViability] || esc(s.functionalViability)}</span>` : '—'}</td>
        <td class="c-st">${s.difficultyLevel ? `<span class="badge ${LVL_CLS[s.difficultyLevel] || 'gray'}"${s.personDays ? ` title="${esc(fmtDays(s.personDays))}"` : ''}>${esc(LVL_LABELS[s.difficultyLevel] || s.difficultyLevel)}</span>` : '—'}</td>
        <td class="c-time">${lib.analyzedAt ? esc(fmtTime(new Date(lib.analyzedAt))) : '—'}</td>
        <td class="c-act">
          <a class="btn sm ghost" href="#/lib/${enc(lib.name)}">详情</a>
          ${(!lib.cloned && lib.cloneUrl) ? `<button class="btn sm primary" data-act="reclone" data-name="${esc(lib.name)}" ${lib.active ? 'disabled' : ''} title="源码仓已删，从报告地址重新克隆">克隆</button>` : ''}
          <button class="btn sm primary" data-act="analyze" data-name="${esc(lib.name)}" ${lib.active || !lib.cloned ? 'disabled' : ''}>分析</button>
          <button class="btn sm ghost" data-act="more" data-name="${esc(lib.name)}" title="更多操作（拓扑/标签/迁移/删除）">⋯</button>
        </td></tr>`;
    }).join('')}</tbody></table>`;

  $('#selAll').onchange = () => {
    pageSelectable.forEach((n) => (allSel ? selected.delete(n) : selected.add(n)));
    renderList();
  };
  $$('[data-sel]', box).forEach((cb) => cb.onchange = () => {
    cb.checked ? selected.add(cb.dataset.sel) : selected.delete(cb.dataset.sel);
    updateBatchBtn();
  });
  $$('[data-act="analyze"]', box).forEach((b) => b.onclick = () => analyzeOne(b.dataset.name));
  $$('[data-act="reclone"]', box).forEach((b) => b.onclick = () => recloneOne(b.dataset.name));
  $$('[data-act="more"]', box).forEach((b) => b.onclick = () => openRowActions(b.dataset.name));

  $('#pager').innerHTML = `
    <div class="pager-nav">
      <button class="btn sm" id="pFirst" ${page <= 1 ? 'disabled' : ''}>« 首页</button>
      <button class="btn sm" id="pPrev" ${page <= 1 ? 'disabled' : ''}>‹ 上一页</button>
      <span class="pinfo">第 ${page} / ${pages} 页 · 共 ${libs.length} 个库</span>
      <button class="btn sm" id="pNext" ${page >= pages ? 'disabled' : ''}>下一页 ›</button>
      <button class="btn sm" id="pLast" ${page >= pages ? 'disabled' : ''}>末页 »</button>
      <span class="pinfo">跳转</span>
      <input id="pJump" type="number" min="1" max="${pages}" value="${page}" style="width:60px" />
      <button class="btn sm" id="pGo">Go</button>
    </div>
    <div class="pager-size">
      <span class="pinfo">每页</span>
      <select id="pSize">${PAGE_SIZES.map((n) => `<option value="${n}" ${n === pageSize ? 'selected' : ''}>${n}</option>`).join('')}</select>
    </div>`;
  $('#pFirst').onclick = () => { if (page > 1) { page = 1; renderList(); } };
  $('#pPrev').onclick = () => { if (page > 1) { page--; renderList(); } };
  $('#pNext').onclick = () => { if (page < pages) { page++; renderList(); } };
  $('#pLast').onclick = () => { if (page < pages) { page = pages; renderList(); } };
  const jump = () => { const v = parseInt($('#pJump').value, 10); if (v >= 1) { page = Math.min(v, pages); renderList(); } };
  $('#pGo').onclick = jump;
  $('#pJump').onkeydown = (e) => { if (e.key === 'Enter') jump(); };
  $('#pSize').onchange = () => { pageSize = parseInt($('#pSize').value, 10) || 15; localStorage.setItem('dashPageSize', pageSize); page = 1; renderList(); };
  updateBatchBtn();
}

// 「⋯」行操作面板：把次要操作（拓扑/标签/迁移/删除）收进弹窗，避免操作列过宽顶出屏幕。
function openRowActions(name) {
  const lib = libsCache.find((l) => l.name === name) || {};
  const active = !!lib.active;
  const hasReport = !!(lib.latest && lib.latest.reportAvailable);
  showModal(`<h2>操作 · ${esc(name)}</h2>
    <div class="rowacts">
      ${hasReport ? '<button class="btn" data-ra="topo">🕸 依赖拓扑</button>' : ''}
      <button class="btn" data-ra="tags">🏷 编辑来源标签</button>
      <button class="btn" data-ra="migrate" ${active ? 'disabled' : ''}>↗ 迁移分组</button>
      <button class="btn danger ghost" data-ra="del" ${active ? 'disabled' : ''}>🗑 删除该库</button>
    </div>
    <div class="actions"><button class="btn" data-close>关闭</button></div>`);
  const bind = (k, fn) => { const el = $(`[data-ra="${k}"]`); if (el) el.onclick = () => { closeModal(); fn(); }; };
  bind('topo', () => { location.hash = '#/topology/' + enc(name); });
  bind('tags', () => openTagsModal(name));
  bind('migrate', () => openMigrateModal(name));
  bind('del', () => deleteLib(name));
}

// 编辑某库的来源标签（主软件/被动依赖，可同时勾选）
function openTagsModal(name) {
  const lib = libsCache.find((l) => l.name === name);
  const cur = new Set((lib && lib.tags) || []);
  showModal(`<h2>来源标签 · ${esc(name)}</h2>
    <p class="hint">主软件＝主动分析的目标软件；被动依赖＝作为依赖被引入。可同时勾选。</p>
    <label><input type="checkbox" id="tgPrimary" ${cur.has('primary') ? 'checked' : ''} /> 主软件</label>
    <label><input type="checkbox" id="tgPassive" ${cur.has('passive') ? 'checked' : ''} /> 被动依赖</label>
    <div class="actions"><button class="btn" data-close>取消</button>
      <button class="btn primary" id="tgSave">保存</button></div>`);
  $('#tgSave').onclick = async () => {
    const tags = [];
    if ($('#tgPrimary').checked) tags.push('primary');
    if ($('#tgPassive').checked) tags.push('passive');
    try { await api('/api/library-tags', { method: 'POST', headers: JSONH, body: JSON.stringify(withGroup({ name, tags })) }); }
    catch { return toast('保存失败', 'err'); }
    closeModal(); toast('标签已更新', 'ok'); loadDash();
  };
}

function updateBatchBtn() {
  const byName = (n) => libsCache.find((x) => x.name === n);
  const analyzeN = [...selected].filter((n) => { const l = byName(n); return l && l.cloned; }).length;
  const cloneN = [...selected].filter((n) => { const l = byName(n); return l && !l.cloned && l.cloneUrl; }).length;
  const ba = $('#batchAnalyze');
  if (ba) { ba.disabled = analyzeN === 0; ba.textContent = analyzeN ? `分析选中 (${analyzeN})` : '分析选中'; }
  const bc = $('#batchClone');
  if (bc) { bc.disabled = cloneN === 0; bc.textContent = cloneN ? `克隆选中 (${cloneN})` : '克隆选中'; }
  const migrateN = [...selected].filter((n) => { const l = byName(n); return l && (l.cloned || l.cloneUrl); }).length;
  const bm = $('#batchMigrate');
  if (bm) { bm.disabled = migrateN === 0; bm.textContent = migrateN ? `迁移选中 (${migrateN})` : '迁移选中'; }
}

function renderJobsStrip(jobs) {
  const strip = $('#jobsStrip'); if (!strip) return;
  const active = jobs.filter((j) => j.status === 'running' || j.status === 'queued');
  if (!active.length) { strip.innerHTML = ''; return; }
  strip.innerHTML = `<div class="card"><div class="section-title">进行中的任务 (${active.length})</div>` +
    active.map((j) => {
      const el = j.startedAt ? fmtDuration(Date.now() - Date.parse(j.startedAt)) : '';
      return `<div class="jobline">
      <span class="spin"></span>
      <span class="jname">${esc(j.name)}</span>
      <span class="badge ${j.status}">${j.type === 'clone' ? '克隆' : '分析'} · ${statusZh(j.status)}</span>
      ${el ? `<span class="muted" title="已运行时长">⏱ ${el}</span>` : ''}
      <span class="spacer"></span>
      <a href="#/lib/${enc(j.name)}">查看 →</a></div>`; }).join('') + '</div>';
}

async function analyzeOne(name) {
  const r = await api('/api/analyze', { method: 'POST', headers: JSONH, body: JSON.stringify(withGroup({ name })) });
  if (r.jobs && r.jobs[0] && r.jobs[0].jobId) location.hash = '#/lib/' + enc(name);
  else toast((r.jobs && r.jobs[0] && r.jobs[0].error) || '启动失败', 'err');
}

async function deleteLib(name) {
  if (!confirm(`确认彻底删除「${name}」？\n将删除其克隆代码、全部分析记录与来源标签，不可恢复。`)) return;
  let r;
  try { r = await api('/api/library/delete', { method: 'POST', headers: JSONH, body: JSON.stringify(withGroup({ name })) }); }
  catch { return toast('删除失败', 'err'); }
  if (r && r.error) return toast(r.error, 'err');
  selected.delete(name);            // 清掉批量选择残留
  toast('已删除', 'ok');
  loadDash();
}

async function openMigrateModal(name) {
  let groups;
  try { ({ groups } = await api('/api/groups')); }
  catch { return toast('获取分组列表失败', 'err'); }
  const targets = groups.filter((g) => g !== activeGroup);
  showModal(`<h2>迁移库「${esc(name)}」</h2>
    <p class="hint">将此库的克隆代码、全部分析记录和标签迁移到另一个分组。</p>
    <label style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
      <span style="width:80px;text-align:right">当前分组</span>
      <span class="chip">${esc(activeGroup)}</span>
    </label>
    <label style="display:flex;align-items:center;gap:8px;margin-bottom:16px">
      <span style="width:80px;text-align:right">目标分组</span>
      ${targets.length
        ? `<select id="mgTarget" class="sel">${targets.map((g) => `<option value="${esc(g)}">${esc(g)}</option>`).join('')}</select>`
        : `<span class="hint">暂无其他分组，请先创建分组</span>`}
    </label>
    <div class="actions">
      <button class="btn" data-close>取消</button>
      <button class="btn primary" id="mgConfirm" ${targets.length ? '' : 'disabled'}>确认迁移</button>
    </div>`);
  if (!targets.length) return;
  $('#mgConfirm').onclick = async () => {
    const toGroup = $('#mgTarget').value;
    let r;
    try { r = await api('/api/library/migrate', { method: 'POST', headers: JSONH, body: JSON.stringify({ name, fromGroup: activeGroup, toGroup }) }); }
    catch { return toast('迁移失败', 'err'); }
    if (r && r.error) return toast(r.error, 'err');
    const res0 = r && r.results && r.results[0];       // 单库结果在 results[0]
    if (res0 && res0.error) return toast(res0.error, 'err');
    closeModal();
    toast(`已迁移到分组「${toGroup}」`, 'ok');
    loadDash();
  };
}

// 批量迁移选中的库到另一个分组（复用 /api/library/migrate 的 names[] 批量）。
async function openBatchMigrateModal() {
  const names = [...selected].filter((n) => { const l = libsCache.find((x) => x.name === n); return l && (l.cloned || l.cloneUrl); });
  if (!names.length) return toast('请先勾选要迁移的库', 'err');
  let groups;
  try { ({ groups } = await api('/api/groups')); }
  catch { return toast('获取分组列表失败', 'err'); }
  const targets = groups.filter((g) => g !== activeGroup);
  showModal(`<h2>批量迁移 ${names.length} 个库</h2>
    <p class="hint">将选中库的克隆代码、全部分析记录和标签迁移到另一个分组。目标分组已存在同名库的会跳过。</p>
    <div class="lsub" style="max-height:120px;overflow:auto;margin-bottom:12px">${names.map((n) => esc(n)).join('、')}</div>
    <label style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
      <span style="width:80px;text-align:right">当前分组</span>
      <span class="chip">${esc(activeGroup)}</span>
    </label>
    <label style="display:flex;align-items:center;gap:8px;margin-bottom:16px">
      <span style="width:80px;text-align:right">目标分组</span>
      ${targets.length
        ? `<select id="mgTarget" class="sel">${targets.map((g) => `<option value="${esc(g)}">${esc(g)}</option>`).join('')}</select>`
        : `<span class="hint">暂无其他分组，请先创建分组</span>`}
    </label>
    <div class="actions">
      <button class="btn" data-close>取消</button>
      <button class="btn primary" id="mgConfirm" ${targets.length ? '' : 'disabled'}>确认迁移</button>
    </div>`);
  if (!targets.length) return;
  $('#mgConfirm').onclick = async () => {
    const toGroup = $('#mgTarget').value;
    let r;
    try { r = await api('/api/library/migrate', { method: 'POST', headers: JSONH, body: JSON.stringify({ names, fromGroup: activeGroup, toGroup }) }); }
    catch { return toast('迁移失败', 'err'); }
    if (r && r.error) return toast(r.error, 'err');
    const results = (r && r.results) || [];
    const okNames = results.filter((x) => x.ok).map((x) => x.name);
    const failN = results.length - okNames.length;
    okNames.forEach((n) => selected.delete(n));         // 成功的移出选择集
    closeModal();
    toast(`迁移到「${toGroup}」：${okNames.length} 成功${failN ? ` · ${failN} 失败` : ''}`, failN ? 'err' : 'ok');
    loadDash();
  };
}

// ===========================================================================
//  PENDING DEPENDENCIES (level 1.5) — 未分析的「三方库依赖的三方库」
// ===========================================================================
let pdepCloneableOnly = false;
let pdepHideAdapted = false;        // 只看未鸿蒙化
let pdepMustPort = false;           // 只看必须鸿蒙化（运行时·非本地；排除 test/dev/build + 本地）
const PDEP_TOOLING = new Set(['test', 'dev', 'build']);
// A dep "must be ported" if it's a real runtime/optional dep that isn't already local
// (vendored/in-tree) and isn't purely tooling (test/dev/build — not shipped).
function pdepIsMustPort(it) {
  if (it.locality === 'local') return false;
  const sc = (it.scopes || []).filter(Boolean);
  if (sc.length && sc.every((s) => PDEP_TOOLING.has(String(s).toLowerCase()))) return false;
  return true;
}
const pdepUrlEdits = {};            // key -> user-typed URL (survives polling re-render)
const pdepResolved = {};            // key -> last resolve result (re-applied after re-render)
let pdepItems = [];                 // last-rendered items (for 一键填充全部)
let pdepHlKey = null;               // active tag-highlight key (survives polling re-render)
// Click a tag on a pending-dep row → highlight all rows with the same tag (like the
// report dep-tree). Delegated on #pdeps; re-applied after each 4s poll re-render.
function pdepHighlightHandler(e) {
  const scope = $('#pdeps'); if (!scope) return;
  const b = e.target.closest('[data-hl]');
  if (!b) { if (pdepHlKey) { pdepHlKey = null; applyTagHighlight(scope, null, '.pdep-row'); } return; }
  e.preventDefault();
  pdepHlKey = (pdepHlKey === b.dataset.hl) ? null : b.dataset.hl;
  applyTagHighlight(scope, pdepHlKey, '.pdep-row');
}
const pdepKey = (it) => `${it.ecosystem || ''}|${it.name}`;

// Write a resolved URL into a row's input + pdepUrlEdits (survives polling re-render).
function fillRowUrl(key, url) {
  pdepUrlEdits[key] = url;
  const inp = $(`input.pdep-url[data-key="${cssAttr(key)}"]`);
  if (inp) inp.value = url;
}
// Render a per-row candidate picker for interface / multi-implementation results.
// Candidates may be {name,url} (curated) or bare url strings (github search).
function renderDepCandidates(btn, key, r) {
  const row = btn.closest('.pdep-row'); if (!row) return;
  const info = row.querySelector('.pdep-info'); if (!info) return;
  let box = info.querySelector('.pdep-cands');
  const cands = (r && r.candidates) || [];
  const detail = r && (r.note || r.reasoning);
  const show = r && (r.interface || r.is_system || cands.length > 1 || detail);
  if (!show) { if (box) box.remove(); return; }
  if (!box) { box = document.createElement('div'); box.className = 'pdep-cands'; info.appendChild(box); }
  const norm = cands.map((c) => (typeof c === 'string') ? { url: c, name: c } : c).filter((c) => c && c.url);
  const conf = r.confidence ? `<span class="muted">置信度 ${esc(r.confidence)}</span> ` : '';
  const tag = r.is_system ? '<span class="badge gray">系统/平台库 · 无独立仓</span>'
    : r.interface ? '<span class="badge gray">接口/多实现</span>'
    : (cands.length > 1 ? '<span class="muted">多个候选</span>' : '');
  const chosen = pdepUrlEdits[key];   // re-highlight the chip matching the filled URL
  box.innerHTML = `${tag} ${conf}` + (detail ? `<span class="muted">${esc(r.reasoning || r.note)}</span>` : '')
    + (norm.length ? '<br>' + norm.map((c) =>
        `<button class="pdep-cand${c.url === chosen ? ' sel' : ''}" data-url="${esc(c.url)}">${esc(c.name || c.url)}</button>`).join('')
      : (r.is_system ? '' : ' <span class="muted">（无可克隆候选，请手动填写）</span>'));
  box.querySelectorAll('.pdep-cand').forEach((b) => b.onclick = () => {
    fillRowUrl(key, b.dataset.url);
    box.querySelectorAll('.pdep-cand').forEach((x) => x.classList.remove('sel'));
    b.classList.add('sel');
  });
}
// Resolve one dep's repo online. Returns the full result {url, interface, candidates,
// note, ...} or null. Auto-fills the input ONLY for a single concrete repo — interface
// packages (BLAS…) or multi-candidate results are left for the user to pick.
async function resolveDepUrl(eco, name, key, btn) {
  if (btn) { btn.disabled = true; btn.textContent = '…'; }
  let r;
  try { r = await api(`/api/resolve-repo?ecosystem=${enc(eco || '')}&name=${enc(name)}`); }
  catch { r = null; }
  if (btn) { btn.disabled = false; btn.textContent = '🔎'; }
  if (r && r.disabled) { toast('联网解析已在设置中关闭', 'err'); return r; }
  const cands = (r && r.candidates) || [];
  if (r && r.url && !r.interface && cands.length <= 1) fillRowUrl(key, r.url);
  return r;
}

const pdepItemByKey = (key) => (pdepItems || []).find((it) => pdepKey(it) === key);
// 🤖 agent resolve: read the dep's description/context + search, judge the repo (or that
// it's a system/platform lib). Spawns a server-side opencode job; poll until done.
async function runAgentResolve(key, btn) {
  const it = pdepItemByKey(key); if (!it) return;
  const orig = btn ? btn.textContent : '';
  if (btn) { btn.disabled = true; btn.textContent = '🤖…'; }
  const restore = () => { if (btn) { btn.disabled = false; btn.textContent = orig || '🤖'; } };
  const dependents = [...new Set((it.dependents || []).map((d) => d.lib))];
  const purpose = (it.dependents || []).map((d) => d.purpose).find(Boolean) || '';
  let start;
  try {
    start = await api('/api/resolve-repo-agent', { method: 'POST', headers: JSONH, body: JSON.stringify(withGroup({
      ecosystem: it.ecosystem, name: it.name, scope: (it.scopes || []).join(','),
      locality: it.locality, acquisition: it.acquisition, source: it.source, purpose, dependents })) });
  } catch { restore(); return toast('智能解析请求失败', 'err'); }
  if (start && start.disabled) { restore(); return toast('智能解析已在设置中关闭', 'err'); }
  if (!start || !start.jobId) { restore(); return toast((start && start.error) || '智能解析启动失败', 'err'); }
  // poll for completion (LLM job: up to ~3min)
  for (let i = 0; i < 90; i++) {
    await new Promise((res) => setTimeout(res, 2000));
    let s;
    try { s = await api('/api/resolve-repo-agent?job=' + enc(start.jobId)); } catch { continue; }
    if (s.status === 'error') { restore(); return toast('智能解析失败', 'err'); }
    if (s.status === 'done') {
      restore();
      const r = s.result || {};
      pdepResolved[key] = r;
      const b = $(`[data-pdep-agent="${cssAttr(key)}"]`) || btn;
      if (b) renderDepCandidates(b, key, r);
      if (r.is_system) toast(`「${it.name}」判为系统/平台库，无独立仓`, 'ok');
      else if (r.url) { fillRowUrl(key, r.url); toast(`已填充：${r.url}`, 'ok'); }
      else if ((r.candidates || []).length) toast('给出候选，请选择', 'ok');
      else toast(r.reasoning || '未能确定仓库地址', 'err');
      return;
    }
  }
  restore(); toast('智能解析超时，请稍后重试', 'err');
}

async function renderPendingDeps() {
  setHeader('<a class="btn ghost" href="#/">← 返回库列表</a>');
  $('#app').innerHTML = `<div class="detail-head"><h1>📦 待分析依赖库</h1></div>
    <p class="muted">已分析项目所依赖、但自身尚未被分析的第三方库，跨所有项目聚合。把某个依赖「加入分析列表」即克隆入库；克隆完成后就地点「分析」。分析完成后它会自动从此列表消失。</p>
    <div class="toolbar">
      <label class="pdep-toggle"><input type="checkbox" id="pdepCloneable" ${pdepCloneableOnly ? 'checked' : ''} /> 只看可克隆（有候选仓库 URL / 远端来源）</label>
      <label class="pdep-toggle"><input type="checkbox" id="pdepHideAdapted" ${pdepHideAdapted ? 'checked' : ''} /> 只看未鸿蒙化</label>
      <label class="pdep-toggle"><input type="checkbox" id="pdepMustPort" ${pdepMustPort ? 'checked' : ''} /> 只看必须鸿蒙化（排除 test/dev/build 与本地依赖）</label>
      <span id="pdepHarmonySummary" class="muted"></span>
      <button class="btn sm" id="pdepResolveAll">🔎 一键填充全部</button>
      <button class="btn sm" id="pdepRefresh">刷新</button>
    </div>
    <div id="pdeps"><p class="muted">加载中…</p></div>`;
  $('#pdepCloneable').onchange = (e) => { pdepCloneableOnly = e.target.checked; loadPendingDeps(); };
  $('#pdepHideAdapted').onchange = (e) => { pdepHideAdapted = e.target.checked; loadPendingDeps(); };
  $('#pdepMustPort').onchange = (e) => { pdepMustPort = e.target.checked; loadPendingDeps(); };
  $('#pdepResolveAll').onclick = resolveAllPendingDeps;
  $('#pdepRefresh').onclick = loadPendingDeps;
  pdepHlKey = null;
  $('#pdeps').onclick = pdepHighlightHandler;   // delegated tag click-to-highlight (survives poll re-render)
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
  try { [data, { libraries: libs }] = await Promise.all([api('/api/pending-deps?' + gq()), api('/api/libraries?' + gq())]); }
  catch { box.innerHTML = '<div class="hint err">加载失败</div>'; return; }
  const libMap = {};
  (libs || []).forEach((l) => { libMap[l.name] = l; });
  let items = data.items || [];
  if (pdepCloneableOnly) items = items.filter((it) => it.candidateUrl || it.locality === 'remote');
  if (pdepMustPort) items = items.filter(pdepIsMustPort);
  pdepItems = items;
  if (!items.length) {
    const filtered = pdepCloneableOnly || pdepMustPort;
    box.innerHTML = `<div class="empty">${filtered ? '没有符合筛选条件的待分析依赖。' : '暂无待分析依赖。分析更多库后，它们的依赖会出现在这里。'}</div>`;
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
    const key = b.dataset.pdepResolve;
    const r = await resolveDepUrl(b.dataset.eco, b.dataset.name, key, b);
    if (r && r.disabled) return;
    pdepResolved[key] = r;            // persist so the 4s poll re-render can re-apply
    const cands = (r && r.candidates) || [];
    const multi = r && (r.interface || cands.length > 1);
    renderDepCandidates(b, key, r);   // clears or fills the per-row picker
    if (multi) {
      toast(r.interface ? `「${b.dataset.name}」是接口/多实现，请从候选中选择` : '有多个候选仓库，请选择', 'ok');
    } else if (r && r.url) {
      toast(`已填充：${r.url}` + (r.note ? `（${r.note}）` : ''), 'ok');
    } else {
      toast((r && r.note) ? r.note : '未找到仓库地址，请手动填写', 'err');
    }
  });
  $$('[data-pdep-agent]', box).forEach((b) => b.onclick = () => runAgentResolve(b.dataset.pdepAgent, b));
  $$('input.pdep-url', box).forEach((inp) => inp.oninput = () => { pdepUrlEdits[inp.dataset.key] = inp.value; });
  // Re-apply candidate pickers wiped by this re-render (the 4s poll rebuilds innerHTML).
  $$('[data-pdep-resolve]', box).forEach((b) => {
    const r = pdepResolved[b.dataset.pdepResolve];
    if (r) renderDepCandidates(b, b.dataset.pdepResolve, r);
  });
  if (pdepHlKey) applyTagHighlight(box, pdepHlKey, '.pdep-row');   // re-apply tag highlight after re-render
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
      const r = await resolveDepUrl(it.ecosystem, it.name, pdepKey(it), null);
      if (r) pdepResolved[pdepKey(it)] = r;   // surface pickers on next render
      done++; if (r && r.url && !r.interface) hit++;
      if (btn) btn.textContent = `🔎 解析中 ${done}/${targets.length}`;
    }
  };
  await Promise.all(Array.from({ length: Math.min(4, targets.length) }, worker));
  if (btn) { btn.disabled = false; btn.textContent = '🔎 一键填充全部'; }
  // refresh once so candidate pickers (interface/multi) render for batch results.
  loadPendingDeps();
  toast(`已解析 ${hit}/${targets.length} 个仓库地址`, hit ? 'ok' : 'err');
}

function pdepRowHtml(it, libMap) {
  const key = pdepKey(it);
  const eco = it.ecosystem ? `<span class="chip eco-chip" data-hl="eco:${esc(it.ecosystem)}">${esc(ECO_LABELS[it.ecosystem] || it.ecosystem)}</span>` : '';
  const loc = it.locality ? `<span class="badge ${LOCALITY_CLS[it.locality] || 'gray'}" data-hl="loc:${esc(it.locality)}">${LOCALITY_LABELS[it.locality] || it.locality}</span>` : '';
  const scopes = (it.scopes || []).filter((s) => s && s !== 'runtime').map((s) => `<span class="tag" data-hl="scope:${esc(s)}">${esc(s)}</span>`).join('');
  const acq = it.acquisition ? `<span class="tag acq" data-hl="acq:${esc(it.acquisition)}">${esc(ACQ_LABELS[it.acquisition] || it.acquisition)}</span>` : '';
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
    const agentBtn = ['cpp', 'c'].includes(String(it.ecosystem || '').toLowerCase())
      ? `<button class="btn sm" data-pdep-agent="${esc(key)}" title="用 agent 读描述+检索判断仓库地址（较慢）">🤖</button>` : '';
    action = `<input class="pdep-url" type="text" data-key="${esc(key)}" value="${esc(url)}" placeholder="Git URL" />
      <button class="btn sm" data-pdep-resolve="${esc(key)}" data-eco="${esc(it.ecosystem || '')}" data-name="${esc(it.name)}" title="联网查询仓库地址">🔎</button>
      ${agentBtn}
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
  try { r = await api('/api/clone', { method: 'POST', headers: JSONH, body: JSON.stringify(withGroup({ urls: [url], tag: 'passive' })) }); }
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
  const names = [...selected].filter((n) => { const l = libsCache.find((x) => x.name === n); return l && l.cloned; });
  if (!names.length) return;
  const r = await api('/api/analyze', { method: 'POST', headers: JSONH, body: JSON.stringify(withGroup({ names })) });
  const ok = (r.jobs || []).filter((j) => j.jobId);
  const err = (r.jobs || []).filter((j) => j.error);
  toast(`已提交 ${ok.length} 个分析任务` + (err.length ? `，${err.length} 个失败` : ''), err.length ? 'err' : 'ok');
  names.forEach((n) => selected.delete(n));
  loadDash();
}

// 批量重新克隆选中的「有报告但源码仓已删」的库（cloneUrl 由后端从报告 library.source_url 恢复）。
async function batchClone() {
  const names = [...selected].filter((n) => {
    const l = libsCache.find((x) => x.name === n);
    return l && !l.cloned && l.cloneUrl;
  });
  if (!names.length) return;
  const r = await api('/api/reclone', { method: 'POST', headers: JSONH, body: JSON.stringify(withGroup({ names })) });
  const ok = (r.jobs || []).filter((j) => j.jobId);
  const err = (r.jobs || []).filter((j) => j.error);
  toast(`已开始克隆 ${ok.length} 个库` + (err.length ? `，${err.length} 个失败` : ''), err.length ? 'err' : 'ok');
  err.forEach((e) => toast(`${e.name}：${e.error}`, 'err'));
  names.forEach((n) => selected.delete(n));
  loadDash();
}

async function recloneOne(name) {
  const r = await api('/api/reclone', { method: 'POST', headers: JSONH, body: JSON.stringify(withGroup({ names: [name] })) });
  const j = (r.jobs || [])[0];
  if (j && j.jobId) { selected.delete(name); toast(`已开始克隆 ${name}`, 'ok'); loadDash(); }
  else toast((j && j.error) || '克隆失败', 'err');
}

// ---- clone modal ----------------------------------------------------------
async function openCloneModal() {
  let groups = [activeGroup];
  try { groups = (await api('/api/groups')).groups || groups; } catch (_) {}
  showModal(`<h2>克隆库</h2>
    <label>Git 仓库地址（每行一个，支持批量并发克隆）
      <textarea id="mUrls" rows="5" placeholder="https://github.com/owner/lib.git
https://github.com/chromium/chromium/tree/main/components/cronet"></textarea></label>
    <p class="hint">支持 monorepo 子目录：粘贴 <code>…/tree/&lt;分支&gt;/&lt;子目录&gt;</code> 形式的地址即可，每行自动解析出子目录并只稀疏克隆该子树。</p>
    <div class="row">
      <label class="grow">分支 / Tag（可选，应用于全部）<input id="mRef" type="text" placeholder="main / v1.2.0" /></label>
      <label class="grow">来源标签<select id="mTag"><option value="primary">主软件</option><option value="passive">被动依赖</option></select></label>
    </div>
    <div class="row">
      <label class="grow">子目录（可选，仅单条 URL 时生效；分支名带斜杠时用它指定）<input id="mSubpath" type="text" placeholder="components/cronet" /></label>
    </div>
    <div class="row">
      <label class="grow">分组<select id="mGroup">${groups.map((g) => `<option value="${esc(g)}" ${g === activeGroup ? 'selected' : ''}>${esc(g)}</option>`).join('')}</select></label>
      <label style="white-space:nowrap"><input id="mOver" type="checkbox" /> 覆盖已存在</label>
    </div>
    <div class="actions"><button class="btn" data-close>取消</button>
      <button class="btn primary" id="mGo">开始克隆</button></div>`);
  $('#mGo').onclick = async () => {
    const urls = $('#mUrls').value.split('\n').map((s) => s.trim()).filter(Boolean);
    if (!urls.length) return toast('请输入至少一个 Git URL', 'err');
    const subpath = $('#mSubpath').value.trim();
    if (subpath && urls.length > 1) return toast('「子目录」仅在单条 URL 时生效，请只填一个地址', 'err');
    const r = await api('/api/clone', { method: 'POST', headers: JSONH, body: JSON.stringify({
      urls, ref: $('#mRef').value.trim() || undefined, overwrite: $('#mOver').checked,
      subpath: subpath || undefined, tag: $('#mTag').value, group: $('#mGroup').value }) });
    // 克隆到非活动分组时切过去，便于查看
    if ($('#mGroup').value && $('#mGroup').value !== activeGroup) {
      activeGroup = $('#mGroup').value; localStorage.setItem('activeGroup', activeGroup);
    }
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
  const { settings: s, defaults: d, codegraphAvailable: cg } = await api('/api/settings');
  showModal(`<h2>系统设置</h2>
    <label>默认模型 Model
      <div class="row"><input id="sModel" class="grow" type="text" list="modelList" value="${esc(s.model)}" placeholder="provider/model（留空用 opencode 默认）" />
        <datalist id="modelList"></datalist>
        <button class="btn sm" id="sTest">Test</button></div>
      <div id="sTestR" class="hint"></div></label>
    <label>opencode 命令 <input id="sCmd" type="text" value="${esc(s.opencodeCmd)}" /></label>
    <label>最大并发分析数 <input id="sConc" type="number" min="1" max="10" value="${s.maxConcurrent}" /></label>
    <label>最大并发克隆数 <input id="sConcClone" type="number" min="1" max="10" value="${s.maxConcurrentClone}" /></label>
    <div class="row" style="gap:10px">
      <label style="flex:1;margin:0">重编速率 行/天 <input id="sRecRate" type="number" min="1" step="100" value="${s.recompileLocPerDay}" />
        <span class="hint" style="display:block">工作量分项「重编/交叉编译」= 代码分区 recompile_reuse 桶 LOC ÷ 此值</span></label>
      <label style="flex:1;margin:0">适配速率 行/天 <input id="sAdpRate" type="number" min="1" step="50" value="${s.adaptationLocPerDay}" />
        <span class="hint" style="display:block">「平台 API 适配」= needs_adaptation 桶 LOC ÷ 此值；改后对新分析生效，存量需重跑 migrate</span></label>
    </div>
    <label><input id="sLogs" type="checkbox" ${s.printLogs ? 'checked' : ''} /> 记录 opencode 调试日志（--print-logs）</label>
    <label><input id="sCodegraph" type="checkbox" ${s.useCodegraph ? 'checked' : ''} ${cg ? '' : 'disabled'} /> 启用 codegraph 结构化分析${cg ? '' : '<span class="hint err" style="display:inline"> — 未检测到 codegraph，将回退 grep</span>'}</label>
    <label><input id="sPruneGit" type="checkbox" ${s.pruneGitAfterAnalyze ? 'checked' : ''} /> 分析完成后删除 repos/&lt;库&gt;/.git 省磁盘 <span class="hint" style="display:inline">（重新分析将读不到 commit）</span></label>
    <label><input id="sNetResolve" type="checkbox" ${s.enableNetworkResolve ? 'checked' : ''} /> 待分析依赖页允许联网解析仓库地址 <span class="hint" style="display:inline">（PyPI/npm/crates/Maven，C/C++ 走 GitHub 搜索）</span></label>
    <label><input id="sHarmonyMirror" type="checkbox" ${s.enableHarmonyMirror ? 'checked' : ''} /> 联网检测依赖是否已鸿蒙化 <span class="hint" style="display:inline">（OpenHarmony PC 镜像，有 ohos wheel 即已移植）</span></label>
    <label><input id="sAgentResolve" type="checkbox" ${s.enableAgentResolve ? 'checked' : ''} /> 待分析依赖页 C/C++ 「🤖 智能解析」 <span class="hint" style="display:inline">（用 LLM agent 读描述+检索判断仓库地址，较慢/耗模型额度）</span></label>
    <label><input id="sRecursive" type="checkbox" ${s.recursiveAfterAnalyze ? 'checked' : ''} /> 分析完成后自动递归分析其依赖 <span class="hint" style="display:inline">（克隆并分析运行时依赖，系统库作叶子不下钻）</span></label>
    <details><summary class="hint" style="cursor:pointer">Prompt 模板（高级）</summary>
      <div class="row" style="justify-content:flex-end"><button class="btn sm" id="sPromptReset">恢复默认</button></div>
      <textarea id="sPrompt" rows="9">${esc(s.promptTemplate)}</textarea>
      <p class="hint">占位符：{repoPath} {agentFile} {reportPath} {metricsPath} {name} {codegraphHint}</p></details>
    <div class="actions"><button class="btn" data-close>取消</button>
      <button class="btn primary" id="sSave">保存</button></div>`);
  loadModelsInto('#modelList');
  $('#sTest').onclick = async () => {
    const span = $('#sTestR'); span.className = 'hint'; span.textContent = '测试中…';
    const r = await api('/api/testmodel?model=' + enc($('#sModel').value.trim()));
    span.className = 'hint ' + (r.ok ? 'ok' : 'err');
    span.textContent = r.ok ? `✅ 可用 (${r.ms}ms) · ${r.output}` : `❌ ${r.error}`;
  };
  $('#sPromptReset').onclick = () => { $('#sPrompt').value = d.promptTemplate; toast('已恢复默认 Prompt（记得点保存）'); };
  $('#sSave').onclick = async () => {
    await api('/api/settings', { method: 'POST', headers: JSONH, body: JSON.stringify({
      model: $('#sModel').value.trim(), opencodeCmd: $('#sCmd').value.trim(),
      maxConcurrent: Number($('#sConc').value) || 3,
      maxConcurrentClone: Number($('#sConcClone').value) || 3, printLogs: $('#sLogs').checked,
      useCodegraph: $('#sCodegraph').checked, pruneGitAfterAnalyze: $('#sPruneGit').checked,
      enableNetworkResolve: $('#sNetResolve').checked, enableHarmonyMirror: $('#sHarmonyMirror').checked,
      enableAgentResolve: $('#sAgentResolve').checked,
      recursiveAfterAnalyze: $('#sRecursive').checked,
      recompileLocPerDay: Number($('#sRecRate').value) || 3000,
      adaptationLocPerDay: Number($('#sAdpRate').value) || 500,
      promptTemplate: $('#sPrompt').value }) });
    closeModal(); toast('设置已保存', 'ok');
  };
}

// ===========================================================================
//  OBSERVATIONS (skill 反哺)
// ===========================================================================
const OBS_KIND_LABELS = { new_value: '新造值', gap: '盲区', ambiguity: '歧义', caps_gap: '目标能力缺口' };
const OBS_KIND_CLS = { new_value: 'done', gap: 'running', ambiguity: 'queued', caps_gap: 'queued' };
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
        <td class="muted">${esc(it.rationale || '')}${it.kind === 'caps_gap' ? ` <button class="btn sm ghost obs-cap-add" data-cap="${esc(it.value || '')}" data-sec="${esc(it.field || 'cli_tools')}">补进能力库</button>` : ''}</td></tr>`).join('')}</tbody></table>
    </div>`).join('');
  // caps_gap → 一键补进目标能力库（无绑定：跨库聚合项，登记后各库重分析或逐份「补充到能力库」绑定即刷新）
  $$('.obs-cap-add').forEach((b) => b.onclick = () => capAddModal(
    { capability: b.dataset.cap, sectionId: b.dataset.sec || 'cli_tools' }, null, () => renderObservations()));
}

// ===========================================================================
//  HARMONY PC TARGET CAPABILITIES (#/harmony-caps) — 目标能力画像策展
// ===========================================================================
const STALE_DAYS = 90;
function capStale(r) {
  if (!r.checked_at) return true;
  const t = Date.parse(r.checked_at);
  return isNaN(t) || (Date.now() - t) > STALE_DAYS * 86400 * 1000;
}
async function renderHarmonyCaps() {
  setHeader('<a class="btn ghost" href="#/">← 返回库列表</a>' +
    '<button class="btn ghost" id="capAdd">＋ 补充能力/缺口</button>' +
    '<button class="btn" id="capSync">🔄 联网同步(包清单)</button>');
  $('#app').innerHTML = `<div class="detail-head"><h1>🧭 鸿蒙 PC 目标能力画像</h1><span id="capSynced" class="muted"></span></div>
    <p class="muted">鸿蒙适配判定的<strong>目标侧事实源</strong>（库与应用通用）。带「检查源」的行可一键联网同步（复用 cmd-pkgs/PyPI）；其余需人工核实——把社区已确认的能力内联标记为已支持并填来源。<strong>「研究优先级」</strong>列＝该能力被多少个已分析报告的 <code>target_assumptions</code> 需要（未核实 + 高需求 = 优先核实）。<span class="hint" style="display:inline">未核实 / 过期(>${STALE_DAYS}天) 的行高亮。</span></p>
    <div id="caps"><p class="muted">加载中…</p></div>`;
  $('#capSync').onclick = async () => {
    const btn = $('#capSync'); btn.disabled = true; btn.textContent = '同步中…';
    try {
      const r = await api('/api/harmony-caps/sync', { method: 'POST', headers: JSONH, body: '{}' });
      if (r.disabled) toast('已关闭「联网检测已鸿蒙化」设置，无法同步', 'err');
      else { toast(`同步完成：核对 ${r.checked} 项，翻转 ${r.flipped} 项`, 'ok'); drawCaps(r.caps); }
    } catch { toast('同步失败', 'err'); }
    btn.disabled = false; btn.textContent = '🔄 联网同步(包清单)';
  };
  $('#capAdd').onclick = () => capAddModal({}, null, async () => {
    try { drawCaps(await api('/api/harmony-caps')); } catch { /* keep current view */ }
  });
  try { drawCaps(await api('/api/harmony-caps')); }
  catch { $('#caps').innerHTML = '<div class="hint err">加载失败</div>'; }
}
function drawCaps(data) {
  const synced = $('#capSynced'); if (synced) synced.textContent = data.synced_at ? `最近联网同步：${fmtTime(data.synced_at)}` : '尚未联网同步';
  const demand = data.demand || {};   // rowId -> {count, unknown, libs[]}（反哺：被 N 个分析需要）
  const demandCell = (id) => {
    const d = demand[id];
    if (!d || !d.count) return '<span class="muted">—</span>';
    const uk = d.unknown ? ` <span class="muted">(${d.unknown} 未核实)</span>` : '';
    return `<span class="badge ${d.unknown ? 'queued' : 'gray'}" title="${esc((d.libs || []).join('、'))}">被 ${d.count} 需要</span>${uk}`;
  };
  $('#caps').innerHTML = (data.sections || []).map((sec) => {
    // 高需求行在段内置顶（研究优先级）；其余保持原序
    const rows = (sec.rows || []).map((r, i) => [r, i]).sort((a, b) =>
      ((demand[b[0].id] && demand[b[0].id].count) || 0) - ((demand[a[0].id] && demand[a[0].id].count) || 0) || a[1] - b[1]);
    return `
    <div class="card" style="margin-bottom:12px">
      <div class="section-title">${esc(sec.title)}</div>
      <table class="obstable"><thead><tr><th>能力</th><th>状态</th><th>研究优先级</th><th>来源</th><th>核对时间</th><th>说明</th><th></th></tr></thead>
      <tbody>${rows.map(([r]) => {
    const st = r.status || 'unknown';
    const warn = (st === 'unknown' || capStale(r)) ? ' style="background:var(--warn-soft)"' : '';
    return `<tr data-id="${esc(r.id)}"${warn}>
        <td>${esc(r.capability)}${r.check ? ' <span class="chip" title="可联网同步">🔄</span>' : ''}</td>
        <td><span class="badge ${TGT_CLS[st] || 'gray'}">${TGT_LABELS[st] || esc(st)}</span></td>
        <td>${demandCell(r.id)}</td>
        <td class="muted">${esc(r.source || '')}</td>
        <td class="muted">${esc(r.checked_at || '—')}</td>
        <td class="muted">${esc(r.note || '')}</td>
        <td><button class="btn sm ghost cap-edit" data-id="${esc(r.id)}">编辑</button></td></tr>`;
  }).join('')}</tbody></table>
    </div>`;
  }).join('');
  $$('.cap-edit').forEach((b) => b.onclick = () => capEdit(b.dataset.id, data));
}
function capEdit(id, data, onSaved) {
  let row = null;
  for (const s of data.sections) { const r = (s.rows || []).find((x) => x.id === id); if (r) { row = r; break; } }
  if (!row) return;
  const opts = ['available', 'partial', 'unavailable', 'unknown']
    .map((v) => `<option value="${v}" ${row.status === v ? 'selected' : ''}>${TGT_LABELS[v]}</option>`).join('');
  showModal(`<h2>核实能力：${esc(row.capability)}</h2>
    <label>状态 <select id="capStatus">${opts}</select></label>
    <label>来源（社区链接 / 文档，建议填）<input id="capSource" type="text" value="${esc(row.source || '')}" placeholder="https://gitcode.com/OpenHarmonyPCDeveloper/..." /></label>
    <label>说明 <input id="capNote" type="text" value="${esc(row.note || '')}" /></label>
    <div class="actions"><button class="btn" data-close>取消</button>
      <button class="btn primary" id="capSave">保存（标记已核实）</button></div>`);
  $('#capSave').onclick = async () => {
    try {
      const r = await api('/api/harmony-caps/row', { method: 'POST', headers: JSONH, body: JSON.stringify({
        id, status: $('#capStatus').value, source: $('#capSource').value.trim(), note: $('#capNote').value.trim() }) });
      if (r.error) return toast(r.error, 'err');
      closeModal(); toast('已保存并标记已核实', 'ok');
      if (onSaved) onSaved(r); else drawCaps(r.caps);
    } catch { toast('保存失败', 'err'); }
  };
}

// Sections a promoted capability can land in (id → 中文 title). cli_tools first (the common
// shell-out/external-binary case). Used by capAddModal's section picker.
const CAP_SECTIONS = [
  ['cli_tools', '命令行工具 / 外部二进制'], ['runtimes', '语言运行时'], ['gui', '桌面 GUI'],
  ['graphics_3d', '3D 图形栈'], ['media', '媒体'], ['hardware_devices', '硬件设备'],
  ['process_security', '进程/安全模型'], ['desktop_integration', '桌面集成'],
  ['app_delivery', '应用交付'], ['jdk_internals', 'JDK 内部模块'], ['permissions', '权限模型'], ['arch', '架构'],
];
// Add/confirm a target-capability row (create the section if new). `bindCtx` (optional):
// {group,name,run,ta_id} binds the originating report's assumption to the new row so it refreshes
// on read (no re-analysis). `onSaved(resp)` fires after success.
function capAddModal(prefill, bindCtx, onSaved) {
  prefill = prefill || {};
  const guessId = (String(prefill.capability || '').match(/[A-Za-z0-9]+([._-][A-Za-z0-9]+)*/) || [''])[0].toLowerCase();
  const secId0 = prefill.sectionId || 'cli_tools';
  const secOpts = CAP_SECTIONS.map(([id, t]) => `<option value="${id}" ${id === secId0 ? 'selected' : ''}>${esc(t)} (${id})</option>`).join('');
  const stOpts = ['unavailable', 'available', 'partial', 'unknown']
    .map((v) => `<option value="${v}" ${v === (prefill.status || 'unavailable') ? 'selected' : ''}>${TGT_LABELS[v]}</option>`).join('');
  const willBind = bindCtx && bindCtx.ta_id && bindCtx.name && bindCtx.run;
  showModal(`<h2>补充到目标能力库</h2>
    <p class="muted">把该目标能力登记进 <code>harmony-pc-capabilities.json</code> 并核实其状态。${willBind ? '保存后本报告的该假设将绑定此能力行并<strong>立即刷新</strong>（无需重分析）。' : ''}</p>
    <label>所属段 <select id="capAddSec">${secOpts}</select></label>
    <label>能力名（展示）<input id="capAddCap" type="text" value="${esc(prefill.capability || '')}" /></label>
    <label>能力行 id（英文 slug，唯一）<input id="capAddId" type="text" value="${esc(guessId)}" placeholder="如 nmap / ffmpeg / libusb" /></label>
    <label>状态 <select id="capAddStatus">${stOpts}</select></label>
    <label>来源（核实依据，建议填）<input id="capAddSource" type="text" placeholder="社区链接 / 文档 / 人工核实说明" /></label>
    <label>说明 <input id="capAddNote" type="text" /></label>
    <div class="actions"><button class="btn" data-close>取消</button>
      <button class="btn primary" id="capAddSave">保存并确认</button></div>`);
  $('#capAddSave').onclick = async () => {
    const id = $('#capAddId').value.trim();
    if (!id) return toast('请填写能力行 id（英文 slug）', 'err');
    const secId = $('#capAddSec').value;
    const secTitle = (CAP_SECTIONS.find(([x]) => x === secId) || [])[1] || secId;
    const body = { sectionId: secId, sectionTitle: secTitle, id,
      capability: $('#capAddCap').value.trim() || id, status: $('#capAddStatus').value,
      source: $('#capAddSource').value.trim(), note: $('#capAddNote').value.trim() };
    if (willBind) body.bind = { group: bindCtx.group, name: bindCtx.name, run: bindCtx.run, ta_id: bindCtx.ta_id };
    try {
      const r = await api('/api/harmony-caps/add-row', { method: 'POST', headers: JSONH, body: JSON.stringify(body) });
      if (r.error) return toast(r.error, 'err');
      closeModal(); toast(r.bound ? '已补充能力并绑定，报告已刷新' : '已补充到能力库', 'ok');
      if (onSaved) onSaved(r);
    } catch { toast('保存失败', 'err'); }
  };
}

// ===========================================================================
//  DETAIL (level 2)
// ===========================================================================
let curReport = null;     // {name, run, obj}
let curRun = null;
let tocObserver = null;   // scroll-spy for the report anchor nav (disconnected on re-render / leave)

async function renderDetail(name) {
  if (tocObserver) { try { tocObserver.disconnect(); } catch (_) {} tocObserver = null; }
  setHeader('<a class="btn ghost" href="#/">← 返回库列表</a>');
  $('#app').innerHTML = `
    <div class="detail-head">
      <h1>${esc(name)}</h1>
      <span id="dStatus"></span>
      <span id="dElapsed" class="muted"></span>
      <label class="run-pick"><span class="muted">运行</span>
        <select id="runSelect" title="选择一次运行以查看报告"></select></label>
      <button class="btn sm ghost danger" id="runDel" title="删除当前选中的运行记录" disabled>🗑</button>
      <span class="spacer"></span>
      <button class="btn sm" id="dTest">Test 模型</button>
      <button class="btn sm" id="dRecurse">🌳 递归分析依赖</button>
      <button class="btn primary sm" id="dAnalyze">重新分析</button>
    </div>
    <details id="consoleWrap" class="card">
      <summary>实时 / 运行日志</summary>
      <div id="console" class="console"></div>
    </details>
    <nav id="reportNav" class="report-nav" hidden></nav>
    <div class="card report-card">
      <div class="row" style="justify-content:space-between;margin-bottom:10px">
        <div class="section-title" style="margin:0">分析报告</div>
        <div class="row" style="gap:6px">
          <button class="btn sm ghost" id="rawBtn" disabled>原始 JSON</button>
          <button class="btn sm ghost" id="htmlBtn" disabled>导出 HTML</button>
          <button class="btn sm ghost" id="dlBtn" disabled>下载</button></div>
      </div>
      <div id="report"><p class="muted">选择一次运行以查看报告。</p></div>
      <pre id="rawJson" class="raw hidden"></pre>
    </div>`;

  $('#runSelect').onchange = (e) => { if (e.target.value) loadRun(name, e.target.value); };
  $('#runDel').onclick = () => { const run = $('#runSelect').value; if (run) deleteRun(name, run); };

  $('#dTest').onclick = async () => {
    toast('正在测试默认模型…');
    const r = await api('/api/testmodel?model=');
    toast(r.ok ? `模型可用 (${r.ms}ms)` : `模型不可用：${r.error}`, r.ok ? 'ok' : 'err');
  };
  $('#dAnalyze').onclick = () => reAnalyze(name);
  $('#dRecurse').onclick = () => { location.hash = '#/recursive/' + enc(name); };
  $('#rawBtn').onclick = () => { $('#rawJson').classList.toggle('hidden'); $('#report').classList.toggle('hidden'); };
  $('#htmlBtn').onclick = exportReportHtml;
  $('#dlBtn').onclick = downloadReport;

  await loadDetail(name);
}

function setDStatus(status) {
  const el = $('#dStatus'); if (el) el.innerHTML = status ? `<span class="badge ${status}">${statusZh(status)}</span>` : '';
}

async function loadDetail(name) {
  const d = await api('/api/library?name=' + enc(name) + '&' + gq());
  if (d.error) { const s = $('#runSelect'); if (s) s.innerHTML = `<option>${esc(d.error)}</option>`; return; }
  renderRuns(name, d.runs, d.active);
  const cw = $('#consoleWrap'); if (cw) cw.open = !!d.active;   // 展开日志仅当有正在进行的分析
  if (d.active) {
    setDStatus(d.active.status);
    subscribe(d.active.id, name, () => loadDetail(name), d.active.startedAt);   // live, reload on end
  } else {
    const latest = d.runs[0];
    setDStatus(latest ? latest.status : '');
    const de = $('#dElapsed');                         // 非进行中：显示最近一次耗时（若有）
    if (de) { const dur = runDuration(latest); de.textContent = dur ? `⏱ 耗时 ${dur}` : ''; }
    if (latest) loadRun(name, latest.run);
  }
}

// Run history as a header dropdown (was a left-column list). Options: 状态 · 时间 · 📄;
// an in-progress run (active, not yet in `runs`) is prepended. 🗑 deletes the selected run.
function renderRuns(name, runs, active) {
  const sel = $('#runSelect'), del = $('#runDel');
  if (!sel) return;
  const opts = [];
  // A running/queued job usually already appears in `runs` (its run dir + meta exist). If not yet,
  // show an inert placeholder (value="" → onchange no-op) so the in-progress state is visible.
  const hasLiveRow = runs.some((r) => r.status === 'running' || r.status === 'queued');
  if (active && !hasLiveRow) opts.push('<option value="">▶ 分析中…</option>');
  for (const r of runs) {
    const dur = runDuration(r);
    const lbl = `${statusZh(r.status)} · ${fmtTime(r.startedAt)}${dur ? ' · ⏱ ' + dur : ''}${r.reportAvailable ? ' · 📄' : ''}`;
    opts.push(`<option value="${esc(r.run)}"${r.run === curRun ? ' selected' : ''}>${esc(lbl)}</option>`);
  }
  if (!opts.length) { sel.innerHTML = '<option value="">暂无运行记录</option>'; if (del) del.disabled = true; return; }
  sel.innerHTML = opts.join('');
  // default selection: current run if present, else the first option (latest / in-progress)
  if (curRun && runs.some((r) => r.run === curRun)) sel.value = curRun;
  if (del) del.disabled = !sel.value;
}

async function deleteRun(name, run) {
  if (!confirm(`确认删除该运行记录（${fmtTime(run)}）？\n将删除该次分析的报告与日志，不可恢复。`)) return;
  let r;
  try { r = await api('/api/run/delete', { method: 'POST', headers: JSONH, body: JSON.stringify(withGroup({ name, run })) }); }
  catch { return toast('删除失败', 'err'); }
  if (r && r.error) return toast(r.error, 'err');
  toast('已删除', 'ok');
  if (curRun === run) curRun = null;                    // 删的是当前查看那条 → 让 loadDetail 重选最新
  loadDetail(name);
}

async function reAnalyze(name) {
  const r = await api('/api/analyze', { method: 'POST', headers: JSONH, body: JSON.stringify(withGroup({ name })) });
  const job = r.jobs && r.jobs[0];
  if (!job || !job.jobId) return toast((job && job.error) || '启动失败', 'err');
  toast('已开始分析', 'ok');
  setDStatus(job.status);
  subscribe(job.jobId, name, () => loadDetail(name), Date.now());
  loadDetail(name);   // refresh run list to include the new run
}

// ---- SSE ------------------------------------------------------------------
function subscribe(jobId, name, onEnd, startedAt) {
  if (es) es.close();
  clearConsole();
  // 进行中实时计时：每秒刷新 #dElapsed（已运行时长），进程结束时定格为总耗时。
  const startMs = startedAt ? Date.parse(startedAt) : Date.now();
  const setElapsed = (txt) => { const de = $('#dElapsed'); if (de) de.textContent = txt; };
  const tick = () => setElapsed(`⏱ 已运行 ${fmtDuration(Date.now() - startMs)}`);
  tick();
  const elapsedTimer = setInterval(tick, 1000);
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
  const stopHb = () => { clearInterval(hbTimer); clearInterval(elapsedTimer); if (hbEl) { hbEl.remove(); hbEl = null; } };
  es = new EventSource('/api/stream?job=' + jobId);
  es.addEventListener('input', (e) => { bump(); const d = JSON.parse(e.data).data; metaLine('$ ' + (d.argv ? d.argv.join(' ') : '')); });
  es.addEventListener('status', (e) => { bump(); const d = JSON.parse(e.data).data; setDStatus(d.status); sysLine('状态：' + statusZh(d.status)); });
  es.addEventListener('log', (e) => { bump(); const { stream, text } = JSON.parse(e.data).data; renderLog(text, stream); });
  es.addEventListener('end', (e) => {
    stopHb();
    const d = JSON.parse(e.data).data;
    const total = fmtDuration(Date.now() - startMs);
    setElapsed(total ? `⏱ 总耗时 ${total}` : '');
    sysLine(`— 进程结束，退出码 ${d.code}（${statusZh(d.status)}）${total ? '，总耗时 ' + total : ''} —`);
    setDStatus(d.status);
    if (es) { es.close(); es = null; }
    if (onEnd) onEnd(d);
  });
  es.onerror = () => {};
  view.cleanup = () => { stopHb(); if (es) { es.close(); es = null; } };
}

// ===========================================================================
//  RECURSIVE DEPENDENCY ANALYSIS (session view)
// ===========================================================================
// per-decision state → {label, badge-class}. Leaves (system/prebuilt/interface)
// and no-source are intentionally NOT recursed into.
const RC_STATE = {
  pending: { t: '待处理', c: 'gray' }, resolving: { t: '解析地址中', c: 'queued' }, resolved: { t: '待克隆', c: 'queued' },
  cloning: { t: '克隆中', c: 'running' }, analyzing: { t: '分析中', c: 'running' }, analyzed: { t: '已分析', c: 'done' },
  leaf_system: { t: '系统库 (叶子)', c: 'queued' }, leaf_prebuilt: { t: '预编译 (叶子)', c: 'queued' },
  leaf_interface: { t: '接口/系统 (叶子)', c: 'queued' }, leaf_no_source: { t: '无源码 · 待人工', c: 'gray' },
  leaf_harmonized: { t: '已鸿蒙化 (叶子)', c: 'done' },
  ambiguous: { t: '歧义 · 待确认', c: 'gray' }, failed: { t: '失败', c: 'error' }, capped: { t: '超出上限', c: 'gray' },
};
const RC_SESSION_ZH = { running: '运行中', done: '完成', stopped: '已停止' };
const RC_SESSION_CLS = { running: 'running', done: 'done', stopped: 'queued' };

let rcSession = null, rcName = null;
const rcUrlEdits = {};   // key -> 已编辑/解析出的 git url（防 SSE 重渲染覆盖输入）
const RC_TERMINAL = new Set(['analyzed', 'leaf_system', 'leaf_prebuilt', 'leaf_interface',
  'leaf_no_source', 'leaf_harmonized', 'ambiguous', 'failed', 'capped']);

async function renderRecursive(name) {
  rcName = name; rcSession = null;
  for (const k in rcUrlEdits) delete rcUrlEdits[k];
  setHeader(`<a class="btn ghost" href="#/lib/${enc(name)}">← 返回 ${esc(name)}</a>` +
    `<a class="btn" href="#/topology/${enc(name)}">🕸 依赖拓扑</a>`);
  $('#app').innerHTML = `
    <div class="detail-head">
      <h1>🌳 递归依赖分析 · ${esc(name)}</h1>
      <span id="rcStatus"></span>
      <span class="spacer"></span>
      <button class="btn sm" id="rcRescan">🔄 重新扫描</button>
      <button class="btn sm" id="rcAuto" title="从该库出发，整树自动递归克隆并分析全部运行时依赖">🌲 自动递归全部</button>
      <button class="btn sm" id="rcStop" disabled>■ 停止</button>
    </div>
    <p class="hint">进入只列出当前一层未分析的运行时依赖（不会自动分析）。勾选要分析的依赖（可手动填写 / 修正 Git 地址），再选「仅本层」或「递归」分析——系统库 / 无源码库作为叶子不再下钻。</p>
    <div id="rcBar" class="rc-bar"></div>
    <div class="card"><div id="rcPick"></div></div>
    <div class="card"><div class="section-title">进行中 / 已完成</div><div id="rcTable"></div></div>`;
  $('#rcRescan').onclick = () => advanceRecurse({ rescan: true });
  $('#rcAuto').onclick = () => { if (confirm('从该库出发，整树自动递归分析全部运行时依赖？')) advanceRecurse({ recurseAll: true }); };
  // 找现有会话；没有就建一个手动会话（只展示、不分析）
  try {
    const { sessions } = await api('/api/recurse');
    const s = (sessions || []).find((x) => x.root === name && (x.group || 'default') === activeGroup);
    if (s) rcSession = s.id;
  } catch (_) {}
  if (!rcSession) {
    let r;
    try { r = await api('/api/recurse', { method: 'POST', headers: JSONH, body: JSON.stringify(withGroup({ name, manual: true })) }); }
    catch { $('#rcPick').innerHTML = '<div class="hint err">创建会话失败</div>'; return; }
    if (r.error) { $('#rcPick').innerHTML = `<div class="hint err">${esc(r.error)}</div>`; return; }
    rcSession = r.sessionId;
  }
  openRecurseStream(rcSession);
}

// 批准选中依赖并推进。opts: { recurse } 分析本层/递归；{ recurseAll } 整树自动；{ rescan } 仅重算 frontier。
async function advanceRecurse(opts = {}) {
  if (!rcSession) return;
  const body = { session: rcSession };
  if (opts.recurseAll) body.recurseAll = true;
  else if (opts.rescan) body.items = [];                 // 空批准 → 仅 re-tick
  else {
    const items = [];
    $$('#rcPick tr[data-key]').forEach((tr) => {
      const cb = tr.querySelector('.rc-sel');
      if (!cb || !cb.checked) return;
      const inp = tr.querySelector('.rc-url');
      items.push({ key: tr.dataset.key, url: inp ? inp.value.trim() : '' });
    });
    if (!items.length) return toast('请先勾选要分析的依赖', 'err');
    if (items.some((it) => !it.url)) return toast('选中依赖缺少 Git 地址，请填写或用 🔎 解析', 'err');
    body.items = items; body.recurse = !!opts.recurse;
  }
  let snap;
  try { snap = await api('/api/recurse/advance', { method: 'POST', headers: JSONH, body: JSON.stringify(body) }); }
  catch { return toast('提交失败', 'err'); }
  if (snap && snap.error) return toast(snap.error, 'err');
  if (snap) renderRecurseSnap(snap);
  if (!es && rcSession) openRecurseStream(rcSession);    // 会话之前 done 关流了 → 重新挂上
}

function openRecurseStream(id) {
  if (es) { es.close(); es = null; }
  const stopBtn = $('#rcStop');
  if (stopBtn) {
    stopBtn.disabled = false;
    stopBtn.onclick = async () => {
      await api('/api/recurse/stop', { method: 'POST', headers: JSONH, body: JSON.stringify({ session: id }) });
      toast('已请求停止（在途任务将自然结束）', 'ok');
    };
  }
  es = new EventSource('/api/recurse/stream?session=' + enc(id));
  es.addEventListener('update', (e) => { try { renderRecurseSnap(JSON.parse(e.data).data); } catch (_) {} });
  es.onerror = () => {};
  view.cleanup = () => { if (es) { es.close(); es = null; } };
}

function renderRecurseSnap(snap) {
  // 用户正在输入 Git 地址时跳过整页重渲染，避免清空输入
  if (document.activeElement && document.activeElement.classList && document.activeElement.classList.contains('rc-url')) return;
  const stEl = $('#rcStatus');
  if (stEl) stEl.innerHTML = `<span class="badge ${RC_SESSION_CLS[snap.status] || 'gray'}">${RC_SESSION_ZH[snap.status] || snap.status}</span>`;
  if (snap.status !== 'running' && es) { es.close(); es = null; }
  const stopBtn = $('#rcStop'); if (stopBtn) stopBtn.disabled = snap.status !== 'running';
  const rows = snap.decisions || [];
  // 待选择：尚未批准、且非终态、非在途的依赖（pending / resolved 等待用户挑选）
  const awaiting = rows.filter((d) => !d.approved && !RC_TERMINAL.has(d.state) && d.state !== 'cloning' && d.state !== 'analyzing');
  const processed = rows.filter((d) => !awaiting.includes(d));
  const c = snap.counts || {};
  const g = (keys) => keys.reduce((n, k) => n + (c[k] || 0), 0);
  const bar = [
    ['待选择', awaiting.length, 'gray'],
    ['处理中', processed.filter((d) => !RC_TERMINAL.has(d.state)).length, 'running'],
    ['已分析', c.analyzed || 0, 'done'],
    ['已鸿蒙化叶子', c.leaf_harmonized || 0, 'done'],
    ['系统/无源码叶子', g(['leaf_system', 'leaf_prebuilt', 'leaf_interface']), 'queued'],
    ['待人工解析', c.leaf_no_source || 0, 'gray'],
    ['歧义', c.ambiguous || 0, 'gray'],
    ['失败', c.failed || 0, 'error'],
  ];
  if (c.capped) bar.push(['超出上限', c.capped, 'gray']);
  $('#rcBar').innerHTML = bar.map(([t, n, cl]) => `<span class="rc-chip"><span class="badge ${cl}">${num(n)}</span>${t}</span>`).join('');
  renderRcPick(awaiting);
  if (!processed.length) $('#rcTable').innerHTML = '<div class="hint muted">尚无进行中 / 已完成的依赖。</div>';
  else $('#rcTable').innerHTML = `<table class="obstable"><thead><tr>
      <th>依赖</th><th>生态</th><th>深度</th><th>状态</th><th>说明</th></tr></thead>
    <tbody>${processed.map(rcRow).join('')}</tbody></table>`;
}

function renderRcPick(awaiting) {
  const box = $('#rcPick'); if (!box) return;
  if (!awaiting.length) {
    box.innerHTML = '<div class="hint muted">当前没有待选择的依赖。分析完成后若出现更深一层依赖，会在此列出。</div>';
    return;
  }
  box.innerHTML = `
    <div class="row" style="justify-content:space-between;align-items:center;margin-bottom:8px">
      <div class="section-title" style="margin:0">待选择依赖（${awaiting.length}）</div>
      <div class="row" style="gap:6px">
        <label class="muted" style="font-size:12px"><input type="checkbox" id="rcSelAll" /> 全选</label>
        <button class="btn sm" id="rcAnalyzeLayer">分析选中（仅本层）</button>
        <button class="btn sm primary" id="rcAnalyzeRecurse">递归分析选中</button>
      </div>
    </div>
    <table class="obstable"><thead><tr>
      <th class="c-chk"></th><th>依赖</th><th>生态</th><th>深度</th><th>Git 地址</th><th></th></tr></thead>
    <tbody>${awaiting.map(rcPickRow).join('')}</tbody></table>`;
  $('#rcSelAll').onchange = (e) => $$('#rcPick .rc-sel').forEach((cb) => { cb.checked = e.target.checked; });
  $('#rcAnalyzeLayer').onclick = () => advanceRecurse({ recurse: false });
  $('#rcAnalyzeRecurse').onclick = () => advanceRecurse({ recurse: true });
  $$('#rcPick .rc-url').forEach((inp) => inp.oninput = () => { rcUrlEdits[inp.dataset.key] = inp.value; });
  $$('#rcPick [data-rc-resolve]').forEach((b) => b.onclick = () => rcResolve(b.dataset.eco, b.dataset.name, b.dataset.rcResolve, b));
}

function rcPickRow(d) {
  const key = d.key || (d.ecosystem + ':' + d.name);
  const url = rcUrlEdits[key] != null ? rcUrlEdits[key] : (d.url || '');
  const eco = ECO_LABELS[d.ecosystem] || d.ecosystem || '';
  return `<tr data-key="${esc(key)}">
    <td class="c-chk"><input type="checkbox" class="rc-sel" /></td>
    <td>${esc(d.name)}</td><td>${esc(eco)}</td><td>${d.depth}</td>
    <td><input class="rc-url" type="text" data-key="${esc(key)}" value="${esc(url)}" placeholder="Git URL" style="width:100%;min-width:220px" /></td>
    <td><button class="btn sm" data-rc-resolve="${esc(key)}" data-eco="${esc(d.ecosystem || '')}" data-name="${esc(d.name)}" title="联网解析仓库地址">🔎</button></td>
  </tr>`;
}

// 联网解析单个依赖的仓库地址，命中单一具体仓库则填回该行（复用 /api/resolve-repo）
async function rcResolve(eco, name, key, btn) {
  if (btn) { btn.disabled = true; btn.textContent = '…'; }
  let r;
  try { r = await api(`/api/resolve-repo?ecosystem=${enc(eco || '')}&name=${enc(name)}`); }
  catch { r = null; }
  if (btn) { btn.disabled = false; btn.textContent = '🔎'; }
  if (r && r.disabled) return toast('联网解析已在设置中关闭', 'err');
  const cands = (r && r.candidates) || [];
  if (r && r.url && !r.interface && cands.length <= 1) {
    rcUrlEdits[key] = r.url;
    const tr = $$('#rcPick tr[data-key]').find((x) => x.dataset.key === key);
    const inp = tr && tr.querySelector('.rc-url'); if (inp) inp.value = r.url;
    toast('已填入解析地址', 'ok');
  } else {
    toast(r && r.url ? '接口 / 多候选，请手动确认地址' : '未解析到仓库地址，请手动填写', 'err');
  }
}

function rcRow(d) {
  const s = RC_STATE[d.state] || { t: d.state, c: 'gray' };
  const nm = d.libName ? `<a href="#/lib/${enc(d.libName)}">${esc(d.name)}</a>` : esc(d.name);
  const repo = d.repoName && d.repoName !== d.name ? ` <span class="muted">→ ${esc(d.repoName)}</span>` : '';
  const rec = d.autoRecurse ? ' <span class="chip">递归</span>' : '';
  const eco = ECO_LABELS[d.ecosystem] || d.ecosystem || '';
  return `<tr><td>${nm}${repo}${rec}</td><td>${esc(eco)}</td><td>${d.depth}</td>` +
    `<td><span class="badge ${s.c}">${esc(s.t)}</span></td><td class="muted">${esc(d.reason || '')}</td></tr>`;
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
  let obj;
  try {
    const txt = await fetch(`/api/report?name=${enc(name)}&run=${enc(run)}&${gq()}`).then((x) => x.text());
    obj = JSON.parse(txt);
  } catch (_) {
    $('#report').innerHTML = '<p class="muted">本次运行没有报告（可能未完成或失败）。</p>';
    $('#rawBtn').disabled = $('#htmlBtn').disabled = $('#dlBtn').disabled = true;
    obj = null;
  }
  if (obj) {
    curReport = { name, run, obj };
    $('#rawJson').textContent = JSON.stringify(obj, null, 2);
    $('#rawBtn').disabled = $('#htmlBtn').disabled = $('#dlBtn').disabled = false;
    // Render failures (e.g. a weak model's off-contract field shape) must not
    // masquerade as "no report" — fall back to the raw JSON view instead.
    try {
      renderReport(obj);
    } catch (e) {
      $('#report').innerHTML =
        `<p class="hint err">报告渲染异常，已降级为原始 JSON 视图。（${esc(e && e.message || e)}）</p>`
        + `<pre class="raw">${esc(JSON.stringify(obj, null, 2))}</pre>`;
    }
  }
  // also replay this run's persisted log if not currently streaming live
  if (!es) {
    try {
      const log = await fetch(`/api/runlog?name=${enc(name)}&run=${enc(run)}&${gq()}`).then((x) => x.text());
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

// Export the currently-rendered report as a single, offline, self-contained HTML file —
// identical to what's on screen. We capture the live #report DOM (so the async-loaded dep
// tree + 已鸿蒙化 badges are included) and inline styles.css; no external assets are used.
async function exportReportHtml() {
  if (!curReport) return;
  const name = curReport.name;
  const btn = $('#htmlBtn'); if (btn) { btn.disabled = true; btn.textContent = '导出中…'; }
  try {
    // make sure the (idempotent) dep tree is loaded before we snapshot the DOM
    const hasDeps = ((curReport.obj.dependencies || {}).dependencies || []).length ||
      (curReport.obj.dependencies || {}).count != null;
    if (hasDeps) { try { await loadDepTree(name); } catch (_) {} }
    const css = await fetch('/styles.css').then((r) => r.text());
    const src = $('#report');
    const report = src.cloneNode(true);
    // drop transient interaction state (click-to-highlight) so the export is clean
    report.querySelectorAll('.hl-on, .hl-dim, .hl-badge-on')
      .forEach((el) => el.classList.remove('hl-on', 'hl-dim', 'hl-badge-on'));
    report.classList.remove('hidden');
    const doc = `<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(name)} · 分析报告</title>
<style>${css}</style>
<style>body{max-width:980px;margin:0 auto;padding:28px 24px 60px}
.export-head{margin-bottom:18px}.export-head h1{margin:0 0 4px;font-size:20px}</style>
</head><body>
<div class="export-head"><h1>${esc(name)} 分析报告</h1>
<div class="muted">导出时间 ${esc(fmtTime(Date.now()))} · 由「PC 开源软件分析控制台」生成</div></div>
${report.outerHTML}
</body></html>`;
    const blob = new Blob([doc], { type: 'text/html' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = `${name}.report.html`; a.click();
    URL.revokeObjectURL(a.href);
    toast('已导出 HTML', 'ok');
  } catch (e) {
    toast('导出失败：' + (e && e.message || e), 'err');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '导出 HTML'; }
  }
}

// Defensive shape normalisation for reports produced by weaker models that drift
// off the contract (a lone string where the UI expects string[], an object where
// it expects an array). New runs are already normalised at assembly time
// (scripts/assemble_report.py); this covers pre-existing on-disk reports and any
// future drift so a single off-shape field never blanks the whole render.
function coerceReportShapes(r) {
  if (!r || typeof r !== 'object') return r;
  const flatten = (v) => {
    if (Array.isArray(v)) return v;
    if (v && typeof v === 'object') {
      const groups = Object.values(v).filter((x) => Array.isArray(x) && x.some((e) => e && typeof e === 'object'));
      if (groups.length) return groups.flat();
      return [v];
    }
    return v == null || v === '' ? [] : [v];
  };
  // any property literally named "evidence" must be a string[]
  const fixEvidence = (o) => {
    if (Array.isArray(o)) { o.forEach(fixEvidence); return; }
    if (o && typeof o === 'object') {
      for (const k of Object.keys(o)) {
        if (k === 'evidence' && o[k] != null && !Array.isArray(o[k])) o[k] = [o[k]];
        else fixEvidence(o[k]);
      }
    }
  };
  fixEvidence(r);
  if (r.build_env && !Array.isArray(r.build_env.entry_points) && r.build_env.entry_points)
    r.build_env.entry_points = flatten(r.build_env.entry_points);
  return r;
}

function renderReport(r) {
  coerceReportShapes(r);
  if (tocObserver) { try { tocObserver.disconnect(); } catch (_) {} tocObserver = null; }
  const el = $('#report'); el.classList.remove('hidden'); $('#rawJson').classList.add('hidden');
  // sec() also records a {id,title} into toc[] (display order) so the sticky #reportNav
  // can anchor-jump to each module. id is per-render (toc + sections built in one pass).
  const toc = [];
  const sec = (title, inner) => {
    const id = 'sec-' + toc.length; toc.push({ id, title });
    return `<div class="rsec" id="${id}"><h3>${title}</h3>${inner}</div>`;
  };
  const parts = [];
  const lib = r.library || {}, fs = r.function_summary || {}, cm = r.code_metrics || {},
    t = r.tests || {}, lic = r.license || {}, dep = r.dependencies || {}, na = r.native_api || {};

  parts.push(sec('概览', `<div class="kv">
    <b>名称</b><span>${esc(lib.name)}${kindLabel(lib.kind) ? ` <span class="badge ${lib.kind === 'application' ? 'running' : 'gray'}">${esc(kindLabel(lib.kind))}</span>` : ''}</span>
    <b>一句话</b><span>${esc(lib.one_liner || fs.summary || '')}</span>
    <b>生态</b><span>${lib.ecosystem ? `<span class="chip eco-chip">${esc(ECO_LABELS[lib.ecosystem] || lib.ecosystem)}</span>` : '—'}${bindingChips(lib.bindings, lib.ecosystem)}</span>
    <b>主语言</b><span>${esc((r.languages || {}).primary || '—')}</span>
    <b>许可证</b><span>${esc(lic.spdx || '—')} <span class="muted">(${esc(lic.confidence || '')})</span>${lic.category ? ` <span class="badge ${LIC_CAT_CLS[lic.category] || 'gray'}">${LIC_CAT_LABELS[lic.category] || esc(lic.category)}</span>` : ''}</span>
    <b>来源</b><span>${esc(lib.source_url || '')}${lib.source_subpath ? ` <span class="chip" title="monorepo 子目录">▸ ${esc(lib.source_subpath)}</span>` : ''}</span></div>`));

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

  const pa = cm.platform_adaptation || {};
  const paBy = pa.by_platform || {};
  if (pa.total > 0 && Object.keys(paBy).length) {
    const PLAT_LABELS = { windows: 'Windows', macos: 'macOS', linux: 'Linux', posix: 'POSIX' };
    const ent = Object.entries(paBy)
      .filter(([, v]) => v && v.code)
      .sort((a, b) => (b[1].code || 0) - (a[1].code || 0));
    const max = Math.max(...ent.map(([, v]) => v.code || 0), 1);
    const blocks = ent.map(([k, v]) => {
      const mac = (v.macros || []).map((m) => `<span class="mtok">${esc(m)}</span>`).join('');
      return `<div class="platblock">
        <div class="platrow">
          <span class="pl-name">${esc(PLAT_LABELS[k] || k)}</span>
          <span class="pl-bar"><span class="bar" style="width:${Math.max(3, 100 * (v.code || 0) / max)}%"></span></span>
          <span class="pl-count">${num(v.code)} 行 · ${num(v.files)} 文件</span>
        </div>${mac ? `<div class="pl-macros">${mac}</div>` : ''}</div>`;
    }).join('');
    parts.push(sec('平台适配代码量（编译宏）',
      `<div class="pl-head" title="${esc(pa.notes || '')}"><span class="muted">各平台被编译宏正向包裹的生产代码行</span><b>共 ${num(pa.total)} 行</b></div>` +
      blocks +
      `<p class="hint">正向 #ifdef 守卫（_WIN32/__APPLE__/__linux__…）的生产代码（C/C++/ObjC，#ifndef·!defined 不计），作为鸿蒙适配复杂度参考信号。</p>`));
  }

  const pb = cm.platform_branches || {};
  const pbLang = pb.by_language || {};
  if (pb.total > 0 && Object.keys(pbLang).length) {
    const LANG_LABELS = { python: 'Python', javascript: 'JS/TS', java: 'Java/Kotlin', go: 'Go', rust: 'Rust', csharp: 'C#' };
    const PLAT_LABELS = { windows: 'Windows', macos: 'macOS', linux: 'Linux', posix: 'POSIX', other: '其它' };
    const ent = Object.entries(pbLang)
      .filter(([, v]) => v && v.hits)
      .sort((a, b) => (b[1].hits || 0) - (a[1].hits || 0));
    const max = Math.max(...ent.map(([, v]) => v.hits || 0), 1);
    const blocks = ent.map(([k, v]) => `<div class="platblock">
        <div class="platrow">
          <span class="pl-name">${esc(LANG_LABELS[k] || k)}</span>
          <span class="pl-bar"><span class="bar" style="width:${Math.max(3, 100 * (v.hits || 0) / max)}%"></span></span>
          <span class="pl-count">${num(v.hits)} 处 · ${num(v.files)} 文件</span>
        </div></div>`).join('');
    const platTally = Object.entries(pb.by_platform || {})
      .filter(([, n]) => n)
      .map(([k, n]) => `<span class="mtok">${esc(PLAT_LABELS[k] || k)} ${num(n)}</span>`).join('');
    const samp = (pb.samples || []).slice(0, 8)
      .map((s) => `<div class="codeloc"><span class="muted">${esc(s.file)}:${s.line}</span> ${esc(s.text)}</div>`).join('');
    parts.push(sec('平台判断分支（运行时）',
      `<div class="pl-head" title="${esc(pb.notes || '')}"><span class="muted">运行时平台判断（sys.platform / process.platform / runtime.GOOS…）</span><b>共 ${num(pb.total)} 处</b></div>` +
      blocks +
      (platTally ? `<div class="pl-macros" style="margin-left:0">${platTally}</div>` : '') +
      (samp ? `<div class="codeloc-list">${samp}</div>` : '') +
      `<p class="hint">机械计数（启发式）：脚本/JVM/Go/Rust/C# 等运行时平台分支——这类分支同样需逐一确认鸿蒙等价，是 dim-9 适配评估信号之一。C/C++ 编译宏见上一卡片。</p>`));
  }

  // 架构相关代码（汇编/SIMD，机械信号 3）
  const as = cm.arch_specific || {};
  const asBy = as.by_arch || {};
  if (Object.keys(asBy).length) {
    const ARCH_LABELS = { x86: 'x86/x64', arm: 'ARM/NEON', riscv: 'RISC-V', generic: '未归类' };
    const ent = Object.entries(asBy).sort((a, b) => ((b[1].loc || 0) + (b[1].simd_loc || 0) + (b[1].hits || 0)) - ((a[1].loc || 0) + (a[1].simd_loc || 0) + (a[1].hits || 0)));
    const rows = ent.map(([k, v]) => `<div class="platblock"><div class="platrow">
        <span class="pl-name">${esc(ARCH_LABELS[k] || k)}</span>
        <span class="pl-count">${v.loc ? `汇编 ${num(v.loc)} 行 · ` : ''}${v.simd_loc ? `SIMD ${num(v.simd_loc)} 行 · ` : ''}${v.hits ? `intrinsics头/内联 ${num(v.hits)} 处 · ` : ''}${num(v.files)} 文件</span>
      </div></div>`).join('');
    const hdrs = (as.intrinsics_headers || []).map((h) => `<span class="mtok">${esc(h)}</span>`).join('');
    const samp = (as.samples || []).slice(0, 6)
      .map((s) => `<div class="codeloc"><span class="muted">${esc(s.file)}${s.line ? ':' + s.line : ''}</span> ${esc(s.text || s.kind)}</div>`).join('');
    const x86Only = asBy.x86 && !asBy.arm;
    const asmT = as.total || 0, simdT = as.simd_total || 0;
    const headNum = (asmT && simdT) ? `架构相关 ${num(asmT + simdT)} 行（汇编 ${num(asmT)} · SIMD ${num(simdT)}）`
      : simdT ? `SIMD ${num(simdT)} 行` : `汇编 ${num(asmT)} 行`;
    parts.push(sec('架构相关代码（汇编 / SIMD）',
      `<div class="pl-head" title="${esc(as.notes || '')}"><span class="muted">独立汇编文件、SIMD intrinsics、内联汇编（生产代码）</span><b>${headNum}</b></div>` +
      rows + (hdrs ? `<div class="pl-macros" style="margin-left:0">${hdrs}</div>` : '') +
      (samp ? `<div class="codeloc-list">${samp}</div>` : '') +
      `<p class="hint">${x86Only ? '⚠ 仅见 x86 架构实现、未见 ARM 对应——arm64 鸿蒙 PC 上需补 NEON/标量回退，是适配硬点。' : '机械计数：x86 与 ARM 并存时多为已有双路径，重编验证即可。'}</p>`));
  }

  // 代码分区 (code_partition, dim 12) — 迁移复用性 LOC 分桶。
  // 构造成 cpInner 变量后并入「鸿蒙适配评估」(dim 9) 卡片（dim-12 是 dim-9 工作量的量化底座）；
  // 仅当报告没有 harmony_adaptation 块时才独立成卡（见文末兜底）。
  let cpInner = '';
  const cp = r.code_partition || {};
  const buckets = (cp.buckets || []).filter((b) => b && b.class);
  if (buckets.length || cp.summary) {
    // read-side tolerance for field-name drift (server also normalizes; belt-and-suspenders)
    const bLoc = (b) => Number(b.loc != null ? b.loc : b.total_loc) || 0;
    const mPath = (md) => md.path || md.dir || md.module || md.name || '';
    const mReason = (md) => md.reason || md.note || '';
    const totalLoc = buckets.reduce((a, b) => a + bLoc(b), 0) || 1;
    const ordered = PART_ORDER.map((k) => buckets.find((b) => b.class === k)).filter(Boolean)
      .concat(buckets.filter((b) => !PART_ORDER.includes(b.class)));
    const bar = ordered.map((b) => {
      const m = PART_META[b.class] || { label: b.class, color: '#9aa4b2' };
      const w = Math.max(1.5, 100 * bLoc(b) / totalLoc);
      return `<span class="part-seg" style="width:${w}%;background:${m.color}" title="${m.label} ${num(bLoc(b))} 行"></span>`;
    }).join('');
    const legend = ordered.map((b) => {
      const m = PART_META[b.class] || { label: b.class, color: '#9aa4b2' };
      const pct = b.pct != null ? b.pct : Math.round(1000 * bLoc(b) / totalLoc) / 10;
      return `<span class="part-leg"><span class="dot" style="background:${m.color}"></span>${m.label} <b>${num(bLoc(b))}</b> 行 (${pct}%)</span>`;
    }).join('');
    const modTables = ordered.filter((b) => (b.modules || []).length).map((b) => {
      const m = PART_META[b.class] || { label: b.class, color: '#9aa4b2' };
      const rows = (b.modules || []).map((md) => {
        const ev = (md.evidence || []).slice(0, 2).map(esc).join('、');
        return `<tr><td class="api-n"><code>${esc(mPath(md))}</code></td><td>${md.loc != null ? num(md.loc) + ' 行' : '—'}</td>
          <td>${esc(mReason(md))}${ev ? `<div class="muted">${ev}</div>` : ''}</td></tr>`;
      }).join('');
      return `<div class="subtitle"><span class="dot" style="background:${m.color}"></span> ${m.label}${b.basis ? ` <span class="muted">· ${esc(b.basis)}</span>` : ''}</div>
        <table class="apitable"><thead><tr><th>模块</th><th>代码量</th><th>归类理由 / 证据</th></tr></thead><tbody>${rows}</tbody></table>`;
    }).join('');
    const cov = cp.coverage || {};
    const covTxt = cov.production_code
      ? `<p class="hint">对账：已分区 ${num(cov.partitioned_code)} / 生产代码 ${num(cov.production_code)} 行（覆盖 ${cov.pct != null ? cov.pct : Math.round(1000 * totalLoc / cov.production_code) / 10}%）；LOC 引用 code_metrics.dir_loc 机械数字。</p>`
      : '';
    cpInner =
      (cp.summary ? `<p>${esc(cp.summary)}</p>` : '') +
      (buckets.length ? `<div class="part-bar">${bar}</div><div class="part-legend">${legend}</div>` : '') +
      modTables + covTxt +
      (cp.notes ? `<p class="hint">${esc(cp.notes)}</p>` : '');
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
      const rows = (g.apis || []).map((a) => {
        const loc = (a.evidence || []).slice(0, 3).map(esc).join('、');
        const more = (a.evidence || []).length > 3 ? ` <span class="muted" title="${esc((a.evidence || []).join(', '))}">…</span>` : '';
        const cnt = (a.count != null) ? ` <span class="api-cnt" title="调用次数">×${num(a.count)}</span>` : '';
        return `<tr><td class="api-n"><code>${esc(a.name)}</code>${cnt}${a.conditional ? ' <span class="tag">#ifdef</span>' : ''}</td>
          <td>${esc(a.purpose || '')}</td><td class="api-loc">${loc || '—'}${more}</td></tr>`;
      }).join('');
      return rows
        ? `${head}<table class="apitable"><thead><tr><th>API</th><th>用途</th><th>调用位置</th></tr></thead><tbody>${rows}</tbody></table>`
        : `${head}<div class="cat"><i class="muted">—</i></div>`;
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
      (rs.subprocess || []).length || (rs.devices || []).length || (rs.services || []).length || rs.summary) {
    parts.push(sec('外部交互面', `${rs.summary ? `<p>${esc(rs.summary)}</p>` : ''}` +
      surfRow('环境变量', rs.env_vars, (e) => surfItem(e.name, e.purpose, e.evidence)) +
      surfRow('网络', rs.network, (e) => surfItem(e.detail, e.purpose, e.evidence)) +
      surfRow('文件系统', rs.filesystem, (e) => surfItem(e.detail, e.purpose, e.evidence)) +
      surfRow('子进程', rs.subprocess, (e) => surfItem(e.command, e.purpose, e.evidence)) +
      surfRow('外部服务', rs.services, (e) => surfItem(e.detail, e.purpose, e.evidence)) +
      surfRow('设备', rs.devices, (e) => surfItem(e.detail, e.purpose, e.evidence))));
  }

  // 构建与平台 (build_env)
  const be = r.build_env || {};
  if (be.language_standard || be.build_system || be.runtime_version || be.packaging ||
      (be.platforms || []).length || (be.compiler_extensions || []).length ||
      (be.entry_points || []).length || be.notes) {
    const plats = (be.platforms || []).map((p) =>
      `<span class="chip" title="${esc((p.evidence || []).join(', '))}">${esc(p.os || '')}${p.arch ? ' / ' + esc(p.arch) : ''}</span>`).join('');
    const exts = (be.compiler_extensions || []).map((e) => surfItem(e.detail, e.purpose, e.evidence)).join('');
    const eps = (be.entry_points || []).map((e) =>
      surfItem((e.name || e.kind || e.file || e.type || '—') + (e.type && e.name ? ` (${e.type})` : ''),
        e.command || e.file, e.evidence)).join('');
    parts.push(sec('构建与平台', `<div class="kv">
      <b>语言标准</b><span>${esc(be.language_standard || '—')}</span>
      <b>运行时版本</b><span>${esc(be.runtime_version || '—')}</span>
      <b>构建系统</b><span>${esc(be.build_system || '—')}</span>` +
      (be.packaging ? `<b>打包分发</b><span>${esc(be.packaging)}</span>` : '') + `</div>` +
      (eps ? `<div class="subtitle">入口 / 启动器</div>${eps}` : '') +
      (plats ? `<div class="subtitle">支持平台</div>${plats}` : '') +
      (exts ? `<div class="subtitle">编译器特有扩展</div>${exts}` : '') +
      (be.notes ? `<p class="hint">${esc(be.notes)}</p>` : '')));
  }

  // 能力画像 (capability_profile, dim 10) — GUI/3D/媒体/硬件 场景
  const cap = r.capability_profile || {};
  const scen = (cap.scenarios || []).filter((s) => s && s.present);
  if (scen.length || cap.summary) {
    const rows = scen.map((s) => {
      const st = s.harmony_status || 'unknown';
      const kinds = (s.kind || []).map((k) => `<span class="mtok">${esc(k)}</span>`).join('');
      const via = (s.via || []).length ? `<span class="muted">来源：${(s.via || []).map(esc).join('、')}</span>` : '';
      const spec = s.specific_hardware ? ' <span class="badge error">特定硬件</span>' : '';
      const ev = (s.evidence || []).length ? `<div class="codeloc"><span class="muted">${(s.evidence || []).slice(0, 3).map(esc).join('  ')}</span></div>` : '';
      return `<div class="platblock">
        <div class="cap-row">
          <span class="cap-name">${esc(CAP_LABELS[s.key] || s.key)}${spec}</span>
          <span class="badge ${TGT_CLS[st] || 'gray'}">${TGT_LABELS[st] || esc(st)}</span>
          <span class="cap-kinds">${kinds} ${via}</span>
        </div>${s.adaptation ? `<p class="hint" style="margin:2px 0 0">${esc(s.adaptation)}</p>` : ''}${ev}</div>`;
    }).join('');
    parts.push(sec('能力画像（GUI / 3D / 媒体 / 硬件）',
      (cap.summary ? `<p>${esc(cap.summary)}</p>` : '') + (rows || '<p class="hint">未触及 GUI/3D/媒体/特定硬件场景。</p>') +
      `<p class="hint">这些场景的鸿蒙支持状态（徽标）对照目标能力参考；详见鸿蒙适配评估。</p>`));
  }

  // 云服务 (cloud_services, dim 11) — 是否涉及云端 + 厂商推测
  const cs = r.cloud_services || {};
  const csvc = (cs.services || []).filter((s) => s && s.vendor);
  if (csvc.length || cs.summary || cs.present === false) {
    const rows = csvc.map((s) => {
      const conf = s.confidence || '';
      const cats = (s.categories || []).map((c) => `<span class="mtok">${esc(CLOUD_CAT_LABELS[c] || c)}</span>`).join('');
      const via = (s.via || []).length ? `<span class="muted">来源：${(s.via || []).map(esc).join('、')}</span>` : '';
      const eps = (s.endpoints || []).length ? `<div class="codeloc"><span class="muted">云端域名：${(s.endpoints || []).slice(0, 4).map(esc).join('  ')}</span></div>` : '';
      const ev = (s.evidence || []).length ? `<div class="codeloc"><span class="muted">${(s.evidence || []).slice(0, 3).map(esc).join('  ')}</span></div>` : '';
      const confBadge = conf ? ` <span class="badge ${conf === 'high' ? 'done' : conf === 'medium' ? 'running' : 'gray'}">置信 ${CONF_LABELS[conf] || esc(conf)}</span>` : '';
      return `<div class="platblock">
        <div class="cap-row">
          <span class="cap-name">${esc(VENDOR_LABELS[s.vendor] || s.vendor)}${confBadge}</span>
          <span class="cap-kinds">${cats} ${via}</span>
        </div>${eps}${ev}</div>`;
    }).join('');
    parts.push(sec('云服务（厂商 / 用途）',
      (cs.summary ? `<p>${esc(cs.summary)}</p>` : '') +
      (rows || '<p class="hint">未涉及第三方云端服务。</p>') +
      (csvc.length ? '<p class="hint">涉及云端 ⇒ 鸿蒙化需网络权限（ohos.permission.INTERNET）；详见鸿蒙适配评估。</p>' : '')));
  }

  // 鸿蒙适配评估 (harmony_adaptation, dim 9) — 代码分区(dim 12)并入此卡
  let harmonyRendered = false;
  const ha = r.harmony_adaptation || {};
  const aa = ha.adaptation_assessment || {};
  if (ha.summary || (ha.blockers || []).length ||
      aa.overall || (ha.key_tasks || []).length ||
      ha.porting_class || (ha.unadaptable_apis || []).length ||
      (ha.target_assumptions || []).length) {
    // 是否可适配总判（adaptation_assessment.overall，派生，替代旧 feasibility）
    const overallBadge = aa.overall
      ? `<span class="badge ${OVERALL_CLS[aa.overall] || 'gray'}">${OVERALL_LABELS[aa.overall] || esc(aa.overall)}</span>` : '—';
    // 运行前提是否满足（functional_viability，派生自 target_assumptions，与 overall 正交）
    const fv = ha.functional_viability || null;
    const viabilityBadge = fv
      ? `<span class="badge ${FV_CLS[fv] || 'gray'}">${FV_LABELS[fv] || esc(fv)}</span>` : '—';
    // 难度等级（effort.level，server 派生）+ 工作量人天
    const lvl = (ha.effort && ha.effort.level) || null;
    const diffBadge = lvl
      ? `<span class="badge ${LVL_CLS[lvl] || 'gray'}">${LVL_LABELS[lvl] || esc(lvl)}</span>` : '—';
    const pd = ha.effort && ha.effort.person_days;
    const effortTxt = fmtDays(pd) || '—';
    const confBadge = ha.confidence
      ? `<span class="badge ${ha.confidence === 'low' ? 'error' : ha.confidence === 'medium' ? 'sev-major' : 'done'}">${CONF_LABELS[ha.confidence] || esc(ha.confidence)}</span>` : '—';
    const blockRows = (ha.blockers || []).map((b) => {
      const sev = b.severity
        ? `<span class="badge ${SEV_CLS[b.severity] || 'gray'}">${SEV_LABELS[b.severity] || esc(b.severity)}</span>` : '';
      const adapt = b.adaptability
        ? ` <span class="badge ${ADAPT_CLS[b.adaptability] || 'gray'}">${ADAPT_LABELS[b.adaptability] || esc(b.adaptability)}</span>` : '';
      const bStatus = b.remediation_status || b.harmony_status;   // v6 改名，兼容存量
      const status = bStatus ? `<span class="tag">${esc(bStatus)}</span>` : '';
      const cat = b.category ? ` <code>${esc(b.category)}</code>` : '';
      const src = b.source_dimension ? ` <span class="muted">·${esc(b.source_dimension)}</span>` : '';
      const ev = (b.evidence || []).slice(0, 3).map(esc).join('、');
      const more = (b.evidence || []).length > 3
        ? ` <span class="muted" title="${esc((b.evidence || []).join(', '))}">…</span>` : '';
      return `<tr><td class="api-n">${sev}${adapt}${cat}${src}</td>
        <td><b>${esc(b.issue || '')}</b>${b.remediation ? `<br><span class="muted">${esc(b.remediation)}</span>` : ''}</td>
        <td class="api-loc">${status}${ev ? `<div>${ev}${more}</div>` : ''}</td></tr>`;
    }).join('');
    const blockers = blockRows
      ? `<div class="subtitle">移植阻碍点</div><table class="apitable"><thead><tr><th>严重度 / 类别</th><th>问题与改造建议</th><th>鸿蒙状态 / 证据</th></tr></thead><tbody>${blockRows}</tbody></table>`
      : '';
    // 移植分级徽章：按 5 档 effective_class 上色（派生）
    const effClass = aa.effective_class || ha.porting_class || null;
    const pcBadge = effClass ? pclassBadge(effClass) : '—';
    const unRows = (ha.unadaptable_apis || []).map((u) => {
      const cat = u.category ? `<code>${esc(u.category)}</code>` : '';
      const fc = u.functionality_class
        ? `<span class="badge ${u.functionality_class === 'core' ? 'error' : 'sev-major'}">${FUNC_CLASS_LABELS[u.functionality_class] || esc(u.functionality_class)}</span>` : '';
      const ev = (u.evidence || []).slice(0, 3).map(esc).join('、');
      return `<tr><td class="api-n"><code>${esc(u.api || '')}</code>${u.public_entry ? `<br><span class="muted">入口 <code>${esc(u.public_entry)}</code></span>` : ''}</td>
        <td>${fc}</td>
        <td>${esc(u.reason || '')}${u.blocking_native_api && u.blocking_native_api !== u.api ? `<br><span class="muted">根源 <code>${esc(u.blocking_native_api)}</code></span>` : ''}</td>
        <td class="api-loc">${cat}${ev ? `<div>${ev}</div>` : ''}</td></tr>`;
    }).join('');
    const unadaptable = unRows
      ? `<div class="subtitle">无法适配的功能点（父库调用到才阻塞其迁移）</div><table class="apitable"><thead><tr><th>API / 公共入口</th><th>功能类别</th><th>原因</th><th>类别 / 证据</th></tr></thead><tbody>${unRows}</tbody></table>`
      : '';
    // 两维评估（核心功能 vs 平台差异功能），仅 needs_adaptation 有意义
    const dimRow = (label, dim) => {
      if (!dim) return '';
      const ok = dim.adaptable;
      const badge = `<span class="badge ${ok ? 'done' : 'error'}">${ok ? '全部可适配' : '部分不可适配'}</span>`;
      const pts = (dim.unadaptable || []).map((id) => `<code>${esc(id)}</code>`).join(' ');
      return `<tr><td>${label}</td><td>${badge}</td><td class="muted">${pts || '—'}</td></tr>`;
    };
    const twoDim = (aa.core || aa.platform_specific)
      ? `<div class="subtitle">功能两维评估</div><table class="apitable"><thead><tr><th>功能维度</th><th>可适配性</th><th>不可适配点</th></tr></thead><tbody>${dimRow('核心功能（各平台交集）', aa.core)}${dimRow('平台差异功能（平台特有）', aa.platform_specific)}</tbody></table>`
      : '';
    const compat = (ha.compatible || []).map((c) => surfItem(c.aspect, c.note, c.evidence)).join('');
    const tasks = (ha.key_tasks || []).length
      ? `<div class="subtitle">关键工作项</div><ul class="ha-tasks">${ha.key_tasks.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>` : '';
    // 目标平台能力假设（结论依赖哪些鸿蒙 PC 目标事实、哪些未核实）
    const ta = ha.target_assumptions || [];
    const unverified = ta.filter((a) => a.required && a.target_status === 'unknown').length;
    const taRows = ta.map((a) => {
      const st = a.target_status || 'unknown';
      // action: keyed → 去核实(打开该 caps 行编辑)；未登记(caps_gap) → 补充到能力库(建行+绑定本报告)
      const act = a.capability_key
        ? `<button class="btn sm ghost ta-verify" data-key="${esc(a.capability_key)}">核实</button>`
        : `<button class="btn sm ghost ta-add" data-ta="${esc(a.id || '')}" data-cap="${esc(a.capability || '')}">补充到能力库</button>`;
      return `<tr><td>${esc(a.capability || '')}${a.capability_key ? ` <code class="muted" title="caps 行 id">${esc(a.capability_key)}</code>` : ''}</td>
        <td>${a.required ? '<b>必需</b>' : '可选'}</td>
        <td><span class="badge ${TGT_CLS[st] || 'gray'}">${TGT_LABELS[st] || esc(st)}</span></td>
        <td class="muted">${esc(a.impact || '')}</td>
        <td>${act}</td></tr>`;
    }).join('');
    const assumptions = taRows
      ? (unverified ? `<div class="hint err" style="margin:6px 0">⚠ 结论依赖 ${unverified} 项未核实的鸿蒙 PC 目标能力，准确性受限——「补充到能力库」登记并核实后报告即刷新（无需重分析）。</div>` : '')
        + `<div class="subtitle">目标平台能力假设</div><table class="apitable"><thead><tr><th>目标能力</th><th>必需性</th><th>目标状态</th><th>影响</th><th>核实</th></tr></thead><tbody>${taRows}</tbody></table>`
      : '';
    // 所需鸿蒙权限（required_permissions）
    const permRows = (ha.required_permissions || []).map((p) => {
      const st = p.grantability || p.harmony_status || 'unknown';   // v6 改名，兼容存量
      return `<tr><td><code>${esc(p.permission || '')}</code></td>
        <td class="muted">${esc(p.reason || '')}${p.source_capability ? ` <span class="chip">${esc(CAP_LABELS[p.source_capability] || p.source_capability)}</span>` : ''}</td>
        <td><span class="badge ${TGT_CLS[st] || 'gray'}">${TGT_LABELS[st] || esc(st)}</span></td></tr>`;
    }).join('');
    const permissions = permRows
      ? `<div class="subtitle">所需鸿蒙权限</div><table class="apitable"><thead><tr><th>权限</th><th>原因 / 来源场景</th><th>鸿蒙可授予</th></tr></thead><tbody>${permRows}</tbody></table>`
      : '';
    // 迁移关键路径依赖（critical_dependencies，有序）
    const cdRows = (ha.critical_dependencies || []).slice()
      .sort((a, b) => (a.order || 99) - (b.order || 99))
      .map((c) => {
        const refs = (c.refs || []).map((x) => `<code>${esc(x)}</code>`).join(' ');
        const share = fmtDays(c.person_days_share);
        return `<tr><td class="api-n"><b>${c.order || ''}</b></td>
          <td><span class="chip" data-hname="${esc(c.name)}">${esc(c.name)}</span>${share ? ` <span class="muted">${share}</span>` : ''}</td>
          <td>${esc(c.why || '')}${refs ? `<div class="muted">${refs}</div>` : ''}</td></tr>`;
      }).join('');
    const critDeps = cdRows
      ? `<div class="subtitle">迁移关键路径依赖（按建议移植顺序）</div><table class="apitable"><thead><tr><th>顺序</th><th>依赖</th><th>为何关键</th></tr></thead><tbody>${cdRows}</tbody></table>`
      : '';
    // 工作量分项（effort.breakdown）
    const ebRows = ((ha.effort && ha.effort.breakdown) || []).map((b) =>
      `<tr><td class="api-n">${esc(EFFORT_COMP_LABELS[b.component] || b.component || '')}</td>
        <td><b>${fmtDays(b.person_days) || '—'}</b></td>
        <td class="muted">${esc(b.basis || '')}</td></tr>`).join('');
    const breakdown = ebRows
      ? `<div class="subtitle">工作量分项</div><table class="apitable"><thead><tr><th>分项</th><th>人天</th><th>估算依据</th></tr></thead><tbody>${ebRows}</tbody></table>`
      : '';
    parts.push(sec('鸿蒙适配评估', `<div class="kv">
      <b>代码适配</b><span>${overallBadge}</span>
      <b>运行前提</b><span>${viabilityBadge}</span>
      <b>移植分级</b><span>${pcBadge}</span>
      <b>难度等级</b><span>${diffBadge}</span>
      <b>工作量</b><span>${effortTxt}</span>
      <b>置信度</b><span>${confBadge}</span>
      <b>目标平台</b><span>${esc(ha.target || '—')}</span></div>` +
      (((r.meta || {}).harmony_warnings || []).length
        ? `<div class="hint err" style="margin:6px 0">⚠ 数据一致性提示：<ul style="margin:4px 0 0">${r.meta.harmony_warnings.map((w) => `<li>${esc(typeof w === 'string' ? w : (w && w.message) || '')}</li>`).join('')}</ul></div>` : '') +
      (((r.meta || {}).harmony_warnings_reviewed || []).length
        ? `<details class="hint" style="margin:6px 0;opacity:.75"><summary>✓ 已复核（模型判为误报，${r.meta.harmony_warnings_reviewed.length}）</summary><ul style="margin:4px 0 0">${r.meta.harmony_warnings_reviewed.map((w) => `<li>${esc((w && w.message) || '')}<br><span style="opacity:.8">复核：${esc((w && w.rationale) || '')}</span></li>`).join('')}</ul></details>` : '') +
      (ha.summary ? `<p>${esc(ha.summary)}</p>` : '') +
      twoDim +
      (cpInner ? `<div class="subtitle">代码分区（迁移复用性 · 工作量底座）</div>${cpInner}` : '') +
      breakdown +
      critDeps +
      assumptions +
      permissions +
      unadaptable +
      blockers +
      (compat ? `<div class="subtitle">可平滑移植</div>${compat}` : '') +
      tasks +
      (ha.notes ? `<p class="hint">${esc(ha.notes)}</p>` : '')));
    harmonyRendered = true;
  }
  // 兜底：报告没有 harmony_adaptation 块但有代码分区 → 代码分区仍独立成卡，避免丢数据。
  if (!harmonyRendered && cpInner) parts.push(sec('代码分区（鸿蒙迁移复用性）', cpInner));

  const warn = (r.meta || {}).warnings || [];
  if (warn.length) parts.push(sec('警告', warn.map((w) => `<div class="cat">⚠ ${esc(w)}</div>`).join('')));

  el.innerHTML = parts.join('');
  depHlKey = null;
  el.onclick = depHighlightHandler;   // delegated click-to-highlight for dep tags
  // target_assumptions 核实动作：keyed → 编辑该 caps 行；caps_gap → 补充能力并绑定本报告。
  // 保存后重载报告 → serve-time caps 回投刷新 target_status/functional_viability（无需重分析）。
  const reloadReport = () => { if (curReport) loadRun(curReport.name, curReport.run); };
  el.querySelectorAll('.ta-verify').forEach((b) => b.onclick = async (ev) => {
    ev.stopPropagation();
    try { capEdit(b.dataset.key, await api('/api/harmony-caps'), reloadReport); }
    catch { toast('加载能力库失败', 'err'); }
  });
  el.querySelectorAll('.ta-add').forEach((b) => b.onclick = (ev) => {
    ev.stopPropagation();
    capAddModal({ capability: b.dataset.cap },
      { group: activeGroup, name: curReport && curReport.name, run: curReport && curReport.run, ta_id: b.dataset.ta },
      reloadReport);
  });
  if (hasDeps) loadDepTree(curReport && curReport.name);
  decorateHarmonyBadges(el).then(() => updateDepHarmonyCount(r));
  buildReportNav(toc);
}

// Sticky anchor bar for the report modules. Click smooth-scrolls to the section — NOT via
// href="#..." (that would drive the SPA hash router); a scroll-spy highlights the current one.
function buildReportNav(toc) {
  const nav = $('#reportNav'); if (!nav) return;
  if (!toc.length) { nav.hidden = true; nav.innerHTML = ''; return; }
  nav.hidden = false;
  // chip label is plain text — strip any HTML in the section title (e.g. 依赖's
  // <span id="depHarmonyCount">, which belongs to the <h3> header, not the chip).
  const label = (t) => esc(t.title.replace(/<[^>]*>/g, '').trim());
  nav.innerHTML = '<div class="nav-inner">'
    + toc.map((t) => `<a class="nav-chip" data-target="${t.id}">${label(t)}</a>`).join('')
    + '</div>';
  nav.onclick = (e) => {
    const chip = e.target.closest('.nav-chip'); if (!chip) return;
    const sec = document.getElementById(chip.dataset.target);
    if (sec) sec.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  // scroll-spy: highlight the chip of the section nearest the top of the viewport.
  if (tocObserver) { try { tocObserver.disconnect(); } catch (_) {} }
  const chipFor = {}; $$('.nav-chip', nav).forEach((c) => { chipFor[c.dataset.target] = c; });
  const visible = new Set();
  tocObserver = new IntersectionObserver((entries) => {
    for (const en of entries) {
      if (en.isIntersecting) visible.add(en.target.id); else visible.delete(en.target.id);
    }
    // pick the visible section with the smallest DOM order (topmost) as active
    const active = toc.find((t) => visible.has(t.id));
    $$('.nav-chip', nav).forEach((c) => c.classList.toggle('active', !!active && c.dataset.target === active.id));
    // top inset MUST track the sticky-nav bottom / .rsec scroll-margin-top (128px) so a clicked
    // section becomes the topmost-visible immediately (else the prior section's tail, still in the
    // band, keeps the highlight until you scroll down). Keep -130 in sync with that CSS value.
  }, { rootMargin: '-130px 0px -55% 0px', threshold: 0 });
  toc.forEach((t) => { const s = document.getElementById(t.id); if (s) tocObserver.observe(s); });
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
// Click a tag → highlight rows carrying the same data-hl, dim the rest. Shared by the
// report dep-tree and the pending-deps page (different row selectors).
function applyTagHighlight(scope, key, rowSel) {
  scope.querySelectorAll(rowSel).forEach((row) => {
    row.classList.remove('hl-on', 'hl-dim');
    if (key) row.classList.add(row.querySelector(`[data-hl="${key}"]`) ? 'hl-on' : 'hl-dim');
  });
  scope.querySelectorAll('[data-hl]').forEach((b) => b.classList.toggle('hl-badge-on', !!key && b.dataset.hl === key));
}
function applyDepHighlight(scope, key) {
  applyTagHighlight(scope, key, '.deptree li.leaf, .deptree summary, .dynlib');
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
    const { tree } = await api('/api/depgraph?name=' + enc(name) + '&' + gq());
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

// ===========================================================================
//  DEPENDENCY TOPOLOGY (level 2.5) — runtime dep graph colored by HarmonyOS status
// ===========================================================================
let cyInstance = null;
let topoCurrent = null;       // currently-loaded lib (avoid redundant reloads)
let topoHidden = new Set();   // statuses toggled off via the legend
let topoData = null;          // last-loaded /api/dep-topology payload (for view toggle)
let topoView = 'rollup';      // 'self' (本体) | 'rollup' (含依赖综合)
// the status field a node uses under the current view
const nodeStatus = (n) => topoView === 'rollup' ? (n.rollupStatus || n.status) : n.status;
function ensureCytoscape() {
  if (window.cytoscape) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = '/vendor/cytoscape.min.js';
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('无法加载 cytoscape.min.js'));
    document.head.appendChild(s);
  });
}

async function renderTopology(preselect) {
  setHeader('<a class="btn ghost" href="#/">← 返回库列表</a>');
  let libs = [];
  try { libs = (await api('/api/libraries?' + gq())).libraries.filter((l) => l.latest && l.latest.reportAvailable); } catch (_) {}
  const names = new Set(libs.map((l) => l.name));
  const opts = libs.map((l) => `<option value="${esc(l.name)}"></option>`).join('');
  const initial = preselect && names.has(preselect) ? preselect : (libs[0] && libs[0].name) || '';
  $('#app').innerHTML = `<div class="detail-head"><h1>🕸 依赖拓扑</h1></div>
    <p class="muted">选中一个已分析库，展示它的<strong>运行时依赖</strong>拓扑（直接 + 间接），节点按鸿蒙化状态着色。间接依赖只对已分析的依赖可见。</p>
    <div class="toolbar">
      <label class="pdep-toggle">库：<input id="topoLib" list="topoLibList" placeholder="搜索库名…" value="${esc(initial)}" autocomplete="off" />
        <datalist id="topoLibList">${opts}</datalist></label>
      <span class="topo-view-toggle">视角：
        <button class="btn sm" id="topoViewSelf">本体</button><button class="btn sm" id="topoViewRollup">含依赖(综合)</button></span>
      <span id="topoLegend" class="topo-legend"></span>
    </div>
    <div class="topo-wrap"><div id="topoGraph" class="topo-graph"><p class="muted" style="padding:16px">${libs.length ? '加载中…' : '（无已分析库）'}</p></div>
      <div id="topoDetail" class="topo-detail"><p class="muted">点击节点查看详情。</p></div></div>`;
  const onpick = () => { const v = $('#topoLib').value.trim(); if (names.has(v)) loadTopology(v); };
  $('#topoLib').onchange = onpick;
  $('#topoLib').oninput = () => { if (names.has($('#topoLib').value.trim())) onpick(); };  // datalist selection
  const syncViewBtns = () => {
    $('#topoViewSelf').classList.toggle('primary', topoView === 'self');
    $('#topoViewRollup').classList.toggle('primary', topoView === 'rollup');
  };
  const setView = (v) => { if (topoView === v || !topoData) { topoView = v; syncViewBtns(); return; } topoView = v; syncViewBtns(); redrawTopology(); };
  $('#topoViewSelf').onclick = () => setView('self');
  $('#topoViewRollup').onclick = () => setView('rollup');
  syncViewBtns();
  cyInstance = null; topoCurrent = null; topoHidden = new Set(); topoData = null;
  view.cleanup = () => { if (cyInstance) { try { cyInstance.destroy(); } catch (_) {} cyInstance = null; } };
  if (initial) loadTopology(initial);
}

async function loadTopology(name) {
  if (!name || name === topoCurrent) return;   // skip reloading the same lib (input+change both fire)
  topoCurrent = name;
  const box = $('#topoGraph'); if (box) box.innerHTML = '<p class="muted" style="padding:16px">加载中…</p>';
  let data;
  try { data = await api('/api/dep-topology?name=' + enc(name) + '&' + gq()); }
  catch { if (box) box.innerHTML = '<p class="hint err" style="padding:16px">加载失败</p>'; return; }
  try { await ensureCytoscape(); }
  catch (e) { if (box) box.innerHTML = `<p class="hint err" style="padding:16px">${esc(e.message)}</p>`; return; }
  topoData = data;
  redrawTopology();
}

// re-render legend + graph from the cached topoData under the current view (no refetch)
function redrawTopology() {
  if (!topoData) return;
  const counts = (topoView === 'rollup' ? topoData.rollupCounts : topoData.counts) || {};
  renderTopoLegend(counts);
  drawTopology(topoData);
}

function renderTopoLegend(counts) {
  const el = $('#topoLegend'); if (!el) return;
  el.innerHTML = TOPO_ORDER.filter((s) => counts[s]).map((s) => {
    const st = topoStatusMeta(s); const n = counts[s] || 0;
    const off = topoHidden.has(s) ? ' off' : '';
    return `<button class="topo-leg${off}" data-st="${s}"><span class="dot" style="background:${st.color}"></span>${st.label} <b>${n}</b></button>`;
  }).join('');
  el.querySelectorAll('.topo-leg').forEach((b) => b.onclick = () => {
    const s = b.dataset.st;
    if (topoHidden.has(s)) topoHidden.delete(s); else topoHidden.add(s);
    b.classList.toggle('off');
    if (cyInstance) cyInstance.nodes().forEach((n) => n.style('display', topoHidden.has(n.data('status')) ? 'none' : 'element'));
  });
}

function drawTopology(data) {
  const box = $('#topoGraph'); if (!box) return;
  box.innerHTML = '';
  const elements = [];
  for (const n of data.nodes) elements.push({ data: {
    id: n.id, label: n.label, status: nodeStatus(n), selfStatus: n.status, rollupStatus: n.rollupStatus || n.status,
    ecosystem: n.ecosystem, analyzed: n.analyzed, libName: n.libName, overall: n.overall || '',
    summary: n.summary || '', isRoot: !!n.isRoot, level: n.level || '', rollupLevel: n.rollupLevel || '',
    rollupEffort: n.rollupEffort || null, rollupConfidence: n.rollupConfidence || '',
    rollupUncertain: !!n.rollupUncertain, blockingChildren: n.blockingChildren || [],
    criticalPath: n.criticalPath || [] } });
  for (const e of data.edges) elements.push({ data: { source: e.source, target: e.target } });
  cyInstance = window.cytoscape({
    container: box, elements, wheelSensitivity: 0.2,
    style: [
      { selector: 'node', style: {
        'background-color': (n) => topoStatusMeta(n.data('status')).color,
        label: 'data(label)', color: '#1b2430', 'font-size': 11, 'text-valign': 'bottom',
        'text-margin-y': 3, width: 18, height: 18, 'border-width': (n) => n.data('isRoot') ? 3 : 0,
        'border-color': '#1b2430' } },
      { selector: 'edge', style: {
        width: 1, 'line-color': '#c2cad6', 'target-arrow-color': '#c2cad6',
        'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'arrow-scale': 0.8 } },
      { selector: 'node:selected', style: { 'border-width': 3, 'border-color': '#3b6cf6' } },
      { selector: 'edge.critpath', style: {
        width: 2.5, 'line-color': '#d65745', 'target-arrow-color': '#d65745', 'z-index': 9 } },
    ],
    layout: { name: 'breadthfirst', directed: true, roots: ['lib:' + data.root], spacingFactor: 1.15, padding: 20 },
  });
  cyInstance.on('tap', 'node', (ev) => showTopoDetail(ev.target.data()));
  cyInstance.nodes().forEach((n) => n.style('display', topoHidden.has(n.data('status')) ? 'none' : 'element'));
  // 高亮根节点的关键路径链（serve-time rollup 派生：贡献人天最多的依赖链）
  const rootNode = data.nodes.find((n) => n.isRoot);
  const cpChain = (rootNode && rootNode.criticalPath) || [];
  let prev = rootNode ? rootNode.id : null;
  for (const step of cpChain) {
    const from = prev, to = step.id;
    cyInstance.edges().forEach((e) => {
      if (e.data('source') === from && e.data('target') === to) e.addClass('critpath');
    });
    prev = to;
  }
}

function showTopoDetail(d) {
  const el = $('#topoDetail'); if (!el) return;
  const selfM = topoStatusMeta(d.selfStatus), rollM = topoStatusMeta(d.rollupStatus);
  const dot = (m) => `<span class="dot" style="background:${m.color}"></span> ${m.label}`;
  const differs = d.rollupStatus && d.rollupStatus !== d.selfStatus;
  const blockers = Array.isArray(d.blockingChildren) ? d.blockingChildren : [];
  const blockHtml = blockers.length ? `<div class="topo-block"><b>因依赖拉高分级：</b><ul>${blockers.map((b) => {
    const via = (b.viaSymbols || []).length ? `经 <code>${b.viaSymbols.map(esc).join('</code> <code>')}</code>`
      : b.basis === 'scope' ? '（按依赖范围保守计入）' : '';
    const link = b.libName ? `<a href="#/lib/${enc(b.libName)}">${esc(b.child)}</a>` : esc(b.child);
    const days = fmtDays(b.days) ? ` <span class="muted">${fmtDays(b.days)}</span>` : '';
    return `<li>${link} → ${esc(topoStatusMeta(b.childClass).label)}${days} ${via}</li>`;
  }).join('')}</ul></div>` : '';
  const cpath = Array.isArray(d.criticalPath) ? d.criticalPath : [];
  const cpathHtml = cpath.length ? `<div class="topo-block"><b>关键路径（按子树人天）：</b><ol class="topo-cpath">${cpath.map((p) => {
    const link = p.libName ? `<a href="#/lib/${enc(p.libName)}">${esc(p.label)}</a>` : esc(p.label);
    const m = topoStatusMeta(p.class);
    return `<li>${link} <span class="dot" style="background:${m.color}"></span>${esc(m.label)}${fmtDays(p.days) ? ` <span class="muted">${fmtDays(p.days)}</span>` : ''}</li>`;
  }).join('')}</ol><p class="hint" style="margin:2px 0 0">先移植链尾（最深）依赖，逐级向上解锁。</p></div>` : '';
  el.innerHTML = `<div class="topo-d-name"><b>${esc(d.label)}</b> ${d.ecosystem ? `<span class="chip eco-chip">${esc(ECO_LABELS[d.ecosystem] || d.ecosystem)}</span>` : ''}</div>
    <div class="kv">
      <b>本体分级</b><span>${dot(selfM)}</span>
      <b>含依赖(综合)</b><span>${dot(rollM)}${d.rollupUncertain ? ' <span class="badge gray" title="存在未分析的子依赖，综合结论可能偏乐观">含未分析依赖</span>' : ''}</span>
      <b>是否已分析</b><span>${d.analyzed ? '是' : '否（未分析）'}</span>
      ${d.level ? `<b>本体难度</b><span>${esc(LVL_LABELS[d.level] || d.level)}</span>` : ''}
      ${d.rollupLevel ? `<b>综合难度</b><span>${esc(LVL_LABELS[d.rollupLevel] || d.rollupLevel)}${fmtDays(d.rollupEffort) ? ` <span class="muted">(${fmtDays(d.rollupEffort)})</span>` : ''}${d.rollupConfidence ? ` <span class="muted">置信 ${CONF_LABELS[d.rollupConfidence] || d.rollupConfidence}</span>` : ''}</span>` : ''}
      ${d.overall ? `<b>是否可适配</b><span>${esc(OVERALL_LABELS[d.overall] || d.overall)}</span>` : ''}
    </div>
    ${differs ? '<p class="hint">综合分级高于本体，因为它（用到的）依赖的适配等级更高，见下。</p>' : ''}
    ${cpathHtml}
    ${blockHtml}
    ${d.summary ? `<p class="muted">${esc(d.summary)}</p>` : ''}
    ${d.analyzed && d.libName ? `<a class="btn sm primary" href="#/lib/${enc(d.libName)}">查看报告 →</a>` : '<p class="hint">该依赖尚未分析，去「待分析依赖」分析它以解锁其子依赖与分级。</p>'}`;
}

// Initial route render — kept last so all module-level state above is initialized.
navigate();
