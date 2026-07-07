---
name: runtime-environment
description: Analyze what a library or application needs from its host environment at runtime (network, filesystem, environment variables, subprocesses, devices) and its build/toolchain requirements (language standard, compiler extensions, runtime version, supported OS/arch). Use for dimension 8 of PC library/application analysis. Model reasoning over source and build files, descriptive only.
---

# Runtime & build environment (model-driven)

Two complementary, **descriptive** views (no adaptation advice):
- `runtime_surface` — what the code reaches for in the HOST at runtime, beyond the
  libraries it links (those are dim 6) and the APIs it calls (those are dim 7).
- `build_env` — what is needed to build/run it: language standard, compiler
  extensions, runtime version, build system, and supported OS/arch.

Confirm by reading call sites; cite file (+line where useful) in `evidence`. Ignore
vendored/third-party subtrees and test fixtures — report the library's OWN needs.

## 主旨与原则
**输出契约（下方 Output）是唯一硬约束。** 下面的「what to look for」是**推荐起点，不是封闭清单** ——
遇到清单外的宿主交互（如 IPC/共享内存/时钟源/特殊设备）或工具链特性，照常归到最贴近的字段，
必要时在 `meta.observations` 记录。描述性，不给适配建议。

## runtime_surface — what to look for
- **env_vars**: `getenv`/`std::getenv`, Python `os.environ`/`os.getenv`, Java
  `System.getenv`, Node `process.env`. Record the variable name + why it's read
  (e.g. RDKit's `RDBASE`, `COMBICHEM_ROOT`).
- **network**: socket creation, bound/listened ports, HTTP/gRPC clients, hard-coded
  hosts/URLs, DNS lookups.
- **filesystem**: config/data files, model/locale/resource files loaded at runtime,
  temp dirs, hard-coded absolute paths, home-dir lookups.
- **subprocess**: `exec*`/`posix_spawn`/`system`, Python `subprocess`/`os.system`,
  Java `Runtime.exec`/`ProcessBuilder`, Node `child_process`, Win32 `CreateProcess`.
- **devices**: `/dev/*`, GPU/accelerator handles, serial/USB, camera/audio.
- **services**（多见于 **application**）：应用集成/对接的外部服务或守护进程——attach 其他 JVM
  (`com.sun.tools.attach`)、JMX、jstatd、数据库/消息队列连接、本机 IPC/socket 服务。库通常 []。

## build_env — what to look for
- **language_standard**: `CMAKE_CXX_STANDARD`/`-std=c++NN`, `python_requires`,
  `<maven.compiler.release>`, `edition` (Rust), `go` directive.
- **compiler_extensions**: `__attribute__`, `#pragma`, `__declspec`, `__builtin_*`,
  GCC/Clang/MSVC-specific flags or intrinsics.
- **runtime_version**: minimum interpreter/VM/runtime version.
- **build_system**: CMake / Make / setuptools / Maven / Gradle / Cargo / npm.
- **platforms**: OS/arch the project supports — infer from `#ifdef _WIN32`/`__APPLE__`/
  `__linux__` branches, CI matrices (`.github/workflows`), packaged wheels
  (`cp3x-*_x86_64` / `aarch64`), and manifest classifiers.
- **entry_points**（应用必填，库通常 []）：应用如何被启动——启动器脚本(`bin/*.sh`/`*.bat`)、
  原生 launcher(`*.exe`/C++ launcher 源码)、`main`/`Main` 类、框架托管启动模块（如 NetBeans
  startup）、Python `console_scripts`、systemd/service 单元。标 `type` 与 `evidence`。
- **packaging**（应用）：如何构建/打包/分发给终端用户——installer / zip 分发(如 Ant `build-zip`) /
  AppImage / 容器镜像 / 应用商店包 / 无（库）；是否**捆绑运行时**(JRE/Node)。

## Output (fills report `runtime_surface` + `build_env`)

**⚠️ 这是两个独立的 block 文件，不是一个合并对象。** 下面示例用一个 JSON 同时展示两块只为对照——
落盘时必须拆成两个文件：`blocks/runtime_surface.json` 的内容**只**是 `runtime_surface` 的值
（顶层键就是 `summary`/`network`/`filesystem`/`env_vars`/`subprocess`/`devices`/`services`），
`blocks/build_env.json` 的内容**只**是 `build_env` 的值（顶层键就是 `language_standard`/
`runtime_version`/`build_system`/`compiler_extensions`/`platforms`/`entry_points`/`packaging`/`notes`）。
**切勿**把两块合并写进同一个文件，**切勿**在文件里再套一层 `"runtime_surface"`/`"build_env"` 键——
双重嵌套会让整个维度在报告里失踪（组装脚本会硬失败并要求你重填）。

```json
{
  "runtime_surface": {
    "summary": "运行期读取 RDBASE 指向的数据目录；无网络访问。",
    "network": [],
    "filesystem": [{"detail": "$RDBASE/Data 下的特征定义文件", "purpose": "加载化学特征模板",
      "evidence": ["rdkit/RDPaths.py"]}],
    "env_vars": [{"name": "RDBASE", "purpose": "定位数据/资源根目录", "evidence": ["rdkit/RDPaths.py:12"]}],
    "subprocess": [],
    "devices": [],
    "services": []
  },
  "build_env": {
    "language_standard": "C++17",
    "runtime_version": "Python >= 3.9",
    "build_system": "CMake",
    "compiler_extensions": [{"detail": "__builtin_popcountll 回退路径", "evidence": ["Code/DataStructs/BitOps.cpp"]}],
    "platforms": [
      {"os": "linux", "arch": "x86_64", "evidence": [".github/workflows/build.yml"]},
      {"os": "windows", "arch": "x86_64", "evidence": ["#ifdef _WIN32 分支"]},
      {"os": "macos", "arch": "arm64", "evidence": ["cibuildwheel 配置"]}
    ],
    "entry_points": [],
    "packaging": "",
    "notes": "三大桌面平台 + x86_64/arm64。"
  }
}
```
对 **application**（如 VisualVM）则形如：`services` 列 attach/jvmstat/JMX；`entry_points` 列
`{type:"launcher", name:"launcher/visualvm", ...}`、原生 `visualvm.exe`、framework_startup 模块；
`packaging` 写「Ant build-zip 产出 zip 分发 + 各平台原生 launcher，运行依赖外部 JDK」。

## Rules
- Descriptive only — list what the code needs/touches, never give porting/adaptation advice.
- Ground every item in something you read; use `[]` / omit when there is nothing.
- Don't duplicate dim 6 (linked libraries) or dim 7 (API call families) here.

## 自我发现（反哺）
清单外的新宿主交互类型或工具链特性，追加到顶层 `meta.observations`：
`{dimension:"runtime_surface"|"build_env", field, kind, value, rationale}`，供面板「模型观察」页人工反哺。
