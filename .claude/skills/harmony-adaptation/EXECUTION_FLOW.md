# harmony-adaptation（dim-9）执行流程 + 设计评估

> 本文件是 `SKILL.md` 的**配套说明**：讲清 dim-9 在整条分析流水线里怎么被驱动、内部怎么推理、
> 哪些字段是模型产出、哪些由归一派生，并附一份设计评估与优化清单。**只读文档，不参与分析产出**。
> 对应源码：`.claude/agents/pc-lib-analyzer.md`（编排）、`scripts/report_normalize.py`（归一，单一真相源）、
> `web/server.js`（等价 JS 镜像 + serve-time rollup）、`references/report_schema.json`（输出契约）。

---

## 1. 宏观流程：dim-9 在流水线中的位置

dim-9（harmony_adaptation）是**综合层的最后一维**，消费前面所有维度的产出，**不重扫源码**。

```
输入：git URL / 本地 checkout
  │
  └─► git clone --depth 1  ──►  metrics.py  ──►  metrics.json
        （唯一被授权的计数脚本）              dims 2-4：languages / code_metrics / tests
                                             + platform_adaptation / platform_branches
                                             + arch_specific / dir_loc（dim-9/12 的机械信号）
  │
  ├─► 特征层（客观描述"碰了什么"，各自事实的唯一权威源）
  │     dim1 function_summary   dim5 license      dim6 dependencies
  │     dim7 native_api         dim8 runtime_surface + build_env
  │
  ├─► 3a  harmony_adapted.js 盖章  ──►  dependencies[].harmony_adapted
  │       （已鸿蒙化的依赖不计阻碍——这一步必须在 dim-9 之前）
  │
  ├─► 综合输入层（必须先于 dim-9；见 pc-lib-analyzer.md「两层契约」）
  │     dim10 capability_profile   GUI/3D/媒体/硬件 场景 + harmony_status
  │                                （★查 harmony-pc-capabilities.json 定这四类状态，只在此做一次）
  │     dim11 cloud_services        是否涉及云端 + 推测厂商
  │     dim12 code_partition        生产代码按复用性分 4 桶 + LOC（person_days 的量化底座）
  │
  ├─► ★★  dim9 harmony_adaptation（pc-lib-analyzer.md step 3b）——纯综合、不重扫源码
  │        内部 12 步，见 §2；产出写到 blocks/harmony_adaptation.json
  │
  ├─► 3c  组装前自检（跨维一致性，模型侧）
  │
  ├─► assemble_report.py
  │       ├ splice metrics（languages/code_metrics/tests 来自 metrics.json，模型不写）
  │       ├ merge blocks/*.json（文件名=顶层键，内容=该块的值）
  │       └ 内部调用 report_normalize.py（归一，见 §3）
  │            → report.json + meta.harmony_warnings{code,class} + meta.normalized_version=4
  │
  ├─► 4b  自我复核 harmony_warnings（单趟）
  │       只处理 class=="actionable"：真漏→带 file:line 补源维度块；误报→meta.harmony_warnings_dismissed
  │       →重跑 assemble（第 2 趟归一，扣除 dismissed、落盘干净 warnings + _reviewed）
  │
  └─► serve-time（web/server.js，/api/dep-topology，不落盘）
        rollupAdaptation 沿依赖 DAG 自底向上：rollupClass / rollupEffort / criticalPath
        + effective_class 5 档拓扑上色（存量报告不重跑即有）
```

**关键时序**：dim-10/11/12 按维度编号在 dim-9 之后，但**执行**必须在 dim-9 之前（它们是 dim-9 的综合输入）。
agent 文件用 step 3（列 dim10/11/12，各标「BEFORE dim 9」）→ step 3b（dim-9）把执行顺序钉死。

---

## 2. 微观流程：dim-9 内部 12 步（SKILL.md「评估步骤」）

顺序：**框定（1-4）→ 产问题清单（5-9）→ 量化（10-11）→ 收尾（12）**。移植分级的三档/两维/可适配判据/
常见误判是**核心框架**（SKILL.md 开篇定义一次），下面步骤只引用不重述。

