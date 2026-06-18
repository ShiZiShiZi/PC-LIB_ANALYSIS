---
name: native-api-analysis
description: Analyze a third-party library's use of low-level and platform APIs — Win32, POSIX, C/C++ standard library, OS syscalls, GPU/graphics APIs, and FFI bridges (ctypes, JNI, N-API) — by reading source includes and call sites, and judging platform dependence. Use for dimension 7 of PC library analysis. Model reasoning over code, not a fixed grep list.
---

# Low-level / platform API analysis (model-driven)

Determine which platform and system APIs the library reaches for, and how
portable it is. Use search to locate candidates, then **read the call sites** to
confirm — a fixed symbol grep produces false positives and misses indirection.

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
    {"type": "win32", "symbols": ["WSAStartup", "closesocket"],
     "evidence": ["src/net/socket_win.cpp"]},
    {"type": "posix", "symbols": ["epoll_wait", "pthread_create"],
     "evidence": ["src/net/socket_posix.cpp"]},
    {"type": "cpp_stl", "symbols": ["std::thread", "std::filesystem"],
     "evidence": ["src/util/"]}
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
- Pure-managed libraries (plain Python/Java/JS with no FFI and no native syscalls)
  should report empty `groups` and `platform_dependence: "cross-platform"`.
