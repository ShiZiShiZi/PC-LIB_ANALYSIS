#!/usr/bin/env python3
"""按「模版.txt」列结构 + 「开源仓库clone地址.csv」顺序，把 runs/software42 的分析结果
汇总成一张业务向「鸿蒙移植评估汇总表」xlsx。

机械字段（代码量 / 工作量）运行时从每库最新 report.json 读取；解释字段（大类别 / 品类 /
一句话描述 / 技术栈 / 软件类型 / 分析说明 / 三个决策列）为模型逐库总结后内嵌于 ROWS。
工作量换算（用户选定）：原始工作量(人月) = dim-9 person_days 区间中值 ÷ 22；
预估工作量(人月) = 原始 × 0.4（AI 折扣）。缺失分析结果的 3 个软件保留行、标「未分析」。

Usage:  python3 scripts/export_software42_template.py [--out <path.xlsx>]
"""
from __future__ import annotations

import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RUNS = "runs/software42"
NA = "未分析"
WORKDAYS_PER_MONTH = 22.0
AI_DISCOUNT = 0.4

# 代码量驱动的工作量估算速率（用户给定，行/天）
RATE_XCOMPILE_CPP = 3000    # 交叉编译 C/C++
RATE_ADAPT_CPP = 500        # 适配 C/C++
RATE_ADAPT_OTHER = 1100     # 适配 Java/JS/Python/Rust 等

LANG_CLOC = {   # 主语言类别 -> 对应 cloc 语言名集合（求生产代码行用）
    "cpp": {"C", "C++", "C/C++ Header", "Objective-C", "Objective-C++", "CUDA"},
    "java": {"Java"},
    "python": {"Python"},
    "js": {"JavaScript", "TypeScript", "Vuejs Component", "JSX", "TSX"},
    "rust": {"Rust"},
    "go": {"Go"},
    "csharp": {"C#"},
    "shell": {"Bourne Shell", "Bourne Again Shell", "Shell", "POSIX"},
}

# runs 目录名 -> 主语言类别（Goby 仅文档无生产代码，故不列入 -> 三列留空）
LANG_CATEGORY = {
    "brasero": "cpp", "keepass": "cpp", "KeePass2.x": "csharp", "keepassxc": "cpp",
    "zotero": "js", "VeraCrypt": "cpp", "diffuse": "python", "GrADS": "cpp", "Ditto": "cpp",
    "pulseview": "cpp", "libsigrok": "cpp", "Arduino": "java", "MilkyTracker": "cpp",
    "Cura": "python", "processing": "java", "moby": "go", "notebook": "js", "gambas": "cpp",
    "deluge": "python", "sonarqube": "java", "geany": "cpp", "shadowsocks-rust": "rust",
    "BlueJ-Greenfoot": "java", "pip": "python", "kazam": "python", "maven": "java",
    "redis": "cpp", "FreeCAD": "cpp", "ComfyUI": "python", "FFmpeg": "cpp", "mpc-hc": "cpp",
    "mplayer": "cpp", "mysql-workbench": "cpp", "sqlitestudio": "cpp", "server": "cpp",
    "robomongo": "cpp", "hive": "java", "jpegview": "cpp", "seafile": "cpp", "klavaro": "cpp",
    "nvm": "shell", "QGIS": "cpp", "YesPlayMusic": "js", "rhythmbox": "cpp",
}

HEADER = [
    "大类别", "品类", "应用名称", "原始工作量(人月)",
    "交叉编译C/C++(人月)", "适配C/C++(人月)", "适配其他语言(人月)",
    "源码仓地址", "一句话功能描述",
    "代码量", "主要技术栈", "软件类型", "分析说明", "依赖框架阻塞", "重写UI/新增功能",
    "AI为主转换", "预估工作量(人月)",
]

