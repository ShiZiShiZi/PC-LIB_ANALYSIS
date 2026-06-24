---
name: native-api-analysis
description: Analyze a third-party library's or application's use of low-level and platform APIs — Win32, POSIX, C/C++ standard library, OS syscalls, GPU/graphics APIs, and FFI bridges (ctypes, JNI, N-API) — by reading source includes and call sites, and judging platform dependence. Use for dimension 7 of PC library/application analysis. Model reasoning over code, not a fixed grep list.
---

# System & platform API analysis (model-driven)

Determine which system, platform and standard-library APIs the library calls
into, and classify each. Use search to locate candidates, then **read the call
sites** to confirm — a fixed symbol grep produces false positives and misses
indirection. This is descriptive (what it calls), not advice.

## 主旨与原则
目标：一张「这个库到底碰了哪些平台/系统 API、在哪碰的」的可下钻清单。
**输出契约（下方 Output）是唯一硬约束。** `category`/`platform` 是**稳定闭轴**（按可移植性，下面给定）；
`type`（API 家族名）与各 API 名是**开放词**，按实际写。遇到分类清单覆盖不到的情况，尽力归类，
必要时在 `meta.observations` 记录。方法是参考思路，可按仓库调整。

## Classify every group by PORTABILITY (`category`) + `platform`
Use a **consistent portability lens** — Win32 and POSIX-only calls are the SAME kind
of thing (OS-specific), so they share the `platform` category, distinguished only by
the `platform` field:
- **standard** — language standard library / runtime, available everywhere: C++ STL,
  Python stdlib (`os`/`io`/`logging`…), Java SE (`java.io`/`java.net`/`java.nio`),
  Node core (`fs`/`net`/`stream`). → `platform: portable`.
- **platform** — OS-specific, gone if you switch OS: **Win32** (`platform: windows`),
  **POSIX-only** (`mmap`/`fork`/`pthread`/`epoll`, `<unistd.h>`/`<fcntl.h>`/`<sys/mman.h>`
  → `platform: posix`), macOS Cocoa/Carbon (`macos`), Linux-only `inotify`/`netlink`
  (`linux`), glibc/MSVC extensions.
- **system** — kernel / system-call level ONLY: raw `syscall()`, `ioctl`, `/proc`·`/sys`,
  Windows registry/WMI, device handles. (Do NOT put ordinary POSIX file/mem APIs here —
  those are `platform`+`posix`.)
- **ffi** — interop bridges: ctypes/cffi, JNI, N-API.
- **hardware** — GPU / SIMD / accelerators: OpenGL/Vulkan/DirectX/Metal/CUDA/OpenCL,
  x86/ARM SIMD intrinsics. → `platform` usually the OS or `portable`.

> **应用（application）尤需关注**：桌面 GUI 工具包（Swing/AWT、JavaFX、SWT、Qt、GTK、Electron）
> 与 RCP 平台（NetBeans `org.openide`/`org.netbeans`、Eclipse）是应用的平台相关面，按 `platform`
> 归类；JDK 内部/`sun.*`/Attach API（`com.sun.tools.attach`）、JNI 原生 agent 同样要列入——它们
> 是 dim-9 判断应用能否在鸿蒙跑起来的关键。

## Drill down to individual APIs (`apis`)
For each group, fill `apis` with the **specific APIs actually called** — representative,
not every call site. Each entry: `name`, a one-line 简体中文 `purpose`, `count`
(how many call sites / occurrences — approximate via `grep -c` or codegraph callers),
`evidence` (`file:line`, 1-3 representative sites), and `conditional` (true if guarded
by `#ifdef`/platform branch). This turns the dimension into a concrete, drill-down
inventory of which API is called, how often, and where.

> **喂给 dim-9（鸿蒙适配）**：这里标为 `platform`/`system`/`hardware` 且鸿蒙无对应实现的具体
> API，正是 dim-9 `harmony_adaptation.unadaptable_apis[]` 的来源（按 API 名 + 调用点证据）。本维度
> 只做"是什么 API、在哪、可移植性如何"的客观清点，是否"无法适配"由 dim-9 综合判定——但务必把
> 这些 API 的 `name`/`evidence` 列准，dim-9 与父库 `used_symbols` 求交都依赖它。

