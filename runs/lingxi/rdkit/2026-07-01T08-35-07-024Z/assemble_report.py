#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble the RDKit analysis report from metrics + model reasoning."""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
metrics_path = here / "metrics.json"
report_path = here / "report.json"

with open(metrics_path, "r", encoding="utf-8") as f:
    metrics = json.load(f)

dependencies = [
    {"name": "Boost", "ecosystem": "cpp", "registry_name": "boost", "source_repo": "https://github.com/boostorg/boost",
     "aliases": ["boost"], "scope": "runtime", "version": "1.81.0", "purpose": "C++ 头文件库、Python 绑定（Boost.Python/Boost.NumPy）、序列化、iostreams、zlib 后端",
     "acquisition": "system", "locality": "system", "source": "系统(find_package(Boost 1.81.0)，需预装)",
     "declared_in": ["CMakeLists.txt:337", "CMakeLists.txt:412", "CMakeLists.txt:448", "CMakeLists.txt:458", "CMakeLists.txt:467"],
     "used_symbols": ["boost::python", "boost::iostreams", "boost::serialization"]},
    {"name": "Python3", "ecosystem": "python", "registry_name": None, "source_repo": "https://github.com/python/cpython",
     "aliases": [], "scope": "build", "version": None, "purpose": "Python 解释器与开发头文件，用于构建 Python 包装",
     "acquisition": "system", "locality": "system", "source": "系统(find_package(Python3 COMPONENTS Interpreter Development.Module)，需预装)",
     "declared_in": ["CMakeLists.txt:320"], "used_symbols": []},
    {"name": "NumPy", "ecosystem": "python", "registry_name": "numpy", "source_repo": "https://github.com/numpy/numpy",
     "aliases": [], "import_names": ["numpy"], "scope": "runtime", "version": None, "purpose": "Python 包装中的 NumPy 数组互操作",
     "acquisition": "system", "locality": "system", "source": "系统(find_package(Python3 COMPONENTS NumPy)，需预装)",
     "declared_in": ["CMakeLists.txt:320"], "used_symbols": ["numpy.ndarray"]},
    {"name": "Eigen3", "ecosystem": "cpp", "registry_name": "eigen3", "source_repo": "https://gitlab.com/libeigen/eigen",
     "aliases": ["Eigen"], "scope": "optional", "version": None, "purpose": "3D 描述符与数值计算的线性代数库",
     "acquisition": "system", "locality": "system", "source": "系统(find_package(Eigen3))；若未找到则使用 External/Eigen 内置源码",
     "declared_in": ["CMakeLists.txt:415", "External/Eigen"], "used_symbols": ["Eigen::Matrix"]},
    {"name": "Threads", "ecosystem": "cpp", "registry_name": None, "source_repo": None,
     "aliases": ["pthread"], "scope": "runtime", "version": None, "purpose": "多线程支持（pthread/Windows threads）",
     "acquisition": "system", "locality": "system", "source": "系统(find_package(Threads))",
     "declared_in": ["CMakeLists.txt:430"], "used_symbols": ["std::thread", "pthread"]},
    {"name": "ZLIB", "ecosystem": "cpp", "registry_name": "zlib", "source_repo": "https://github.com/madler/zlib",
     "aliases": ["zlib"], "scope": "runtime", "version": None, "purpose": "压缩 SD/MOL 供应商与文件解析（gzip）",
     "acquisition": "system", "locality": "system", "source": "系统(find_package(ZLIB) 或 Boost::zlib)",
     "declared_in": ["CMakeLists.txt:467", "CMakeLists.txt:475", "Code/GraphMol/FileParsers/CMakeLists.txt:4"], "used_symbols": ["deflate", "inflate"]},
    {"name": "InChI", "ecosystem": "cpp", "registry_name": "inchi", "source_repo": "https://www.inchi-trust.org",
     "aliases": [], "scope": "optional", "version": None, "purpose": "InChI 化学标识符解析与生成",
     "acquisition": "vendored", "locality": "local", "source": "仓库内 External/INCHI-API 源码（可经 download-inchi.sh 下载官方源码）",
     "declared_in": ["CMakeLists.txt:312", "External/INCHI-API/CMakeLists.txt"], "used_symbols": ["GetINCHI", "GetINCHIKey"]},
    {"name": "PostgreSQL", "ecosystem": "cpp", "registry_name": "postgresql", "source_repo": "https://git.postgresql.org/git/postgresql.git",
     "aliases": ["postgres"], "scope": "optional", "version": None, "purpose": "RDKit PostgreSQL cartridge 扩展",
     "acquisition": "system", "locality": "system", "source": "系统(find_package(PostgreSQL))",
     "declared_in": ["CMakeLists.txt:494", "Code/PgSQL/rdkit/CMakeLists.txt:1"], "used_symbols": []},
    {"name": "coordgen", "ecosystem": "cpp", "registry_name": "coordgen", "source_repo": "https://github.com/schrodinger/coordgenlibs",
     "aliases": ["coordgenlibs"], "scope": "optional", "version": "3.0.2", "purpose": "2D 分子坐标生成（CoordGen 算法）",
     "acquisition": "download_build", "locality": "remote", "source": "https://github.com/schrodinger/coordgenlibs/archive/v3.0.2.tar.gz（构建时下载并内嵌编译）",
     "declared_in": ["External/CoordGen/CMakeLists.txt:73"], "used_symbols": ["sketcherMinimizer", "CoordgenMinimizer"]},
    {"name": "maeparser", "ecosystem": "cpp", "registry_name": "maeparser", "source_repo": "https://github.com/schrodinger/maeparser",
     "aliases": [], "scope": "optional", "version": "1.3.3", "purpose": "Schrödinger Maestro MAE 文件解析",
     "acquisition": "download_build", "locality": "remote", "source": "https://github.com/schrodinger/maeparser/archive/v1.3.3.tar.gz（构建时下载并内嵌编译）",
     "declared_in": ["External/CoordGen/CMakeLists.txt:19"], "used_symbols": ["MaeParser"]},
    {"name": "FreeSASA", "ecosystem": "cpp", "registry_name": "freesasa", "source_repo": "https://github.com/mittinatten/freesasa",
     "aliases": [], "scope": "optional", "version": "2.0.3", "purpose": "分子溶剂可及表面积（SASA）计算",
     "acquisition": "download_build", "locality": "remote", "source": "https://github.com/mittinatten/freesasa/releases/download/2.0.3/freesasa-2.0.3.tar.gz",
     "declared_in": ["External/FreeSASA/CMakeLists.txt:18"], "used_symbols": ["freesasa_calc_structure"]},
    {"name": "AvalonTools", "ecosystem": "cpp", "registry_name": "AvalonToolkit", "source_repo": "https://github.com/rdkit/ava-formake",
     "aliases": ["AvalonToolkit"], "scope": "optional", "version": "2.0.5-pre.3", "purpose": "额外分子指纹与结构检查",
     "acquisition": "download_build", "locality": "remote", "source": "https://github.com/rdkit/ava-formake/archive/refs/tags/AvalonToolkit_2.0.5-pre.3.tar.gz",
     "declared_in": ["External/AvalonTools/CMakeLists.txt:25"], "used_symbols": []},
    {"name": "YAeHMOP", "ecosystem": "cpp", "registry_name": "yaehmop", "source_repo": "https://github.com/greglandrum/yaehmop",
     "aliases": [], "scope": "optional", "version": "2025.03.2", "purpose": "扩展 Hückel 紧束缚计算",
     "acquisition": "download_build", "locality": "remote", "source": "https://github.com/greglandrum/yaehmop/archive/refs/tags/v2025.03.2.tar.gz",
     "declared_in": ["External/YAeHMOP/CMakeLists.txt:14"], "used_symbols": []},
    {"name": "ChemDraw", "ecosystem": "cpp", "registry_name": "chemdraw", "source_repo": "https://github.com/Glysade/chemdraw",
     "aliases": [], "scope": "optional", "version": "1.0.14", "purpose": "CDX/CDXML 化学绘图文件解析",
     "acquisition": "download_build", "locality": "remote", "source": "https://codeload.github.com/Glysade/chemdraw/tar.gz/refs/tags/v1.0.14",
     "declared_in": ["External/ChemDraw/CMakeLists.txt:15"], "used_symbols": []},
    {"name": "EXPAT", "ecosystem": "cpp", "registry_name": "expat", "source_repo": "https://github.com/libexpat/libexpat",
     "aliases": ["expat"], "scope": "optional", "version": None, "purpose": "ChemDraw CDXML 的 XML 解析",
     "acquisition": "system", "locality": "system", "source": "系统(find_package(EXPAT))",
     "declared_in": ["External/ChemDraw/CMakeLists.txt:29"], "used_symbols": ["XML_Parse"]},
    {"name": "pubchem-align3d", "ecosystem": "cpp", "registry_name": "pubchem-align3d", "source_repo": "https://github.com/ncbi/pubchem-align3d",
     "aliases": [], "scope": "optional", "version": "daefab3", "purpose": "PubChem 3D 形状对齐",
     "acquisition": "download_build", "locality": "remote", "source": "https://github.com/ncbi/pubchem-align3d/archive/daefab3.tar.gz",
     "declared_in": ["External/pubchem_shape/CMakeLists.txt:19"], "used_symbols": []},
    {"name": "Qt", "ecosystem": "cpp", "registry_name": "qtbase", "source_repo": "https://github.com/qt/qtbase",
     "aliases": ["Qt5", "Qt6"], "scope": "optional", "version": None, "purpose": "MolDraw2D 可选 Qt6/Qt5 绘制后端",
     "acquisition": "system", "locality": "system", "source": "系统(find_package(Qt6 或 Qt5 COMPONENTS Core Widgets OpenGL))",
     "declared_in": ["Code/GraphMol/MolDraw2D/Qt/CMakeLists.txt:10", "Code/GraphMol/MolDraw2D/CMakeLists.txt:53"], "used_symbols": ["QPainter", "QWidget"]},
    {"name": "Cairo", "ecosystem": "cpp", "registry_name": "cairo", "source_repo": "https://gitlab.freedesktop.org/cairo/cairo",
     "aliases": [], "scope": "optional", "version": None, "purpose": "MolDraw2D 可选 Cairo 2D 绘制后端",
     "acquisition": "system", "locality": "system", "source": "系统(find_package(Cairo))",
     "declared_in": ["Code/GraphMol/MolDraw2D/CMakeLists.txt:58"], "used_symbols": ["cairo_create"]},
    {"name": "FreeType", "ecosystem": "cpp", "registry_name": "freetype", "source_repo": "https://github.com/freetype/freetype",
     "aliases": [], "scope": "optional", "version": None, "purpose": "MolDraw2D 字体渲染（默认可用）",
     "acquisition": "system", "locality": "system", "source": "系统(find_package(Freetype))",
     "declared_in": ["Code/GraphMol/MolDraw2D/CMakeLists.txt:84", "Code/GraphMol/MolDraw2D/Qt/CMakeLists.txt:57"], "used_symbols": ["FT_Init_FreeType"]},
    {"name": "Catch2", "ecosystem": "cpp", "registry_name": "catch2", "source_repo": "https://github.com/catchorg/Catch2",
     "aliases": [], "scope": "test", "version": "3.4.0", "purpose": "C++ 单元测试框架",
     "acquisition": "fetchcontent", "locality": "remote", "source": "https://github.com/catchorg/Catch2.git v3.4.0（CMake FetchContent）",
     "declared_in": ["CMakeLists.txt:183"], "used_symbols": []},
    {"name": "better_enums", "ecosystem": "cpp", "registry_name": "better-enums", "source_repo": "https://github.com/aantron/better-enums",
     "aliases": [], "scope": "build", "version": "0.11.3", "purpose": "编译期枚举反射宏库",
     "acquisition": "fetchcontent", "locality": "remote", "source": "https://github.com/aantron/better-enums.git c35576be（CMake FetchContent）",
     "declared_in": ["CMakeLists.txt:195"], "used_symbols": []},
    {"name": "SWIG", "ecosystem": "other", "registry_name": "swig", "source_repo": "https://github.com/swig/swig",
     "aliases": [], "scope": "build", "version": "4.2+", "purpose": "Java/C# 绑定代码生成工具",
     "acquisition": "system", "locality": "system", "source": "系统(find_package(SWIG 4.2 REQUIRED))",
     "declared_in": ["Code/JavaWrappers/CMakeLists.txt:1"], "used_symbols": []},
    {"name": "Java JDK / JNI", "ecosystem": "java", "registry_name": None, "source_repo": "https://github.com/openjdk/jdk",
     "aliases": [], "scope": "build", "version": None, "purpose": "Java 包装构建所需的 JDK 与 JNI 头文件",
     "acquisition": "system", "locality": "system", "source": "系统(find_package(Java), find_package(JNI))",
     "declared_in": ["Code/JavaWrappers/gmwrapper/CMakeLists.txt:7"], "used_symbols": ["JNIEXPORT", "JNIEnv"]},
    {"name": "Flex / Bison", "ecosystem": "other", "registry_name": None, "source_repo": None,
     "aliases": [], "scope": "build", "version": None, "purpose": "可选 SMILES/SMARTS/SLN 解析器生成",
     "acquisition": "system", "locality": "system", "source": "系统（当 RDK_USE_FLEXBISON=ON 时 find_package）",
     "declared_in": ["CMakeLists.txt:49"], "used_symbols": []},
    {"name": "TBB", "ecosystem": "cpp", "registry_name": "tbb", "source_repo": "https://github.com/oneapi-src/oneTBB",
     "aliases": ["oneTBB"], "scope": "test", "version": None, "purpose": "可选的并行迭代器测试依赖",
     "acquisition": "system", "locality": "system", "source": "系统(find_package(TBB))",
     "declared_in": ["Code/GraphMol/FileParsers/CMakeLists.txt:133"], "used_symbols": []},
]

