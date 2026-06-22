---
name: dependency-analysis
description: Identify and explain a third-party library's dependencies across ecosystems (Python, C/C++, Java, JS/TS) by reading manifest and build files, then reasoning about what each dependency is and why it's used. Distinguishes runtime vs dev/test/build deps. Use for dimension 6 of PC library analysis. Model reasoning over manifests, not a fixed parser.
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

## How to analyze
1. Find every manifest (record their paths in `manifests`).
2. Extract each declared dependency with its **ecosystem**, **scope**
   (runtime / dev / test / optional / build / peer) and **version constraint**.
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
     "declared_in": ["External/CoordGen/CMakeLists.txt"]},
    {"name": "AvalonTools", "ecosystem": "cpp", "scope": "optional", "version": "2.0.5-pre.3",
     "purpose": "额外指纹与结构检查", "acquisition": "vendored", "locality": "local",
     "source": "仓库内 External/AvalonTools", "declared_in": ["External/AvalonTools/CMakeLists.txt"]}
  ],
  "notes": "Also vendors 'chardet' under src/; pytest is dev-only."
}
```

## Rules
- Prefer runtime deps in the headline `count`; keep dev/test/build but scoped.
- Don't list transitive deps unless lockfiles are the only source and the user
  needs them — say so in `notes` if you do.

## 自我发现（反哺）
新造的 `acquisition` 值、推荐清单没覆盖的依赖场景、难归类的歧义，追加到顶层 `meta.observations`：
`{dimension:"dependencies", field:"acquisition", kind, value, rationale}`，供面板「模型观察」页人工反哺。
