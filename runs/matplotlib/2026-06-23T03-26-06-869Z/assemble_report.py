#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from pathlib import Path
from datetime import datetime, timezone

RUN_DIR = Path(__file__).parent
METRICS = json.loads((RUN_DIR / "metrics.json").read_text(encoding="utf-8"))

report = {
    "library": {
        "name": "matplotlib",
        "package_name": "matplotlib",
        "source_url": "https://github.com/matplotlib/matplotlib.git",
        "analyzed_at": "2026-06-23T03:26:06.869Z",
        "commit": "91f9a9d166b4454b16877fde6246deeee44e6a31",
        "one_liner": "Python 生态下用于创建静态、动态和交互式二维数据可视化的综合绘图库",
        "ecosystem": "python",
        "bindings": []
    },
    "function_summary": {
        "summary": "Matplotlib 是 Python 生态中主流的综合性二维绘图库，面向科研人员、数据分析师、教育工作者和应用开发者。它提供面向对象（OO）与 pyplot 过程式两套 API，支持丰富的图形元素（点、线、面、文本、图像、色彩映射、动画等），并可通过多种后端输出为 Agg、SVG、PDF、PostScript、Cairo 等格式或在 Qt/GTK/Tk/wx/macOS/Web 等交互环境中展示。",
        "categories": [
            {
                "name": "二维图形绘制 API",
                "description": "提供 Figure、Axes、Artist 等对象以及 pyplot 过程式接口，用于创建和组织图表元素（线、标记、面、文本、图像等）。",
                "evidence": ["lib/matplotlib/figure.py:Figure", "lib/matplotlib/axes/_axes.py:Axes", "lib/matplotlib/artist.py:Artist", "lib/matplotlib/pyplot.py:figure", "lib/matplotlib/pyplot.py:plot"]
            },
            {
                "name": "后端与输出格式",
                "description": "支持 Agg、SVG、PDF、PS、Cairo 等光栅/矢量输出，以及 Qt、GTK、Tk、wx、macOS、WebAgg 等交互后端。",
                "evidence": ["lib/matplotlib/backends/backend_agg.py", "lib/matplotlib/backends/backend_svg.py", "lib/matplotlib/backends/backend_pdf.py", "lib/matplotlib/backends/backend_qt.py", "lib/matplotlib/backends/backend_webagg.py", "src/_backend_agg.cpp"]
            },
            {
                "name": "文本与数学排版",
                "description": "通过 mathtext 实现 TeX 风格数学表达式，结合 FreeType/libraqm/harfbuzz 进行字体渲染，并支持 DVI/PostScript 字体读取。",
                "evidence": ["lib/matplotlib/_mathtext.py", "lib/matplotlib/dviread.py", "lib/matplotlib/font_manager.py", "src/ft2font.cpp", "src/ft2font_wrapper.cpp"]
            },
            {
                "name": "颜色与色彩映射",
                "description": "管理颜色规格、colormap、colorbar、多变量/双变量色彩映射，为 ScalarMappable 对象提供颜色映射能力。",
                "evidence": ["lib/matplotlib/colors.py", "lib/matplotlib/cm.py", "lib/matplotlib/_cm.py", "lib/matplotlib/colorbar.py"]
            },
            {
                "name": "动画支持",
                "description": "通过 ArtistAnimation/FuncAnimation 生成动画，并可将帧输出为 GIF、MP4 等视频格式（依赖 ffmpeg/imagemagick 等外部程序）。",
                "evidence": ["lib/matplotlib/animation.py:MovieWriter", "lib/matplotlib/animation.py:FuncAnimation"]
            },
            {
                "name": "三维绘图工具包",
                "description": "mpl_toolkits.mplot3d 提供 Axes3D 及三维曲面、散点、线框等绘图能力。",
                "evidence": ["lib/mpl_toolkits/mplot3d/axes3d.py", "lib/mpl_toolkits/mplot3d/art3d.py"]
            },
            {
                "name": "配置与样式",
                "description": "通过 rcParams、matplotlibrc 配置文件和 style 模块统一管理默认样式、后端、字体、动画参数等。",
                "evidence": ["lib/matplotlib/rcsetup.py", "lib/matplotlib/style.py", "lib/matplotlib/__init__.py:rcParams"]
            }
        ],
        "domain": "数据可视化 / 科学计算",
        "target_users": "Python 科研人员、数据分析师、教育工作者及应用开发者"
    },
    "languages": METRICS["languages"],
    "code_metrics": METRICS["code_metrics"],
    "tests": METRICS["tests"],
    "license": {
        "spdx": "PSF-2.0",
        "name": "Python Software Foundation License (Matplotlib License Agreement)",
        "confidence": "high",
        "is_dual_licensed": False,
        "license_files": ["LICENSE/LICENSE"],
        "evidence": "pyproject.toml 的 license 字段与 classifiers 均声明为 PSF；仓库根目录 LICENSE/LICENSE 为 Matplotlib 与早期 PSF 风格的许可协议；meson.build license 字段包含 PSF-2.0。",
        "notes": "仓库还包含 bundled 字体/代码的附加许可（OFL、Bitstream-Vera、Public Domain、MIT 等），详见 LICENSE/ 目录。"
    },
    "dependencies": {
        "count": 0,
        "manifests": ["pyproject.toml", "meson.build", "extern/meson.build", "src/meson.build"],
        "by_ecosystem": {},
        "dependencies": [],
        "notes": "仅列出运行时、构建、测试及常用可选后端依赖；文档构建依赖（sphinx 等）在 pyproject.toml dependency-groups/doc 中声明，此处从略。"
    },
    "native_api": {
        "summary": "Matplotlib 核心绘图逻辑为 Python，但包含多个 C/C++/Objective-C 扩展。原生代码以 pybind11 绑定 Python，使用 C++ STL；平台相关代码集中在后端与辅助扩展中：Linux 下通过 dlopen 动态探测 X11/Wayland，Windows 下调用 Win32 窗口/DPI/进程 API，macOS 下使用 Cocoa 事件循环。",
        "groups": [
            {
                "type": "python_stdlib",
                "category": "standard",
                "platform": "portable",
                "apis": [
                    {"name": "os.environ / os.getenv", "purpose": "读取 MPLBACKEND、MPLCONFIGDIR、DISPLAY 等运行时配置与环境", "count": 60, "evidence": ["lib/matplotlib/__init__.py:529", "lib/matplotlib/__init__.py:1288", "lib/matplotlib/font_manager.py:159", "lib/matplotlib/backends/qt_compat.py:26"]},
                    {"name": "subprocess.Popen / check_output", "purpose": "查询外部可执行程序版本、调用 fc-list/system_profiler/TeX/ffmpeg 等", "count": 30, "evidence": ["lib/matplotlib/__init__.py:405", "lib/matplotlib/font_manager.py:257", "lib/matplotlib/dviread.py:1259", "lib/matplotlib/animation.py:324"]},
                    {"name": "sys.platform", "purpose": "Windows/macOS/Linux 等平台分支判断", "count": 50, "evidence": ["lib/matplotlib/backend_bases.py:2867", "lib/matplotlib/tests/test_matplotlib.py:99"]},
                    {"name": "pathlib.Path.home", "purpose": "定位用户主目录以搜索字体与配置文件", "count": 10, "evidence": ["lib/matplotlib/font_manager.py:136", "lib/matplotlib/__init__.py:516"]}
                ]
            },
            {
                "type": "cpp_stl",
                "category": "standard",
                "platform": "portable",
                "apis": [
                    {"name": "std::vector", "purpose": "路径顶点、点集、变换矩阵等容器", "count": 80, "evidence": ["src/ft2font.cpp:89", "src/_path_wrapper.cpp:45"]},
                    {"name": "std::string", "purpose": "字体名、路径、错误信息等字符串处理", "count": 40, "evidence": ["src/ft2font.cpp:12", "src/_tkagg.cpp:171"]},
                    {"name": "std::map", "purpose": "键值映射缓存", "count": 10, "evidence": ["src/ft2font.cpp:9"]}
                ]
            },
            {
                "type": "python_c_api",
                "category": "ffi",
                "platform": "portable",
                "apis": [
                    {"name": "PyOS_setsig", "purpose": "在 macOS 后端注册 SIGINT 处理函数以中断事件循环", "count": 2, "evidence": ["src/_macosx.m:140"]},
                    {"name": "Py_BEGIN_ALLOW_THREADS / Py_END_ALLOW_THREADS", "purpose": "在图像重采样、macOS 事件循环等原生计算期间释放 GIL", "count": 8, "evidence": ["src/_image_wrapper.cpp:195", "src/_macosx.m:494"]},
                    {"name": "PyUnicode_EncodeFSDefault", "purpose": "将 tkinter 模块路径编码为文件系统字节以 dlopen", "count": 1, "evidence": ["src/_tkagg.cpp:334"]},
                    {"name": "PyErr_SetString / PyErr_SetFromWindowsErr", "purpose": "将 C/C++ 错误转换为 Python 异常", "count": 6, "evidence": ["src/_c_internal_utils.cpp:106", "src/_tkagg.cpp:50"]}
                ]
            },
            {
                "type": "posix_dynamic_loader",
                "category": "platform",
                "platform": "posix",
                "apis": [
                    {"name": "dlopen", "purpose": "运行时打开 X11/Wayland/tkinter 等动态库", "count": 5, "evidence": ["src/_c_internal_utils.cpp:43", "src/_tkagg.cpp:315", "src/_tkagg.cpp:336"]},
                    {"name": "dlsym", "purpose": "解析 XOpenDisplay、wl_display_connect、Tcl/Tk 等符号", "count": 9, "evidence": ["src/_c_internal_utils.cpp:46", "src/_tkagg.cpp:255"]},
                    {"name": "dlclose", "purpose": "关闭动态库句柄", "count": 4, "evidence": ["src/_c_internal_utils.cpp:53", "src/_tkagg.cpp:318"]}
                ]
            },
            {
                "type": "linux_display_loader",
                "category": "platform",
                "platform": "linux",
                "apis": [
                    {"name": "XOpenDisplay / XCloseDisplay", "purpose": "探测 X11 显示是否可用", "count": 2, "evidence": ["src/_c_internal_utils.cpp:46", "src/_c_internal_utils.cpp:48"]},
                    {"name": "wl_display_connect / wl_display_disconnect", "purpose": "探测 Wayland 显示是否可用", "count": 2, "evidence": ["src/_c_internal_utils.cpp:78", "src/_c_internal_utils.cpp:80"]}
                ]
            },
            {
                "type": "win32",
                "category": "platform",
                "platform": "windows",
                "apis": [
                    {"name": "LoadLibrary", "purpose": "加载 user32.dll 等系统库以动态获取函数", "count": 3, "evidence": ["src/_c_internal_utils.cpp:163", "src/_tkagg.cpp:206"]},
                    {"name": "GetProcAddress", "purpose": "解析 DPI 相关、Tcl/Tk 等函数指针", "count": 6, "evidence": ["src/_c_internal_utils.cpp:165", "src/_tkagg.cpp:210"]},
                    {"name": "GetForegroundWindow / SetForegroundWindow", "purpose": "控制窗口焦点", "count": 2, "evidence": ["src/_c_internal_utils.cpp:132", "src/_c_internal_utils.cpp:150"]},
                    {"name": "GetCurrentProcessExplicitAppUserModelID / SetCurrentProcessExplicitAppUserModelID", "purpose": "Windows 任务栏应用用户模型 ID", "count": 2, "evidence": ["src/_c_internal_utils.cpp:103", "src/_c_internal_utils.cpp:120"]},
                    {"name": "SetProcessDpiAwarenessContext / SetProcessDPIAware", "purpose": "设置进程 DPI 感知", "count": 2, "evidence": ["src/_c_internal_utils.cpp:175", "src/_c_internal_utils.cpp:186"]},
                    {"name": "EnumProcessModules", "purpose": "扫描进程模块以定位 tkinter 中的 Tcl/Tk 符号", "count": 2, "evidence": ["src/_tkagg.cpp:284", "src/_tkagg.cpp:290"]},
                    {"name": "SetWindowSubclass / DefSubclassProc / RemoveWindowSubclass", "purpose": "子类化 Tk 窗口以处理 WM_DPICHANGED", "count": 3, "evidence": ["src/_tkagg.cpp:238", "src/_tkagg.cpp:189", "src/_tkagg.cpp:239"]}
                ]
            },
            {
                "type": "macos_cocoa",
                "category": "platform",
                "platform": "macos",
                "apis": [
                    {"name": "NSApplication stop:/postEvent:/run", "purpose": "管理 macOS 应用事件循环的启停", "count": 3, "evidence": ["src/_macosx.m:84", "src/_macosx.m:98", "src/_macosx.m:157"]},
                    {"name": "NSEvent nextEventMatchingMask:untilDate:inMode:dequeue:", "purpose": "分发 Cocoa 事件", "count": 1, "evidence": ["src/_macosx.m:113"]},
                    {"name": "NSWindow / NSView drawRect:", "purpose": "macOS 原生窗口与视图绘制", "count": 2, "evidence": ["src/_macosx.m:177", "src/_macosx.m:191"]}
                ]
            }
        ],
        "dynamic_libraries": [
            {
                "name": "libX11.so.6",
                "mechanism": "dlopen",
                "acquisition": "system",
                "source": "系统 X11 客户端库",
                "description": "运行时按需加载以探测 X11 显示可用性",
                "optional": True,
                "evidence": ["src/_c_internal_utils.cpp:43"]
            },
            {
                "name": "libwayland-client.so.0",
                "mechanism": "dlopen",
                "acquisition": "system",
                "source": "系统 Wayland 客户端库",
                "description": "运行时按需加载以探测 Wayland 显示可用性",
                "optional": True,
                "evidence": ["src/_c_internal_utils.cpp:75"]
            },
            {
                "name": "user32.dll",
                "mechanism": "LoadLibrary",
                "acquisition": "system",
                "source": "Windows 系统 DLL",
                "description": "加载 DPI 感知与窗口子类化相关函数",
                "optional": False,
                "evidence": ["src/_c_internal_utils.cpp:163", "src/_tkagg.cpp:206"]
            },
            {
                "name": "_tkinter",
                "mechanism": "dlopen / GetProcAddress",
                "acquisition": "runtime",
                "source": "Python tkinter 扩展模块（.so/.pyd），随 Python 安装提供",
                "description": "TkAgg 后端运行时解析 Tcl/Tk 函数指针",
                "optional": False,
                "evidence": ["src/_tkagg.cpp:315", "src/_tkagg.cpp:336"]
            }
        ],
        "platform_dependence": "mixed"
    },
    "runtime_surface": {
        "summary": "运行期依赖宿主环境提供配置目录、系统字体、显示变量以及若干外部可执行程序；WebAgg 后端会启动本地 HTTP/WebSocket 服务。",
        "network": [
            {"detail": "WebAgg 本地 HTTP/WebSocket 服务器", "purpose": "通过浏览器展示交互式图表", "evidence": ["lib/matplotlib/backends/backend_webagg.py:49", "lib/matplotlib/backends/backend_webagg.py:128"]}
        ],
        "filesystem": [
            {"detail": "matplotlibrc 配置文件", "purpose": "读取用户/系统默认 rcParams", "evidence": ["lib/matplotlib/__init__.py:668"]},
            {"detail": "$MPLCONFIGDIR / $XDG_CONFIG_HOME / $XDG_CACHE_HOME", "purpose": "缓存与配置目录", "evidence": ["lib/matplotlib/__init__.py:516", "lib/matplotlib/__init__.py:525", "lib/matplotlib/__init__.py:529"]},
            {"detail": "系统与用户字体目录", "purpose": "搜索可用字体", "evidence": ["lib/matplotlib/font_manager.py:148-170"]},
            {"detail": "动画临时帧文件", "purpose": "FileMovieWriter 生成中间帧并组装成视频", "evidence": ["lib/matplotlib/animation.py:416"]}
        ],
        "env_vars": [
            {"name": "MPLBACKEND", "purpose": "选择 Matplotlib 后端", "evidence": ["lib/matplotlib/__init__.py:1288"]},
            {"name": "MPLCONFIGDIR", "purpose": "指定配置/缓存根目录", "evidence": ["lib/matplotlib/__init__.py:529", "lib/matplotlib/__init__.py:591"]},
            {"name": "MATPLOTLIBRC", "purpose": "指定 matplotlibrc 文件路径", "evidence": ["lib/matplotlib/__init__.py:668"]},
            {"name": "XDG_CONFIG_HOME", "purpose": "Linux/Unix 配置目录", "evidence": ["lib/matplotlib/__init__.py:516"]},
            {"name": "XDG_CACHE_HOME", "purpose": "Linux/Unix 缓存目录", "evidence": ["lib/matplotlib/__init__.py:525"]},
            {"name": "XDG_DATA_HOME", "purpose": "Linux/Unix 数据目录（字体搜索）", "evidence": ["lib/matplotlib/font_manager.py:159"]},
            {"name": "LOCALAPPDATA", "purpose": "Windows 本地应用数据目录", "evidence": ["lib/matplotlib/__init__.py:552"]},
            {"name": "HOME / USERPROFILE", "purpose": "用户主目录", "evidence": ["lib/matplotlib/font_manager.py:136"]},
            {"name": "WINDIR", "purpose": "Windows 系统目录（字体回退）", "evidence": ["lib/matplotlib/font_manager.py:218"]},
            {"name": "DISPLAY", "purpose": "X11 显示选择", "evidence": ["src/_c_internal_utils.cpp:42", "lib/matplotlib/backend_bases.py:2867"]},
            {"name": "WAYLAND_DISPLAY", "purpose": "Wayland 显示选择", "evidence": ["src/_c_internal_utils.cpp:74"]},
            {"name": "QT_API", "purpose": "选择 Qt 绑定（PyQt5/PyQt6/PySide2/PySide6）", "evidence": ["lib/matplotlib/backends/qt_compat.py:26"]},
            {"name": "QT_MAC_WANTS_LAYER", "purpose": "macOS Qt 渲染兼容", "evidence": ["lib/matplotlib/backends/qt_compat.py:137"]},
            {"name": "_MPLHIDEEXECUTABLES", "purpose": "隐藏特定外部可执行程序", "evidence": ["lib/matplotlib/__init__.py:432"]},
            {"name": "MPL_IGNORE_SYSTEM_FONTS", "purpose": "跳过系统字体扫描", "evidence": ["lib/matplotlib/font_manager.py:301"]},
            {"name": "SOURCE_DATE_EPOCH", "purpose": "可复现构建/输出时间戳", "evidence": ["lib/matplotlib/backends/backend_svg.py:411", "lib/matplotlib/backends/backend_pdf.py:148"]}
        ],
        "subprocess": [
            {"command": "dvipng / gs / inkscape / magick / pdftocairo / pdftops", "purpose": "查询可选外部工具版本", "evidence": ["lib/matplotlib/__init__.py:405"]},
            {"command": "fc-list", "purpose": "获取 fontconfig 字体列表", "evidence": ["lib/matplotlib/font_manager.py:257"]},
            {"command": "system_profiler SPFontsDataType", "purpose": "获取 macOS 系统字体", "evidence": ["lib/matplotlib/font_manager.py:272"]},
            {"command": "kpsewhich / latex / dvipdf / xelatex / lualatex", "purpose": "TeX/DVI 字体与文件解析", "evidence": ["lib/matplotlib/dviread.py:1259", "lib/matplotlib/texmanager.py:258", "lib/matplotlib/backends/backend_pgf.py:293"]},
            {"command": "ffmpeg / convert", "purpose": "将动画帧组装为视频/GIF", "evidence": ["lib/matplotlib/animation.py:324", "lib/matplotlib/mpl-data/matplotlibrc:836"]}
        ],
        "devices": []
    },
    "build_env": {
        "language_standard": "C++17 (meson.build cpp_std=c++17); Python >=3.12",
        "runtime_version": "Python >=3.12",
        "build_system": "Meson + meson-python",
        "compiler_extensions": [
            {"detail": "MSVC /Zc:preprocessor 或 /experimental:preprocessor", "evidence": ["src/meson.build:113-126"]}
        ],
        "platforms": [
            {"os": "linux", "arch": "x86_64", "evidence": [".github/workflows/cibuildwheel.yml:128"]},
            {"os": "linux", "arch": "aarch64", "evidence": [".github/workflows/cibuildwheel.yml:130"]},
            {"os": "windows", "arch": "AMD64", "evidence": [".github/workflows/cibuildwheel.yml:132"]},
            {"os": "windows", "arch": "ARM64", "evidence": [".github/workflows/cibuildwheel.yml:134"]},
            {"os": "macos", "arch": "x86_64", "evidence": [".github/workflows/cibuildwheel.yml:136"]},
            {"os": "macos", "arch": "arm64", "evidence": [".github/workflows/cibuildwheel.yml:138"]}
        ],
        "notes": "原生扩展包含 C/C++ 与 Objective-C（macOS 专属）；移植到 HarmonyOS PC 时需用 OHOS NDK 重新编译 C/C++ 扩展，Objective-C 与 Windows/macOS 专属分支不会参与构建。"
    },
    "harmony_adaptation": {
        "target": "HarmonyOS NEXT PC（跑在已移植 Python 3.12 运行时上；原生扩展经 OHOS NDK/musl 重编；arm64/x86_64；自研内核，无 Linux ABI）",
        "feasibility": "feasible_with_effort",
        "overall_difficulty": "medium",
        "effort_estimate": "M",
        "porting_class": "needs_adaptation_full",
        "recommended_path": "run_on_ported_runtime + cross_compile_native_extensions",
        "summary": "Matplotlib 主体为 Python 库，鸿蒙 PC 已移植 Python 运行时，纯 Python 部分可直接运行。核心难点在于用 OHOS NDK 重新编译多个 C/C++ 扩展（ft2font、_image、_path、_backend_agg、_qhull、_c_internal_utils、_tkagg），并确保未鸿蒙化的 qhull 能交叉编译。大量平台专属代码（Win32、Cocoa、X11/Wayland）受 #ifdef 保护，在鸿蒙构建时不会启用。已鸿蒙化的 numpy、pillow、contourpy、kiwisolver、pycairo、tornado 以及 C/C++ 镜像中的 freetype/harfbuzz/libraqm 可降低移植工作量；可选 GUI 后端（Qt/GTK/wx/macOS/Tk）未适配，可改用 Agg 或 WebAgg 后端。",
        "blockers": [
            {
                "issue": "多个 C/C++ 原生扩展需用 OHOS NDK 重新编译",
                "severity": "major",
                "category": "toolchain",
                "source_dimension": "build_env",
                "harmony_status": "replace_with_ohos",
                "remediation": "使用 ohos.toolchain.cmake + clang/musl 对 src/ 下扩展进行交叉编译，生成 arm64/x86_64 .so",
                "evidence": ["meson.build:32", "src/meson.build:33-111"]
            },
            {
                "issue": "qhull 未在 OpenHarmony PC C/C++ 镜像中提供，需自行交叉编译",
                "severity": "major",
                "category": "native_dependency",
                "source_dimension": "dependencies",
                "harmony_status": "partial",
                "remediation": "用 OHOS NDK 交叉编译 subprojects/qhull 为静态/动态库，或在 meson 选项中启用 system-qhull 并预装鸿蒙版 qhull_r",
                "evidence": ["extern/meson.build:72-81", "src/_qhull_wrapper.cpp:192"]
            },
            {
                "issue": "可选交互式 GUI 后端（Qt/GTK/wx/macOS/Tk）依赖未鸿蒙化或平台专属",
                "severity": "minor",
                "category": "platform_backend",
                "source_dimension": "dependencies",
                "harmony_status": "replace_with_ohos",
                "remediation": "默认使用非交互式 Agg 后端保存图片；需要交互时改用 WebAgg（tornado 已鸿蒙化）或后续开发基于 @ohos 图形能力的原生后端",
                "evidence": ["lib/matplotlib/backends/backend_qt.py", "lib/matplotlib/backends/backend_webagg.py"]
            },
            {
                "issue": "外部命令依赖（fc-list、system_profiler、LaTeX、ffmpeg 等）在鸿蒙上可能不存在，导致字体发现、usetex、动画功能受限",
                "severity": "major",
                "category": "subprocess_unavailable",
                "source_dimension": "runtime_surface",
                "harmony_status": "partial",
                "remediation": "预置字体文件并通过 rcParams 指定字体路径；关闭 usetex；动画改用 PillowWriter 保存 GIF；为关键外部工具提供鸿蒙可执行版本或移除相关功能调用",
                "evidence": ["lib/matplotlib/font_manager.py:257", "lib/matplotlib/dviread.py:1259", "lib/matplotlib/animation.py:324"]
            },
            {
                "issue": "TkAgg 运行时动态加载 tkinter/Tcl/Tk 符号，依赖 HarmonyOS Python 是否包含 tkinter",
                "severity": "minor",
                "category": "ffi_bridge",
                "source_dimension": "native_api",
                "harmony_status": "partial",
                "remediation": "若 tkinter 不可用，禁用 TkAgg；优先使用 Agg/WebAgg 后端",
                "evidence": ["src/_tkagg.cpp:336", "src/_tkagg.cpp:255"]
            }
        ],
        "unadaptable_apis": [],
        "compatible": [
            {"aspect": "纯 Python 绘图逻辑与后端抽象层", "note": "可直接跑在鸿蒙 Python 3.12 上，无需修改", "evidence": ["lib/matplotlib/pyplot.py", "lib/matplotlib/figure.py"]},
            {"aspect": "已鸿蒙化的核心依赖", "note": "numpy、pillow、contourpy、kiwisolver、pycairo、tornado 以及 C/C++ 镜像中的 freetype/harfbuzz/libraqm 可直接使用", "evidence": []},
            {"aspect": "Agg/WebAgg 输出后端", "note": "Agg 后端不依赖 GUI 平台库；WebAgg 依赖 tornado 已鸿蒙化", "evidence": ["lib/matplotlib/backends/backend_agg.py", "lib/matplotlib/backends/backend_webagg.py"]}
        ],
        "key_tasks": [
            "配置 OHOS NDK 工具链，交叉编译 Matplotlib 的 C/C++ 扩展",
            "交叉编译 qhull 或在鸿蒙环境中提供 qhull_r",
            "在鸿蒙 Python 上安装并验证已鸿蒙化的 numpy/pillow/kiwisolver/contourpy",
            "验证 font_manager 在缺少 fc-list 时的字体回退路径，预置字体或设置 rcParams",
            "跑通核心单元测试（使用 Agg 后端），必要时跳过依赖 LaTeX/外部 GUI 后端的测试"
        ],
        "notes": "评估按模型 A（库跑在已移植的鸿蒙 Python 运行时上）。平台专属分支（_WIN32/__linux__/darwin）在鸿蒙构建时默认不启用，因此不构成核心阻塞；真正的移植工作量在于原生扩展的重编与可选外部命令/后端的可用性验证。若目标是 ArkTS 沙箱应用（模型 B），则需将 Python 实现整体替换为 Node-API/ArkTS 方案，结论将收紧为 hard/very_high。"
    },
    "meta": {
        "schema_version": "1.0",
        "analyzer": "pc-lib-analyzer",
        "counter_tool": METRICS["code_metrics"]["tool"],
        "confidence_overall": "high",
        "warnings": [],
        "observations": [
            {"dimension": "dependencies", "field": "acquisition", "kind": "new_value", "value": "meson_subproject", "rationale": "Matplotlib 使用 meson subproject/wrap 下载并构建 freetype2、qhull、libraqm、harfbuzz、sheenbidi 等源码，现有推荐值 fetchcontent/download_build/submodule 均不能准确描述 meson subproject 机制。"},
            {"dimension": "dependencies", "field": "acquisition", "kind": "new_value", "value": "runtime_loaded_module", "rationale": "TkAgg 在运行时 dlopen Python 的 _tkinter 扩展模块并解析 Tcl/Tk 符号，acquisition 既不是 system 也不是 self_build，用 runtime_loaded_module 描述更准确。"},
            {"dimension": "harmony_adaptation", "field": "blockers[].category", "kind": "new_value", "value": "platform_backend", "rationale": "Qt/GTK/wx/macOS/Tk 等 GUI 后端属于可选的平台专属后端类别，与通用 native_dependency 区分开。"}
        ]
    }
}