by_ecosystem = {}
for d in dependencies:
    by_ecosystem.setdefault(d["ecosystem"], []).append(d["name"])

deps_block = {
    "count": len(dependencies),
    "manifests": [
        "CMakeLists.txt",
        "setup.cfg",
        "Code/GraphMol/MolDraw2D/CMakeLists.txt",
        "Code/GraphMol/FileParsers/CMakeLists.txt",
        "External/CoordGen/CMakeLists.txt",
        "External/AvalonTools/CMakeLists.txt",
        "External/FreeSASA/CMakeLists.txt",
        "External/YAeHMOP/CMakeLists.txt",
        "External/INCHI-API/CMakeLists.txt",
        "External/ChemDraw/CMakeLists.txt",
        "External/pubchem_shape/CMakeLists.txt",
        "Code/JavaWrappers/CMakeLists.txt"
    ],
    "by_ecosystem": by_ecosystem,
    "dependencies": dependencies,
    "notes": "RDKit 是 C++ 核心库，依赖栈以 C++ 系统库和构建时下载的可选外部库为主；Python/Java/C# 绑定依赖对应运行时与 SWIG/Boost.Python。未锁死版本到 requirements.txt，版本约束主要来自 CMake find_package 与 option。"
}

report = {
    "library": {
        "name": "RDKit",
        "kind": "library",
        "package_name": "rdkit",
        "aliases": ["RDKit"],
        "import_names": ["rdkit"],
        "source_url": "https://github.com/rdkit/rdkit.git",
        "analyzed_at": "2026-07-01T08:35:07.024Z",
        "commit": "b9e91ba76bae5e9974491e885cade9668ba1bfd0",
        "one_liner": "开源的 C++ 化学信息学与机器学习工具库，提供分子操作、描述符/指纹、2D/3D 处理及多语言绑定。",
        "ecosystem": "cpp",
        "bindings": ["python", "java", "dotnet", "nodejs"]
    },
    "function_summary": {
        "summary": "RDKit 是一套用于化学信息学与机器学习的开源 C++ 工具库，核心提供分子数据模型、SMILES/SMARTS 解析、描述符与指纹计算、2D/3D 分子操作、子结构/相似性搜索及化学反应处理。它通过 Boost.Python、SWIG 和 Emscripten 向 Python、Java、C#、JavaScript 提供绑定，主要面向药物研发、计算化学与数据科学开发者。",
        "categories": [
            {"name": "分子数据模型与基本操作", "description": "提供 ROMol/RWMol 分子对象、原子/键/构象、芳香性/手性/环信息等核心数据结构及分子编辑操作。", "evidence": ["Code/GraphMol/ROMol.h", "Code/GraphMol/RWMol.h", "Code/GraphMol/MolOps.h", "Code/GraphMol/Atom.h"]},
            {"name": "化学格式解析与生成", "description": "支持 SMILES/SMARTS/SLN、MOL/SDF、PDB、XYZ、CML、MAE、InChI、CDXML 等分子文件的读写与转换。", "evidence": ["Code/GraphMol/SmilesParse/SmilesWrite.cpp", "Code/GraphMol/FileParsers/FileParsers.h", "Code/GraphMol/SmilesParse", "Code/GraphMol/SLNParse"]},
            {"name": "分子描述符与指纹", "description": "计算理化性质、拓扑/3D 描述符、MACCS/Morgan/RDKit 指纹等，用于机器学习和虚拟筛选。", "evidence": ["Code/GraphMol/Descriptors", "Code/GraphMol/Fingerprints", "Code/DataStructs/BitOps.cpp"]},
            {"name": "2D/3D 分子处理与绘制", "description": "提供 2D 坐标生成（Depictor/CoordGen）、3D 构象生成、力场优化、分子对齐，以及 MolDraw2D 绘制到 SVG/JS/Qt/Cairo。", "evidence": ["Code/GraphMol/Depictor", "Code/GraphMol/MolDraw2D", "Code/GraphMol/MolAlign", "Code/DistGeom", "Code/ForceField"]},
            {"name": "子结构与相似性搜索", "description": "支持子结构匹配、SMARTS 查询、相似性搜索、子结构库（SubstructLibrary）及合成空间搜索。", "evidence": ["Code/GraphMol/Substruct", "Code/GraphMol/SubstructLibrary", "Code/GraphMol/SynthonSpaceSearch", "Code/GraphMol/GeneralizedSubstruct"]},
            {"name": "化学反应与合成规划", "description": "提供反应模板、反应物/产物转换、R-Group 分解、MMPA、分子枚举等反应化学能力。", "evidence": ["Code/GraphMol/ChemReactions", "Code/GraphMol/RGroupDecomposition", "Code/GraphMol/MMPA", "Code/GraphMol/MolEnumerator"]},
            {"name": "多语言绑定与集成", "description": "通过 Boost.Python 暴露 Python API，通过 SWIG 生成 Java/C# 绑定，通过 Emscripten/CFFI 提供 JavaScript/C 接口；还提供 PostgreSQL cartridge 与 KNIME 节点。", "evidence": ["rdkit/__init__.py", "Code/JavaWrappers", "Code/MinimalLib", "Code/PgSQL"]}
        ],
        "domain": "化学信息学 / 药物研发 / 机器学习",
        "target_users": "药物研发人员、计算化学/化学信息学开发者、数据科学家及机器学习工程师"
    },
    "languages": metrics["languages"],
    "code_metrics": metrics["code_metrics"],
    "tests": metrics["tests"],
    "license": {
        "spdx": "BSD-3-Clause",
        "name": "BSD 3-Clause License",
        "confidence": "high",
        "is_dual_licensed": False,
        "license_files": ["license.txt"],
        "evidence": "根目录 license.txt 包含标准 BSD-3-Clause 全文；README.md 亦声明 BSD license。",
        "notes": "宽松许可。仓库内 vendored/外部依赖（如 External/ 下载的 CoordGen、FreeSASA、AvalonTools 等）可能各自携带不同许可证，需单独确认。"
    },
    "dependencies": deps_block,
    "native_api": {
        "summary": "RDKit 以 C++20 标准库实现跨平台算法核心，平台相关代码极少。多线程使用 std::thread/std::mutex/std::async；Python 绑定直接调用 Python C-API；仅 SynthonSpaceSearch 的 MemoryMappedFileReader 使用平台相关的内存映射（Windows CreateFileMapping vs POSIX mmap），且 Depictor/Basement 中存在仅 WIN32_DLLBUILD 下编译的历史 DLL 加载代码。x86 popcount 内建函数有条件回退。",
        "groups": [
            {"type": "cpp_stl", "category": "standard", "platform": "portable", "apis": [
                {"name": "std::thread", "purpose": "多线程任务并行", "count": 40, "evidence": ["Code/GraphMol/SynthonSpaceSearch/SynthonSpace.cpp:431", "Code/GraphMol/MolAlign/AlignMolecules.cpp:170"], "conditional": False},
                {"name": "std::mutex / std::lock_guard", "purpose": "线程同步与数据保护", "count": 80, "evidence": ["Code/RDGeneral/ConcurrentQueue.h:25", "Code/GraphMol/MolPickler.cpp:82"], "conditional": False},
                {"name": "std::async", "purpose": "异步并行计算", "count": 30, "evidence": ["Code/GraphMol/Substruct/SubstructMatch.cpp:634", "Code/GraphMol/Resonance.cpp:1421"], "conditional": False},
                {"name": "std::atomic", "purpose": "无锁原子计数", "count": 20, "evidence": ["Code/GraphMol/SynthonSpaceSearch/SynthonSpaceSearcher.cpp:69"], "conditional": False}
            ]},
            {"type": "python_c_api", "category": "ffi", "platform": "portable", "apis": [
                {"name": "PyTuple_New", "purpose": "构造 Python 元组返回结果", "count": 50, "evidence": ["Code/GraphMol/Wrap/substructmethods.h:56", "Code/GraphMol/Wrap/MolOps.cpp:336"], "conditional": False},
                {"name": "PyBytes_FromStringAndSize", "purpose": "将 C++ 字节串转为 Python bytes", "count": 20, "evidence": ["Code/GraphMol/Wrap/Mol.cpp:47", "Code/GraphMol/Wrap/rdmolfiles.cpp:604"], "conditional": False},
                {"name": "PyObject_CallMethod", "purpose": "调用 Python logging 等对象方法", "count": 10, "evidence": ["Code/RDBoost/Wrap/RDBase.cpp:59", "Code/RDBoost/Wrap/RDBase.cpp:95"], "conditional": False},
                {"name": "Py_DECREF", "purpose": "减少 Python 对象引用计数", "count": 40, "evidence": ["Code/RDBoost/Wrap/RDBase.cpp:60", "Code/SimDivPickers/Wrap/MaxMinPicker.cpp:56"], "conditional": False}
            ]},
            {"type": "posix", "category": "platform", "platform": "posix", "apis": [
                {"name": "mmap", "purpose": "POSIX 内存映射文件读取", "count": 1, "evidence": ["Code/GraphMol/SynthonSpaceSearch/MemoryMappedFileReader.cpp:84"], "conditional": True},
                {"name": "munmap", "purpose": "解除 POSIX 内存映射", "count": 2, "evidence": ["Code/GraphMol/SynthonSpaceSearch/MemoryMappedFileReader.cpp:108"], "conditional": True},
                {"name": "open", "purpose": "打开文件描述符", "count": 1, "evidence": ["Code/GraphMol/SynthonSpaceSearch/MemoryMappedFileReader.cpp:68"], "conditional": True},
                {"name": "fstat", "purpose": "获取文件状态", "count": 1, "evidence": ["Code/GraphMol/SynthonSpaceSearch/MemoryMappedFileReader.cpp:76"], "conditional": True}
            ]},
            {"type": "win32", "category": "platform", "platform": "windows", "apis": [
                {"name": "CreateFileMapping", "purpose": "Windows 内存映射文件", "count": 1, "evidence": ["Code/GraphMol/SynthonSpaceSearch/MemoryMappedFileReader.cpp:50"], "conditional": True},
                {"name": "MapViewOfFile", "purpose": "映射视图到进程地址空间", "count": 1, "evidence": ["Code/GraphMol/SynthonSpaceSearch/MemoryMappedFileReader.cpp:58"], "conditional": True},
                {"name": "UnmapViewOfFile", "purpose": "解除 Windows 映射视图", "count": 2, "evidence": ["Code/GraphMol/SynthonSpaceSearch/MemoryMappedFileReader.cpp:105"], "conditional": True},
                {"name": "GetFileSizeEx", "purpose": "获取 Windows 文件大小", "count": 1, "evidence": ["Code/GraphMol/SynthonSpaceSearch/MemoryMappedFileReader.cpp:43"], "conditional": True},
                {"name": "LoadLibrary", "purpose": "加载外部 Depict DLL（历史功能）", "count": 1, "evidence": ["Code/GraphMol/Depictor/Basement/DepictorDLL.cpp:63"], "conditional": True},
                {"name": "GetProcAddress", "purpose": "获取 DLL 导出函数", "count": 1, "evidence": ["Code/GraphMol/Depictor/Basement/DepictorDLL.cpp:69"], "conditional": True}
            ]},
            {"type": "arch_simd", "category": "hardware", "platform": "portable", "apis": [
                {"name": "__builtin_popcountll", "purpose": "GCC/Clang 64 位 popcount（有查表回退）", "count": 2, "evidence": ["Code/DataStructs/BitOps.cpp:910"], "conditional": True},
                {"name": "__popcnt / __popcnt64", "purpose": "MSVC x86/x64 popcount（有查表回退）", "count": 2, "evidence": ["Code/DataStructs/BitOps.cpp:903"], "conditional": True},
                {"name": "-mpopcnt / RDK_OPTIMIZE_POPCNT", "purpose": "编译期启用 SSE4.2 POPCNT 指令（可选，默认开）", "count": 1, "evidence": ["CMakeLists.txt:54", "CMakeLists.txt:94"], "conditional": True}
            ]}
        ],
        "dynamic_libraries": [
            {"name": "librdkitcffi.so", "mechanism": "ctypes.cdll.LoadLibrary", "acquisition": "self_build", "source": "本仓 MinimalLib CFFI 包装产物", "description": "RDKit MinimalLib 的 CFFI 共享库，供 Python 等语言加载", "optional": False, "evidence": ["Code/MinimalLib/simple.py:3"]},
            {"name": "GraphMolWrap", "mechanism": "JNI System.loadLibrary", "acquisition": "self_build", "source": "本仓 SWIG Java 包装产物", "description": "SWIG 生成的 Java 包装原生库，Java 测试加载", "optional": True, "evidence": ["Code/JavaWrappers/gmwrapper/src-test/org/RDKit/GraphMolTest.java:51"]},
            {"name": "depict32-0.dll", "mechanism": "LoadLibrary", "acquisition": "third_party", "source": "外部 Combichem Depict DLL（历史 Windows 专有）", "description": "旧版 Depictor 依赖的第三方 Windows DLL", "optional": True, "evidence": ["Code/GraphMol/Depictor/Basement/DepictorDLL.cpp:63"]}
        ],
        "platform_dependence": "cross-platform"
    },
    "runtime_surface": {
        "summary": "RDKit 运行期主要读取 $RDBASE 下的数据/字体/模板文件；除构建时下载外部源码外，生产代码无网络访问，也不执行外部命令。",
        "network": [],
        "filesystem": [
            {"detail": "$RDBASE/Data 下的化学数据、SMARTS 库、特征定义等", "purpose": "加载分子模板、特征、运行数据", "evidence": ["rdkit/RDConfig.py:18", "External/CoordGen/CoordGen.h:64"]},
            {"detail": "$RDBASE/Data/Fonts/ComicNeue-Regular.ttf", "purpose": "MolDraw2D comic 模式字体（构建时下载到数据目录）", "evidence": ["Code/GraphMol/MolDraw2D/CMakeLists.txt:22"]},
            {"detail": "CoordGen 模板目录 $RDBASE/Data", "purpose": "2D 坐标生成模板", "evidence": ["External/CoordGen/CoordGen.h:67"]}
        ],
        "env_vars": [
            {"name": "RDBASE", "purpose": "定位 RDKit 数据/代码/资源根目录", "evidence": ["rdkit/RDConfig.py:18", "External/CoordGen/CoordGen.h:64"]},
            {"name": "RD_MOLVIEWER", "purpose": "指定 3D 分子可视化工具（如 PYMOL）", "evidence": ["rdkit/RDConfig.py:88"]},
            {"name": "COMBICHEM_ROOT / COMBICHEM_RELEASE", "purpose": "旧版 DepictorDLL 查找外部 depict32.dll（仅 WIN32_DLLBUILD）", "evidence": ["Code/GraphMol/Depictor/Basement/DepictorDLL.cpp:50"]}
        ],
        "subprocess": [],
        "devices": [],
        "services": []
    },
    "build_env": {
        "language_standard": "C++20, C99；Python 包装依赖 Python 3.x",
        "runtime_version": "Python 3.x（find_package(Python3) 动态匹配）",
        "build_system": "CMake（>=3.18）+ CPack",
        "compiler_extensions": [
            {"detail": "x86 popcount 内建函数 / -mpopcnt 编译选项", "evidence": ["CMakeLists.txt:54", "Code/DataStructs/BitOps.cpp:900"]},
            {"detail": "-fPIC 与符号可见性控制（hidden / WINDOWS_EXPORT_ALL_SYMBOLS）", "evidence": ["CMakeLists.txt:526", "External/ChemDraw/CMakeLists.txt:85"]},
            {"detail": "MSVC 特定警告抑制与 _CRT_SECURE_NO_WARNINGS", "evidence": ["CMakeLists.txt:292", "CMakeLists.txt:602"]}
        ],
        "platforms": [
            {"os": "linux", "arch": "x86_64", "evidence": [".azure-pipelines/linux_build.yml", "CMakeLists.txt #ifdef __linux"]},
            {"os": "macos", "arch": "x86_64/arm64", "evidence": [".azure-pipelines/mac_build.yml", "CMakeLists.txt #ifdef __APPLE__"]},
            {"os": "windows", "arch": "x86_64", "evidence": [".azure-pipelines/vs_build.yml", "CMakeLists.txt #ifdef _WIN32"]}
        ],
        "entry_points": [],
        "packaging": "CMake 安装目标 + CPack 生成 TGZ/DEB/RPM 分发包；Python 包由 conda-forge/PyPI 分发；不捆绑运行时。",
        "notes": "大量功能通过 CMake option 开关；C#/Java 绑定由 SWIG 在构建时生成。"
    },
    "capability_profile": {
        "summary": "RDKit 核心是计算/算法库，不直接涉及 3D 图形、媒体编解码或特定硬件；仅在 MolDraw2D 模块提供可选的 Qt/Cairo 2D 绘制后端，以及遗留的 sping/PyQt4/Tkinter 等 Python 2D 绘图包装。",
        "scenarios": [
            {"key": "gui", "present": True, "kind": ["qt6", "qt5", "cairo", "freetype"], "via": ["Qt6/Qt5", "Cairo", "FreeType"], "harmony_status": "available", "adaptation": "可选绘制后端；目标环境无 Qt/Cairo 时可关闭对应 CMake option，使用 SVG/JS 后端输出", "evidence": ["Code/GraphMol/MolDraw2D/Qt/CMakeLists.txt:10", "Code/GraphMol/MolDraw2D/CMakeLists.txt:57", "Code/GraphMol/MolDraw2D/CMakeLists.txt:84"]},
            {"key": "rendering_2d", "present": True, "kind": ["svg", "cairo", "qt"], "via": ["MolDraw2DSVG", "MolDraw2DCairo", "MolDraw2DQt"], "harmony_status": "available", "adaptation": "2D 绘制可用纯 SVG 实现；Cairo/Qt 为可选后端", "evidence": ["Code/GraphMol/MolDraw2D/MolDraw2DSVG.h", "Code/GraphMol/MolDraw2D/CMakeLists.txt:41"]},
            {"key": "rendering_3d", "present": False},
            {"key": "media", "present": False},
            {"key": "hardware", "present": False}
        ]
    },
    "harmony_adaptation": {
        "target": "HarmonyOS NEXT PC：C++ 核心经 OHOS NDK（musl + POSIX 子集）重新编译为 arm64/x86_64 .so；Python/Java/C# 绑定依赖已移植的语言运行时，只需重建原生扩展。",
        "porting_class": "needs_adaptation_full",
        "feasibility": "feasible_with_effort",
        "effort": {"person_days": [15, 35]},
        "confidence": "high",
        "recommended_path": "recompile_napi",
        "summary": "RDKit 以 C++20 算法核心为主，平台相关代码极少（仅 MemoryMappedFileReader 的 mmap/CreateFileMapping 双路径、少量 Win32/x86 popcount 内建函数），且都有通用回退或 POSIX 路径；Python/Java/C# 绑定依赖已移植的运行时，只需用 OHOS NDK 重新编译 C/C++ 扩展和外部依赖。主要工作量在于为 OHOS NDK 交叉编译 Boost、Eigen 及大量可选外部库（InChI/CoordGen/maeparser/FreeSASA/Avalon/YAeHMOP/ChemDraw/pubchem_shape），并验证多线程/文件路径行为。",
        "blockers": [
            {"id": "bk:mmap", "issue": "SynthonSpaceSearch 的 MemoryMappedFileReader 在 Windows 外走 POSIX mmap 路径，需确认 OHOS 的 mmap/MAP_SHARED 支持", "severity": "minor", "adaptability": "partial", "category": "posix_subset_gap", "source_dimension": "native_api", "harmony_status": "partial", "remediation": "在 OHOS NDK 下走 #else 分支；若 mmap 受限可改用 std::ifstream 顺序读取", "evidence": ["Code/GraphMol/SynthonSpaceSearch/MemoryMappedFileReader.cpp:23"]},
            {"id": "bk:deps", "issue": "大量可选外部 C/C++ 依赖（Boost、Eigen、InChI、CoordGen/maeparser、FreeSASA、Avalon、YAeHMOP、ChemDraw/EXPAT、pubchem_shape）需经 OHOS NDK 交叉编译或禁用", "severity": "major", "adaptability": "adaptable", "category": "native_dependency", "source_dimension": "dependencies", "harmony_status": "partial", "remediation": "优先使用社区已鸿蒙化的 Boost/Eigen/Cairo/FreeType；其余库逐项用 OHOS NDK 交叉编译，禁用暂不可移植的模块（如 ChemDraw）", "evidence": ["CMakeLists.txt:52-65", "External/CoordGen/CMakeLists.txt", "External/AvalonTools/CMakeLists.txt"]},
            {"id": "bk:popcnt", "issue": "x86 POPCNT 内建函数在 OHOS arm64 上不可用，但已有查表回退路径", "severity": "minor", "adaptability": "adaptable", "category": "arch_simd", "source_dimension": "native_api", "harmony_status": "replace_with_ohos", "remediation": "在 arm64 构建中关闭 RDK_OPTIMIZE_POPCNT 或改用 __builtin_popcountll；byte_popcounts 表已提供通用回退", "evidence": ["Code/DataStructs/BitOps.cpp:900", "CMakeLists.txt:54"]}
        ],
        "unadaptable_apis": [],
        "target_assumptions": [
            {"id": "ta:ndk", "capability": "OHOS NDK C++20 / musl POSIX 子集（arm64/x86_64）", "required": True, "target_status": "available", "impact": "C++ 核心与原生扩展经 OHOS NDK 重编的基础", "source": "references/harmony-pc-capabilities.json intro / arch.arm64"}
        ],
        "required_permissions": [],
        "compatible": [
            {"aspect": "核心 cheminformatics 算法（图操作、SMILES/SMARTS 解析、描述符/指纹、子结构搜索）", "note": "纯 C++20/STL，跨平台，无需改动", "evidence": ["Code/GraphMol/ROMol.h", "Code/GraphMol/SmilesParse/SmilesWrite.cpp"]},
            {"aspect": "Python/Java/C# 绑定层", "note": "跑在已移植的 Python/JDK 上，只需重新编译原生扩展", "evidence": ["CMakeLists.txt:24-44", "Code/JavaWrappers/CMakeLists.txt:1"]},
            {"aspect": "2D 绘制 SVG/JS 后端", "note": "不依赖 Qt/Cairo，可直接在鸿蒙使用", "evidence": ["Code/GraphMol/MolDraw2D/MolDraw2DSVG.h", "Code/GraphMol/MolDraw2D/MolDraw2DJS.h"]}
        ],
        "key_tasks": [
            "用 OHOS NDK 交叉编译 RDKit C++ 核心（arm64 优先），关闭 RDK_OPTIMIZE_POPCNT 或验证 arm64 内建 popcount",
            "交叉编译或引入社区已鸿蒙化的 Boost、Eigen、Cairo、FreeType；处理剩余可选依赖（InChI/CoordGen/maeparser/FreeSASA/Avalon/YAeHMOP/ChemDraw/pubchem_shape）或禁用不可移植模块",
            "重新生成 Python（Boost.Python）、Java/C#（SWIG）绑定并在已移植运行时下跑通测试",
            "验证 MemoryMappedFileReader 在 OHOS 的 mmap 行为，必要时改为普通文件流",
            "验证多线程（std::thread/atomic/mutex）在 OHOS 下的行为"
        ],
        "notes": "默认按模型 A（库跑在已移植运行时上）评估；未启用可选 Qt/Cairo 时工作量可控。历史 DepictorDLL（WIN32_DLLBUILD）为 Windows 专属遗留功能，鸿蒙下不可用，但默认不编译。"
    },
    "meta": {
        "schema_version": "1.0",
        "analyzer": "pc-lib-analyzer (single-session, no subagents)",
        "counter_tool": "cloc",
        "confidence_overall": "high",
        "warnings": [],
        "observations": [
            {"dimension": "function_summary", "field": "bindings", "kind": "new_value", "value": "nodejs", "rationale": "RDKit 通过 Emscripten 生成 MinimalLib JS/WASM 包装，可运行在 Node.js 或浏览器，故在 bindings 中加入 nodejs。"},
            {"dimension": "capability_profile", "field": "scenarios.key", "kind": "new_value", "value": "rendering_2d", "rationale": "RDKit 的 MolDraw2D 是典型的 2D 分子绘制场景，既非 GUI 也不属于 3D 渲染，建议 capability_profile 增加 rendering_2d 键。"},
            {"dimension": "dependencies", "field": "ecosystem", "kind": "ambiguity", "value": "SWIG as other", "rationale": "SWIG 是 C++ 代码生成工具，不是目标语言库；按 skill 要求 ecosystem 不能填 tool，故记为 other + scope:build。"}
        ]
    }
}

with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"Wrote {report_path}")