**One entry = one concrete API.** Do NOT bundle several calls into one `name`
(`mmap / munmap`, `open / fstat / close`, `std::async / std::future`,
`PyObject / Py_INCREF`). List tightly-related variants as **separate entries** so each
carries its own `count` and `evidence` — bundling defeats the per-API count. `count`
is **required** for every entry.

**Pseudo-file / pseudo-interface APIs** (procfs/sysfs, Windows registry, WMI-style
queries, device handles): these ARE system APIs — a `/proc/cpuinfo` read is a kernel
query, the Linux equivalent of a syscall — so keep them in `category: system`. But
don't list a **bare path** as the `name`; write it as **`family (specific node)`** so it
reads like an API, not a data file — e.g. `procfs (/proc/cpuinfo)`,
`sysfs (/sys/class/net)`, `registry (HKLM\\...\\BIOS)`. In `purpose`, name the **access
mechanism** (e.g. "经 `fs.readFileSync` 读取的内核伪文件接口"). The portable read call
(`fs.readFileSync`, `open`) belongs to its `standard` group; the platform-coupled
interface target (the path) belongs to the `system` group — these are two lenses on the
same call site and listing both is intentional, **not** a duplicate.

## What to look for
- **Win32 / Windows**: `#include <windows.h>` and friends (`winsock2`, `wininet`,
  `shlobj`, `winreg`, `tlhelp32`, `psapi`); API calls (`CreateFileW`,
  `RegOpenKeyEx`, `VirtualAlloc`, `WaitForSingleObject`, …); from Python:
  `ctypes.windll`, `import win32api`/`pywin32`; `#ifdef _WIN32`/`_MSC_VER`.
- **POSIX / Unix**: `<unistd.h>`, `<pthread.h>`, `<sys/socket.h>`, `<sys/mman.h>`,
  `<fcntl.h>`, `<dlfcn.h>`, `<signal.h>`; calls like `fork`, `mmap`, `pthread_*`,
  `epoll`/`kqueue`, `dlopen`.
- **C/C++ standard library (STL)**: which `<...>` headers and `std::` facilities
  (containers, `<thread>`, `<atomic>`, `<filesystem>`, `<regex>`, `<chrono>`).
- **Managed-language standard library & system calls** (so a pure Python/Java/Node
  library is NOT reported as empty):
  - Python: `os`/`sys`/`socket`/`subprocess`/`threading`/`multiprocessing`/`mmap`/
    `select`/`signal`/`ctypes` — classify std ones as `standard`, OS-coupled ones
    (e.g. `os.fork`, `fcntl`, `termios`) as `system`.
  - Java: `java.io`/`java.net`/`java.nio`/`java.util.concurrent` (`standard`),
    `sun.misc.Unsafe`/`com.sun.*` (`platform`/`system`).
  - Node: `fs`/`net`/`dgram`/`http`/`stream`/`worker_threads` (`standard`),
    `child_process`/`process.binding` (`system`).
- **System / kernel level**: raw syscalls (`syscall(2)`, `prctl`, `clone`), `ioctl`,
  `/proc`·`/sys` reads, Windows registry (`RegOpenKeyEx`)/WMI/device handles.
- **FFI / interop bridges** — list only **real interop API calls**: Python C-API
  (`PyObject`, `Py_INCREF`, `PyBytes_*`, `boost::python` call sites), JNI functions
  (`JNIEnv`, `GetMethodID`, actual `JNIEXPORT` implementations), N-API (`napi_*`).
  Do NOT list **binding-generator directives / build tooling** — SWIG `%module`/`%include`,
  `EMSCRIPTEN_BINDINGS`, bare `extern "C"` declarations — those are bindings, already
  captured by dependencies (dim 6), `library.bindings`, and `dynamic_libraries`. If a
  library only has binding tooling and no direct C-API calls, omit the `ffi` group.