# Build dependency list
py_runtime = [
    ("contourpy", ">=1.2.1", "Delaunay/等值线计算", "numpy.ndarray", True),
    ("cycler", ">=0.10", "样式循环管理", "", False),
    ("fonttools", ">=4.22.0", "字体文件解析", "fontTools.agl.toUnicode", False),
    ("kiwisolver", ">=1.3.1", "约束布局求解", "", True),
    ("numpy", ">=2.0", "数组计算与数据交换", "numpy.ndarray,numpy.asarray,numpy.array", True),
    ("packaging", ">=20.0", "版本解析", "packaging.version.parse", False),
    ("pillow", ">=9", "图像读写", "PIL.Image.frombuffer,PIL.Image.fromarray", True),
    ("pyparsing", ">=3", "数学表达式解析", "pyparsing.ParserElement", False),
    ("python-dateutil", ">=2.7", "日期时间处理", "dateutil.parser.parse", False),
]

build_py = [
    ("meson-python", ">=0.13.2,!=0.17.*", "Meson 构建的 Python 打包后端", "build"),
    ("pybind11", ">=2.13.2,!=2.13.3", "C++ / Python 绑定生成", "build"),
    ("setuptools_scm", ">=7,<10", "基于 git 的版本管理", "build"),
    ("setuptools", ">=64", "setuptools_scm 的兼容依赖", "build"),
]

