#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone

RUN_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(RUN_DIR, '..', '..', '..', '..', 'repos', 'pc-lib-84', 'PyMuPDF'))

with open(os.path.join(RUN_DIR, 'metrics.json'), 'r', encoding='utf-8') as f:
    metrics = json.load(f)

# --- library header ---
library = {
    "name": "PyMuPDF",
    "kind": "library",
    "package_name": "pymupdf",
    "aliases": ["PyMuPDF", "fitz"],
    "import_names": ["pymupdf", "fitz"],
    "source_url": "https://github.com/pymupdf/PyMuPDF.git",
    "analyzed_at": "2026-06-29T06:05:57.679Z",
    "commit": "e9cdfc9e7fe3260efcc9d28713903f075ab05bce",
    "one_liner": "基于 MuPDF 的高性能 Python PDF 处理库，支持文本/图像/表格提取、页面渲染、注释编辑与格式转换。",
    "ecosystem": "python",
    "bindings": []
}

# --- function summary ---
function_summary = {
    "summary": "PyMuPDF 是 MuPDF C 引擎的 Python 绑定层，提供 Document、Page、Pixmap、Annot 等高层对象，用于 PDF（及 XPS/EPUB/图片等）的读取、文本/图像/表格提取、页面渲染、注释与表单编辑、合并拆分、加密以及格式转换。目标用户是 Python 应用开发者、数据流水线构建者以及需要本地处理 PDF 的 AI/RAG 开发者。",
    "categories": [
        {
            "name": "PDF 文档对象模型与元数据操作",
            "description": "打开、关闭、遍历文档，读取/设置元数据、目录、页面标签、嵌入文件等核心文档对象操作。",
            "evidence": ["src/__init__.py:2825 (Document)", "src/__init__.py:9528 (Page)", "src/__init__.py:9384 (Outline)", "src/__init__.py:1959 (Archive)"]
        },
        {
            "name": "文本、图像、表格提取与结构化输出",
            "description": "通过 Page.get_text() 提取多种格式文本，调用 utils 提取 words/blocks，使用 table.Table 检测表格并输出 Markdown、HTML、JSON 或 pandas DataFrame。",
            "evidence": ["src/__init__.py:9528 (Page.get_text)", "src/utils.py:48 (get_text_blocks)", "src/table.py:1523 (Table)", "src/__init__.py:13278 (Pixmap)"]
        },
        {
            "name": "页面渲染与位图输出",
            "description": "将 PDF 页面光栅化为 Pixmap，支持指定 DPI、色彩空间、裁剪区域，并保存为 PNG/JPEG 等图片。",
            "evidence": ["src/__init__.py:13278 (Pixmap)", "src/__init__.py:9528 (Page.get_pixmap)"]
        },
        {
            "name": "注释、表单、加密与文档编辑",
            "description": "创建和修改高亮、下划线、墨迹、图章等注释，读写 AcroForm 字段，应用密文，设置加密与权限。",
            "evidence": ["src/__init__.py:586 (Annot)", "src/__init__.py:9044 (Widget)", "src/__init__.py:14874 (Shape)", "src/__init__.py:2825 (Document.save)"]
        },
        {
            "name": "文档转换、合并与嵌入文件",
            "description": "插入/删除/重排页面，合并多个 PDF，转换 Office/图片为 PDF，以及增删改嵌入文件流。",
            "evidence": ["src/__init__.py:2825 (Document.insert_pdf / convert_to_pdf)", "src/__main__.py:267 (doc_join)", "src/__main__.py:288 (embedded_copy)"]
        },
        {
            "name": "几何、颜色与排版工具",
            "description": "提供 Rect、Point、Matrix、Quad、IRect、Colorspace 等几何与颜色抽象，支撑页面坐标变换、区域计算和 Story 排版。",
            "evidence": ["src/__init__.py:14583 (Rect)", "src/__init__.py:14164 (Point)", "src/__init__.py:8673 (Matrix)", "src/__init__.py:2720 (Colorspace)", "src/__init__.py:15864 (Story)"]
        },
        {
            "name": "命令行工具",
            "description": "提供 pymupdf 控制台命令，支持 show、clean、join、extract、embed-*、gettext 等子命令。",
            "evidence": ["src/__main__.py:843 (main)", "setup.py:1375-1377 (console_scripts)"]
        }
    ],
    "domain": "文档处理 / PDF 工具库",
    "target_users": "Python 应用开发者、数据与 RAG/AI 流水线构建者、需要本地处理 PDF 的终端用户"
}