- **Graphics / device / accelerator APIs**: OpenGL, Vulkan, DirectX/Direct3D,
  Metal, CUDA, OpenCL, audio/video device APIs.
- **Architecture-specific code (`arch_simd` group)**: x86/x64 SIMD intrinsics
  (`__popcnt`/`__popcnt64`, `<immintrin.h>`/SSE/AVX `_mm_*`), ARM NEON, CPU-id
  checks, and inline assembly (`asm`/`__asm`). Flag these as their own `arch_simd`
  group and note whether a generic fallback (e.g. `__builtin_popcountll`) exists —
  they indicate CPU-architecture coupling.
- **Dynamic loading (libraries loaded at runtime, NOT in package manifests)**:
  - C/C++: `dlopen`/`dlsym`/`dlclose`, `LoadLibrary(Ex)`/`GetProcAddress`/`FreeLibrary`.
  - Python: `ctypes.CDLL`/`WinDLL`/`OleDLL`/`cdll.LoadLibrary`, `ctypes.util.find_library`,
    `cffi.FFI().dlopen`.
  - Java: `System.loadLibrary(...)` / `System.load(...)`.
  - Node: native addons loaded at runtime — `require('*.node')`, `bindings`,
    `node-gyp-build`, `process.dlopen`.

## How to analyze
1. Use `grep`/search for the include/symbol families above to find candidate files.
   When codegraph is available (the agent will tell you), prefer it for structural
   lookups — `codegraph query <symbol> -p repos/<name> -j` to find definitions and
   `codegraph callers/callees -p repos/<name>` to confirm call sites — and fall back
   to grep/Read when it isn't.
2. Open representative hits and confirm real usage (ignore comments, strings,
   third-party/vendored subtrees). **限定生产代码 —— 排除测试与示例/演示代码。** 用
   `metrics.json` 的 `code_metrics.top_dirs`/`test_example_dirs` 作基线，并对**按功能命名的
   demo 目录**（脚本 token 漏判的，如 `QLabel/`、`QThread/`、`QAxWidget/`——独立可运行示例）
   用判断补判为 example。**只在 test/example 里出现的 API 不是库的平台依赖，不要列入** ——
   每条 evidence 必须来自生产代码。若整仓是示例/教程集合，平台 API 据库本体收敛（通常近空）。
3. Group findings by API family with concrete **evidence** (file + include/symbol).
   **List the concrete API symbols you actually saw — not just the family name.**
4. For each dynamic-loading call site, **resolve the loaded library name** (read the
   string/variable passed to `dlopen`/`LoadLibrary`/`CDLL`/`loadLibrary`; if the name
   is computed at runtime, record `<dynamic>` and note what you can infer), and
   **infer its purpose in 简体中文** (e.g. `libssl.so` → "OpenSSL，提供 TLS/加密"). Note
   whether the load is `optional` (failure handled gracefully → an optional feature).
   Also infer, for the loaded lib, **`acquisition` (怎么获取)** and **`source` (是什么库/出处)** —
   crucially decide whether it is a **`self_build`** artifact built from THIS repo (a
   CFFI/JNI/SWIG wrapper like `librdkitcffi.so` / `GraphMolWrap`) or an external
   `system`/`third_party`/`bundled` library (like a proprietary `depict32.dll`).
5. Judge **platform dependence**: are platform calls guarded by `#ifdef` (→
   cross-platform with backends) or unconditional (→ windows-only / posix-only)?

