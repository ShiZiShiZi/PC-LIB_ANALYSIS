#!/usr/bin/env python3
"""Assemble the pypdfium2 analysis report."""
import json
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
METRICS = json.loads((RUN_DIR / "metrics.json").read_text())

def rel(*parts):
    return "/".join(parts)

report = {
    "library": {
        "name": "pypdfium2",
        "kind": "library",
        "package_name": "pypdfium2",
        "aliases": ["pypdfium2_raw", "pypdfium2_helpers"],
        "import_names": ["pypdfium2", "pypdfium2_raw", "pypdfium2_cli"],
        "source_url": "https://github.com/pypdfium2-team/pypdfium2.git",
        "analyzed_at": "2026-07-01T08:35:07.074Z",
        "commit": "9df9188b082c3acac1afdf4fbe0fd38d37b9a26b",
        "one_liner": "Python 到 PDFium 的 ABI 级绑定库，提供 PDF 渲染、文本提取、页面操作与文档处理的高层 API 和底层 ctypes 接口。",
        "ecosystem": "python",
        "bindings": []
    },

    "function_summary": {
        "summary": "pypdfium2 是 PDFium 的 Python ABI 级绑定库，通过 ctypes 暴露 PDFium 的 C API，并在此基础上提供面向对象的辅助类。它面向需要在 Python 中处理 PDF 的开发者，支持打开/创建 PDF 文档、提取文本与图片、渲染页面为位图、操作页面与书签、处理附件和表单、以及合并/拆分/旋转页面等常见任务。安装时通常随包捆绑预编译的 PDFium 共享库，也支持链接系统 PDFium 或从源码构建。",
        "categories": [
            {
                "name": "PDF 文档操作",
                "description": "打开、创建、保存、关闭 PDF 文档，支持文件路径、字节流和原始 FPDF_DOCUMENT 句柄。",
                "evidence": [rel("src/pypdfium2/_helpers/document.py:PdfDocument"), rel("src/pypdfium2/_helpers/document.py:_open_pdf")]
            },
            {
                "name": "页面渲染与位图处理",
                "description": "将 PDF 页面光栅化为位图，创建/填充/转换位图缓冲区，并提供与 PIL、NumPy、OpenCV 的便捷互操作适配器。",
                "evidence": [rel("src/pypdfium2/_helpers/page.py:PdfPage.render"), rel("src/pypdfium2/_helpers/bitmap.py:PdfBitmap"), rel("src/pypdfium2/_helpers/bitmap.py:convert_to_pil")]
            },
            {
                "name": "文本提取",
                "description": "基于 PDFium 的 FPDFText_* API 提取页面文本，支持按区域、按字符范围以及搜索功能。",
                "evidence": [rel("src/pypdfium2/_helpers/textpage.py:PdfTextPage"), rel("src/pypdfium2/_helpers/textpage.py:get_text_bounded")]
            },
            {
                "name": "页面与文档结构操作",
                "description": "插入、删除、旋转页面，读取/设置页面盒子（MediaBox/CropBox 等），处理书签、附件、页面对象和表单环境。",
                "evidence": [rel("src/pypdfium2/_helpers/page.py:PdfPage"), rel("src/pypdfium2/_helpers/attachment.py:PdfAttachment"), rel("src/pypdfium2/_helpers/pageobjects.py:PdfObject")]
            },
            {
                "name": "底层 ctypes 绑定",
                "description": "通过 ctypesgen 从 PDFium 头文件自动生成的原始绑定，直接暴露 FPDF_* 函数、结构与常量。",
                "evidence": [rel("autorelease/bindings.py"), rel("src/pypdfium2/raw.py"), rel("src/pypdfium2_raw/__init__.py")]
            },
            {
                "name": "命令行工具",
                "description": "提供 pypdfium2 命令行接口，用于渲染、文本/图片提取、文档信息查看、页面重排等测试与快速操作场景。",
                "evidence": [rel("src/pypdfium2_cli/__main__.py:cli_main"), rel("src/pypdfium2_cli/render.py"), rel("src/pypdfium2_cli/extract_text.py")]
            }
        ],
        "domain": "文档处理 / PDF 渲染",
        "target_users": "需要在 Python 中读取、渲染或操作 PDF 的开发者、数据提取工具作者、自动化测试人员"
    },

    "languages": METRICS["languages"],
    "code_metrics": METRICS["code_metrics"],
    "tests": METRICS["tests"],

    "license": {
        "spdx": "Apache-2.0 OR BSD-3-Clause",
        "name": "Apache License 2.0 or BSD 3-Clause",
        "confidence": "high",
        "is_dual_licensed": True,
        "license_files": [
            rel("LICENSES/Apache-2.0.txt"),
            rel("LICENSES/BSD-3-Clause.txt"),
            rel("REUSE.toml")
        ],
        "evidence": "pyproject.toml 与源码文件头明确声明 'SPDX-License-Identifier: Apache-2.0 OR BSD-3-Clause'；REUSE.toml 对数据/补丁等文件做了额外标注。",
        "notes": "采用宽松的双许可策略。BUILD_LICENSES/ 目录包含 PDFium 等二进制依赖的许可文本；README 也声明了 dependency licenses。"
    },

    "dependencies": {
        "count": 9,
        "manifests": [rel("pyproject.toml"), rel("setup.py"), rel("setup.cfg"), rel("req/setup.txt"), rel("req/converters.txt"), rel("req/test.txt"), rel("req/utilities.txt")],
        "by_ecosystem": {
            "python": 9
        },
        "dependencies": [
            {
                "name": "PDFium",
                "ecosystem": "cpp",
                "registry_name": None,
                "source_repo": "https://pdfium.googlesource.com/pdfium",
                "import_names": [],
                "aliases": ["pdfium"],
                "scope": "runtime",
                "version": None,
                "purpose": "底层 PDF 处理引擎，提供渲染、文本提取、文档操作等 C/C++ API；pypdfium2 通过 ctypes 调用其共享库。",
                "acquisition": "prebuilt_binary",
                "locality": "remote",
                "source": "默认从 pdfium-binaries (bblanchon/pdfium-binaries) 下载对应平台预编译二进制；可选 system-search 链接系统 pdfium，或 sourcebuild 从源码构建。",
                "declared_in": [rel("setupsrc/base.py"), rel("setupsrc/update.py"), rel("setupsrc/emplace.py")],
                "used_symbols": [
                    "FPDF_LoadDocument", "FPDF_CloseDocument", "FPDF_GetPageCount", "FPDF_LoadPage",
                    "FPDF_ClosePage", "FPDF_RenderPageBitmap", "FPDFBitmap_CreateEx",
                    "FPDFBitmap_GetBuffer", "FPDFBitmap_Destroy", "FPDFText_GetBoundedText",
                    "FPDF_InitLibraryWithConfig", "FPDF_DestroyLibrary"
                ],
                "harmony_adapted": False,
                "harmony_adapted_source": None
            },
            {
                "name": "ctypesgen",
                "ecosystem": "python",
                "registry_name": "ctypesgen",
                "source_repo": "https://github.com/pypdfium2-team/ctypesgen",
                "import_names": ["ctypesgen"],
                "aliases": [],
                "scope": "build",
                "version": "pypdfium2 branch",
                "purpose": "从 PDFium C 头文件生成 ctypes 绑定接口 (pypdfium2_raw/bindings.py)。",
                "acquisition": "package_manager",
                "locality": "remote",
                "source": "pyproject.toml [build-system] 声明为 git+https://github.com/pypdfium2-team/ctypesgen@pypdfium2；pip 安装。",
                "declared_in": [rel("pyproject.toml")],
                "used_symbols": [],
                "harmony_adapted": False,
                "harmony_adapted_source": None
            },
            {
                "name": "setuptools",
                "ecosystem": "python",
                "registry_name": "setuptools",
                "source_repo": None,
                "import_names": ["setuptools"],
                "aliases": [],
                "scope": "build",
                "version": ">= 70.1.0 (推荐)",
                "purpose": "构建后端，执行自定义 setup.py 以捆绑 PDFium 二进制与生成绑定。",
                "acquisition": "package_manager",
                "locality": "remote",
                "source": "PyPI / pip；pyproject.toml [build-system] 与 req/setup.txt 声明。",
                "declared_in": [rel("pyproject.toml"), rel("req/setup.txt")],
                "used_symbols": [],
                "harmony_adapted": False,
                "harmony_adapted_source": None
            },
            {
                "name": "packaging",
                "ecosystem": "python",
                "registry_name": "packaging",
                "source_repo": None,
                "import_names": ["packaging"],
                "aliases": [],
                "scope": "build",
                "version": None,
                "purpose": "musllinux 检测与版本解析辅助。",
                "acquisition": "package_manager",
                "locality": "remote",
                "source": "PyPI / pip；pyproject.toml [build-system] 与 req/setup.txt 声明。",
                "declared_in": [rel("pyproject.toml"), rel("req/setup.txt")],
                "used_symbols": ["packaging._musllinux._get_musl_version"],
                "harmony_adapted": False,
                "harmony_adapted_source": None
            },
            {
                "name": "wheel",
                "ecosystem": "python",
                "registry_name": "wheel",
                "source_repo": None,
                "import_names": ["wheel"],
                "aliases": [],
                "scope": "build",
                "version": "!=0.38.0, !=0.38.1",
                "purpose": "旧版 setuptools 构建 wheel 时使用（setuptools >= v70.1.0 后不再需要）。",
                "acquisition": "package_manager",
                "locality": "remote",
                "source": "PyPI / pip；pyproject.toml [build-system] 声明。",
                "declared_in": [rel("pyproject.toml")],
                "used_symbols": [],
                "harmony_adapted": False,
                "harmony_adapted_source": None
            },
            {
                "name": "Pillow",
                "ecosystem": "python",
                "registry_name": "Pillow",
                "source_repo": "https://github.com/python-pillow/Pillow",
                "import_names": ["PIL"],
                "aliases": [],
                "scope": "optional",
                "version": None,
                "purpose": "可选运行时依赖，用于将 PDFium 位图缓冲区转换为 PIL.Image 并保存图像。",
                "acquisition": "package_manager",
                "locality": "remote",
                "source": "PyPI / pip；req/converters.txt 声明，运行时懒加载。",
                "declared_in": [rel("req/converters.txt"), rel("README.md")],
                "used_symbols": ["PIL.Image.frombytes", "PIL.ImageOps", "PIL.ImageFilter", "PIL.ImageDraw"],
                "harmony_adapted": False,
                "harmony_adapted_source": None
            },
            {
                "name": "NumPy",
                "ecosystem": "python",
                "registry_name": "numpy",
                "source_repo": "https://github.com/numpy/numpy",
                "import_names": ["numpy"],
                "aliases": [],
                "scope": "optional",
                "version": None,
                "purpose": "可选运行时依赖，用于将位图缓冲区导出为 numpy 数组视图。",
                "acquisition": "package_manager",
                "locality": "remote",
                "source": "PyPI / pip；req/converters.txt 声明，运行时懒加载。",
                "declared_in": [rel("req/converters.txt"), rel("README.md")],
                "used_symbols": ["numpy.ndarray"],
                "harmony_adapted": False,
                "harmony_adapted_source": None
            },
            {
                "name": "opencv-python",
                "ecosystem": "python",
                "registry_name": "opencv-python",
                "source_repo": "https://github.com/opencv/opencv-python",
                "import_names": ["cv2"],
                "aliases": [],
                "scope": "optional",
                "version": None,
                "purpose": "可选运行时依赖，渲染 CLI 中用于通过 cv2 保存 numpy 适配后的图像。",
                "acquisition": "package_manager",
                "locality": "remote",
                "source": "PyPI / pip；README 说明，渲染 CLI 懒加载。",
                "declared_in": [rel("README.md")],
                "used_symbols": ["cv2.cvtColor", "cv2.imwrite"],
                "harmony_adapted": False,
                "harmony_adapted_source": None
            },
            {
                "name": "tabulate",
                "ecosystem": "python",
                "registry_name": "tabulate",
                "source_repo": "https://github.com/astanin/python-tabulate",
                "import_names": ["tabulate"],
                "aliases": [],
                "scope": "optional",
                "version": None,
                "purpose": "可选运行时依赖，为 CLI 表格输出提供美化格式。",
                "acquisition": "package_manager",
                "locality": "remote",
                "source": "PyPI / pip；req/test.txt 声明。",
                "declared_in": [rel("req/test.txt"), rel("README.md")],
                "used_symbols": [],
                "harmony_adapted": False,
                "harmony_adapted_source": None
            }
        ],
        "notes": "无强制 Python 运行时依赖，核心依赖是 PDFium 原生库。构建/源码构建时需要 C/C++ 工具链（gcc/clang）、git、gn、ninja、pkg-config 等外部系统工具，以及 PDFium 的 C/C++ 依赖库（freetype/icu/lcms2/libjpeg/openjpeg/libpng/libtiff/zlib/harfbuzz/glib 等）。"
    },

    "native_api": {
        "summary": "pypdfium2 的 Python 代码主要依赖 ctypes 进行原生 FFI 调用，几乎所有原生功能都通过 PDFium 共享库完成。此外，setup 阶段使用大量 Python 标准库（os/sys/platform/subprocess/urllib/shutil/tarfile）来检测平台、下载/解压预编译二进制、调用 ctypesgen、执行 git/pkg-config/gn/ninja 等外部工具。代码中几乎没有直接调用 Win32/POSIX 专有 API，平台差异主要通过 sys.platform 与 platform 模块做条件分支处理。",
        "groups": [
            {
                "type": "ctypes_ffi",
                "category": "ffi",
                "platform": "portable",
                "apis": [
                    {
                        "name": "ctypes.CDLL",
                        "purpose": "运行时加载 PDFium 共享库（libpdfium.so/dylib/dll）。",
                        "count": 1,
                        "evidence": [rel("autorelease/bindings.py:67")],
                        "conditional": False
                    },
                    {
                        "name": "ctypes.util.find_library",
                        "purpose": "在系统库搜索路径中查找 pdfium 共享库。",
                        "count": 1,
                        "evidence": [rel("autorelease/bindings.py:41"), rel("setupsrc/system_pdfium.py:12")],
                        "conditional": False
                    },
                    {
                        "name": "ctypes.c_double / c_float / c_int / c_ushort / c_ubyte / c_char / c_void_p",
                        "purpose": "与 PDFium C API 传递基本类型参数和接收返回值。",
                        "count": 40,
                        "evidence": [rel("src/pypdfium2/_helpers/bitmap.py:89"), rel("src/pypdfium2/_helpers/page.py:96"), rel("src/pypdfium2/_helpers/textpage.py:82")],
                        "conditional": False
                    },
                    {
                        "name": "ctypes.create_string_buffer",
                        "purpose": "为 PDFium 分配字节缓冲区，用于读取文档内容、附件数据、文本等。",
                        "count": 6,
                        "evidence": [rel("src/pypdfium2/_helpers/document.py:290"), rel("src/pypdfium2/_helpers/attachment.py:69")],
                        "conditional": False
                    },
                    {
                        "name": "ctypes.cast / ctypes.POINTER / ctypes.byref",
                        "purpose": "指针类型转换与传址调用。",
                        "count": 15,
                        "evidence": [rel("src/pypdfium2/_helpers/bitmap.py:89"), rel("src/pypdfium2/_helpers/matrix.py:51")],
                        "conditional": False
                    }
                ],
                "evidence": [rel("autorelease/bindings.py"), rel("src/pypdfium2/raw.py")]
            },
            {
                "type": "python_stdlib",
                "category": "standard",
                "platform": "portable",
                "apis": [
                    {
                        "name": "os / os.path / os.environ / os.name",
                        "purpose": "路径操作、环境变量读取、POSIX/Windows 判断。",
                        "count": 30,
                        "evidence": [rel("setupsrc/base.py:496"), rel("setupsrc/base.py:217")],
                        "conditional": False
                    },
                    {
                        "name": "sys.platform / sys.byteorder / sys.getandroidapilevel",
                        "purpose": "运行时平台识别与字节序/安卓 API 级别检测。",
                        "count": 12,
                        "evidence": [rel("autorelease/bindings.py:18"), rel("setupsrc/base.py:464")],
                        "conditional": False
                    },
                    {
                        "name": "platform.system / platform.machine / platform.libc_ver",
                        "purpose": "获取操作系统、CPU 架构与 C 库类型，用于选择对应平台二进制。",
                        "count": 8,
                        "evidence": [rel("setupsrc/base.py:464"), rel("setupsrc/base.py:434")],
                        "conditional": False
                    },
                    {
                        "name": "subprocess.run",
                        "purpose": "调用 git/pkg-config/gn/ninja/gh 等外部命令。",
                        "count": 1,
                        "evidence": [rel("setupsrc/base.py:615")],
                        "conditional": False
                    },
                    {
                        "name": "urllib.request.urlopen / urlretrieve",
                        "purpose": "下载 pdfium-binaries 发布包、PDFium 源码/依赖、LibreOffice 依赖列表等。",
                        "count": 5,
                        "evidence": [rel("setupsrc/update.py:101"), rel("setupsrc/system_pdfium.py:101"), rel("setupsrc/build_native.py:239")],
                        "conditional": False
                    },
                    {
                        "name": "shutil.which / copyfile / copyfileobj / rmtree",
                        "purpose": "查找外部可执行文件、复制绑定/二进制文件、清理目录。",
                        "count": 15,
                        "evidence": [rel("setupsrc/base.py:52"), rel("setupsrc/emplace.py:69")],
                        "conditional": False
                    }
                ],
                "evidence": [rel("setupsrc/base.py"), rel("setupsrc/update.py"), rel("setupsrc/system_pdfium.py")]
            },
            {
                "type": "pdfium_c_api",
                "category": "standard",
                "platform": "portable",
                "apis": [
                    {
                        "name": "FPDF_* (PDFium public API)",
                        "purpose": "PDF 文档加载、页面渲染、文本提取、书签、附件、表单、对象等全部核心功能。",
                        "count": 200,
                        "evidence": [rel("autorelease/bindings.py:399")],
                        "conditional": False
                    }
                ],
                "evidence": [rel("autorelease/bindings.py"), rel("src/pypdfium2/raw.py")]
            }
        ],
        "dynamic_libraries": [
            {
                "name": "libpdfium.so / libpdfium.dylib / pdfium.dll",
                "mechanism": "ctypes.CDLL",
                "acquisition": "prebuilt_binary",
                "source": "默认从 pdfium-binaries 发布页下载对应平台预编译库；sourcebuild 时由本仓脚本从 PDFium 源码构建。",
                "description": "PDFium 共享库，pypdfium2 的全部原生 PDF 能力都依赖它。",
                "optional": False,
                "evidence": [rel("autorelease/bindings.py:67"), rel("src/pypdfium2_raw/__init__.py:15")]
            },
            {
                "name": "libabsl_strings.so / libopenjp2.so",
                "mechanism": "ctypes.CDLL (RTLD_GLOBAL)",
                "acquisition": "system",
                "source": "仅在 FreeBSD 且使用 LibreOffice 提供的 pdfium 时，显式加载其隐式依赖库以解析符号。",
                "description": "BSD + LibreOffice pdfium 的符号解析 workaround。",
                "optional": True,
                "evidence": [rel("src/pypdfium2_raw/__init__.py:11")]
            }
        ],
        "platform_dependence": "mixed"
    },

    "runtime_surface": {
        "summary": "运行时主要依赖 PDFium 共享库和文件系统；除安装/构建阶段外，pypdfium2 本身不主动发起网络请求，也不依赖后台服务或硬件设备。",
        "network": [
            {
                "name": "GitHub / pdfium-binaries releases",
                "purpose": "setup 阶段下载预编译 PDFium 二进制与构建证明（gh attestation）。",
                "evidence": [rel("setupsrc/update.py")]
            },
            {
                "name": "Chromium / PDFium git servers",
                "purpose": "sourcebuild 阶段通过 git fetch/clone 下载 PDFium 及其 DEPS 依赖源码。",
                "evidence": [rel("setupsrc/build_native.py:20"), rel("setupsrc/build_toolchained.py")]
            },
            {
                "name": "raw.githubusercontent.com (LibreOffice deps list)",
                "purpose": "system-search 使用 LibreOffice pdfium 时，联网解析其依赖版本。",
                "evidence": [rel("setupsrc/system_pdfium.py:101")]
            }
        ],
        "filesystem": [
            {
                "name": "data/<platform>/",
                "purpose": "setup 阶段存放下载或构建好的 PDFium 共享库、绑定文件与版本信息。",
                "evidence": [rel("setupsrc/emplace.py")]
            },
            {
                "name": "/usr/lib, /usr/local/lib, /usr/include",
                "purpose": "system-search 模式下查找系统提供的 pdfium 库与头文件。",
                "evidence": [rel("setupsrc/system_pdfium.py:33"), rel("setupsrc/system_pdfium.py:73")]
            },
            {
                "name": "用户输入的 PDF 文件/路径/字节流",
                "purpose": "运行时为 PdfDocument 提供输入数据源。",
                "evidence": [rel("src/pypdfium2/_helpers/document.py:55")]
            }
        ],
        "env_vars": [
            {"name": "PDFIUM_PLATFORM", "purpose": "指定 setup 使用的 PDFium 来源（auto/system/sourcebuild/sdist 等）。", "evidence": [rel("setupsrc/base.py:46")]},
            {"name": "PDFIUM_BINARY", "purpose": "显式指定外部 pdfium 共享库路径。", "evidence": [rel("setupsrc/system_pdfium.py:115")]},
            {"name": "PDFIUM_HEADERS", "purpose": "显式指定 PDFium 头文件目录，用于 system-search 生成绑定。", "evidence": [rel("setupsrc/system_pdfium.py:29")]},
            {"name": "PYPDFIUM_MODULES", "purpose": "选择构建的模块（raw/helpers）。", "evidence": [rel("setup.py:216")]},
            {"name": "PDFIUM_BINDINGS", "purpose": "设为 reference 时使用预生成绑定，跳过 ctypesgen。", "evidence": [rel("setupsrc/base.py:50")]}
        ],
        "subprocess": [
            {"command": "git", "purpose": "获取版本信息、克隆/同步 PDFium 与依赖仓库。", "evidence": [rel("setupsrc/base.py:371"), rel("setupsrc/build_native.py:120")]},
            {"command": "gh", "purpose": "可选，验证 pdfium-binaries 构建证明。", "evidence": [rel("setupsrc/update.py:113")]},
            {"command": "pkg-config", "purpose": "system-search 模式下获取系统 pdfium 版本。", "evidence": [rel("setupsrc/system_pdfium.py:63")]},
            {"command": "gn", "purpose": "sourcebuild 时生成 Ninja 构建文件。", "evidence": [rel("setupsrc/build_native.py:398")]},
            {"command": "ninja", "purpose": "sourcebuild 时编译 PDFium。", "evidence": [rel("setupsrc/build_native.py:398")]},
            {"command": "libreoffice --version", "purpose": "使用 LibreOffice 自带 pdfium 时确定版本。", "evidence": [rel("setupsrc/system_pdfium.py:94")]}
        ],
        "devices": [],
        "services": []
    },

    "build_env": {
        "language_standard": "Python >= 3.6",
        "runtime_version": "CPython >= 3.6（声明支持 Python 3.6+；CI 测试覆盖较新版本）",
        "build_system": "setuptools（自定义 setup.py + pyproject.toml build-system）",
        "compiler_extensions": [
            {"detail": "ctypesgen 生成 ctypes 绑定", "purpose": "将 PDFium C 头文件转为 Python ctypes 接口", "evidence": [rel("setupsrc/base.py:661")]},
            {"detail": "PDFium 默认关闭 V8/XFA/Skia，可选开启", "purpose": "控制 PDFium 功能集与二进制体积", "evidence": [rel("setupsrc/base.py:87")]}
        ],
        "platforms": [
            {"os": "windows", "arch": "x86_64 / x86 / arm64", "evidence": [rel("PLATFORMS.csv:4"), rel("setupsrc/base.py:117")]},
            {"os": "macos", "arch": "x86_64 / arm64", "evidence": [rel("PLATFORMS.csv:2"), rel("setupsrc/base.py:113")]},
            {"os": "linux", "arch": "x86_64 / x86 / aarch64 / armv7l / ppc64le / riscv64 / loong64 / mips64el / mipsel", "evidence": [rel("PLATFORMS.csv:7")]},
            {"os": "android", "arch": "arm64 / armeabi / x86_64 / x86", "evidence": [rel("PLATFORMS.csv:25")]},
            {"os": "ios", "arch": "arm64 / x86_64 simulator", "evidence": [rel("PLATFORMS.csv:29")]}
        ],
        "entry_points": [
            {
                "type": "console_script",
                "name": "pypdfium2",
                "command": "pypdfium2 <subcommand>，支持 render/extract-text/extract-images/arrange/toc 等子命令",
                "evidence": [rel("setup.py:163"), rel("src/pypdfium2_cli/__main__.py")]
            }
        ],
        "packaging": "通过 pip/PyPI 分发平台相关 wheel，默认捆绑 PDFium 共享库与绑定；也提供 sdist 与 sourcebuild 路径。CLI 随库一起安装，无独立安装包。",
        "notes": "构建脚本对平台检测非常细致，区分 glibc/musl、CPU 架构、字节序；源码构建需要较新的 gn/ninja 与 clang/gcc。"
    },

    "capability_profile": {
        "summary": "pypdfium2 是一个纯文档处理/2D 渲染库，不触及桌面 GUI、3D 图形、音视频编解码或硬件设备访问。其核心能力依赖 PDFium 原生引擎，鸿蒙化工作的关键是让 PDFium 在 OHOS NDK 上编译并提供 ohos 平台的共享库。",
        "scenarios": [
            {
                "key": "gui",
                "present": False,
                "kind": [],
                "specific_hardware": False,
                "via": [],
                "harmony_status": "unknown",
                "adaptation": "无需 GUI 改造；库本身无窗口/桌面集成。",
                "evidence": []
            },
            {
                "key": "rendering_3d",
                "present": False,
                "kind": [],
                "specific_hardware": False,
                "via": [],
                "harmony_status": "unknown",
                "adaptation": "仅 2D 页面光栅化，不依赖 OpenGL/Vulkan/DirectX/Metal。PDFium 内部可能使用 Skia/AGG，但属于 2D 光栅化后端，非 3D 场景。",
                "evidence": [rel("src/pypdfium2/_helpers/page.py:render")]
            },
            {
                "key": "media",
                "present": False,
                "kind": [],
                "specific_hardware": False,
                "via": [],
                "harmony_status": "unknown",
                "adaptation": "不处理音视频流；PDF 内嵌媒体不是该库关注重点。",
                "evidence": []
            },
            {
                "key": "hardware",
                "present": False,
                "kind": [],
                "specific_hardware": False,
                "via": [],
                "harmony_status": "unknown",
                "adaptation": "无 GPU 计算、USB、蓝牙、传感器等硬件访问。",
                "evidence": []
            },
            {
                "key": "document_rendering",
                "present": True,
                "kind": ["pdf_rendering", "2d_rasterization"],
                "specific_hardware": False,
                "via": ["PDFium", "pypdfium2.raw"],
                "harmony_status": "unknown",
                "adaptation": "核心场景。需要将 PDFium 交叉编译到鸿蒙 OHOS NDK（arm64），并确保 ctypes 绑定在鸿蒙 Python 上正确加载 .so。",
                "evidence": [rel("autorelease/bindings.py:67"), rel("src/pypdfium2/_library_scope.py:init_lib")]
            }
        ]
    },

    "harmony_adaptation": {
        "target": "HarmonyOS NEXT PC（自研内核，OHOS NDK 原生层，Python 已移植）",
        "feasibility": "feasible_with_effort",
        "porting_class": "needs_adaptation_full",
        "effort": {
            "person_days": [20, 45],
            "level": "high"
        },
        "confidence": "medium",
        "unadaptable_apis": [],
        "target_assumptions": [
            {
                "id": "ta:python",
                "capability": "Python 运行时已移植到鸿蒙 PC",
                "required": True,
                "target_status": "available",
                "impact": "Python 已移植，纯 Python 代码可直接运行；这是库类项目默认口径。",
                "source": "references/harmony-pc-capabilities.json runtimes/python"
            },
            {
                "id": "ta:ohos_ndk_pdfium",
                "capability": "OHOS NDK 能够交叉编译 PDFium 及其依赖（C/C++ 标准库、gn/ninja 工具链）",
                "required": True,
                "target_status": "unknown",
                "impact": "PDFium 是 C++ 核心，必须在鸿蒙上获得 libpdfium.so；若 OHOS NDK 不支持 Chromium/PDFium 的编译工具链或依赖库，则无法运行。",
                "source": "references/harmony-pc-capabilities.json arch/arm64 + 模型推断"
            },
            {
                "id": "ta:ctypes",
                "capability": "鸿蒙 Python 支持 ctypes 动态加载 .so 并调用 C 函数",
                "required": True,
                "target_status": "available",
                "impact": "pypdfium2 完全依赖 ctypes 做 FFI；若鸿蒙 Python 的 ctypes 不完整则核心功能失效。",
                "source": "Python 已移植的默认假设"
            },
            {
                "id": "ta:file_storage",
                "capability": "读写应用私有/用户授权存储（文件访问权限）",
                "required": True,
                "target_status": "unknown",
                "impact": "PDF 输入输出依赖文件系统访问；鸿蒙 PC 权限模型若受限需申请 ohos.permission 读写存储。",
                "source": "references/harmony-pc-capabilities.json permissions/perm_storage"
            },
            {
                "id": "ta:network_download",
                "capability": "setup 阶段允许联网下载预编译二进制或源码（或提供离线 bundle）",
                "required": False,
                "target_status": "unknown",
                "impact": "默认安装路径会下载 pdfium-binaries；鸿蒙上若无法联网需改为 sourcebuild 或预置 .so。",
                "source": "模型推断"
            }
        ],
        "required_permissions": [
            {
                "permission": "ohos.permission.READ_MEDIA / 读写存储",
                "reason": "读取用户 PDF 文件并输出渲染图片/提取内容需要文件系统访问。",
                "source_capability": "document_rendering",
                "harmony_status": "unknown",
                "evidence": [rel("src/pypdfium2/_helpers/document.py:59")]
            }
        ],
        "blockers": [],
        "recommended_path": "在鸿蒙 PC 上使用 OHOS NDK 交叉编译 PDFium（关闭 V8/XFA 以减小复杂度），生成 libpdfium.so；调整 setupsrc/base.py 中的平台检测逻辑以识别 ohos 目标；将预编译的 ohos-arm64 二进制放入数据目录或提供 sourcebuild 路径；验证 ctypes 加载与符号解析；可选依赖 Pillow/NumPy/opencv 需确认鸿蒙 PyPI 镜像是否提供对应 ohos wheel。",
        "notes": "核心障碍不是平台专有 API 不可适配，而是 PDFium 这一大型 C++ 引擎能否在 OHOS NDK 上成功编译。PDFium 内部依赖的 freetype/icu/lcms2/libjpeg/openjpeg/libpng/libtiff/zlib/harfbuzz 等库大多为标准 C/C++ 库，理论上可移植，但工具链（gn/ninja、clang、musl 兼容性）和构建配置需要专门适配。由于 'OHOS NDK 能否编译 PDFium' 目前为 unknown，置信度评为 medium。"
    },

    "meta": {
        "agent": "pc-lib-analyzer (single-session)",
        "model": "kimi-k2.7",
        "observations": [
            {
                "dimension": "capability_profile",
                "field": "scenarios[].key",
                "kind": "new_value",
                "value": "document_rendering",
                "rationale": "pypdfium2 核心场景是 PDF 文档的 2D 渲染与处理，不属于 gui/rendering_3d/media/hardware 推荐键，故新增 document_rendering 作为自定义场景键。"
            }
        ],
        "confidence_overall": "medium",
        "notes": "分析基于已检出的源码与预构建 codegraph 索引；未实际执行构建。"
    }
}

out = RUN_DIR / "report.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(f"Wrote {out}")