# --- tests ---
tests = dict(metrics["tests"])
tests["frameworks"] = ["pytest"]
tests["notes"] = "测试以 pytest 为主；metrics 按目录名将 docs/ 下的 .po/.rst 计入 production，实际应视为文档翻译与示例。"
# schema uses 'notes', metrics uses 'note'
tests.pop("note", None)

# --- license ---
license_block = {
    "spdx": "AGPL-3.0-only",
    "name": "GNU Affero General Public License v3.0 only",
    "confidence": "high",
    "is_dual_licensed": True,
    "license_files": ["COPYING"],
    "evidence": "COPYING 为完整 AGPL-3.0 文本；README.md 声明 GNU AGPL v3；setup.py:1409 声明 Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License。",
    "notes": "copyleft；同时提供 Artifex 商业许可。注意 src/__init__.py 头部写 GPL-3.0-only，与 COPYING/README/setup.py 的 AGPL 声明不一致，以 COPYING 为准。"
}

# --- dependencies ---
dependencies = {
    "count": 9,
    "manifests": ["pyproject.toml", "setup.py", "docs/requirements.txt"],
    "by_ecosystem": {
        "python": ["pipcl", "libclang", "fonttools", "pandas", "pymupdf-fonts", "pytest"],
        "cpp": ["MuPDF", "swig"],
        "other": ["tesseract-ocr"]
    },
    "dependencies": [
        {
            "name": "MuPDF",
            "ecosystem": "cpp",
            "registry_name": "mupdf",
            "source_repo": "https://github.com/ArtifexSoftware/mupdf",
            "scope": "runtime",
            "version": "1.28.0",
            "purpose": "底层 C/C++ PDF/文档渲染与解析引擎，PyMuPDF 的核心原生依赖",
            "acquisition": "download_build",
            "locality": "remote",
            "source": "构建时从 https://mupdf.com/downloads/archive 下载 mupdf-1.28.0-source.tar.gz 并本地编译",
            "declared_in": ["setup.py:428-560 (get_mupdf_internal / get_mupdf)", "setup.py:576-630 (build)", "setup.py:904-1064 (build_mupdf_unix)"],
            "used_symbols": [],
            "harmony_adapted": False,
            "harmony_adapted_source": None
        },
        {
            "name": "pipcl",
            "ecosystem": "python",
            "scope": "build",
            "version": None,
            "purpose": "PEP-517 构建后端，提供包构建、扩展编译辅助函数",
            "acquisition": "package_manager",
            "locality": "remote",
            "source": "PyPI (pyproject.toml build-system.requires)",
            "declared_in": ["pyproject.toml:2", "setup.py:210 (import pipcl)"],
            "used_symbols": ["pipcl.build_extension", "pipcl.run", "pipcl.log0"]
        },
        {
            "name": "swig",
            "ecosystem": "cpp",
            "scope": "build",
            "version": None,
            "purpose": "生成 Python 与 MuPDF C++ API 之间的绑定代码",
            "acquisition": "package_manager",
            "locality": "remote",
            "source": "PyPI swig 包（setup.py 按平台返回 swig==4.3.1 或 swig）",
            "declared_in": ["setup.py:1472-1482 (get_requires_for_build_wheel)"],
            "used_symbols": []
        },
        {
            "name": "libclang",
            "ecosystem": "python",
            "scope": "build",
            "version": None,
            "purpose": "MuPDF 绑定生成/编译期间解析 C/C++ 头文件",
            "acquisition": "package_manager",
            "locality": "remote",
            "source": "PyPI libclang 包",
            "declared_in": ["setup.py:1461-1471 (get_requires_for_build_wheel)"],
            "used_symbols": []
        },
        {
            "name": "fonttools",
            "ecosystem": "python",
            "registry_name": "fonttools",
            "scope": "optional",
            "version": None,
            "purpose": "字体子集化（font subsetting），在嵌入字体时裁剪未使用字形",
            "acquisition": "package_manager",
            "locality": "remote",
            "source": "PyPI fonttools",
            "declared_in": ["src/__init__.py:7598 (import fontTools.subset as fts)"],
            "used_symbols": ["fontTools.subset.main"]
        },
        {
            "name": "pandas",
            "ecosystem": "python",
            "registry_name": "pandas",
            "scope": "optional",
            "version": None,
            "purpose": "Table.to_pandas() 将提取的表格转换为 DataFrame",
            "acquisition": "package_manager",
            "locality": "remote",
            "source": "PyPI pandas",
            "declared_in": ["src/table.py:1670 (import pandas as pd)"],
            "used_symbols": ["pandas.DataFrame"]
        },
        {
            "name": "pymupdf-fonts",
            "ecosystem": "python",
            "registry_name": "pymupdf-fonts",
            "scope": "optional",
            "version": None,
            "purpose": "扩展字体集合，为 TextWriter/Story 等提供额外字体",
            "acquisition": "package_manager",
            "locality": "remote",
            "source": "PyPI pymupdf-fonts",
            "declared_in": ["src/__init__.py:17816 (from pymupdf_fonts import ...)", "src/__init__.py:8264", "src/__init__.py:12294"],
            "used_symbols": ["pymupdf_fonts.myfont", "pymupdf_fonts.fontdescriptors", "pymupdf_fonts.fontbuffers"]
        },
        {
            "name": "tesseract-ocr",
            "ecosystem": "other",
            "scope": "optional",
            "version": None,
            "purpose": "OCR 功能所需的系统级 Tesseract 引擎二进制及 tessdata 语言数据",
            "acquisition": "system",
            "locality": "system",
            "source": "系统预装 Tesseract OCR（README 提示 brew/apt 安装）及 tessdata",
            "declared_in": ["src/__init__.py:22458-22483 (get_tessdata subprocess calls)", "README.md:70-76"],
            "used_symbols": []
        },
        {
            "name": "pytest",
            "ecosystem": "python",
            "scope": "dev",
            "version": None,
            "purpose": "测试框架",
            "acquisition": "package_manager",
            "locality": "remote",
            "source": "PyPI pytest",
            "declared_in": ["pytest.ini", "setup.py:1394 (PYODIDE_ROOT 时加入 requires_dist)"],
            "used_symbols": []
        }
    ],
    "notes": "README 声明无强制运行时依赖；默认 wheel 已将 MuPDF 共享库捆绑。PyMuPDF Pro / pymupdf4llm 是独立可选包，不在本仓库源码中导入。"
}