## Output (fills report `native_api`)
```json
{
  "summary": "Cross-platform; thin OS abstraction over Win32 and POSIX sockets.",
  "groups": [
    {"type": "cpp_stl", "category": "standard", "platform": "portable", "apis": [
      {"name": "std::filesystem", "purpose": "跨平台路径与文件操作", "evidence": ["src/util/path.cpp:20"]},
      {"name": "std::thread", "purpose": "并发执行", "evidence": ["src/pool.cpp:14"]}
    ]},
    {"type": "win32", "category": "platform", "platform": "windows", "apis": [
      {"name": "CreateFileMapping", "purpose": "Windows 内存映射文件", "evidence": ["src/io/mmap_win.cpp:31"], "conditional": true}
    ]},
    {"type": "posix", "category": "platform", "platform": "posix", "apis": [
      {"name": "mmap", "purpose": "POSIX 内存映射文件读取", "count": 4, "evidence": ["src/io/mmap_posix.cpp:40"], "conditional": true},
      {"name": "epoll_wait", "purpose": "Linux 事件多路复用", "count": 2, "evidence": ["src/net/loop.cpp:88"], "conditional": true}
    ]},
    {"type": "syscall", "category": "system", "platform": "linux", "apis": [
      {"name": "ioctl", "purpose": "设备控制", "evidence": ["src/dev/tty.c:12"]}
    ]},
    {"type": "linux_sysfs", "category": "system", "platform": "linux", "apis": [
      {"name": "procfs (/proc/cpuinfo)", "purpose": "经 fs.readFileSync 读取的内核伪文件接口，获取 CPU 详情", "count": 4, "evidence": ["lib/util.js:640"], "conditional": true},
      {"name": "sysfs (/sys/class/net)", "purpose": "经 fs.readFileSync 读取的内核伪文件接口，获取网卡属性", "count": 3, "evidence": ["lib/network.js:943"], "conditional": true}
    ]}
  ],
  "dynamic_libraries": [
    {"name": "libssl.so", "mechanism": "dlopen", "optional": true,
     "acquisition": "system", "source": "外部 OpenSSL，需系统/运行环境提供",
     "description": "OpenSSL，按需加载以提供 TLS/加密；缺失时降级为明文。",
     "evidence": ["src/net/tls.c:42"]},
    {"name": "libfoocffi.so", "mechanism": "ctypes.CDLL", "optional": false,
     "acquisition": "self_build", "source": "本仓 CFFI 构建产物（MinimalLib）",
     "description": "本库的 CFFI 包装，供 Python 调用 C++ 接口。", "evidence": ["bindings/cffi/simple.py:3"]}
  ],
  "platform_dependence": "cross-platform"
}
```

## Rules
- Confirm by reading; don't report a symbol you only matched by regex.
- **Dimension boundary** — `native_api` records OS/runtime **API call sites** only.
  Environment variables belong to `runtime_surface` (dim 8); linked or runtime-loaded
  libraries belong to `dependencies` (dim 6) / `dynamic_libraries`. Don't duplicate them here.
- **Two lenses, not duplication** — for a pseudo-file interface, the portable read
  call (`fs.readFileSync`/`open`, in a `standard` group) and the platform-coupled
  interface it targets (the `/proc`·`/sys`/registry path, in a `system` group) may both
  appear; that is intentional. (The same path may also surface in `runtime_surface`
  (dim 8) as an external-interaction resource — also fine, different dimension.)
- `dynamic_libraries` is for runtime-loaded libs only; libraries declared in package
  manifests belong to dependency-analysis (dim 6), not here. Emit `[]` when none.
  These ARE runtime dependencies — whenever you see an FFI/dynamic loader symbol
  (`ctypes.CDLL`/`dlopen`/`LoadLibrary`/`System.loadLibrary`/N-API), always record the
  **loaded library name** here (not just the loader), so the panel can list it under
  dependencies.
- Pure-managed libraries still report their **standard-library / system** API usage
  (category `standard`/`system`) — only report empty `groups` if the code truly
  touches no notable stdlib/system API. Set `platform_dependence: "cross-platform"`
  when there is no platform-specific code.

## 自我发现（反哺）
遇到难以归入 standard/platform/system/hardware/ffi 的 API 家族，或分类口径的歧义，追加到顶层
`meta.observations`：`{dimension:"native_api", field, kind, value, rationale}`，供面板「模型观察」页人工反哺。
