---
name: dependency-analysis
description: Identify and explain a third-party library's or application's dependencies across ecosystems (Python, C/C++, Java, JS/TS) by reading manifest and build files, then reasoning about what each dependency is and why it's used. Distinguishes runtime vs dev/test/build deps. Use for dimension 6 of PC library/application analysis. Model reasoning over manifests, not a fixed parser.
---

# Dependency analysis (model-driven)

Read the dependency manifests and build files, then produce a clean list with
scope and purpose. A rigid parser misses bundled headers, transitive build
deps, and ecosystem-specific quirks — reason about them.

## 主旨与原则
目标：把这个库的**第一层依赖关系**说清楚 —— 有哪些依赖、各自什么来源、怎么集成进来的。
**输出契约（下方 Output）是唯一硬约束。** 下面的 manifest 清单与 `acquisition` 取值是
**推荐起点，不是封闭清单**：`acquisition` 是**开放词表**，没有合适的就**自造一个简洁小写值**
（如 `conda`/`apt`/`cpm`/`git_subtree`/`runtime_download`）并写进 `meta.observations`；而
`locality`(本地/远端/系统) 是**稳定闭轴，必须显式给**，保证新造的 acquisition 仍能正确归类展示。
方法仅是参考思路，可按仓库实际调整。

**粒度硬规则：一个可独立安装的包 = 一条依赖。** `name` 必须是**单一规范包名**（manifest/
registry 里的样子），**禁止**用 `/`、`,`、`+`、`、` 把多个不同的包拼进一个 `name`（下游的
已鸿蒙化查询/仓库解析/依赖聚合/依赖树/导出都以 `name` 为单一包名）。

## Manifests by ecosystem
- **Python**: `requirements*.txt`, `pyproject.toml` (`[project].dependencies`,
  `[project.optional-dependencies]`, poetry/PDM tables), `setup.py`
  (`install_requires`/`extras_require`), `setup.cfg`, `Pipfile`, `environment.yml`.
- **C/C++**: `CMakeLists.txt` / `*.cmake` (`find_package`, `target_link_libraries`,
  `FetchContent`, `ExternalProject`), `vcpkg.json`, `conanfile.txt`/`.py`,
  `Makefile` (`-l` link flags, `pkg-config`), git submodules (`.gitmodules`),
  vendored `third_party/`/`extern/` trees.
- **Java**: `pom.xml` (`<dependencies>`, distinguish `<scope>`), `build.gradle`(`.kts`)
  (`implementation`/`api`/`testImplementation`/`compileOnly`), `ivy.xml`.
- **JS/TS**: `package.json` (`dependencies` / `devDependencies` /
  `peerDependencies` / `optionalDependencies`), workspace/monorepo manifests.
- **应用（application）的依赖栈常不是单一 manifest**：要额外找——模块图（NetBeans
  `nbproject/project.xml` 的 `<module-dependencies>`/`<code-name-base>`）、构建期下载清单
  (`binaries-list`)、捆绑/随包分发的 jar/so/dll（`release/modules/ext/*.jar`、`lib/`、`external/`）、
  vendored 库、捆绑运行时(JRE/Node)。把应用**运行时实际捆绑/加载**的第三方库作为 `scope: runtime`
  依赖收录（locality 据来源：local 内嵌 / remote 下载 / system 预装），这样递归分析与依赖拓扑
  能照常下钻这些库。

## How to analyze
1. Find every manifest (record their paths in `manifests`).
2. Extract **each** declared dependency with its **ecosystem**, **scope**
   (runtime / dev / test / optional / build / peer) and **version constraint**.
   **每行/每个声明一个包 = 一条**：requirements 里钉版本的 7 个 `pytest-*` 插件 = **7 条**，
   不要因为"都属测试/同族"就合并成一条；要表达归属就写在各自的 `purpose`（如"pytest 并发
   插件"），而不是把多个包名合进一个 `name`。
   `ecosystem` is the **language world only** (cpp/c/python/java/nodejs/rust/go/dotnet/other) —
   use `other` for non-language deps (data files, generic tools). Do NOT put role
   values like `tool`/`data` in `ecosystem`; a dep being a **build tool**
   (SWIG/Bison/Flex/codegen) is expressed by `scope: build` (its ecosystem is its
   implementation language or `other`).