# --- native_api ---
native_api = {
    "summary": "PyMuPDF 的纯 Python 代码以跨平台标准库为主，平台相关代码集中在 Tesseract 自动发现、安装后软链接创建以及可选的 fork 并发路径；C 扩展层通过 SWIG 大量使用 CPython API，并包含一个 Windows 专属的 vasprintf/asprintf 后备实现。",
    "groups": [
        {
            "type": "python_c_api",
            "category": "standard",
            "platform": "portable",
            "apis": [
                {"name": "PyUnicode_InternFromString", "purpose": "初始化扩展使用的 Python 字符串键", "count": 53, "evidence": ["src/extra.i:22-74"]},
                {"name": "PyObject_Repr", "purpose": "实现 repr() 风格字符串表示", "count": 1, "evidence": ["src/extra.i:121"]},
                {"name": "PyBytes_FromStringAndSize", "purpose": "将 MuPDF 缓冲区转换为 Python bytes", "count": 5, "evidence": ["src/extra.i:631-639", "src/extra.i:660"]},
                {"name": "PyImport_ImportModule", "purpose": "导入 pymupdf 模块以回调 message()", "count": 1, "evidence": ["src/extra.i:224"]},
                {"name": "PyObject_GetAttrString", "purpose": "获取 pymupdf.message 函数", "count": 1, "evidence": ["src/extra.i:225"]},
                {"name": "PyObject_CallObject", "purpose": "调用 Python 回调函数", "count": 1, "evidence": ["src/extra.i:230"]},
                {"name": "PyTuple_Pack", "purpose": "构造回调参数元组", "count": 1, "evidence": ["src/extra.i:229"]},
                {"name": "PyBool_FromLong", "purpose": "将 C 布尔值转换为 Python bool", "count": 15, "evidence": ["src/extra.i:179 (JM_BOOL)"]},
                {"name": "PyList_Append", "purpose": "向 Python 列表追加元素", "count": 4, "evidence": ["src/extra.i:706-712"]},
                {"name": "PyFloat_AsDouble", "purpose": "读取 Python 序列中的浮点数", "count": 4, "evidence": ["src/extra.i:672-678"]}
            ],
            "evidence": ["src/extra.i"]
        },
        {
            "type": "python_stdlib",
            "category": "standard",
            "platform": "portable",
            "apis": [
                {"name": "os.environ.get / os.getenv", "purpose": "读取 PYMUPDF_MESSAGE、PYMUPDF_LOG、TESSDATA_PREFIX、MUPDF_CPPYY 等配置", "count": 7, "evidence": ["src/__init__.py:164", "src/__init__.py:167", "src/__init__.py:292", "src/__init__.py:310", "src/__init__.py:375", "src/__init__.py:22452"]},
                {"name": "subprocess.run", "purpose": "调用外部命令进行 Tesseract 语言数据发现", "count": 3, "evidence": ["src/__init__.py:22460", "src/__init__.py:22469", "src/__init__.py:22483"]},
                {"name": "multiprocessing.Pool", "purpose": "apply_pages(method='mp') 的并发处理", "count": 1, "evidence": ["src/_apply_pages.py:84-95"]},
                {"name": "os.symlink", "purpose": "为非 Windows 安装创建 MuPDF .so 符号链接", "count": 1, "evidence": ["src/__init__.py:25632"], "conditional": True},
                {"name": "os.remove", "purpose": "清理已存在的符号链接或临时字体文件", "count": 2, "evidence": ["src/__init__.py:25630", "src/__init__.py:7638"], "conditional": True}
            ],
            "evidence": ["src/__init__.py", "src/_apply_pages.py"]
        },
        {
            "type": "win32_c_runtime",
            "category": "platform",
            "platform": "windows",
            "apis": [
                {"name": "vasprintf", "purpose": "Windows 缺少的变长格式化字符串分配函数", "count": 1, "evidence": ["src/extra.i:188-208"], "conditional": True},
                {"name": "asprintf", "purpose": "Windows 缺少的变长格式化字符串分配函数", "count": 1, "evidence": ["src/extra.i:210-218"], "conditional": True}
            ],
            "evidence": ["src/extra.i:184-219"]
        },
        {
            "type": "posix_process",
            "category": "platform",
            "platform": "posix",
            "apis": [
                {"name": "os.fork", "purpose": "apply_pages(method='fork') 创建子进程并发处理页面", "count": 1, "evidence": ["src/_apply_pages.py:187"], "conditional": True},
                {"name": "os.waitpid", "purpose": "等待 fork 出的子进程结束", "count": 1, "evidence": ["src/_apply_pages.py:249"], "conditional": True}
            ],
            "evidence": ["src/_apply_pages.py:98-253", "src/__init__.py:24829"]
        },
        {
            "type": "system_commands",
            "category": "system",
            "platform": "portable",
            "apis": [
                {"name": "tesseract --list-langs", "purpose": "自动发现已安装的 Tesseract 语言数据目录", "count": 1, "evidence": ["src/__init__.py:22460"]},
                {"name": "where tesseract", "purpose": "Windows 下定位 tesseract 可执行文件路径", "count": 1, "evidence": ["src/__init__.py:22469"]},
                {"name": "whereis tesseract-ocr/tesseract", "purpose": "Unix-like 系统下定位 tesseract 安装目录", "count": 1, "evidence": ["src/__init__.py:22483"]}
            ],
            "evidence": ["src/__init__.py:22434-22501 (get_tessdata)"]
        }
    ],
    "dynamic_libraries": [
        {
            "name": "_extra.so / _extra.pyd",
            "mechanism": "SWIG Python extension import",
            "acquisition": "self_build",
            "source": "本仓 src/extra.i 经 SWIG 生成的 Python C 扩展",
            "description": "PyMuPDF 额外的 Python C 扩展，封装部分 MuPDF 操作与 CPython 互操作",
            "optional": False,
            "evidence": ["src/__init__.py:33 (from . import extra)", "setup.py:1127-1145 (pipcl.build_extension name='extra')"]
        },
        {
            "name": "_mupdf.so / _mupdf.pyd",
            "mechanism": "SWIG Python extension import",
            "acquisition": "self_build",
            "source": "MuPDF platform/python 绑定生成的模块（随 MuPDF 源码构建）",
            "description": "MuPDF Python SWIG 绑定，暴露 mupdf.* API 给 Python 层",
            "optional": False,
            "evidence": ["src/__init__.py:395 (from . import mupdf)", "setup.py:677/691/696/700"]
        },
        {
            "name": "libmupdf.so / libmupdf.dylib / mupdfcpp*.dll",
            "mechanism": "dynamic linker load at import time",
            "acquisition": "self_build",
            "source": "MuPDF C/C++ 共享库（随 MuPDF 源码构建并随 wheel 分发）",
            "description": "MuPDF 渲染与解析引擎核心库，被 Python 扩展动态链接",
            "optional": False,
            "evidence": ["setup.py:680-703 (add MuPDF shared libs to wheel)"]
        }
    ],
    "platform_dependence": "mixed"
}