optional = [
    ("PyQt5", None, "Qt5 绑定后端", "optional"),
    ("PyQt6", None, "Qt6 绑定后端", "optional"),
    ("PySide2", None, "Qt5 绑定后端", "optional"),
    ("PySide6", None, "Qt6 绑定后端", "optional"),
    ("pycairo", None, "Cairo 矢量后端", "optional", True),
    ("cairocffi", None, "Cairo cffi 后端", "optional"),
    ("wxPython", None, "wxWidgets 后端", "optional"),
    ("tornado", None, "WebAgg 后端 HTTP/WebSocket 服务", "optional", True),
    ("ipython", None, "交互式 shell 集成", "optional"),
]

native = [
    ("freetype2", None, "字体光栅化", "build/runtime", "cpp", "meson_subproject", "remote", "默认通过 meson subproject/wrap 下载源码构建；可选 system-freetype", ["extern/meson.build:9-25"], "FT_Open_Face,FT_Load_Glyph,FT_Bitmap_Convert,FT_Outline_Decompose", True),
    ("libraqm", None, "复杂文本排版（RTL/塑形）", "build/runtime", "cpp", "meson_subproject", "remote", "默认通过 meson subproject 构建；可选 system-libraqm", ["extern/meson.build:27-70"], "raqm_create,raqm_add_text", True),
    ("qhull", None, "Delaunay 三角剖分", "build/runtime", "cpp", "meson_subproject", "remote", "默认通过 meson subproject/wrap 下载源码构建；可选 system-qhull", ["extern/meson.build:72-81"], "qh_new_qhull,qh_freeqhull,qh_memfreeshort", False),
    ("harfbuzz", None, "字体塑形（libraqm 子项目依赖）", "build", "cpp", "meson_subproject", "remote", "通过 meson subproject 静态构建", ["extern/meson.build:30-60"], "", True),
    ("sheenbidi", None, "双向文本算法（libraqm 子项目依赖）", "build", "cpp", "meson_subproject", "remote", "通过 meson subproject 静态构建", ["extern/meson.build:61"], "", False),
    ("agg", None, "Anti-Grain Geometry 光栅化（仓库内）", "build/runtime", "cpp", "vendored", "local", "仓库内 extern/agg24-svn 源码", ["extern/meson.build:2"], "agg::trans_affine,agg::rgba8", False),
    ("pybind11", None, "C++ / Python 绑定头文件", "build", "cpp", "package_manager", "remote", "通常由 pip/conda 安装，meson 通过 pkg-config/cmake 查找", ["meson.build:49"], "pybind11::module_,pybind11::array_t", False),
    ("dl", None, "动态加载器", "build/runtime", "cpp", "system", "system", "Linux 系统 libdl；构建时链接，运行时用于 dlopen", ["src/meson.build:16"], "dlopen,dlsym,dlclose", False),
    ("Cocoa", None, "macOS 原生 GUI 框架", "build", "cpp", "system", "system", "macOS 系统框架，仅构建 _macosx 扩展", ["src/meson.build:146"], "NSApplication,NSEvent,NSWindow", True),
    ("comctl32", None, "Windows 通用控件", "build", "cpp", "system", "system", "Windows 系统库，构建 _tkagg 使用", ["src/meson.build:20"], "", False),
    ("ole32", None, "Windows OLE/COM", "build/runtime", "cpp", "system", "system", "Windows 系统库，用于 AppUserModelID", ["src/meson.build:21", "src/_c_internal_utils.cpp:24"], "CoTaskMemFree", False),
    ("psapi", None, "Windows 进程状态 API", "build/runtime", "cpp", "system", "system", "Windows 系统库，_tkagg 扫描进程模块", ["src/meson.build:22", "src/_tkagg.cpp:61"], "EnumProcessModules", False),
    ("shell32", None, "Windows Shell API", "build/runtime", "cpp", "system", "system", "Windows 系统库", ["src/meson.build:23", "src/_c_internal_utils.cpp:25"], "", False),
    ("user32", None, "Windows 用户界面 API", "build/runtime", "cpp", "system", "system", "Windows 系统库，DPI/窗口焦点", ["src/meson.build:24"], "LoadLibrary,GetProcAddress,GetForegroundWindow,SetForegroundWindow", False),
    ("X11", None, "X Window System 客户端库", "runtime", "cpp", "system", "system", "Linux 运行时动态加载，显示有效性探测", ["src/_c_internal_utils.cpp:43"], "XOpenDisplay,XCloseDisplay", False),
    ("Wayland", None, "Wayland 显示协议客户端库", "runtime", "cpp", "system", "system", "Linux 运行时动态加载，显示有效性探测", ["src/_c_internal_utils.cpp:75"], "wl_display_connect,wl_display_disconnect", False),
]