```
框定   1  选部署模型         library.kind → 模型 A(库) / B(ArkTS 应用) / C(整包桌面应用)
      2  由 ecosystem 定基调  python/node/java/rust/go/cpp… → 运行时是否已移植 → 档位基调
      3  消费 capability_profile   GUI/3D/媒体/硬件 状态直接采用(不重判) → 翻成 blocker/effort
                                    ★单一登记源：dim-10 判"鸿蒙有没有"，dim-9 判"于是要做什么"
      4  目标匹配             对照 harmony-pc-capabilities.json → target_assumptions
                              (+capability_key 命中叶 id；对不上 caps → caps_gap observation 反哺)
                              unknown 且 required → confidence 降至 medium，禁臆断
──────────────────────────────────────────────────────────────────────────────────────
产清单 5  逐组消费特征 → blockers   仅 dim-10 覆盖不到的面(平台 I/O/syscall/subprocess/
                                    /proc·注册表·设备伪文件/arch·SIMD/构建工具链/JDK 内部·attach)
      6  判 remediation_status + remediation   @ohos 平替 / needs_permission / partial / unavailable
                                          (具体 API 名优先查鸿蒙文档技能，≤10 次；文档存在≠PC 可用)
      7  填 unadaptable_apis   API 粒度；functionality_class 必填(core/platform_specific)
                              public_entry 用父库引用名(rollup 求交靠它)；自底向上：先 ua→blocker→ta
      8  定 porting_class      走判定树给三档"下限"；归一据 dim-12 桶 + ua 只升不降
      9  required_permissions  ohos.permission.*；该轴状态用 restricted(非 partial)
──────────────────────────────────────────────────────────────────────────────────────
量化  10  effort.person_days   区间[lo,hi]；首要依据 dim-12 needs_adaptation 桶 LOC
                              + breakdown 分项(gui/deps_porting/…) + 三机械信号
                              (platform_adaptation / platform_branches / arch_specific)
      11  critical_dependencies 有序：未鸿蒙化 + 阻塞核心推进的依赖；refs 引 bk:/ua:/ta:
──────────────────────────────────────────────────────────────────────────────────────
收尾  12  compatible + key_tasks   可顺利移植的部分 + 落地关键工作项
```

---

## 3. 契约边界：模型产出 vs 归一派生（本设计的精髓）

`scripts/report_normalize.py` 在 assemble 时**确定性派生**一批字段并**覆盖**模型值，`web/server.js` 是
字节级镜像（全语料 parity 测试断言二者一致），只用于升级旧版存量报告。**报告一出生即归一 + 盖 `normalized_version`**，
面板 / Excel / report.json 因此同源同值。

| 模型（dim-9）产出——可观测量 | 归一确定性派生 + 覆盖（单一真相源） |
|---|---|
| `porting_class`（三档**下限**） | `porting_class`：**只升不降**（据 dim-12 `needs_adaptation`/`unadaptable` 桶、`unadaptable_apis` 非空、任一 `blockers[].adaptability` partial/unadaptable）；原判留存 `porting_class_model`，升档时记 `porting_class_adjusted` |
| `unadaptable_apis[].functionality_class`（core/platform_specific，必填） | `adaptation_assessment`：core/platform_specific 两维小结 + `effective_class`（5 档：no_adaptation / recompile_only / needs_adaptation / needs_adaptation_platform_partial / needs_adaptation_core_partial）+ `overall`（adaptable / adaptable_with_tailoring / core_blocked） |
| `effort.person_days:[lo,hi]` | `effort.level`（5 档，`effective_class` floor × person_days 上界分桶，取高——难度与分级自洽、不漂移） |
| `effort.breakdown` 的 gui/deps_porting/build_system/testing_verification/packaging | `effort.breakdown` 的 **recompile** & **api_adaptation**（= 桶 LOC ÷ 速率，速率读 `.panel-settings.json`）；**一旦有 breakdown，`person_days` 总量重算为各分项之和** |
| `blockers` / `target_assumptions` / `required_permissions` / `critical_dependencies` / `compatible` / `key_tasks` / `summary` / `notes` | `meta.harmony_warnings`{code,class} / `meta.harmony_warnings_reviewed`；`meta.normalized_version` |

归一顺序（`normalize_report`）：`normalize_dim8` → `normalize_code_partition`（先于 harmony，好让 LOC 喂给 dim-9 派生）
→ `normalize_harmony` → `normalize_license` → `validate_*` 产 warnings → dismissed/reviewed 分流 → 盖版本号。

**serve-time rollup（server.js only，不落盘、不镜像进 Python）**：`rollupAdaptation` 沿跨报告依赖 DAG
worst-wins（子库 unadaptable API 只在 `parent.used_symbols ∩ child.public_entry` 非空时上抛），
产每节点 `rollupClass`/`rollupEffort`/`rollupConfidence`/`criticalPath`——因为它依赖 live 的 harmony-mirror
盖章与拼装的拓扑，故意留在 serve-time。

---

## 4. 设计评估

### 合理、值得保留的地方
- **"模型推理 / 脚本派生" 单一真相源**：模型只出可观测量，一切派生轴由 `report_normalize.py` 确定性算出并
  **只升不降**钳制——落盘不可能出现自相矛盾的 porting_class；Python 权威 + JS 镜像 + parity 测试保证多入口同值。
- **两层契约**（特征层 vs 综合层）消除重复分析：GUI/3D/媒体/硬件的鸿蒙状态只在 dim-10 查一次，dim-9 直接消费。
- **单一登记源 + id 交叉引用**（`caused_by`/`manifests_as`/`source_capability`/`refs`）：同一事实只登记一次，
  其余引用——避免 rollup 把 person_days 双计。
- **自我复核闭环（4b）**：护栏严谨——新增须带生产代码 file:line 证据、误报走 `harmony_warnings_dismissed`、
  `info` 类不可驳、单趟不清零。