# --- runtime_surface ---
runtime_surface = {
    "summary": "运行期主要与本地文件系统交互（打开/保存 PDF、临时目录、软链接），并通过环境变量控制日志输出；OCR 功能在自动发现 tessdata 时会调用外部 Tesseract 命令。无网络访问。",
    "network": [],
    "filesystem": [
        {"detail": "打开、保存、转换 PDF 及 Office/图片文档", "purpose": "核心文档 IO", "evidence": ["src/__init__.py:2825 (Document)", "src/__main__.py:57 (open_file)"]},
        {"detail": "字体子集化时创建 TemporaryDirectory 并写入临时字体文件", "purpose": "fontTools 临时工作目录", "evidence": ["src/__init__.py:7604-7643"]},
        {"detail": "安装后在非 Windows 平台创建 libmupdf.so 软链接", "purpose": "让动态链接器找到 MuPDF 共享库", "evidence": ["src/__init__.py:25605-25632"]}
    ],
    "env_vars": [
        {"name": "PYMUPDF_MESSAGE", "purpose": "控制 pymupdf.message() 输出目标（fd/path/logging）", "evidence": ["src/__init__.py:164"]},
        {"name": "PYMUPDF_LOG", "purpose": "控制 pymupdf.log() 输出目标", "evidence": ["src/__init__.py:167"]},
        {"name": "TESSDATA_PREFIX", "purpose": "显式指定 Tesseract 语言数据目录，避免自动探测", "evidence": ["src/__init__.py:22443", "src/__init__.py:22452"]},
        {"name": "MUPDF_CPPYY", "purpose": "实验性：改用 cppyy 绑定替代默认 SWIG 绑定", "evidence": ["src/__init__.py:375"]},
        {"name": "PYTHONPATH", "purpose": "mupdf_cppyy 模式调试时记录路径", "evidence": ["src/__init__.py:379"]}
    ],
    "subprocess": [
        {"command": "tesseract --list-langs", "purpose": "自动发现 Tesseract 语言数据目录", "evidence": ["src/__init__.py:22460"]},
        {"command": "where tesseract", "purpose": "Windows 下定位 tesseract 可执行文件", "evidence": ["src/__init__.py:22469"]},
        {"command": "whereis tesseract-ocr / tesseract", "purpose": "Unix-like 下定位 tesseract 安装目录", "evidence": ["src/__init__.py:22483"]}
    ],
    "devices": [],
    "services": []
}