test_py = [
    ("pytest", "!=4.6.0,!=5.4.0,!=8.1.0", "测试框架", "test"),
    ("pytest-cov", None, "覆盖率", "test"),
    ("pytest-rerunfailures", "!=16.0", "失败重跑", "test"),
    ("pytest-timeout", None, "测试超时", "test"),
    ("pytest-xdist", None, "并发测试", "test"),
    ("pytest-xvfb", None, "虚拟显示测试", "test"),
    ("psutil", "sys_platform != 'cygwin'", "系统/进程信息", "test"),
    ("certifi", None, "TLS 根证书", "test"),
    ("coverage", "!=6.3", "覆盖率工具", "test"),
    ("black", "<27", "代码格式化", "test"),
]

deps = []

# Helper to lookup harmony status
hstatus_py = {
    "contourpy": (True, "OpenHarmony PC PyPI 镜像"),
    "cycler": (False, None),
    "fonttools": (False, None),
    "kiwisolver": (True, "OpenHarmony PC PyPI 镜像"),
    "numpy": (True, "OpenHarmony PC PyPI 镜像"),
    "packaging": (False, None),
    "pillow": (True, "OpenHarmony PC PyPI 镜像"),
    "pyparsing": (False, None),
    "python-dateutil": (False, None),
    "PyQt5": (False, None),
    "PyQt6": (False, None),
    "PySide2": (False, None),
    "PySide6": (False, None),
    "pycairo": (True, "OpenHarmony PC PyPI 镜像"),
    "cairocffi": (False, None),
    "wxPython": (False, None),
    "tornado": (True, "OpenHarmony PC PyPI 镜像"),
    "ipython": (False, None),
    "pybind11": (False, None),
}
hstatus_cpp = {
    "freetype2": (True, "OpenHarmony PC C/C++ 预编译包"),
    "libraqm": (True, "OpenHarmony PC C/C++ 预编译包"),
    "qhull": (False, None),
    "harfbuzz": (True, "OpenHarmony PC C/C++ 预编译包"),
    "sheenbidi": (False, None),
    "agg": (False, None),
}