- **反哺闭环**：`meta.observations` 词表反哺 + `capability_key`/`caps_gap` 让目标能力参考随分析量增长而完善。
- **鸿蒙文档技能核查**有降级链（skill 工具 → Grep 目录 → 仅 caps JSON）与护栏（文档存在 ≠ PC 可用，caps JSON 优先）。

### 已发现的问题与本次处置（P0/P1/P2）

| 级别 | 问题 | 处置 |
|---|---|---|
| **P0** | dim-9 从旧 **5 值** porting_class（`needs_adaptation_full/partial`/`infeasible` + `feasibility`/`recommended_path`）重构为 **3 值** 时，**没同步驱动它/喂它的文件**：`pc-lib-analyzer.md`、`code-partition/SKILL.md`、`capability-profile/SKILL.md`、`report_schema.json:386` 仍指示模型产旧值——与 schema enum 和 SKILL.md 直接矛盾，诱导模型少填 `functionality_class`。 | ✅ **已修**：四处指令位对齐 3 值 + 强调 `functionality_class` 必填。归一的 `LEGACY_PCLASS_MAP`、JS 镜像、测试 fixture、"替代旧 feasibility"派生字段文档等**向后兼容资产刻意保留不动**。 |
| **P1** | SKILL.md 步骤编号 `00/0c/0/0b…` 颠倒（多次插入的累积痕迹），核心判据（三档边界/可适配判据/常见误判）在「主旨」与「step 5」各讲一遍，"你不必填/归一覆盖"散落 ~8 处。 | ✅ **已修**：① 开篇加「模型产出 / 归一派生」边界总表；② 核心框架合并为唯一权威段；③ 步骤重编号 **1..12**（逻辑序：框定→产清单→量化→收尾）。 |
| **P2** | ① `breakdown` 一旦产出即丢弃模型整体 person_days、重算为分项和——原文隐晦；② 三个字段都叫 `harmony_status`（场景/权限/阻碍），权限轴用 `restricted`、场景轴用 `partial`，易误填。 | ✅ **已修**：①在边界表醒目标注；②**v6 彻底改名消除碰撞**：`required_permissions[].harmony_status`→`grantability`、`blockers[].harmony_status`→`remediation_status`，只有 `capability_profile.scenarios[].harmony_status` 保留原名（归一 idempotent 迁移存量）。 |

### 后续修复：`unadaptable_apis[].public_entry` 推导缺口（用户发现）
`public_entry`（rollup 自底向上求交的唯一键）**无上游来源**——`native_api.apis[]` 只记调用点(file:line)、不记"哪个公共函数路由到它"，
schema 里 `public_entry` 只在 `unadaptable_apis` 自己的定义出现；step 7 原先只给命名约定、没给推导方法，叠加强口径「不重扫」→ 模型只能猜 → rollup 漏判。
**已按 Option A 修复**：step 7 补推导法（以 `native_api.evidence` 为种子、codegraph 向上追到公共入口，与 step 10「samples 当追踪种子」同一手法），
并在开篇 + Rules 澄清「不重扫」= 不重新发现/推导特征事实、查预建索引把已知调用点映射到公共入口不算重扫。**纯 prompt 改动，未动 schema/归一/rollup**。

### 悬留权衡（需你拍板）
- **篇幅**：目标曾定 <350 行，实测重构后 **446 → 464 行**（略增）。原因：边界总表是净新增的清晰度，而框架的
  真实重复量比预估少（判定树/常见误判原本只出现一次）。**内容保全审计确认无任何语义丢失**，此处「篇幅收敛」与
  「语义 100% 保全」两个目标直接冲突——按"不静默删除承重 prompt 内容"择稳。若确需更短，可选：
  (a) 把 Output 的 6 个变体示例移到本文件、SKILL.md 只留主示例；(b) 精简「目标侧 API 事实核查」的操作细节。
  两者都会牺牲一点**技能内**的即时 recall。默认维持现状。
- **step 顺序的 fill-order 张力**：blockers(step 5) 在 unadaptable_apis(step 7) 之前，但 step 7 的
  "自底向上填写顺序"要求先填 ua 再回填 blocker 的 `manifests_as`——此为原技能既有约定（靠该 note 消解），
  重构保留原状、未新增矛盾。

---

## 5. 相关一致性告警（归一产、面板「数据一致性提示」展示）
dim-9/12 相关的 `actionable` 告警（真漏用，需 4b 复核）：`cap_miss` / `scenario_no_dim9` / `scenario_no_evidence` /
`cloud_miss` / `cloud_no_internet` / `ua_func_class_defaulted`（漏标 functionality_class）/ `cp_unadapt_no_ua` /
`ua_no_cp_bucket`（dim-9↔dim-12 unadaptable 登记对不齐）/ `*_ref:*`·`ta_unref`·`critical_dep_*`（悬空引用）/
`perm_dangling_cap` / `conf_high_unknown` / `perm_unavail_noblocker`。
`info` 类（归一已确定性修好、**不处理**）：`pclass_adjusted` / `recompile_no_native` / `ua_pclass` /
`cp_loc_coverage` / `cp_unadapt_pclass` / `cp_needs_full` / `effort_breakdown`。