# --- build_env ---
build_env = {
    "language_standard": "Python >=3.10；C/C++14（扩展与 MuPDF）",
    "runtime_version": "Python 3.10–3.14",
    "build_system": "pipcl/setup.py + SWIG + MuPDF scripts/mupdfwrap.py",
    "compiler_extensions": [
        {"detail": "Py_LIMITED_API 条件分支，支持构建稳定 ABI 扩展", "purpose": "减少多 Python 版本 wheel 数量", "evidence": ["src/extra.i:134-147"]},
        {"detail": "Windows 下 FZ_DLL_CLIENT 宏", "purpose": "以 DLL 客户端方式链接 MuPDF", "evidence": ["setup.py:1167"]}
    ],
    "platforms": [
        {"os": "windows", "arch": "x86 / x86_64", "evidence": ["setup.py:784-884", "README.md:297"]},
        {"os": "macos", "arch": "x86_64 / arm64", "evidence": ["setup.py:940-961", "README.md:296"]},
        {"os": "linux", "arch": "x86_64 / aarch64", "evidence": ["setup.py:904-1064", "README.md:294"]},
        {"os": "linux", "arch": "x86_64 (musl)", "evidence": ["README.md:295"]},
        {"os": "pyodide", "arch": "wasm", "evidence": ["setup.py:695-698", ".github/workflows/test_pyodide.yml"]}
    ],
    "entry_points": [
        {
            "type": "console_script",
            "name": "pymupdf",
            "command": "pymupdf <subcommand>，支持 show/clean/join/extract/embed-*/gettext 等子命令",
            "evidence": ["setup.py:1375-1377", "src/__main__.py:843"]
        }
    ],
    "packaging": "通过 pip 分发 wheel，默认随包捆绑 MuPDF 共享库与头文件；源码构建时自动下载 MuPDF 源码并本地编译；无独立安装包。",
    "notes": "构建时需要 C/C++ 工具链、SWIG 与 libclang；在 Pyodide/WebAssembly 上也有支持。"
}