def add_python_dep(name, version, purpose, scope, used_symbols=None, adapted_info=None):
    adapted, src = adapted_info if adapted_info else (False, None)
    dep = {
        "name": name,
        "ecosystem": "python",
        "scope": scope,
        "version": version,
        "purpose": purpose,
        "acquisition": "package_manager",
        "locality": "remote",
        "source": "PyPI（pip/conda 安装）",
        "declared_in": ["pyproject.toml"],
        "used_symbols": [s.strip() for s in used_symbols.split(",") if s.strip()] if used_symbols else [],
        "harmony_adapted": adapted,
        "harmony_adapted_source": src
    }
    deps.append(dep)

for name, ver, purpose, symbols, adapted in py_runtime:
    add_python_dep(name, ver, purpose, "runtime", symbols, (adapted, hstatus_py.get(name, (False, None))[1] if adapted else None))
for name, ver, purpose, scope in build_py:
    add_python_dep(name, ver, purpose, scope)

for item in optional:
    name, ver, purpose, scope = item[:4]
    adapted = item[4] if len(item) > 4 else False
    add_python_dep(name, ver, purpose, scope, None, (adapted, hstatus_py.get(name, (False, None))[1] if adapted else None))

for item in test_py:
    name, ver, purpose, scope = item
    add_python_dep(name, ver, purpose, scope)

for item in native:
    (name, ver, purpose, scope, eco, acq, loc, src, declared, symbols, adapted) = item
    dep = {
        "name": name,
        "ecosystem": eco,
        "scope": scope,
        "version": ver,
        "purpose": purpose,
        "acquisition": acq,
        "locality": loc,
        "source": src,
        "declared_in": declared,
        "used_symbols": [s.strip() for s in symbols.split(",") if s.strip()] if symbols else [],
        "harmony_adapted": adapted,
        "harmony_adapted_source": hstatus_cpp.get(name, (False, None))[1] if adapted else None
    }
    deps.append(dep)

report["dependencies"]["dependencies"] = deps
report["dependencies"]["count"] = len(deps)

by_eco = {}
for d in deps:
    by_eco.setdefault(d["ecosystem"], []).append(d["name"])
report["dependencies"]["by_ecosystem"] = by_eco

# Write report
out = RUN_DIR / "report.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Wrote {out}")
