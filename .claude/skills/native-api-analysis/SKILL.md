---
name: native-api-analysis
description: Analyze a third-party library's use of low-level and platform APIs — Win32, POSIX, C/C++ standard library, OS syscalls, GPU/graphics APIs, and FFI bridges (ctypes, JNI, N-API) — by reading source includes and call sites, and judging platform dependence. Use for dimension 7 of PC library analysis. Model reasoning over code, not a fixed grep list.
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

## Drill down to individual APIs (`apis`)
For each group, fill `apis` with the **specific APIs actually called** — representative,
not every call site. Each entry: `name`, a one-line 简体中文 `purpose`, `evidence`
(`file:line`, 1-3 representative sites), and `conditional` (true if guarded by
`#ifdef`/platform branch). This turns the dimension into a concrete, drill-down
inventory of which API is called and where.

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
- **FFI / interop bridges**: Python `ctypes`/`cffi`; Java JNI (`native` methods,
  `System.loadLibrary`, `JNIEXPORT`); Node `ffi-napi`/N-API/`node-gyp`/native addons.
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
   third-party/vendored subtrees, test fixtures).
3. Group findings by API family with concrete **evidence** (file + include/symbol).
   **List the concrete API symbols you actually saw — not just the family name.**
4. For each dynamic-loading call site, **resolve the loaded library name** (read the
   string/variable passed to `dlopen`/`LoadLibrary`/`CDLL`/`loadLibrary`; if the name
   is computed at runtime, record `<dynamic>` and note what you can infer), and
   **infer its purpose in 简体中文** (e.g. `libssl.so` → "OpenSSL，提供 TLS/加密"). Note
   whether the load is `optional` (failure handled gracefully → an optional feature).
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
      {"name": "mmap", "purpose": "POSIX 内存映射文件读取", "evidence": ["src/io/mmap_posix.cpp:40"], "conditional": true},
      {"name": "epoll_wait", "purpose": "Linux 事件多路复用", "evidence": ["src/net/loop.cpp:88"], "conditional": true}
    ]},
    {"type": "syscall", "category": "system", "platform": "linux", "apis": [
      {"name": "ioctl", "purpose": "设备控制", "evidence": ["src/dev/tty.c:12"]}
    ]}
  ],
  "dynamic_libraries": [
    {"name": "libssl.so", "mechanism": "dlopen", "optional": true,
     "description": "OpenSSL，按需加载以提供 TLS/加密；缺失时降级为明文。",
     "evidence": ["src/net/tls.c:42"]}
  ],
  "platform_dependence": "cross-platform"
}
```

## Rules
- Confirm by reading; don't report a symbol you only matched by regex.
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