3. For notable runtime deps, add a short **purpose** ("HTTP transport",
   "JSON parsing", "test framework") inferred from name + how it's imported/used.
4. Separate the project's **own** name and standard-library/system packages from
   real third-party deps. C/C++ `find_package(Threads)`, `PkgConfig`, the
   project itself, etc. are build plumbing — mark scope `build` or drop.
   **生产范围**：只被**测试或示例/演示代码** import 的依赖**不是 runtime** —— scope 记
   `test`/`dev`，或（仅示例用、与库本体无关时）不收。借 `metrics.json` 的
   `top_dirs`/`test_example_dirs` 判断目录归属，并补判按功能命名的 demo 目录。整仓为示例/
   教程集合时，runtime 依赖据库本体认定（通常只剩框架本身）。
5. Note **vendored** dependencies (copied into the tree) and **git submodules**
   separately — they won't appear in a package manifest.
5b. **C/C++ first-level completeness** — deps aren't only in `find_package`/`FetchContent`.
   Also capture: **pkg-config** (`pkg_check_modules`, `pkg-config --libs/--cflags`),
   **raw `-l` link flags** (Makefile, CMake `target_link_libraries(... -lfoo)` /
   `LINK_LIBRARIES` / `LDFLAGS`), and **third-party/system libs used only via
   `#include`** with no build-file declaration (e.g. `#include <zlib.h>` but no
   `find_package(ZLIB)`). These are usually `acquisition: system`; put the Makefile /
   source file in `declared_in` and note "链接标志 / 头文件包含" in `source`.
6. For each dep set **`acquisition`** (OPEN vocab — HOW the build obtains it) and the
   **`locality`** stable axis (closed — set it explicitly). Recommended acquisition
   values & their usual locality:
   - `find_package(X)` / expected pre-installed → `system` · locality `system`
   - CMake `FetchContent_*` → `fetchcontent` · `remote`
   - `ExternalProject_Add` w/ URL or custom download-build (e.g. `downloadAndCheckMD5`)
     → `download_build` · `remote`
   - `.gitmodules` → `submodule` · `remote`
   - source copied into the tree (`External/`/`third_party/`/`extern/`) → `vendored` · `local`
   - vcpkg/conan/pip/npm/maven coordinate → `package_manager` · `remote`
   - binary `.so`/`.dll`/`.a`/`.lib` shipped in repo → `prebuilt_binary` · `local`
   If none fits, **coin a concise lowercase `acquisition`** (e.g. `conda`, `apt`, `cpm`),
   set the best-matching `locality`, and record the new value in `meta.observations`.
7. Fill **`source`** — WHERE it is obtained from: the download URL, the registry,
   `"系统(find_package，需预装)"`, or the in-tree path (中文).
8. Fill **`declared_in`** — the repo file(s) that declare how it is integrated:
   the CMakeLists with `find_package` / `FetchContent_Declare` / `ExternalProject_Add`
   / `target_link_libraries`, a `.gitmodules` entry, or a requirements/manifest line.
   This answers "仓库里有没有声明它是怎么集成进来的".
9. Fill **`used_symbols`** (best-effort, 选填) — 本库**实际调用到**的该依赖的公共符号/API
   名（如 `cairo_create`、`BIO_new`、`numpy.ndarray`）。用 codegraph（`callees`/`search`）或
   grep 该依赖的头文件/导出符号在本仓的调用点取一组代表性符号即可，不必穷举。这是 dim-9
   **自底向上综合**用：服务端把它与该依赖（子库）`harmony_adaptation.unadaptable_apis[].public_entry`
   求交，命中才把子库的不可适配计为本库阻碍——**本库没调到子库的不可适配 API 就不阻塞本库迁移**。
   只对**非系统、可分析**的依赖填；系统库 / 拿不准用法时留空（综合会回退到依赖 scope）。
   - **命名约定（务必与子库 `public_entry` 同一形式，否则 rollup 求交漏判）**：填**调用方引用该符号时的名字**——
     Python `module.func` / `Class.method`；JS/TS 导出名（`pkg.export`/具名导出）；C/C++ 自由函数名或 `Class::method`；
     Java `Class.method` 或 `pkg.Class`。（服务端 `symKeys` 会再做大小写/尾段归一，但尽量对齐主名。）