# --- capability_profile ---
capability_profile = {
    "summary": "本项目是本地文档处理库，核心能力为 PDF 解析与 2D 页面光栅化，不涉及桌面 GUI、3D 渲染、音视频或特定硬件；OCR 依赖外部 Tesseract 二进制。",
    "scenarios": [
        {"key": "gui", "present": False},
        {"key": "rendering_3d", "present": False},
        {"key": "media", "present": False},
        {"key": "hardware", "present": False, "specific_hardware": False}
    ]
}

# --- harmony_adaptation ---
harmony_adaptation = {
    "target": "HarmonyOS NEXT PC（跑在已移植 Python 3.12 运行时上；原生扩展与 MuPDF 经 OHOS NDK/musl 重编；arm64/x86_64；自研内核，无 Linux ABI）",
    "porting_class": "needs_adaptation_full",
    "feasibility": "feasible_with_effort",
    "effort": {"person_days": [10, 20]},
    "confidence": "high",
    "recommended_path": "run_on_ported_runtime",
    "summary": "PyMuPDF 主体是纯 Python API 封装，可在鸿蒙已移植 Python 上直接运行；真正工作量在于用 OHOS NDK 交叉编译 MuPDF C/C++ 引擎并重新生成 SWIG 绑定。OCR 自动发现 Tesseract 语言数据依赖外部系统命令，在鸿蒙上可能不可用，但可通过显式传入 tessdata 路径绕过；apply_pages 的 fork 并发路径可用 multiprocessing 替代。OpenHarmony PC PyPI 镜像已有 pymupdf 官方 ohos wheel，说明该路径已被社区验证。",
    "unadaptable_apis": [],
    "target_assumptions": [
        {
            "id": "ta:python",
            "capability": "Python 运行时已移植",
            "required": True,
            "target_status": "available",
            "impact": "纯 Python 封装层可直接运行",
            "source": "references/harmony-pc-capabilities.json#runtimes.python"
        },
        {
            "id": "ta:ndk",
            "capability": "OHOS NDK 可交叉编译 MuPDF C/C++ 引擎",
            "required": True,
            "target_status": "partial",
            "impact": "原生扩展与 MuPDF 共享库需用 OHOS NDK 在 arm64/x86_64 上重编；musl POSIX 子集基本够用，但需验证少数编译选项与系统调用",
            "source": "references/harmony-pc-capabilities.json intro + setup.py 构建脚本"
        },
        {
            "id": "ta:tesseract",
            "capability": "Tesseract OCR 二进制及语言数据可用",
            "required": False,
            "target_status": "unknown",
            "impact": "仅影响 OCR 自动语言数据发现；显式设置 TESSDATA_PREFIX 或关闭 Tesseract 构建可绕过",
            "source": "references/harmony-pc-capabilities.json#process_security.spawn 等未知"
        }
    ],
    "required_permissions": [],
    "blockers": [
        {
            "id": "bk:mupdf",
            "issue": "MuPDF C/C++ 引擎与 SWIG 生成的 Python 绑定需针对 HarmonyOS 重新编译",
            "severity": "major",
            "adaptability": "adaptable",
            "category": "native_dependency",
            "source_dimension": "dependencies",
            "harmony_status": "partial",
            "remediation": "下载 MuPDF 1.28 源码，使用 ohos.toolchain.cmake + clang/musl 交叉编译为 arm64/x86_64 .so，再重新生成 SWIG 绑定；鸿蒙 PyPI 镜像已有 pymupdf ohos wheel，可参考其构建方式。",
            "caused_by": ["ta:ndk"],
            "manifests_as": [],
            "evidence": ["setup.py:428-560", "setup.py:576-630", "setup.py:904-1064", "setup.py:1127-1145", "setup.py:680-703"]
        },
        {
            "id": "bk:tesseract",
            "issue": "OCR 自动发现 Tesseract 语言数据依赖外部系统命令（tesseract/where/whereis），HarmonyOS PC 上可能不存在对应工具",
            "severity": "minor",
            "adaptability": "partial",
            "category": "subprocess_unavailable",
            "source_dimension": "runtime_surface",
            "harmony_status": "partial",
            "remediation": "通过 TESSDATA_PREFIX 环境变量或 API 参数显式提供 tessdata 路径；如 MuPDF 编译时未启用 Tesseract，则禁用 OCR 相关 API 或文档说明需用户自行安装。",
            "caused_by": ["ta:tesseract"],
            "manifests_as": [],
            "evidence": ["src/__init__.py:22434-22501"]
        },
        {
            "id": "bk:fork",
            "issue": "apply_pages(method='fork') 使用 POSIX os.fork()，在 HarmonyOS PC 进程模型下的可用性未知，但存在替代方案",
            "severity": "minor",
            "adaptability": "adaptable",
            "category": "posix_subset_gap",
            "source_dimension": "native_api",
            "harmony_status": "partial",
            "remediation": "默认使用 method='mp'（multiprocessing.Pool），将 fork 路径标记为实验性或仅在 Unix 可用；若鸿蒙支持 fork 则无需改动。",
            "caused_by": [],
            "manifests_as": [],
            "evidence": ["src/_apply_pages.py:187", "src/__init__.py:24829"]
        }
    ],
    "compatible": [
        {"aspect": "纯 Python API 封装与文档对象逻辑", "note": "Document/Page/Pixmap/Annot 等类基本不依赖平台 API，可在鸿蒙 Python 上直接运行", "evidence": ["src/__init__.py:2825", "src/__init__.py:9528"]},
        {"aspect": "跨平台 MuPDF C 引擎", "note": "MuPDF 本身高度可移植、依赖少，OHOS NDK 重编成功率较高", "evidence": ["README.md:34", "setup.py:904-1064"]}
    ],
    "key_tasks": [
        "准备 OHOS NDK 交叉编译环境，编译 MuPDF 1.28 为 arm64/x86_64 共享库",
        "用 SWIG 重新生成并编译 _extra 与 _mupdf Python C 扩展",
        "验证 Tesseract OCR：提供 tessdata 路径，或在构建时关闭 Tesseract 后裁剪 OCR API",
        "将 apply_pages 默认并发方法改为 mp，条件化 fork 路径",
        "在鸿蒙 Python 上跑通 pytest 单元测试"
    ],
    "notes": "评估按模型 A（库跑在已移植 Python 运行时上）。OpenHarmony PC PyPI 镜像已有 pymupdf 的 ohos wheel，意味着该移植路径已被社区走通，实际工作量可能偏向构建脚本适配而非代码重写。x86_64 在鸿蒙 PC 上的覆盖情况仍标记为 unknown，但 arm64 已 available。"
}