# 每行：(应用名称, 源码仓地址, runs目录名或None, 大类别, 品类, 一句话功能描述,
#        主要技术栈, 软件类型, 分析说明, 依赖框架阻塞, 重写UI/新增功能, AI为主转换)
# 顺序严格对齐 开源仓库clone地址.csv 的序号 1→42。
ROWS = [
    ("BRASERO", "https://gitlab.gnome.org/GNOME/brasero.git", "brasero",
     "多媒体/桌面工具", "光盘刻录",
     "面向 GNOME 桌面的 CD/DVD/蓝光光盘刻录应用，支持数据盘、音频 CD、视频 DVD 的制作、复制与擦除。",
     "C + GTK3", "GUI 应用",
     "C/GTK3 桌面应用；核心刻录经 SCSI SG_IO 直控光驱、GUI 依赖 X11，鸿蒙内核/桌面栈无等价接口，建议放弃或重构，可行性低。",
     "是", "是", "否"),

    ("KeePass2", "svn checkout https://svn.code.sf.net/p/keepass/code/ keepass", "keepass",
     "安全工具", "密码管理器(插件)",
     "KeePass 密码管理器的导入插件——本 SourceForge 仓库仅托管 KeePass 插件（分析样本为 OublietteImport），将旧版 Oubliette 加密库数据迁移进 KeePass。",
     "C++ + MFC/ATL/Win32", "GUI 插件(Windows DLL)",
     "注意：该 SF SVN 仓库仅含 KeePass 插件、非 KeePass 2.x 主程序。插件深绑 Windows——MFC/ATL GUI、Win32 注册表、MSVC 专有扩展，且须由尚未移植鸿蒙的 KeePass 宿主加载，鸿蒙无等价，判定不可行。",
     "是", "是", "否"),

    ("KeePass 2.x", "https://github.com/dlech/KeePass2.x.git", "KeePass2.x",
     "安全工具", "密码管理器",
     "KeePass 2.x 主程序——开源桌面密码管理器，基于 .NET/WinForms，提供 KDBX 加密数据库、密码生成、自动键入(Auto-Type)、多实例 IPC、插件体系与 70+ 格式导入导出；Windows 原生 .NET，Linux/macOS 走 Mono。",
     "C# + .NET/WinForms（P/Invoke Win32）", "GUI 应用（.NET）",
     "此为 KeePass 2.x 真正主程序（区别于上一行的 SF SVN 插件样本）。依赖 .NET 运行时与 WinForms/Win32，鸿蒙无等价运行时/GUI 栈，且大量 P/Invoke Windows API 与 Mono 专有路径，需整体重写，判定不可行。",
     "是", "是", "否"),

    ("Zotero", "https://github.com/zotero/zotero.git", "zotero",
     "办公/学术工具", "文献管理",
     "基于 Mozilla 平台的桌面文献管理应用，收集、管理、引用与同步参考文献，支持网页/PDF 元数据抓取与 Word/LibreOffice 集成。",
     "JavaScript + Mozilla(XUL/XPCOM)", "GUI 应用",
     "运行于 Mozilla XULRunner/Firefox 框架，业务逻辑遍布 XPCOM API，鸿蒙无等价平台，需整体重写，判定不可行。",
     "是", "是", "否"),

    ("VeraCrypt", "https://github.com/veracrypt/VeraCrypt.git", "VeraCrypt",
     "安全工具", "磁盘加密",
     "开源跨平台磁盘加密软件，支持加密文件容器、整盘/分区加密及 Windows 系统盘启动前认证。",
     "C/C++ + wxWidgets（含内核驱动/FUSE）", "GUI 应用（含内核驱动）",
     "加密卷核心依赖 Windows 内核驱动与 Linux FUSE 设备栈，鸿蒙自研内核无法复现，仅能重写为文件级容器且功能大幅缩水，判定不可行。",
     "是", "是", "否"),

    ("Diffuse", "https://github.com/MightyCreak/diffuse.git", "diffuse",
     "开发工具", "文本对比/合并",
     "基于 GTK3 的 Python 图形化文本文件对比与合并工具，支持 n-way 合并及 Git/SVN/hg 等版本库历史对比。",
     "Python + GTK3", "GUI 应用",
     "Python/GTK3 应用，逻辑可移植；需在鸿蒙编译 PyGObject C 扩展并提供 GTK 后端，工作量中等，可行。",
     "否", "否", "是"),

    ("GrADS", "https://github.com/j-m-adams/GrADS.git", "GrADS",
     "科学计算", "气象数据可视化",
     "面向大气海洋地球科学的交互式网格数据可视化与分析工具，支持代数运算、统计分析与地图图形输出。",
     "C + X11", "GUI 应用（交互/批处理）",
     "C 桌面/批处理应用，已有 X11 显示层函数指针抽象；将显示后端替换为鸿蒙接口即可，可行。",
     "否", "否", "是"),

    ("Ditto", "https://github.com/sabrogden/Ditto.git", "Ditto",
     "系统工具", "剪贴板管理",
     "Windows 平台剪贴板管理应用，后台捕获复制历史存入 SQLite，支持全局热键粘贴、局域网同步与加密。",
     "C++ + MFC/Win32", "GUI 应用",
     "GUI 全基于 MFC/Win32、剪贴板依赖 Win32 Clipboard 与 OLE/COM，均无鸿蒙等价实现，需 ArkUI 完全重写，判定不可行。",
     "是", "是", "否"),

    ("PulseView", "https://github.com/sigrokproject/pulseview.git", "pulseview",
     "电子/工程工具", "逻辑分析仪/示波器 GUI",
     "sigrok 套件的 Qt 图形前端，用于连接、配置并可视化逻辑分析仪、示波器等 USB/网络测量硬件，支持协议解码。",
     "C++ + Qt5/6 + libsigrok", "GUI 应用",
     "Qt 前端可重编，但底层 libsigrok 设备驱动栈能否在鸿蒙运行未知、且依赖传统桌面窗口环境，硬件驱动为主要阻碍，可行性低。",
     "是", "否", "是"),

    ("Goby", "https://github.com/gobysec/Goby.git", "Goby",
     "安全工具", "网络资产测绘/漏洞扫描",
     "网络资产测绘与安全扫描工具（社区版）；本仓库仅为项目首页与文档。",
     "Go + Electron/Vue（本仓库为文档）", "桌面应用（本仓库仅文档）",
     "本仓库仅含 README/文档、无程序源码；实际产品为闭源商业工具（Go 后端 + Electron/Vue 前端），无法据此评估移植。",
     "否", "否", "否"),

    ("Arduino", "https://github.com/arduino/Arduino.git", "Arduino",
     "开发工具", "嵌入式 IDE",
     "面向 Arduino 微控制器的图形化 IDE，集成交叉编译工具链、固件上传、串口监视器与板卡/库管理（1.x 旧版）。",
     "Java + Swing/AWT", "GUI 应用",
     "Java IDE，GUI 基于 Swing/AWT 需 ArkUI 化，另有串口/USB 及 JNI 原生库依赖；建议改用 2.x 或重写客户端，可行性偏低。",
     "否", "是", "是"),

    ("MilkyTracker", "https://github.com/milkytracker/MilkyTracker.git", "MilkyTracker",
     "多媒体", "音乐编曲(Tracker)",
     "跨平台桌面音乐追踪器，用于创建与编辑 .MOD/.XM 模块音乐，复现 FastTracker II 的界面与回放体验。",
     "C++ + SDL2/OpenGL", "GUI 应用",
     "C++ 桌面应用，SDL2/OpenGL 渲染与多套音频/MIDI 后端需在鸿蒙上替换或适配，重编为主，可行性偏低。",
     "否", "否", "是"),

    ("CURA", "https://github.com/Ultimaker/Cura.git", "Cura",
     "图形/3D", "3D 打印切片",
     "UltiMaker 开源桌面 3D 打印切片软件，将 STL/3MF/OBJ 模型转为 G-code，含 OpenGL 3D 预览与插件系统。",
     "Python + PyQt6/QML（+ C++ CuraEngine）", "GUI 应用",
     "PyQt6/QML 前端可用，但 CuraEngine C++ 引擎及多个 Python C 扩展需经 OHOS NDK 交叉编译，工作量较大，可行。",
     "否", "否", "是"),

    ("PROCESSING", "https://github.com/processing/processing.git", "processing",
     "开发工具", "创意编程 IDE",
     "面向视觉艺术的创意编程 IDE（PDE）与运行时库，支持 2D/3D 图形、动画与硬件交互，跨平台导出。",
     "Java + Swing/AWT + OpenGL(JOGL)", "GUI 应用（IDE+库）",
     "PDE 界面完全基于 Swing/AWT（鸿蒙无等价，须 ArkUI 重写），P2D/P3D 渲染依赖 JOGL/OpenGL，可行性偏低。",
     "是", "是", "是"),

    ("Docker", "https://github.com/moby/moby.git", "moby",
     "系统/容器", "容器引擎",
     "Docker Engine 上游源码 Moby，提供容器生命周期管理、镜像构建存储、网络与 Swarm 集群编排。",
     "Go", "服务/后端（守护进程）",
     "核心依赖 Linux 命名空间/cgroup/OverlayFS/iptables 等内核能力，鸿蒙自研内核无对应实现，判定不可行。",
     "是", "否", "否"),

    ("JUPYTER", "https://github.com/jupyter/notebook.git", "notebook",
     "开发/科学工具", "交互式计算笔记本",
     "基于 Web 的交互式计算笔记本，浏览器内编写运行含代码、文本、公式与可视化的 .ipynb 笔记本。",
     "Python + TypeScript（Web）", "Web 应用",
     "Web 架构，前端 TS + 后端 Python Tornado，跑在鸿蒙已移植运行时上即可，几乎无需适配，可行。",
     "否", "否", "是"),

    ("Gambas", "https://gitlab.com/gambas/gambas.git", "gambas",
     "开发工具", "BASIC 开发平台",
     "类 Visual Basic 的开源图形化 BASIC 语言与完整开发平台，含解释器/编译器、IDE 及庞大组件生态。",
     "C/C++ + Qt/GTK", "GUI 应用（开发平台）",
     "BASIC 开发平台，运行时大量 fork/exec/信号管道且组件依赖 X11/D-Bus，鸿蒙缺相应机制，可行性偏低。",
     "是", "否", "是"),

    ("Deluge", "https://github.com/deluge-torrent/deluge.git", "deluge",
     "网络工具", "BitTorrent 客户端",
     "daemon/client 分离架构的 BitTorrent 客户端，前端提供 GTK 桌面、Web 与命令行三种交互方式，可远程管理。",
     "Python + GTK3（+ C++ libtorrent）", "GUI 应用（C/S 架构）",
     "Python + GTK3 前端 + C++ libtorrent 引擎，libtorrent 需 NDK 重编、GTK 绑定需移植，工作量中等，可行。",
     "否", "否", "是"),

    ("Sonarqube", "https://github.com/SonarSource/sonarqube.git", "sonarqube",
     "开发工具", "代码质量平台",
     "开源代码质量与安全持续检测平台，静态分析发现 bug/漏洞/代码异味并提供质量门禁，支持 30+ 语言。",
     "Java + TypeScript（Web）", "服务/后端（Web 平台）",
     "Java 平台，跑在鸿蒙已移植 JDK 上；需为捆绑的 Elasticsearch/JRE 及多进程启动脚本增加鸿蒙支持，可行。",
     "否", "否", "是"),

    ("Geany", "https://github.com/geany/geany.git", "geany",
     "开发工具", "轻量 IDE",
     "基于 GTK3 的跨平台轻量级 IDE，支持 50+ 语言的语法高亮、代码补全、嵌入式终端与插件系统。",
     "C + GTK3", "GUI 应用",
     "C + GTK3 轻量 IDE，GTK3 在鸿蒙可用；主要为构建系统适配 OHOS NDK 与新增平台后端，可行。",
     "否", "否", "是"),

    ("shadowsocks", "https://github.com/shadowsocks/shadowsocks-rust.git", "shadowsocks-rust",
     "网络工具", "加密代理",
     "shadowsocks 代理协议的 Rust 实现，提供 SOCKS5/HTTP/TUN/透明代理等多种模式与多种加密算法。",
     "Rust", "命令行工具",
     "Rust 命令行代理，交叉编译到鸿蒙即可；仅少量 Linux/Windows 特有 socket 选项需条件编译，可行。",
     "否", "否", "是"),

    ("BlueJ", "https://github.com/k-pet-group/BlueJ-Greenfoot.git", "BlueJ-Greenfoot",
     "开发工具", "Java 教学 IDE",
     "面向初学者的 Java/Stride 教学 IDE（BlueJ + Greenfoot），提供编辑、编译、调试、类图与图形化教学框架。",
     "Java + JavaFX", "GUI 应用",
     "Java IDE，跑在已移植 JDK 上；GUI 基于 JavaFX（鸿蒙支持状态待核实、为决定性因素），另需 JDK21，可行（需核实）。",
     "否", "否", "是"),

    ("PIP", "https://github.com/pypa/pip.git", "pip",
     "开发工具", "Python 包管理",
     "Python 官方推荐的包安装器 CLI，从 PyPI 等索引下载、安装、升级、卸载包，支持依赖解析与虚拟环境。",
     "Python", "命令行工具",
     "纯 Python CLI，跑在鸿蒙已移植 Python 上即可，无需适配，可行。",
     "否", "否", "是"),

    ("KAZAM录屏", "https://github.com/hzbd/kazam.git", "kazam",
     "多媒体", "屏幕录制",
     "面向 Linux 桌面的 GTK 屏幕录制与截图工具，通过 GStreamer 管线编码输出，可选 PulseAudio 录音。",
     "Python + GTK3 + GStreamer", "GUI 应用",
     "GTK 录屏工具，屏幕采集依赖 X11、音频依赖 PulseAudio，需为鸿蒙重写采集后端，可行性偏低。",
     "是", "否", "是"),

    ("Maven", "https://github.com/apache/maven.git", "maven",
     "开发工具", "构建/依赖管理",
     "Apache Maven，基于 POM 的 Java 项目构建管理 CLI，自动管理依赖解析与编译/测试/打包/部署生命周期。",
     "Java", "命令行工具",
     "Java 构建 CLI，跑在已移植 JDK 上即可，仅需适配终端库与分发脚本，可行。",
     "否", "否", "是"),

    ("Redis", "https://github.com/redis/redis.git", "redis",
     "数据库", "内存键值存储",
     "开源内存键值数据存储服务器，提供丰富数据结构与原子操作，支持持久化、复制、集群与 Lua 脚本。",
     "C", "服务/后端",
     "C 服务端，主要依赖 fork() 做持久化及 Linux epoll/proc 等特有 API，需条件适配，工作量中等，可行。",
     "否", "否", "是"),

    ("Freecad", "https://github.com/FreeCAD/FreeCAD.git", "FreeCAD",
     "图形/3D", "参数化 CAD",
     "开源参数化 3D CAD 建模器，基于 OpenCASCADE 内核，含 30+ 工作台并通过 Python 暴露完整 API。",
     "C++ + Qt（+ Python）", "GUI 应用",
     "C++/Qt CAD，Qt 在鸿蒙可用；OpenCASCADE 内核与 Qt 需经 NDK 交叉编译、OpenGL 覆盖度待验证，可行。",
     "否", "否", "是"),

    ("ComfyUI", "https://github.com/comfyanonymous/ComfyUI.git", "ComfyUI",
     "AI 工具", "AIGC 节点式界面",
     "基于节点的模块化 AI 内容生成引擎，将 Stable Diffusion 等扩散模型推理管线拆为可编排节点，提供 Web 界面。",
     "Python（+ Web 前端）", "Web 应用（AI 引擎）",
     "Python AI 引擎，跑在已移植运行时上；CUDA 加速与部分 C 扩展依赖需适配（GPU 后端为可选），可行。",
     "否", "否", "是"),

    ("FFMPEG", "https://github.com/FFmpeg/FFmpeg.git", "FFmpeg",
     "多媒体", "音视频处理库",
     "全球最广泛使用的跨平台音视频处理库与工具集，提供编解码、封装、滤镜、转换与设备采集完整管线。",
     "C", "库 / 命令行工具",
     "跨平台 C 多媒体库，交叉编译到鸿蒙即可；各家 GPU 硬件加速无鸿蒙等价（可选、可退化为软解），可行。",
     "否", "否", "是"),

    ("MPC-HC播放器", "https://github.com/clsid2/mpc-hc.git", "mpc-hc",
     "多媒体", "媒体播放器",
     "面向 Windows 的开源音视频播放器，基于 DirectShow，内建 LAV Filters 解码器与 MFC 图形界面。",
     "C++ + MFC/Win32 + DirectShow", "GUI 应用",
     "架构基于 DirectShow + MFC/Win32 + Direct3D，均为 Windows 专有且鸿蒙无等价，判定不可行。",
     "是", "是", "否"),

    ("MPlayer", "svn checkout svn://svn.mplayerhq.hu/mplayer/trunk mplayer", "mplayer",
     "多媒体", "媒体播放器",
     "经典开源跨平台命令行媒体播放器，内置大量原生解码器并集成 FFmpeg(libavcodec)，支持几乎所有主流音视频格式，附带 MEncoder 编码器与多种视频/音频输出后端。",
     "C（内嵌 FFmpeg + x86 SIMD 汇编）", "命令行/桌面应用（播放器）",
     "C 媒体播放器，FFmpeg 引擎可经 OHOS NDK 重编；但视频输出层(libvo 30+驱动)/音频输出层(libao2 20+驱动)紧耦合 X11/ALSA 等需重写鸿蒙后端，x86 SIMD 汇编需转 ARM64 NEON，多项目标平台能力未核实，工作量大，可行（需努力）。",
     "否", "否", "是"),

    ("MySQL Workbench", "https://github.com/mysql/mysql-workbench.git", "mysql-workbench",
     "数据库", "数据库管理工具",
     "Oracle 官方 MySQL 图形化管理工具，整合 SQL 查询、数据库建模、实例运维监控与数据迁移。",
     "C++ + GTK（+ .NET/Cocoa 前端）", "GUI 应用",
     "C++/GTK 前端可重编，但 Windows .NET/macOS Cocoa 前端与大量原生 C++ 依赖需适配、桌面窗口支持待核实，可行性偏低。",
     "是", "否", "是"),

    ("SQLiteStudio", "https://github.com/pawelsalawa/sqlitestudio.git", "sqlitestudio",
     "数据库", "SQLite 管理工具",
     "跨平台桌面 SQLite 管理 GUI，提供 SQL 编辑器、数据网格、对象浏览、导入导出与脚本扩展。",
     "C++ + Qt6", "GUI 应用",
     "C++/Qt6 应用，Qt6 可交叉编译到鸿蒙；主要核实 MDI 多文档窗口支持与崩溃处理适配，可行。",
     "否", "否", "是"),

    ("MariaDB", "https://github.com/MariaDB/server.git", "server",
     "数据库", "关系型数据库",
     "MySQL 开源分支，支持标准 SQL、ACID 事务、多存储引擎、复制与 Galera 集群及 JSON/地理空间等高级类型。",
     "C/C++", "服务/后端",
     "C/C++ 数据库服务端，需整体经 OHOS NDK 重编并适配 musl/glibc 差异与 Win32 专有代码，可行。",
     "否", "否", "是"),

    ("Robo 3T", "https://github.com/Studio3T/robomongo.git", "robomongo",
     "数据库", "MongoDB 管理工具",
     "以 mongo shell 为中心的跨平台 MongoDB 桌面管理工具，GUI 与 shell 无缝切换，支持 SSH 隧道与副本集管理。",
     "C++ + Qt5", "GUI 应用",
     "C++/Qt5 MongoDB 工具，Qt 可重编；内嵌 mongo shell fork、Chromium 组件与 SSH 隧道需适配，可行。",
     "否", "否", "是"),

    ("HIVE", "https://github.com/apache/hive.git", "hive",
     "数据库/大数据", "数据仓库",
     "构建在 Hadoop 之上的分布式数据仓库，将结构化数据映射为表并以类 SQL（HiveQL）编译为分布式计算作业。",
     "Java", "服务/后端",
     "Java 大数据数仓，跑在已移植 JDK 上；主要替换 sun.misc.Unsafe/Signal 反射及 epoll 原生传输，可行。",
     "否", "否", "是"),

    ("JPEGVIEW看图", "https://github.com/sylikc/jpegview.git", "jpegview",
     "多媒体", "图片查看器",
     "轻量快速的 Windows 图片查看器与基础编辑器，基于 WTL/ATL 与 GDI+，内建 30+ 图片格式支持。",
     "C++ + WTL/ATL + GDI+", "GUI 应用",
     "GUI 基于 WTL/ATL、渲染依赖 GDI+ 且深用 Win32 API，均为 Windows 专有无鸿蒙等价，需 ArkUI 重写，判定不可行。",
     "是", "是", "否"),

    ("SEAFILE", "https://github.com/haiwen/seafile.git", "seafile",
     "网络/存储", "文件同步与云存储",
     "Seafile 同步客户端后台守护进程，负责文件仓库本地同步、版本控制、客户端加密与差分传输。",
     "C + GLib", "库 / 后端守护进程",
     "C 同步引擎，需为鸿蒙新增文件系统监控后端并移植 libsearpc RPC，其余重编即可，可行。",
     "否", "否", "是"),

    ("Klavaro", "svn checkout svn://svn.code.sf.net/p/klavaro/code/ klavaro", "klavaro",
     "教育工具", "打字训练",
     "面向终端用户的盲打训练应用，GTK+3 界面提供基础/适应性/速度/流畅度四个递进训练模块，含虚拟键盘指法提示、进度图表与在线排行榜，支持 40+ 语言与多种国际键盘布局。",
     "C + GTK3", "GUI 应用",
     "C/GTK3 打字训练应用，GTK3 在鸿蒙 PC 可用；主要为 OHOS NDK 重编、桌面集成与打包适配，在线排行榜(curl)需 INTERNET 权限，工作量小，可行。",
     "否", "否", "是"),

    ("NVM", "https://github.com/nvm-sh/nvm.git", "nvm",
     "开发工具", "Node.js 版本管理",
     "POSIX 兼容的 Node.js 版本管理 CLI（shell 函数实现），快速安装、切换与管理多个 Node.js 版本。",
     "Shell 脚本", "命令行工具",
     "POSIX shell 脚本，仅需为 nvm_get_os 增加鸿蒙识别及二进制下载 URL 适配，工作量极小，可行。",
     "否", "否", "是"),

    ("QGIS", "https://github.com/qgis/QGIS.git", "QGIS",
     "图形/地理", "地理信息系统(GIS)",
     "功能完备的开源桌面地理信息系统，支持矢量/栅格/点云数据管理、2D/3D 制图渲染及全功能 Python API。",
     "C++ + Qt6（+ Python）", "GUI 应用",
     "C++/Qt6 GIS，Qt6 与 GDAL 等可交叉编译到鸿蒙；核实桌面多窗口/OpenGL 覆盖后重编即可，可行。",
     "否", "否", "是"),

    ("YesPlayMusic", "https://github.com/qier222/YesPlayMusic.git", "YesPlayMusic",
     "多媒体", "音乐播放器",
     "基于 Electron + Vue.js 的第三方网易云音乐桌面播放器，支持账号登录、MV/歌词、私人 FM 与桌面集成。",
     "Electron + Vue.js", "GUI 应用（Electron）",
     "Electron + Vue 播放器，Electron/Chromium 在鸿蒙可用性待核实（可退化为 Web/ArkWeb），另需适配桌面集成与 Rust N-API，可行性偏低。",
     "是", "否", "是"),

    ("RHYTHMBOX音频播放器", "https://gitlab.gnome.org/GNOME/rhythmbox.git", "rhythmbox",
     "多媒体", "音乐播放器",
     "GNOME 桌面的音乐管理与播放器，支持本地库、播放列表、网络电台、播客、CD 抓取及便携设备同步。",
     "C + GTK3 + GStreamer", "GUI 应用",
     "C/GTK3 + GStreamer 音乐播放器，核心可重编；FM 广播(V4L2)/iPod 等硬件插件鸿蒙无对应（可裁剪），另需替换 GNOME 桌面集成，可行。",
     "否", "否", "是"),

    ("KeePassXC", "https://github.com/keepassxreboot/keepassxc.git", "keepassxc",
     "安全工具", "密码管理器",
     "KeePassXC——跨平台桌面密码管理应用，创建管理 KDBX 加密离线数据库，提供自动键入、浏览器集成、TOTP、SSH Agent、Secret Service、YubiKey 挑战-响应与命令行工具 keepassxc-cli。",
     "C++ + Qt6", "GUI 应用",
     "C++/Qt6 桌面应用，Qt6 可交叉编译到鸿蒙；需创建 OHOS 平台后端替换 X11/AppKit/Win32 OSUtils，以 @ohos 能力替代 freedesktop Secret Service/自动键入，YubiKey 等硬件与浏览器集成需适配，部分可适配、工作量较大，可行。",
     "否", "否", "是"),

    ("libsigrok", "https://github.com/sigrokproject/libsigrok.git", "libsigrok",
     "电子/工程工具", "硬件信号采集库",
     "sigrok 套件核心 C 共享库，统一抽象 USB/串口/HID/蓝牙/GPIB/TCP-SCPI 等接口，与逻辑分析仪、示波器、万用表等 90 余种测量设备通信并做二十余种数据输入输出格式转换（PulseView 的后端）。",
     "C（glib + libusb/libserialport）", "库",
     "sigrok 后端 C 库，交叉编译到鸿蒙即可；需为 libusb/串口等提供鸿蒙设备访问后端并核实 USB 设备访问权限，其余重编，全部可适配，工作量小，可行。",
     "否", "否", "是"),
]