10. Fill **身份字段**（best-effort，让"依赖名 ≠ 源码仓名"也能关联到已分析库）——
    - **`source_repo`**（最强键）：该依赖的上游**源码仓库 URL**。能从 manifest/lock（pip `git+`、npm `repository`、
      Cargo/Go module 路径）或常识判断就填，**尤其当 `name` 是别名/接口名/缩写**：`find_package(PNG)`→
      `https://github.com/glennrp/libpng`、`find_package(ZLIB)`→`https://github.com/madler/zlib`。拿不准留 null。
    - **`registry_name`**：规范注册表包名（当 `name` 不是规范包名时，如 CMake 模块名 `PNG` 的 registry 名）。
    - **`import_names`** / **`aliases`**：实际 import 名（Pillow→PIL）/ 其它已知名。无则省略。
    服务端按 `source_repo`（owner 限定的规范 URL）优先关联，再退回 `name`/`registry_name`/`aliases` 变体——填得越准，依赖树/拓扑/待分析依赖关联越对。

## Output (fills report `dependencies`)
```json
{
  "count": 5,
  "manifests": ["pyproject.toml", "requirements-dev.txt"],
  "by_ecosystem": {"python": ["urllib3", "certifi"]},
  "dependencies": [
    {"name": "Qt6", "ecosystem": "cpp", "scope": "optional", "version": null,
     "purpose": "MolDraw2D Qt 后端", "acquisition": "system", "locality": "system",
     "source": "系统(find_package，需预装 Qt6)", "declared_in": ["Code/GraphMol/MolDraw2D/Qt/CMakeLists.txt"]},
    {"name": "coordgen", "ecosystem": "cpp", "scope": "optional", "version": "3.0.2",
     "purpose": "2D coordinate generation", "acquisition": "download_build", "locality": "remote",
     "source": "https://github.com/schrodinger/coordgenlibs（未找到时 downloadAndCheckMD5 下载源码内嵌编译）",
     "declared_in": ["External/CoordGen/CMakeLists.txt"], "used_symbols": ["sketcherMinimize", "CoordgenMinimizer"]},
    {"name": "AvalonTools", "ecosystem": "cpp", "scope": "optional", "version": "2.0.5-pre.3",
     "purpose": "额外指纹与结构检查", "acquisition": "vendored", "locality": "local",
     "source": "仓库内 External/AvalonTools", "declared_in": ["External/AvalonTools/CMakeLists.txt"],
     "registry_name": "AvalonToolkit", "source_repo": "https://github.com/rdkit/ava-formake"}
  ],
  "notes": "Also vendors 'chardet' under src/; pytest is dev-only."
}
```

## Rules
- **一包一条，`name` 不拼接**：
  - ❌ 错：`{"name": "pytest / pytest-asyncio / pytest-cov / pytest-repeat / pytest-rerunfailures / pytest-timeout / pytest-xdist"}`（7 个独立包拼成一条）。
  - ✅ 对：拆成 `pytest`、`pytest-asyncio`、`pytest-cov`… 各一条，各带自己的 `version`。
  - **例外**：`name` 里出现 `/` 仅在它表示**同一个依赖的可选版本/形态**时允许，**不是**多个不同包——
    如 `Qt5/Qt6`（二选一的同一可选依赖）、`Java JDK / JNI`（JDK 经 JNI 访问，仍是一个东西）。
    判据：**各自有独立版本号 / 各自在 registry 单独存在 ⇒ 必须拆**；仅是"同一依赖的别名/可选实现" ⇒ 可合并为一条。
- Prefer runtime deps in the headline `count`; keep dev/test/build but scoped.
- `dependencies[].harmony_adapted` / `harmony_adapted_source` are **script-stamped**
  (`scripts/harmony_adapted.js`, an OpenHarmony-PC-mirror lookup) — leave them to the
  script, do NOT set them from guesses.
- Don't list transitive deps unless lockfiles are the only source and the user
  needs them — say so in `notes` if you do.

## 自我发现（反哺）
新造的 `acquisition` 值、推荐清单没覆盖的依赖场景、难归类的歧义，追加到顶层 `meta.observations`：
`{dimension:"dependencies", field:"acquisition", kind, value, rationale}`，供面板「模型观察」页人工反哺。