# --- meta ---
meta = {
    "schema_version": "1.0",
    "analyzer": "pc-lib-analyzer",
    "counter_tool": metrics["code_metrics"]["tool"],
    "warnings": [
        "metrics.json 将 docs/ 下的 .po/.rst 文档与翻译文件计入 production code，导致 primary language 显示为 PO File；库本身实际为 Python + SWIG/C 扩展。",
        "scripts/ 目录为构建/发布/测试脚本，不是库运行时代码，已排除在 native_api/runtime_surface 证据之外。"
    ],
    "confidence_overall": "high",
    "observations": [
        {
            "dimension": "function_summary",
            "field": "top_dirs classification",
            "kind": "gap",
            "value": "docs/ counted as production",
            "rationale": "docs/ 主要是 reStructuredText 文档与 .po 翻译文件，不是库代码；metrics 脚本按目录名将其判为 production，导致 production LOC 被显著放大。"
        },
        {
            "dimension": "dependencies",
            "field": "ecosystem",
            "kind": "new_value",
            "value": "other for system binary",
            "rationale": "Tesseract OCR 是外部系统二进制（及语言数据），不是 Python/C++ 包；使用 ecosystem=other + scope=optional + locality=system 描述。"
        },
        {
            "dimension": "native_api",
            "field": "category",
            "kind": "new_value",
            "value": "python_c_api as standard",
            "rationale": "PyMuPDF 的 C 扩展大量使用 CPython API；将其归入 standard/portable，因为鸿蒙 PC 已移植 CPython 运行时。"
        },
        {
            "dimension": "harmony_adaptation",
            "field": "porting_class",
            "kind": "ambiguity",
            "value": "root already has official ohos wheel",
            "rationale": "OpenHarmony PC PyPI 镜像已有 pymupdf 的 ohos wheel，说明项目已被移植；本次仍按源码需交叉编译 MuDF + 适配平台分支评估，给出 needs_adaptation_full。"
        }
    ]
}

report = {
    "library": library,
    "function_summary": function_summary,
    "languages": metrics["languages"],
    "code_metrics": metrics["code_metrics"],
    "tests": tests,
    "license": license_block,
    "dependencies": dependencies,
    "native_api": native_api,
    "runtime_surface": runtime_surface,
    "build_env": build_env,
    "capability_profile": capability_profile,
    "harmony_adaptation": harmony_adaptation,
    "meta": meta
}

report_path = os.path.join(RUN_DIR, 'report.json')
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"Wrote {report_path}")