def _latest_report(dir_name):
    lib_dir = os.path.join(RUNS, dir_name)
    try:
        runs = sorted(
            d for d in os.listdir(lib_dir)
            if os.path.isfile(os.path.join(lib_dir, d, "report.json"))
        )
    except OSError:
        return None
    if not runs:
        return None
    try:
        with open(os.path.join(lib_dir, runs[-1], "report.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _person_days_mid(rep):
    pd = (((rep or {}).get("harmony_adaptation") or {}).get("effort") or {}).get("person_days")
    if isinstance(pd, list) and len(pd) == 2:
        try:
            return (float(pd[0]) + float(pd[1])) / 2.0
        except (TypeError, ValueError):
            return None
    return None


def _code_total(rep):
    return (((rep or {}).get("code_metrics") or {}).get("total") or {}).get("code")


def _main_lang_prod_code(rep, names):
    """主语言（指定 cloc 语言名集合）的生产代码行数之和。"""
    bd = ((rep or {}).get("languages") or {}).get("breakdown") or []
    return sum((x.get("production") or {}).get("code", 0)
               for x in bd if x.get("language") in names)


def _pm(lines, rate):
    """行数 -> 人月（行/天 ÷ 每月工作日），保留 1 位小数。"""
    return round(lines / rate / WORKDAYS_PER_MONTH, 1)


def build_rows():
    out = []
    for (name, url, dir_name, big, cat, desc, stack, sw_type, note,
         block, rewrite, ai) in ROWS:
        code = orig = est = ""
        xc = adapt_c = adapt_o = ""   # 代码量驱动的三列工作量
        if dir_name is not None:
            rep = _latest_report(dir_name)
            if rep is None:
                raise SystemExit(f"缺少报告: runs/software42/{dir_name}")
            code = _code_total(rep)
            mid = _person_days_mid(rep)
            if mid is not None:
                orig = round(mid / WORKDAYS_PER_MONTH, 1)
                est = round(orig * AI_DISCOUNT, 1)
            lang_cat = LANG_CATEGORY.get(dir_name)
            if lang_cat is not None:
                lines = _main_lang_prod_code(rep, LANG_CLOC[lang_cat])
                if lines > 0:
                    if lang_cat == "cpp":
                        xc = _pm(lines, RATE_XCOMPILE_CPP)
                        adapt_c = _pm(lines, RATE_ADAPT_CPP)
                    else:
                        adapt_o = _pm(lines, RATE_ADAPT_OTHER)
        out.append([
            big, cat, name, orig, xc, adapt_c, adapt_o, url, desc, code,
            stack, sw_type, note, block, rewrite, ai, est,
        ])
    return out


HEAD_FILL = PatternFill("solid", fgColor="DDE6F0")
HEAD_FONT = Font(bold=True)
WRAP_COLS = {"一句话功能描述", "分析说明", "源码仓地址"}


def write_xlsx(rows, out_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "鸿蒙移植评估汇总"
    ws.append(HEADER)
    for c in ws[1]:
        c.font = HEAD_FONT
        c.fill = HEAD_FILL
        c.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
    for row in rows:
        ws.append(row)
    ws.freeze_panes = "A2"
    last_col = get_column_letter(len(HEADER))
    ws.auto_filter.ref = f"A1:{last_col}{ws.max_row}"
    for idx, title in enumerate(HEADER, start=1):
        letter = get_column_letter(idx)
        if title in WRAP_COLS:
            ws.column_dimensions[letter].width = 52
            for cells in ws.iter_rows(min_row=2, min_col=idx, max_col=idx):
                cells[0].alignment = Alignment(wrap_text=True, vertical="top")
        else:
            longest = len(str(title))
            for row in rows:
                v = row[idx - 1]
                if v not in (None, ""):
                    longest = max(longest, min(len(str(v)), 30))
            ws.column_dimensions[letter].width = max(8, min(longest + 2, 32))
    wb.save(out_path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="模版式鸿蒙移植评估汇总 xlsx 导出")
    ap.add_argument("--out", default="软件42_鸿蒙移植评估汇总.xlsx")
    args = ap.parse_args(argv)
    rows = build_rows()
    write_xlsx(rows, args.out)
    analyzed = sum(1 for r in ROWS if r[2] is not None)
    print(f"导出 {len(rows)} 行（{analyzed} 已分析 + {len(rows) - analyzed} 未分析）-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
