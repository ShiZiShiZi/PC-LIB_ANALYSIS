#!/usr/bin/env python3
"""Assemble the VLC analysis report from metrics + reasoned blocks."""
import json
from datetime import datetime, timezone

METRICS_PATH = "runs/software84/vlc/2026-06-27T03-33-40-240Z/metrics.json"
REPORT_PATH = "runs/software84/vlc/2026-06-27T03-33-40-240Z/report.json"

with open(METRICS_PATH) as f:
    metrics = json.load(f)

report = {
    "library": {
        "name": "vlc",
        "kind": "application",
        "package_name": "vlc",
        "aliases": ["videolan-vlc"],
        "import_names": [],
        "source_url": "https://github.com/videolan/vlc.git",
        "analyzed_at": "2026-06-27T03:33:40.240Z",
        "commit": "7c0bec80ed68d00f5c126fe1080a01bee9aa0db9",
        "one_liner": "VLC 是一款自由开源的跨平台多媒体播放器与引擎，支持播放、转码、串流绝大多数音视频格式。",
        "ecosystem": "cpp",
        "bindings": []
    },

    "function_summary": {
        "summary": "VLC media player 是 VideoLAN 项目出品的终端用户多媒体播放器，也可作为可嵌入引擎 libVLC 被第三方应用调用。核心能力覆盖本地文件、光盘、网络流与采集设备的播放，以及转码、串流输出。代码主体为 C/C++/Objective-C，采用插件化架构，模块覆盖接入、解复用、编解码、音视频输出、GUI 与流媒体输出。",
        "categories": [
            {
                "name": "多媒体播放",
                "description": "播放本地文件、光盘（DVD/Blu-ray/VCD）、网络流（HTTP/RTP/RTSP/DASH/HLS）及采集设备。",
                "evidence": ["bin/vlc.c:117", "modules/access/", "modules/demux/"]
            },
            {
                "name": "音视频编解码与解复用",
                "description": "通过插件支持大量容器格式与编解码器，核心依赖 FFmpeg 并可加载外部编解码模块。",
                "evidence": ["modules/codec/", "modules/demux/", "modules/packetizer/"]
            },
            {
                "name": "流媒体转码与输出",
                "description": "将输入流转码后输出到文件、网络或其他设备，支持 VLM、Chromecast、SDI 等专业场景。",
                "evidence": ["modules/stream_out/", "modules/mux/", "modules/access_output/"]
            },
            {
                "name": "音视频输出与渲染",
                "description": "多平台音频输出（ALSA/PulseAudio/PipeWire/WASAPI/WaveOut）与视频输出（OpenGL/Vulkan/Direct3D/X11/Wayland）。",
                "evidence": ["modules/audio_output/", "modules/video_output/"]
            },
            {
                "name": "用户界面",
                "description": "跨平台 GUI（Qt6 主界面、macOS Cocoa、skins2）、TUI（ncurses）及 Web/Lua 远程控制。",
                "evidence": ["modules/gui/qt/", "modules/gui/macosx/", "modules/gui/skins2/", "modules/gui/ncurses.c"]
            },
            {
                "name": "媒体库与元数据管理",
                "description": "维护本地媒体索引、读取标签与封面、提供搜索与播放列表管理。",
                "evidence": ["modules/meta_engine/", "modules/medialibrary/", "src/media_source/"]
            },
            {
                "name": "服务发现与网络协议",
                "description": "UPnP/DLNA、Bonjour/mDNS、SAP 等服务发现，以及 MTP、Samba 等网络访问。",
                "evidence": ["modules/services_discovery/", "modules/access/dsm/", "modules/access/dvb/"]
            }
        ],
        "domain": "multimedia",
        "target_users": "终端用户（桌面与移动平台）及需要嵌入式媒体引擎的开发者"
    },

    "languages": metrics["languages"],
    "code_metrics": metrics["code_metrics"],
    "tests": {
        "test_files": metrics["tests"]["test_files"],
        "test_cases": metrics["tests"]["test_cases"],
        "frameworks": metrics["tests"]["frameworks"],
        "by_language": metrics["tests"]["by_language"],
        "notes": "计数来自 cloc + 正则匹配；VLC 的测试以 C/C++ 单元测试与 Meson 测试为主，14 个测试用例指 googletest 识别到的用例数。"
    },

    "license": {
        "spdx": "GPL-2.0-or-later",
        "name": "GNU General Public License v2.0 or later",
        "confidence": "high",
        "is_dual_licensed": True,
        "license_files": ["COPYING", "COPYING.LIB"],
        "evidence": "COPYING 为 GPL-2.0 完整文本；COPYING.LIB 为 LGPL-2.1 文本；README.md 明确声明 VLC 主体为 GPLv2 or later，libVLC 引擎为 LGPLv2 or later；src/libvlc.c、bin/vlc.c 等源文件头也包含相应许可证声明。",
        "notes": "主体程序与多数模块为 GPL-2.0-or-later；libVLC 引擎库单独采用 LGPL-2.1-or-later，允许嵌入第三方应用而不强制 GPL。"
    },

    "dependencies": {
        "count": 0,
        "manifests": [
            "meson.build",
            "configure.ac",
            "modules/meson.build",
            "modules/gui/qt/meson.build",
            "modules/video_output/meson.build",
            "modules/audio_output/meson.build",
            "Makefile.am"
        ],
        "by_ecosystem": {"cpp": []},
        "dependencies": [
            {"name": "zlib", "ecosystem": "cpp", "registry_name": "zlib", "source_repo": "https://github.com/madler/zlib", "scope": "runtime", "version": None, "purpose": "压缩/解压缩（流、模块数据等）", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency zlib / pkg-config）", "declared_in": ["meson.build:170"], "used_symbols": ["deflate", "inflate", "zlibVersion"], "harmony_adapted": True, "harmony_adapted_source": "OpenHarmony PC C/C++ 预编译包 (cmd-pkgs)"},
            {"name": "libiconv", "ecosystem": "cpp", "registry_name": "libiconv", "source_repo": "https://www.gnu.org/software/libiconv/", "scope": "runtime", "version": None, "purpose": "字符集转换", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency iconv）", "declared_in": ["meson.build:183"], "used_symbols": ["iconv_open", "iconv", "iconv_close"], "harmony_adapted": True, "harmony_adapted_source": "OpenHarmony PC C/C++ 预编译包 (cmd-pkgs)"},
            {"name": "libidn", "ecosystem": "cpp", "registry_name": "libidn", "source_repo": "https://git.savannah.gnu.org/git/libidn.git", "scope": "runtime", "version": None, "purpose": "国际化域名处理", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libidn）", "declared_in": ["meson.build:237"], "used_symbols": [], "harmony_adapted": False},
            {"name": "libintl", "ecosystem": "cpp", "registry_name": "gettext", "source_repo": "https://git.savannah.gnu.org/git/gettext.git", "scope": "runtime", "version": None, "purpose": "gettext 国际化翻译支持", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency intl）", "declared_in": ["meson.build:221"], "used_symbols": ["bindtextdomain", "gettext"], "harmony_adapted": False},
            {"name": "libgcrypt", "ecosystem": "cpp", "registry_name": "libgcrypt", "source_repo": "https://git.gnupg.org/libgcrypt.git", "scope": "runtime", "version": ">=1.6.0", "purpose": "加密/解密（TLS、DRM、安全模块）", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libgcrypt）", "declared_in": ["meson.build:1112"], "used_symbols": [], "harmony_adapted": True, "harmony_adapted_source": "OpenHarmony PC C/C++ 预编译包 (cmd-pkgs)"},
            {"name": "gnutls", "ecosystem": "cpp", "registry_name": "gnutls", "source_repo": "https://gitlab.com/gnutls/gnutls.git", "scope": "runtime", "version": ">=3.5.0", "purpose": "TLS/SSL 网络传输安全", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency gnutls）", "declared_in": ["modules/misc/meson.build:84"], "used_symbols": [], "harmony_adapted": False},
            {"name": "libavformat", "ecosystem": "cpp", "registry_name": "ffmpeg", "source_repo": "https://git.ffmpeg.org/ffmpeg.git", "scope": "runtime", "version": ">=58.76.100", "purpose": "FFmpeg 容器格式与网络协议封装（demux/access）", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libavformat）", "declared_in": ["modules/meson.build:204"], "used_symbols": ["avformat_open_input", "av_read_frame"], "harmony_adapted": False},
            {"name": "libavcodec", "ecosystem": "cpp", "registry_name": "ffmpeg", "source_repo": "https://git.ffmpeg.org/ffmpeg.git", "scope": "runtime", "version": ">=58.134.100", "purpose": "FFmpeg 音视频编解码", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libavcodec）", "declared_in": ["modules/meson.build:205"], "used_symbols": ["avcodec_decode_subtitle2", "avcodec_send_packet", "avcodec_receive_frame"], "harmony_adapted": False},
            {"name": "libavutil", "ecosystem": "cpp", "registry_name": "ffmpeg", "source_repo": "https://git.ffmpeg.org/ffmpeg.git", "scope": "runtime", "version": ">=56.70.100", "purpose": "FFmpeg 通用工具库", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libavutil）", "declared_in": ["modules/meson.build:206"], "used_symbols": ["av_malloc", "av_frame_alloc"], "harmony_adapted": False},
            {"name": "libswscale", "ecosystem": "cpp", "registry_name": "ffmpeg", "source_repo": "https://git.ffmpeg.org/ffmpeg.git", "scope": "runtime", "version": ">=0.5.0", "purpose": "FFmpeg 视频像素格式转换与缩放", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libswscale）", "declared_in": ["modules/video_chroma/meson.build:16"], "used_symbols": ["sws_getContext", "sws_scale"], "harmony_adapted": False},
            {"name": "libpostproc", "ecosystem": "cpp", "registry_name": "ffmpeg", "source_repo": "https://git.ffmpeg.org/ffmpeg.git", "scope": "runtime", "version": None, "purpose": "FFmpeg 视频后期处理", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libpostproc）", "declared_in": ["modules/video_filter/meson.build:388"], "used_symbols": [], "harmony_adapted": False},
            {"name": "freetype2", "ecosystem": "cpp", "registry_name": "freetype", "source_repo": "https://gitlab.freedesktop.org/freetype/freetype.git", "scope": "runtime", "version": None, "purpose": "字体渲染（字幕、OSD）", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency freetype2 / freetype）", "declared_in": ["modules/meson.build:209"], "used_symbols": ["FT_Init_FreeType", "FT_Load_Glyph"], "harmony_adapted": True, "harmony_adapted_source": "OpenHarmony PC C/C++ 预编译包 (cmd-pkgs)"},
            {"name": "fontconfig", "ecosystem": "cpp", "registry_name": "fontconfig", "source_repo": "https://gitlab.freedesktop.org/fontconfig/fontconfig.git", "scope": "runtime", "version": ">=2.11", "purpose": "系统字体配置与发现", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency fontconfig）", "declared_in": ["modules/text_renderer/meson.build:35"], "used_symbols": ["FcConfigGetCurrent", "FcPatternCreate"], "harmony_adapted": True, "harmony_adapted_source": "OpenHarmony PC C/C++ 预编译包 (cmd-pkgs)"},
            {"name": "fribidi", "ecosystem": "cpp", "registry_name": "fribidi", "source_repo": "https://github.com/fribidi/fribidi.git", "scope": "runtime", "version": None, "purpose": "双向文本布局（阿拉伯语、希伯来语字幕）", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency fribidi）", "declared_in": ["modules/text_renderer/meson.build:44"], "used_symbols": ["fribidi_log2vis"], "harmony_adapted": True, "harmony_adapted_source": "OpenHarmony PC C/C++ 预编译包 (cmd-pkgs)"},
            {"name": "harfbuzz", "ecosystem": "cpp", "registry_name": "harfbuzz", "source_repo": "https://github.com/harfbuzz/harfbuzz.git", "scope": "runtime", "version": None, "purpose": "复杂文字 shaping", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency harfbuzz）", "declared_in": ["modules/text_renderer/meson.build:51"], "used_symbols": ["hb_shape"], "harmony_adapted": True, "harmony_adapted_source": "OpenHarmony PC C/C++ 预编译包 (cmd-pkgs)"},
            {"name": "librsvg-2.0", "ecosystem": "cpp", "registry_name": "librsvg", "source_repo": "https://gitlab.gnome.org/GNOME/librsvg.git", "scope": "runtime", "version": ">=2.9.0", "purpose": "SVG 图像渲染", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency librsvg-2.0）", "declared_in": ["modules/meson.build:215"], "used_symbols": ["rsvg_handle_new_from_data"], "harmony_adapted": False},
            {"name": "libxml-2.0", "ecosystem": "cpp", "registry_name": "libxml2", "source_repo": "https://gitlab.gnome.org/GNOME/libxml2.git", "scope": "runtime", "version": ">=2.5", "purpose": "XML 解析（XSPF、DASH MPD 等）", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libxml-2.0）", "declared_in": ["modules/misc/meson.build:37"], "used_symbols": ["xmlReadMemory", "xmlFreeDoc"], "harmony_adapted": False},
            {"name": "taglib", "ecosystem": "cpp", "registry_name": "taglib", "source_repo": "https://github.com/taglib/taglib.git", "scope": "runtime", "version": ">=1.11", "purpose": "音频文件标签读取", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency taglib）", "declared_in": ["modules/meta_engine/meson.build:8"], "used_symbols": ["TagLib::FileRef"], "harmony_adapted": False},
            {"name": "alsa", "ecosystem": "cpp", "registry_name": "alsa-lib", "source_repo": "https://git.alsa-project.org/alsa-lib.git", "scope": "runtime", "version": ">=1.0.24", "purpose": "Linux ALSA 音频输出", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency alsa）", "declared_in": ["modules/meson.build:70"], "used_symbols": ["snd_pcm_open", "snd_pcm_writei"], "harmony_adapted": False},
            {"name": "libpulse", "ecosystem": "cpp", "registry_name": "pulseaudio", "source_repo": "https://gitlab.freedesktop.org/pulseaudio/pulseaudio.git", "scope": "runtime", "version": ">=6.0", "purpose": "PulseAudio 音频输出", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libpulse）", "declared_in": ["modules/meson.build:67"], "used_symbols": ["pa_context_connect", "pa_stream_write"], "harmony_adapted": False},
            {"name": "libpipewire-0.3", "ecosystem": "cpp", "registry_name": "pipewire", "source_repo": "https://gitlab.freedesktop.org/pipewire/pipewire.git", "scope": "runtime", "version": ">=0.3.64", "purpose": "PipeWire 音频输出", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libpipewire-0.3）", "declared_in": ["modules/meson.build:64"], "used_symbols": ["pw_context_new", "pw_stream_connect"], "harmony_adapted": False},
            {"name": "jack", "ecosystem": "cpp", "registry_name": "jack", "source_repo": "https://github.com/jackaudio/jack2.git", "scope": "optional", "version": None, "purpose": "JACK 专业低延迟音频输出", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency jack）", "declared_in": ["modules/meson.build:73"], "used_symbols": [], "harmony_adapted": False},
            {"name": "Qt6", "ecosystem": "cpp", "registry_name": "qtbase", "source_repo": "https://code.qt.io/qt/qtbase.git", "scope": "runtime", "version": ">=6.2", "purpose": "主桌面图形用户界面（Core/Gui/Widgets/Qml/Quick/QuickControls2）", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency qt6）", "declared_in": ["modules/gui/qt/meson.build:14"], "used_symbols": ["QApplication", "QMainWindow", "QQmlApplicationEngine"], "harmony_adapted": False},
            {"name": "ncursesw", "ecosystem": "cpp", "registry_name": "ncurses", "source_repo": "https://invisible-island.net/archives/ncurses/", "scope": "optional", "version": None, "purpose": "终端文本界面", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency ncursesw）", "declared_in": ["modules/gui/meson.build:4"], "used_symbols": ["initscr", "wprintw"], "harmony_adapted": False},
            {"name": "xcb", "ecosystem": "cpp", "registry_name": "libxcb", "source_repo": "https://gitlab.freedesktop.org/xorg/lib/libxcb.git", "scope": "runtime", "version": ">=1.6", "purpose": "X11 窗口与事件（视频输出窗口、输入）", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency xcb 及扩展）", "declared_in": ["modules/meson.build:15"], "used_symbols": ["xcb_connect", "xcb_map_window"], "harmony_adapted": False},
            {"name": "wayland-client", "ecosystem": "cpp", "registry_name": "wayland", "source_repo": "https://gitlab.freedesktop.org/wayland/wayland.git", "scope": "runtime", "version": ">=1.5.91", "purpose": "Wayland 合成器窗口集成", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency wayland-client 等）", "declared_in": ["modules/meson.build:35"], "used_symbols": ["wl_display_connect", "wl_surface_attach"], "harmony_adapted": False},
            {"name": "libdrm", "ecosystem": "cpp", "registry_name": "libdrm", "source_repo": "https://gitlab.freedesktop.org/mesa/drm.git", "scope": "optional", "version": ">=2.4.83", "purpose": "Direct Rendering Manager（KMS 视频输出）", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libdrm）", "declared_in": ["modules/video_output/meson.build:25"], "used_symbols": ["drmModeSetCrtc"], "harmony_adapted": True, "harmony_adapted_source": "OpenHarmony PC C/C++ 预编译包 (cmd-pkgs)"},
            {"name": "gl", "ecosystem": "cpp", "registry_name": "opengl", "source_repo": "https://gitlab.freedesktop.org/mesa/mesa.git", "scope": "runtime", "version": None, "purpose": "OpenGL 视频渲染", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency gl）", "declared_in": ["modules/video_output/meson.build:19"], "used_symbols": ["glGenTextures", "glDrawArrays"], "harmony_adapted": False},
            {"name": "glesv2", "ecosystem": "cpp", "registry_name": "opengles", "source_repo": "https://gitlab.freedesktop.org/mesa/mesa.git", "scope": "runtime", "version": None, "purpose": "OpenGL ES 2 视频渲染", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency glesv2）", "declared_in": ["modules/video_output/meson.build:21"], "used_symbols": ["glTexImage2D"], "harmony_adapted": False},
            {"name": "egl", "ecosystem": "cpp", "registry_name": "egl", "source_repo": "https://gitlab.freedesktop.org/mesa/mesa.git", "scope": "runtime", "version": None, "purpose": "EGL 显示与上下文管理", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency egl）", "declared_in": ["modules/video_output/meson.build:22"], "used_symbols": ["eglGetDisplay", "eglSwapBuffers"], "harmony_adapted": False},
            {"name": "vulkan", "ecosystem": "cpp", "registry_name": "vulkan-loader", "source_repo": "https://github.com/KhronosGroup/Vulkan-Loader.git", "scope": "optional", "version": ">=1.0.26", "purpose": "Vulkan 视频渲染", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency vulkan）", "declared_in": ["modules/video_output/meson.build:28"], "used_symbols": ["vkCreateInstance", "vkCreateDevice"], "harmony_adapted": False},
            {"name": "libplacebo", "ecosystem": "cpp", "registry_name": "libplacebo", "source_repo": "https://code.videolan.org/videolan/libplacebo.git", "scope": "optional", "version": None, "purpose": "高级 GPU 视频渲染管线", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libplacebo）", "declared_in": ["modules/video_output/libplacebo/meson.build:3"], "used_symbols": [], "harmony_adapted": False},
            {"name": "libarchive", "ecosystem": "cpp", "registry_name": "libarchive", "source_repo": "https://github.com/libarchive/libarchive.git", "scope": "optional", "version": ">=3.1.0", "purpose": "压缩归档流提取", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libarchive）", "declared_in": ["modules/stream_extractor/meson.build:1"], "used_symbols": ["archive_read_open_filename", "archive_read_next_header"], "harmony_adapted": True, "harmony_adapted_source": "OpenHarmony PC C/C++ 预编译包 (cmd-pkgs)"},
            {"name": "libmtp", "ecosystem": "cpp", "registry_name": "libmtp", "source_repo": "https://github.com/libmtp/libmtp.git", "scope": "optional", "version": ">=1.0.0", "purpose": "MTP 设备媒体访问", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libmtp）", "declared_in": ["modules/meson.build:201", "modules/services_discovery/meson.build:32"], "used_symbols": ["LIBMTP_Get_Files_And_Folders"], "harmony_adapted": False},
            {"name": "libupnp", "ecosystem": "cpp", "registry_name": "libupnp", "source_repo": "https://github.com/pupnp/pupnp.git", "scope": "optional", "version": ">=1.8.5", "purpose": "UPnP 服务发现与控制", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libupnp / UPNP）", "declared_in": ["modules/services_discovery/meson.build:42"], "used_symbols": [], "harmony_adapted": False},
            {"name": "microdns", "ecosystem": "cpp", "registry_name": "microdns", "source_repo": "https://github.com/videolan/microdns.git", "scope": "optional", "version": None, "purpose": "mDNS 服务发现", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency microdns）", "declared_in": ["modules/services_discovery/meson.build:148"], "used_symbols": [], "harmony_adapted": True, "harmony_adapted_source": "OpenHarmony PC C/C++ 预编译包 (cmd-pkgs)"},
            {"name": "srt", "ecosystem": "cpp", "registry_name": "srt", "source_repo": "https://github.com/Haivision/srt.git", "scope": "optional", "version": ">=1.3.0", "purpose": "SRT 可靠网络传输协议", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency srt）", "declared_in": ["modules/meson.build:195"], "used_symbols": [], "harmony_adapted": False},
            {"name": "librist", "ecosystem": "cpp", "registry_name": "librist", "source_repo": "https://code.videolan.org/rist/librist.git", "scope": "optional", "version": None, "purpose": "RIST 专业流媒体传输", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency librist）", "declared_in": ["modules/meson.build:198"], "used_symbols": [], "harmony_adapted": False},
            {"name": "libchromaprint", "ecosystem": "cpp", "registry_name": "chromaprint", "source_repo": "https://github.com/acoustid/chromaprint.git", "scope": "optional", "version": ">=0.6.0", "purpose": "音频指纹（Chromecast 流识别）", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency libchromaprint）", "declared_in": ["modules/stream_out/meson.build:161"], "used_symbols": [], "harmony_adapted": False},
            {"name": "protobuf", "ecosystem": "cpp", "registry_name": "protobuf", "source_repo": "https://github.com/protocolbuffers/protobuf.git", "scope": "optional", "version": None, "purpose": "Chromecast 协议序列化", "acquisition": "system", "locality": "system", "source": "系统依赖（meson dependency protobuf）", "declared_in": ["modules/stream_out/chromecast/meson.build:2"], "used_symbols": [], "harmony_adapted": False},
            {"name": "libpng", "ecosystem": "cpp", "registry_name": "libpng", "source_repo": "https://github.com/glennrp/libpng.git", "scope": "runtime", "version": None, "purpose": "PNG 图像编解码", "acquisition": "system", "locality": "system", "source": "通常由 Qt/FFmpeg 间接引入", "declared_in": ["modules/codec/png.c"], "used_symbols": [], "harmony_adapted": True, "harmony_adapted_source": "OpenHarmony PC C/C++ 预编译包 (cmd-pkgs)"},
            {"name": "libjpeg-turbo", "ecosystem": "cpp", "registry_name": "libjpeg-turbo", "source_repo": "https://github.com/libjpeg-turbo/libjpeg-turbo.git", "scope": "runtime", "version": None, "purpose": "JPEG 图像编解码", "acquisition": "system", "locality": "system", "source": "通常由 Qt/FFmpeg 间接引入", "declared_in": ["modules/codec/jpeg.c"], "used_symbols": [], "harmony_adapted": True, "harmony_adapted_source": "OpenHarmony PC C/C++ 预编译包 (cmd-pkgs)"},
            {"name": "libdvdread", "ecosystem": "cpp", "registry_name": "libdvdread", "source_repo": "https://code.videolan.org/libdvdread/libdvdread.git", "scope": "optional", "version": None, "purpose": "DVD 光盘读取", "acquisition": "system", "locality": "system", "source": "系统依赖（access/dvdread）", "declared_in": ["modules/access/dvdread.c"], "used_symbols": [], "harmony_adapted": False},
            {"name": "libdvdnav", "ecosystem": "cpp", "registry_name": "libdvdnav", "source_repo": "https://code.videolan.org/libdvdnav/libdvdnav.git", "scope": "optional", "version": None, "purpose": "DVD 菜单导航", "acquisition": "system", "locality": "system", "source": "系统依赖（access/dvdnav.c）", "declared_in": ["modules/access/dvdnav.c"], "used_symbols": [], "harmony_adapted": False},
            {"name": "libbluray", "ecosystem": "cpp", "registry_name": "libbluray", "source_repo": "https://code.videolan.org/videolan/libbluray.git", "scope": "optional", "version": None, "purpose": "Blu-ray 光盘读取", "acquisition": "system", "locality": "system", "source": "系统依赖（access/bluray.c）", "declared_in": ["modules/access/bluray.c"], "used_symbols": [], "harmony_adapted": False},
            {"name": "aom", "ecosystem": "cpp", "registry_name": "aom", "source_repo": "https://aomedia.googlesource.com/aom", "scope": "optional", "version": None, "purpose": "AV1 视频解码", "acquisition": "system", "locality": "system", "source": "系统依赖（modules/codec/aom.c）", "declared_in": ["modules/codec/aom.c"], "used_symbols": [], "harmony_adapted": False},
            {"name": "dav1d", "ecosystem": "cpp", "registry_name": "dav1d", "source_repo": "https://code.videolan.org/videolan/dav1d.git", "scope": "optional", "version": None, "purpose": "AV1 视频解码（VideoLAN 出品）", "acquisition": "system", "locality": "system", "source": "系统依赖（modules/codec/dav1d.c）", "declared_in": ["modules/codec/dav1d.c"], "used_symbols": [], "harmony_adapted": False},
            {"name": "libass", "ecosystem": "cpp", "registry_name": "libass", "source_repo": "https://github.com/libass/libass.git", "scope": "optional", "version": None, "purpose": "ASS/SSA 字幕渲染", "acquisition": "system", "locality": "system", "source": "系统依赖（modules/codec/libass.c）", "declared_in": ["modules/codec/libass.c"], "used_symbols": [], "harmony_adapted": False}
        ],
        "notes": "VLC 为插件化播放器，依赖数量庞大且多为可选系统库。上表列出核心与常用运行时依赖；大量可选插件依赖（如 fluidsynth、libgoom2、projectM、libvsxu、opencv、decklink 等）未全部枚举。构建系统同时支持 autotools 与实验性 meson。"
    }
}

# Fill derived counts
report["dependencies"]["count"] = len(report["dependencies"]["dependencies"])
report["dependencies"]["by_ecosystem"]["cpp"] = [d["name"] for d in report["dependencies"]["dependencies"]]

report["native_api"] = {
    "summary": "VLC 为跨平台桌面应用，对 OS 原生 API 有重度依赖：POSIX 线程/信号/套接字/mmap 构成核心运行时；Linux 下使用 /proc、eventfd、vmsplice；Windows 使用 Win32 文件/注册表/线程 API；macOS 依赖 Cocoa/Core* 框架；GUI 与视频输出依赖 Qt6、X11/XCB、Wayland、OpenGL/Vulkan/Direct3D；音频输出依赖 ALSA/PulseAudio/PipeWire/WASAPI 等平台后端。",
    "groups": [
        {
            "type": "c_cpp_stl",
            "category": "standard",
            "platform": "portable",
            "apis": [
                {"name": "pthread_create / pthread_join", "purpose": "POSIX 线程创建与回收", "count": 2, "evidence": ["src/posix/thread.c:179", "src/posix/thread.c:195"], "conditional": False},
                {"name": "pthread_mutex_* / pthread_cond_*", "purpose": "POSIX 线程同步原语", "count": 12, "evidence": ["src/posix/wait.c:66", "src/posix/wait.c:86", "src/network/rootbind.c:121"], "conditional": False},
                {"name": "mmap / munmap", "purpose": "内存映射文件与帧缓冲区", "count": 6, "evidence": ["src/posix/picture.c:46", "src/misc/frame.c:441", "src/misc/frame.c:292"], "conditional": False},
                {"name": "socket / accept / connect / bind / listen", "purpose": "BSD/POSIX 网络套接字", "count": 8, "evidence": ["src/posix/filesystem.c:284", "src/posix/filesystem.c:337", "src/network/io.c:146", "src/network/io.c:265"], "conditional": False},
                {"name": "poll", "purpose": "I/O 事件多路复用", "count": 6, "evidence": ["src/network/httpd.c:2011", "src/network/io.c:321", "src/misc/interrupt.c:359"], "conditional": False},
                {"name": "sigaction / sigwait / pthread_sigmask", "purpose": "POSIX 信号管理", "count": 10, "evidence": ["bin/vlc.c:90", "src/posix/thread.c:150", "src/posix/filesystem.c:229", "src/posix/filesystem.c:251"], "conditional": False},
                {"name": "posix_spawn / fork + execvp", "purpose": "启动外部进程", "count": 4, "evidence": ["src/posix/spawn.c:105", "src/posix/spawn.c:146", "src/posix/spawn.c:181"], "conditional": False}
            ]
        },
        {
            "type": "linux_kernel",
            "category": "system",
            "platform": "linux",
            "apis": [
                {"name": "eventfd", "purpose": "Linux 事件通知文件描述符", "count": 1, "evidence": ["meson.build:663"], "conditional": True},
                {"name": "vmsplice", "purpose": "Linux 零拷贝管道写入", "count": 1, "evidence": ["meson.build:664"], "conditional": True},
                {"name": "sched_getaffinity", "purpose": "读取 CPU 亲和性", "count": 1, "evidence": ["meson.build:665"], "conditional": True},
                {"name": "recvmmsg", "purpose": "批量接收网络报文", "count": 1, "evidence": ["meson.build:666"], "conditional": True},
                {"name": "memfd_create", "purpose": "匿名内存文件", "count": 1, "evidence": ["meson.build:667"], "conditional": True},
                {"name": "procfs (/proc/self/maps)", "purpose": "读取进程内存映射以定位模块路径", "count": 1, "evidence": ["src/linux/dirs.c:38"], "conditional": True},
                {"name": "procfs (/proc/cpuinfo)", "purpose": "读取 CPU 信息", "count": 1, "evidence": ["src/linux/cpu.c:104"], "conditional": True}
            ]
        },
        {
            "type": "win32",
            "category": "platform",
            "platform": "windows",
            "apis": [
                {"name": "CreateFileW / CreateFile2", "purpose": "Windows 文件打开", "count": 2, "evidence": ["src/win32/filesystem.c:119", "src/win32/filesystem.c:129"], "conditional": True},
                {"name": "CreateProcess / WaitForSingleObject", "purpose": "Windows 进程创建与等待", "count": 2, "evidence": ["src/win32/spawn.c:262", "src/win32/thread.c:380"], "conditional": True},
                {"name": "RegOpenKeyEx", "purpose": "Windows 注册表读取网络代理", "count": 1, "evidence": ["src/win32/netconf.c:66"], "conditional": True},
                {"name": "LoadLibraryExW / GetProcAddress / FreeLibrary", "purpose": "Windows 动态库加载", "count": 4, "evidence": ["src/win32/plugin.c:64", "src/win32/plugin.c:91", "src/win32/plugin.c:85"], "conditional": True},
                {"name": "ioctlsocket / FIONBIO", "purpose": "Windows 套接字非阻塞设置", "count": 2, "evidence": ["src/win32/filesystem.c:527", "src/win32/filesystem.c:542"], "conditional": True},
                {"name": "WaitForSingleObjectEx", "purpose": "Windows 异步 I/O 等待", "count": 1, "evidence": ["src/win32/process.c:52"], "conditional": True}
            ]
        },
        {
            "type": "darwin_frameworks",
            "category": "platform",
            "platform": "macos",
            "apis": [
                {"name": "CoreFoundation", "purpose": "macOS 基础类型与运行环", "count": 1, "evidence": ["src/darwin/specific.c:32"], "conditional": True},
                {"name": "Cocoa / AppKit", "purpose": "macOS 原生窗口与应用生命周期", "count": 1, "evidence": ["modules/gui/macosx/", "modules/video_output/macosx.m"], "conditional": True},
                {"name": "IOKit", "purpose": "macOS 硬件/设备访问", "count": 1, "evidence": ["modules/meson.build:92"], "conditional": True},
                {"name": "AudioUnit / CoreAudio", "purpose": "macOS/iOS 音频输出", "count": 1, "evidence": ["modules/audio_output/apple/"], "conditional": True},
                {"name": "VideoToolbox / AVFoundation", "purpose": "macOS/iOS 硬件编解码", "count": 1, "evidence": ["modules/codec/avcapture.m", "modules/hw/"], "conditional": True}
            ]
        },
        {
            "type": "x11_xcb",
            "category": "platform",
            "platform": "posix",
            "apis": [
                {"name": "xcb_connect / xcb_map_window", "purpose": "X11 XCB 窗口管理", "count": 2, "evidence": ["modules/video_output/xcb/window.c"], "conditional": True},
                {"name": "xcb_randr", "purpose": "X11 RandR 显示器配置", "count": 1, "evidence": ["modules/meson.build:17"], "conditional": True},
                {"name": "glx", "purpose": "X11 OpenGL 上下文", "count": 1, "evidence": ["modules/video_output/glx.c"], "conditional": True},
                {"name": "egl_x11", "purpose": "X11 EGL 显示", "count": 1, "evidence": ["modules/video_output/meson.build:254"], "conditional": True}
            ]
        },
        {
            "type": "wayland",
            "category": "platform",
            "platform": "linux",
            "apis": [
                {"name": "wl_display_connect / wl_surface_attach", "purpose": "Wayland 合成器表面提交", "count": 2, "evidence": ["modules/video_output/wayland/"], "conditional": True},
                {"name": "wayland-egl", "purpose": "Wayland EGL 集成", "count": 1, "evidence": ["modules/meson.build:37"], "conditional": True},
                {"name": "xkbcommon", "purpose": "Wayland 键盘映射", "count": 1, "evidence": ["modules/video_output/wayland/meson.build:71"], "conditional": True}
            ]
        },
        {
            "type": "graphics_3d",
            "category": "hardware",
            "platform": "portable",
            "apis": [
                {"name": "OpenGL", "purpose": "跨平台 3D/2D 视频渲染", "count": 1, "evidence": ["modules/video_output/opengl/"], "conditional": True},
                {"name": "OpenGL ES 2", "purpose": "移动/嵌入式平台视频渲染", "count": 1, "evidence": ["modules/video_output/meson.build:21"], "conditional": True},
                {"name": "EGL", "purpose": "OpenGL/EGL 显示上下文", "count": 1, "evidence": ["modules/video_output/meson.build:22"], "conditional": True},
                {"name": "Vulkan", "purpose": "Vulkan 视频渲染", "count": 1, "evidence": ["modules/video_output/vulkan/"], "conditional": True},
                {"name": "Direct3D 11", "purpose": "Windows 视频渲染与硬件解码", "count": 1, "evidence": ["modules/video_output/win32/meson.build:12", "modules/hw/d3d11/"], "conditional": True},
                {"name": "Direct3D 9", "purpose": "Windows 旧版视频渲染", "count": 1, "evidence": ["modules/video_chroma/meson.build:118"], "conditional": True},
                {"name": "libdrm / KMS", "purpose": "Linux DRM 直接显示", "count": 1, "evidence": ["modules/video_output/kms.c"], "conditional": True}
            ]
        },
        {
            "type": "audio_output",
            "category": "platform",
            "platform": "posix",
            "apis": [
                {"name": "ALSA (snd_pcm_open)", "purpose": "Linux ALSA 音频输出", "count": 1, "evidence": ["modules/audio_output/alsa.c"], "conditional": True},
                {"name": "PulseAudio (pa_context_connect)", "purpose": "PulseAudio 音频输出", "count": 1, "evidence": ["modules/audio_output/pulse.c", "modules/audio_output/vlcpulse.c"], "conditional": True},
                {"name": "PipeWire (pw_stream_connect)", "purpose": "PipeWire 音频输出", "count": 1, "evidence": ["modules/audio_output/pipewire.c", "modules/audio_output/vlc_pipewire.c"], "conditional": True},
                {"name": "JACK", "purpose": "专业低延迟音频输出", "count": 1, "evidence": ["modules/audio_output/jack.c"], "conditional": True},
                {"name": "WASAPI", "purpose": "Windows 现代音频输出", "count": 1, "evidence": ["modules/audio_output/wasapi.c"], "conditional": True},
                {"name": "WaveOut", "purpose": "Windows 旧版音频输出", "count": 1, "evidence": ["modules/audio_output/waveout.c"], "conditional": True}
            ]
        },
        {
            "type": "hardware_acceleration",
            "category": "hardware",
            "platform": "portable",
            "apis": [
                {"name": "VAAPI", "purpose": "Intel/AMD Linux 硬件视频解码", "count": 1, "evidence": ["modules/hw/vaapi/"], "conditional": True},
                {"name": "VDPAU", "purpose": "NVIDIA Linux 硬件视频解码", "count": 1, "evidence": ["modules/hw/vdpau/"], "conditional": True},
                {"name": "NVDEC", "purpose": "NVIDIA 硬件视频解码", "count": 1, "evidence": ["modules/hw/nvdec/"], "conditional": True},
                {"name": "DXVA2 / D3D11VA", "purpose": "Windows 硬件视频解码", "count": 1, "evidence": ["modules/hw/d3d11/", "modules/hw/d3d9/"], "conditional": True},
                {"name": "VideoToolbox", "purpose": "Apple 硬件编解码", "count": 1, "evidence": ["modules/hw/mmal/", "modules/codec/audiotoolbox_midi.c"], "conditional": True},
                {"name": "AMF", "purpose": "AMD 硬件编码", "count": 1, "evidence": ["modules/hw/amf/"], "conditional": True}
            ]
        }
    ],
    "dynamic_libraries": [
        {
            "name": "VLC plugin .so/.dll/.dylib",
            "mechanism": "dlopen / LoadLibraryExW",
            "acquisition": "self_build",
            "source": "本仓构建产出的插件动态库，运行时从模块目录加载",
            "description": "VLC 插件化架构核心：运行时扫描模块目录并动态加载各功能插件",
            "optional": False,
            "evidence": ["src/modules/bank.c:222", "src/posix/plugin.c:52", "src/win32/plugin.c:64"]
        }
    ],
    "platform_dependence": "mixed"
}

report["runtime_surface"] = {
    "summary": "VLC 作为完整桌面应用，运行期与宿主环境有大量交互：读取插件/数据/配置路径的环境变量、使用 POSIX/Win32 网络套接字进行流接收与串流、访问 /proc、/dev 等伪文件、通过 posix_spawn/fork+exec 启动外部辅助进程，以及依赖平台音频/视频/输入设备。",
    "network": [
        {"detail": "POSIX/Win32 套接字", "purpose": "网络流接入、串流输出、HTTP 控制接口、UDP/RTP 传输", "evidence": ["src/posix/filesystem.c:284", "src/network/io.c:146", "src/network/httpd.c:2011"]},
        {"detail": "HTTP 远程控制 / Lua HTTP 界面", "purpose": "通过 Web 界面远程控制播放", "evidence": ["share/lua/http/", "modules/lua/"]},
        {"detail": "Bonjour/mDNS / UPnP", "purpose": "服务发现与网络设备枚举", "evidence": ["modules/services_discovery/"]},
        {"detail": "代理配置", "purpose": "从环境变量或系统设置读取 HTTP 代理", "evidence": ["src/posix/netconf.c:81", "src/win32/netconf.c:66"]}
    ],
    "filesystem": [
        {"detail": "模块/数据/配置目录", "purpose": "加载插件、读取主题、保存配置", "evidence": ["src/config/dirs.c:41", "src/posix/dirs.c:120", "src/posix/dirs.c:167"]},
        {"detail": "/proc/self/maps", "purpose": "Linux 下定位二进制/模块路径", "evidence": ["src/linux/dirs.c:38"]},
        {"detail": "/proc/cpuinfo", "purpose": "Linux 下获取 CPU 信息", "evidence": ["src/linux/cpu.c:104"]},
        {"detail": "/dev/null", "purpose": "子进程标准流重定向", "evidence": ["src/posix/spawn.c:64", "src/posix/spawn.c:131"]},
        {"detail": "/dev/urandom", "purpose": "获取随机数", "evidence": ["src/posix/rand.c:55"]},
        {"detail": "fd:// / /dev/stdin / /dev/stdout / /dev/stderr", "purpose": "文件描述符流访问", "evidence": ["src/text/url.c:336"]},
        {"detail": "光学设备 /dev/dvd /dev/cdrom /dev/sr0", "purpose": "DVD/VCD 光盘读取", "evidence": ["src/libvlc-module.c:907"]},
        {"detail": "$HOME / $XDG_CONFIG_HOME", "purpose": "用户配置与缓存目录", "evidence": ["src/posix/dirs.c:120", "src/posix/dirs.c:167"]}
    ],
    "env_vars": [
        {"name": "VLC_PLUGIN_PATH", "purpose": "指定插件搜索路径", "evidence": ["bin/vlc.c:143", "src/modules/bank.c:597"]},
        {"name": "VLC_DATA_PATH", "purpose": "指定数据资源路径", "evidence": ["bin/vlc.c:144", "src/win32/dirs-common.c:77"]},
        {"name": "VLC_LIB_PATH / VLC_LIBEXEC_PATH", "purpose": "指定库与可执行辅助程序路径", "evidence": ["bin/vlc.c:145", "bin/vlc.c:146"]},
        {"name": "HOME", "purpose": "用户主目录", "evidence": ["src/posix/dirs.c:120"]},
        {"name": "XDG_CONFIG_HOME", "purpose": "Linux 用户配置目录", "evidence": ["src/posix/dirs.c:167"]},
        {"name": "http_proxy", "purpose": "HTTP 代理", "evidence": ["src/posix/netconf.c:81"]},
        {"name": "DESKTOP_STARTUP_ID", "purpose": "X.Org 启动通知 ID，启动时清除", "evidence": ["bin/vlc.c:152"]},
        {"name": "GNOME_DISABLE_CRASH_DIALOG", "purpose": "禁用 GNOME 崩溃对话框（调试构建）", "evidence": ["bin/vlc.c:139"]},
        {"name": "MALLOC_CHECK_", "purpose": "启用 malloc 检查（调试构建）", "evidence": ["bin/vlc.c:136"]},
        {"name": "PWD", "purpose": "检测 Cygwin/Wine 环境", "evidence": ["src/config/help.c:715"]},
        {"name": "VLC_ROOTWRAP_SOCK", "purpose": "rootwrap 辅助进程通信", "evidence": ["src/network/rootbind.c:125"]},
        {"name": "LANG", "purpose": "macOS 下区域设置", "evidence": ["src/darwin/specific.c:43"]}
    ],
    "subprocess": [
        {"command": "posix_spawn / fork+execvp", "purpose": "启动外部辅助程序或 rootwrap 提权封装", "evidence": ["src/posix/spawn.c:105", "src/posix/spawn.c:146", "bin/rootwrap.c"]},
        {"command": "win32 CreateProcess", "purpose": "Windows 下启动外部进程", "evidence": ["src/win32/spawn.c:262"]}
    ],
    "devices": [
        {"detail": "/dev/dvd /dev/cdrom /dev/sr0", "purpose": "DVD/Blu-ray/VCD 光盘读取", "evidence": ["src/libvlc-module.c:907"]},
        {"detail": "GPU / V4L2 / AVFoundation / DirectShow", "purpose": "视频采集与硬件解码", "evidence": ["modules/access/dc1394.c", "modules/access/dshow/", "modules/access/avcapture.m"]},
        {"detail": "MTP / USB 设备", "purpose": "便携设备媒体访问", "evidence": ["modules/access/mtp.c", "modules/services_discovery/mtp.c"]}
    ],
    "services": []
}

report["build_env"] = {
    "language_standard": "C17/GNU17, C++17",
    "runtime_version": "无解释器依赖，生成原生可执行文件与共享库",
    "build_system": "GNU Autotools（主构建系统）/ Meson（实验性，meson.build 多处标注 EXPERIMENTAL）",
    "compiler_extensions": [
        {"detail": "__attribute__((packed)) / visibility=hidden / _Thread_local", "purpose": " packed 结构、隐藏符号、线程局部存储", "evidence": ["meson.build:857", "meson.build:863", "meson.build:891"]},
        {"detail": "GCC/Clang 警告与优化选项", "purpose": "严格的编译警告与栈保护", "evidence": ["meson.build:494", "meson.build:898"]},
        {"detail": "x86 NASM / yasm 汇编", "purpose": "x86/x86_64 平台 SIMD/汇编优化", "evidence": ["meson.build:114", "configure.ac:142"]},
        {"detail": "MSVC/MinGW 兼容层", "purpose": "Windows 平台编译适配", "evidence": ["meson.build:100", "configure.ac:154"]}
    ],
    "platforms": [
        {"os": "Windows", "arch": "x86_64 / x86", "evidence": ["meson.build:100", "configure.ac:154", "bin/winvlc.c"]},
        {"os": "macOS", "arch": "x86_64 / arm64", "evidence": ["meson.build:105", "configure.ac:187", "bin/darwinvlc.m"]},
        {"os": "Linux", "arch": "x86_64 / arm64 / etc.", "evidence": ["configure.ac:158", "meson.build:246"]},
        {"os": "BSD", "arch": "x86_64", "evidence": ["configure.ac:163"]},
        {"os": "Android", "arch": "arm64 / x86_64", "evidence": ["meson.build:68", "modules/video_output/android/"]},
        {"os": "iOS/tvOS/visionOS", "arch": "arm64", "evidence": ["meson.build:95", "configure.ac:241"]}
    ],
    "entry_points": [
        {"type": "main", "name": "vlc", "command": "C 语言命令行入口，解析参数并启动 libvlc 实例", "evidence": ["bin/vlc.c:117"]},
        {"type": "launcher", "name": "winvlc.c", "command": "Windows 原生 GUI 启动器", "evidence": ["bin/winvlc.c"]},
        {"type": "launcher", "name": "darwinvlc.m", "command": "macOS 原生应用启动器", "evidence": ["bin/darwinvlc.m"]},
        {"type": "console_script", "name": "rootwrap", "command": "提权辅助进程（UDP 低端口等）", "evidence": ["bin/rootwrap.c"]},
        {"type": "tool", "name": "cachegen", "command": "插件缓存生成工具", "evidence": ["bin/cachegen.c"]}
    ],
    "packaging": "多平台分发：Linux 使用 .desktop 与发行版包；Windows 使用 NSIS/MSI 安装包；macOS 使用 .app bundle；移动平台使用对应商店包。",
    "notes": "VLC 4.0 开发版（Otto Chriek），libvlc ABI 版本 12.0.0。仓库同时维护 autotools 与 meson 两套构建文件，后者标记为实验性。"
}

report["capability_profile"] = {
    "summary": "VLC 是典型的桌面多媒体应用，触及 GUI（Qt6/X11/Wayland/Cocoa）、3D 图形渲染（OpenGL/Vulkan/Direct3D）、媒体（FFmpeg 生态、音视频 I/O）三大鸿蒙适配重点场景；硬件加速为可选增强而非核心依赖。",
    "scenarios": [
        {
            "key": "gui",
            "present": True,
            "kind": ["qt6", "x11", "wayland", "cocoa", "ncurses"],
            "via": ["Qt6", "xcb", "wayland-client", "cocoa_dep", "ncursesw_dep"],
            "harmony_status": "available",
            "adaptation": "Qt6 已有社区鸿蒙版，但桌面窗口管理、文件对话框、系统托盘、拖拽、剪贴板等桌面集成能力需逐项验证并可能改用 @ohos 能力。",
            "evidence": ["modules/gui/qt/meson.build:14", "modules/gui/macosx/", "modules/meson.build:15"]
        },
        {
            "key": "rendering_3d",
            "present": True,
            "kind": ["opengl", "opengles2", "vulkan", "direct3d"],
            "via": ["gl", "glesv2", "egl", "vulkan", "d3d11"],
            "harmony_status": "partial",
            "adaptation": "OpenGL ES/EGL 在鸿蒙上部分可用；完整 OpenGL、Vulkan、Direct3D 需迁移到 OpenGL ES 或 ArkGraphics 3D，X11/Wayland 窗口集成需重写。",
            "evidence": ["modules/video_output/meson.build:19", "modules/video_output/meson.build:21", "modules/video_output/meson.build:28", "modules/video_output/win32/meson.build:12"]
        },
        {
            "key": "media",
            "present": True,
            "kind": ["ffmpeg", "video_decode", "audio_output", "video_output", "codec"],
            "via": ["libavformat", "libavcodec", "libavutil", "alsa", "libpulse", "libpipewire-0.3", "wasapi"],
            "harmony_status": "unknown",
            "adaptation": "编解码依赖 FFmpeg 生态在鸿蒙 PC 的可用性未核实；音频输出后端（ALSA/PulseAudio/PipeWire/WASAPI）无直接等价，需改用 @ohos.multimedia.audio。",
            "evidence": ["modules/meson.build:204", "modules/meson.build:67", "modules/meson.build:64", "modules/audio_output/wasapi.c"]
        },
        {
            "key": "hardware",
            "present": True,
            "kind": ["gpu_video_decode"],
            "via": ["vaapi", "vdpau", "nvdec", "d3d11va", "videotoolbox", "amf"],
            "specific_hardware": False,
            "harmony_status": "unknown",
            "adaptation": "硬件加速解码为可选性能增强；VAAPI/VDPAU/NVDEC/Direct3D 等为各平台专有，鸿蒙需使用系统多媒体能力或相应 GPU 接口替代。",
            "evidence": ["modules/hw/"]
        }
    ]
}

report["harmony_adaptation"] = {
    "target": "HarmonyOS NEXT PC（整包桌面应用口径；自研内核，OHOS NDK musl/POSIX 子集，arm64/x86_64）",
    "feasibility": "hard",
    "porting_class": "needs_adaptation_partial",
    "effort": {"person_days": [60, 120]},
    "confidence": "medium",
    "recommended_path": "qt_ohos_rebuild",
    "summary": "VLC 作为完整桌面应用移植鸿蒙 PC 属于极复杂工程：Qt6 界面层有社区鸿蒙版可用，但桌面集成（文件对话框、系统托盘、拖拽、多窗口）能力未核实；核心媒体引擎依赖 FFmpeg 生态与大量平台音频/视频输出后端（ALSA/PulseAudio/PipeWire/WASAPI/X11/Wayland/Direct3D），在鸿蒙上无直接等价，需大量模块重写或改用 @ohos.multimedia；光学介质、硬件解码等模块将不可用或需替换。整体可行但工作量巨大，需分阶段落地。",
    "unadaptable_apis": [
        {"id": "ua:alsa", "api": "snd_pcm_open / snd_pcm_writei", "public_entry": "alsa", "reason": "ALSA 为 Linux 专有音频 I/O 后端，鸿蒙无等价接口", "blocking_native_api": "snd_pcm_open", "category": "platform", "evidence": ["modules/audio_output/alsa.c"]},
        {"id": "ua:pulse", "api": "pa_context_connect / pa_stream_write", "public_entry": "pulse", "reason": "PulseAudio 为 Linux/Unix 音频服务，鸿蒙无对应守护进程", "blocking_native_api": "pa_context_connect", "category": "platform", "evidence": ["modules/audio_output/pulse.c"]},
        {"id": "ua:pipewire", "api": "pw_context_new / pw_stream_connect", "public_entry": "pipewire", "reason": "PipeWire 为 Linux 新一代音频/视频服务，鸿蒙无对应实现", "blocking_native_api": "pw_context_new", "category": "platform", "evidence": ["modules/audio_output/pipewire.c"]},
        {"id": "ua:wasapi", "api": "WASAPI 音频输出", "public_entry": "wasapi", "reason": "WASAPI 为 Windows 专有音频 API", "blocking_native_api": "wasapi", "category": "platform", "evidence": ["modules/audio_output/wasapi.c"]},
        {"id": "ua:x11", "api": "xcb_connect / xcb_map_window / glx", "public_entry": "xcb_window / xcb_x11 / glx", "reason": "X11/XCB/GLX 为 Linux/Unix 显示栈，鸿蒙桌面不使用 X11", "blocking_native_api": "xcb_connect", "category": "platform", "evidence": ["modules/video_output/xcb/", "modules/video_output/glx.c"]},
        {"id": "ua:wayland", "api": "wl_display_connect / wl_surface_attach", "public_entry": "wayland", "reason": "Wayland 为 Linux 合成器协议，鸿蒙桌面窗口模型不同", "blocking_native_api": "wl_display_connect", "category": "platform", "evidence": ["modules/video_output/wayland/"]},
        {"id": "ua:d3d", "api": "Direct3D 9 / 11 / DXGI", "public_entry": "d3d11 / d3d9", "reason": "Direct3D 为 Windows 专有图形 API", "blocking_native_api": "d3d11", "category": "hardware", "evidence": ["modules/video_output/win32/meson.build:12", "modules/hw/d3d11/"]},
        {"id": "ua:vaapi", "api": "VAAPI 硬件解码", "public_entry": "vaapi", "reason": "VAAPI 为 Intel/AMD Linux 硬件解码接口，鸿蒙无等价", "blocking_native_api": "vaapi", "category": "hardware", "evidence": ["modules/hw/vaapi/"]},
        {"id": "ua:vdpau", "api": "VDPAU 硬件解码", "public_entry": "vdpau", "reason": "VDPAU 为 NVIDIA Linux 硬件解码接口，鸿蒙无等价", "blocking_native_api": "vdpau", "category": "hardware", "evidence": ["modules/hw/vdpau/"]},
        {"id": "ua:nvdec", "api": "NVDEC 硬件解码", "public_entry": "nvdec", "reason": "NVDEC 为 NVIDIA 专有硬件解码 API，鸿蒙无 CUDA/NVIDIA 驱动支持", "blocking_native_api": "nvdec", "category": "hardware", "evidence": ["modules/hw/nvdec/"]},
        {"id": "ua:procfs", "api": "procfs (/proc/self/maps, /proc/cpuinfo)", "public_entry": "vlc_GetProxyUrl / vlc_CPU", "reason": "鸿蒙无 Linux procfs 接口，进程/CPU 信息需改用其他系统能力", "blocking_native_api": "/proc/self/maps", "category": "system", "evidence": ["src/linux/dirs.c:38", "src/linux/cpu.c:104"]},
        {"id": "ua:win32_registry", "api": "RegOpenKeyEx", "public_entry": "vlc_GetProxyUrl", "reason": "Windows 注册表为 Windows 专有配置存储", "blocking_native_api": "RegOpenKeyEx", "category": "platform", "evidence": ["src/win32/netconf.c:66"]}
    ],
    "target_assumptions": [
        {"id": "ta:qt", "capability": "Qt6 桌面 GUI 在鸿蒙 PC 可用", "required": True, "target_status": "available", "impact": "Qt 为 VLC 主界面依赖；available 表示界面层有移植基础", "source": "references/harmony-pc-capabilities.json#gui.qt"},
        {"id": "ta:desktop_wm", "capability": "桌面窗口管理器 / 多窗口环境", "required": True, "target_status": "unknown", "impact": "不支持则 VLC 多窗口、停靠、画中画等桌面交互无法正常运行", "source": "references/harmony-pc-capabilities.json#gui.wm"},
        {"id": "ta:desktop_integration", "capability": "文件对话框 / 系统托盘 / 拖拽剪贴板 / HiDPI", "required": True, "target_status": "unknown", "impact": "VLC 桌面集成体验依赖这些子能力；缺失需重写相关模块", "source": "references/harmony-pc-capabilities.json#desktop_integration"},
        {"id": "ta:opengl_es", "capability": "OpenGL ES / EGL", "required": True, "target_status": "partial", "impact": "视频渲染迁移到 GLES/EGL 的基础；partial 表示部分扩展/版本待核实", "source": "references/harmony-pc-capabilities.json#graphics_3d.opengl"},
        {"id": "ta:ffmpeg", "capability": "FFmpeg 生态在鸿蒙 PC 可移植", "required": True, "target_status": "unknown", "impact": "VLC 编解码核心依赖 FFmpeg；unknown 表示需额外验证或替换为 @ohos.multimedia", "source": "references/harmony-pc-capabilities.json#media.video_codec"},
        {"id": "ta:audio_io", "capability": "音频 I/O 后端（ALSA/PulseAudio 等价）", "required": True, "target_status": "unknown", "impact": "不支持则音频输出需重写为 @ohos.multimedia.audio", "source": "references/harmony-pc-capabilities.json#media.audio_io"},
        {"id": "ta:ohos_multimedia", "capability": "@ohos.multimedia 系统媒体能力", "required": True, "target_status": "available", "impact": "可作为 FFmpeg/平台后端的替代路径", "source": "references/harmony-pc-capabilities.json#media.ohos_multimedia"},
        {"id": "ta:desktop_app", "capability": "传统桌面应用交付形态（非仅 ArkTS .hap）", "required": True, "target_status": "unknown", "impact": "若鸿蒙 PC 仅支持 ArkTS HAP，则原生 Qt/C++ 应用需重新打包或重写", "source": "references/harmony-pc-capabilities.json#app_delivery.desktop_app"},
        {"id": "ta:x86_64", "capability": "x86_64 架构支持", "required": False, "target_status": "unknown", "impact": "若仅 arm64 则 x86_64 分发受限", "source": "references/harmony-pc-capabilities.json#arch.x86_64"},
        {"id": "ta:spawn", "capability": "启动外部进程（exec/posix_spawn）", "required": False, "target_status": "unknown", "impact": "rootwrap 等辅助进程受限时需改为库内实现", "source": "references/harmony-pc-capabilities.json#process_security.spawn"}
    ],
    "required_permissions": [
        {"permission": "ohos.permission.INTERNET", "reason": "网络流播放、串流、更新与在线元数据", "source_capability": "media", "harmony_status": "unknown", "evidence": ["src/network/io.c:146", "modules/access/http.c"]},
        {"permission": "读写存储", "reason": "读取本地音视频文件、保存配置、缓存与播放列表", "source_capability": "media", "harmony_status": "unknown", "evidence": ["src/config/dirs.c:41", "src/posix/dirs.c:120"]},
        {"permission": "ohos.permission.MICROPHONE", "reason": "音频采集与录制功能", "source_capability": "media", "harmony_status": "unknown", "evidence": ["modules/access/avaudiocapture.m", "modules/access/imem-access.c"]},
        {"permission": "ohos.permission.CAMERA", "reason": "视频采集功能", "source_capability": "media", "harmony_status": "unknown", "evidence": ["modules/access/avcapture.m", "modules/access/dc1394.c"]}
    ],
    "blockers": [
        {"id": "bk:audio_backends", "issue": "Linux/Windows 音频输出后端（ALSA/PulseAudio/PipeWire/WASAPI）在鸿蒙无直接等价", "severity": "major", "adaptability": "adaptable", "category": "platform_audio", "source_dimension": "native_api", "harmony_status": "replace_with_ohos", "remediation": "为鸿蒙新增基于 @ohos.multimedia.audio 的 audio_output 模块，或适配 OpenSL/OpenAL 中间层", "caused_by": ["ta:audio_io"], "manifests_as": ["ua:alsa", "ua:pulse", "ua:pipewire", "ua:wasapi"], "evidence": ["modules/audio_output/alsa.c", "modules/audio_output/pulse.c", "modules/audio_output/pipewire.c", "modules/audio_output/wasapi.c"]},
        {"id": "bk:video_display", "issue": "X11/XCB/Wayland/GLX/Direct3D 等显示栈为 Linux/Windows 专有，鸿蒙桌面窗口模型不同", "severity": "major", "adaptability": "adaptable", "category": "platform_video", "source_dimension": "native_api", "harmony_status": "replace_with_ohos", "remediation": "基于 Qt6 鸿蒙版的 QPA 窗口 + OpenGL ES/EGL 或 ArkGraphics 3D 重建视频输出模块", "caused_by": ["ta:opengl_es"], "manifests_as": ["ua:x11", "ua:wayland", "ua:d3d"], "evidence": ["modules/video_output/xcb/", "modules/video_output/wayland/", "modules/video_output/win32/"]},
        {"id": "bk:ffmpeg_ecosystem", "issue": "核心编解码依赖 FFmpeg 生态，其在鸿蒙 PC 的可用性未核实", "severity": "major", "adaptability": "partial", "category": "native_dependency", "source_dimension": "dependencies", "harmony_status": "partial", "remediation": "尝试用 OHOS NDK 交叉编译 FFmpeg 全栈；若缺失关键编解码器则回退到 @ohos.multimedia 或裁剪功能", "caused_by": ["ta:ffmpeg"], "evidence": ["modules/meson.build:204", "modules/codec/avcodec/"]},
        {"id": "bk:desktop_integration", "issue": "桌面集成（文件对话框、系统托盘、拖拽、剪贴板、HiDPI）在鸿蒙 PC 能力未核实", "severity": "major", "adaptability": "partial", "category": "desktop_integration", "source_dimension": "capability_profile", "harmony_status": "needs_ohos_equivalent", "remediation": "使用 Qt 鸿蒙版提供的桌面集成能力；缺失项改用 @ohos.filePicker / @ohos.pasteboard 等系统能力", "caused_by": ["ta:desktop_integration"], "evidence": ["modules/gui/qt/dialogs/", "share/vlc.desktop.in"]},
        {"id": "bk:optical_media", "issue": "DVD/Blu-ray/VCD 光盘读取依赖 /dev/sr0 等光学设备及 libdvdread/libdvdnav/libbluray", "severity": "major", "adaptability": "unadaptable", "category": "hardware", "source_dimension": "dependencies", "harmony_status": "unavailable", "remediation": "鸿蒙 PC 通常无光驱支持，相关模块需移除或仅保留 ISO/镜像文件支持", "evidence": ["modules/access/dvdread.c", "modules/access/dvdnav.c", "modules/access/bluray.c", "src/libvlc-module.c:907"]},
        {"id": "bk:procfs", "issue": "Linux procfs 读取在鸿蒙无等价", "severity": "minor", "adaptability": "partial", "category": "sysfs_procfs", "source_dimension": "native_api", "harmony_status": "replace_with_ohos", "remediation": "CPU/模块路径查询改用 OHOS NDK 提供的系统 API 或 Qt 接口", "manifests_as": ["ua:procfs"], "evidence": ["src/linux/dirs.c:38", "src/linux/cpu.c:104"]},
        {"id": "bk:hw_accel", "issue": "平台专有硬件加速（VAAPI/VDPAU/NVDEC/DXVA）无法直接移植", "severity": "major", "adaptability": "partial", "category": "hardware", "source_dimension": "native_api", "harmony_status": "replace_with_ohos", "remediation": "禁用专有硬件解码模块，改用 @ohos.multimedia 系统解码或鸿蒙 GPU 通用计算接口", "manifests_as": ["ua:vaapi", "ua:vdpau", "ua:nvdec"], "evidence": ["modules/hw/vaapi/", "modules/hw/vdpau/", "modules/hw/nvdec/"]}
    ],
    "compatible": [
        {"aspect": "标准 C/C++ 核心与算法逻辑", "note": "libvlccore、播放器控制、同步逻辑等不依赖平台 API 的部分可直接用 OHOS NDK 重编", "evidence": ["src/", "lib/"]},
        {"aspect": "已鸿蒙化的通用依赖", "note": "zlib、libgcrypt、freetype2、fontconfig、fribidi、harfbuzz、libdrm、libarchive、microdns、libpng、libjpeg-turbo 已有 OpenHarmony PC 预编译包", "evidence": ["meson.build:170", "modules/misc/meson.build:84", "modules/text_renderer/meson.build"]},
        {"aspect": "Qt6 界面层", "note": "参考文件称 Qt 已在鸿蒙 PC 可用，为主界面移植提供基础", "evidence": ["modules/gui/qt/meson.build:14", "references/harmony-pc-capabilities.json#gui.qt"]}
    ],
    "key_tasks": [
        "用 OHOS NDK 交叉编译 libvlccore、libvlc 及不依赖专有平台的模块",
        "为鸿蒙实现基于 Qt6 的 GUI 模块，验证桌面窗口/对话框/托盘/拖拽能力",
        "新增基于 @ohos.multimedia.audio 的音频输出模块，替换 ALSA/PulseAudio/PipeWire/WASAPI",
        "新增基于 OpenGL ES/EGL 或 ArkGraphics 3D 的视频输出模块，替换 X11/Wayland/Direct3D",
        "评估并移植/替换 FFmpeg 生态，确保核心编解码可用",
        "移除或禁用 DVD/Blu-ray 光驱、VAAPI/VDPAU/NVDEC/DXVA 等专有硬件模块",
        "处理 /proc、环境变量、文件路径等 Linux/Windows 假设，适配鸿蒙 POSIX 子集",
        "申请 INTERNET、存储、麦克风、摄像头等鸿蒙权限，适配沙箱文件访问模型"
    ],
    "notes": "评估按 HarmonyOS PC 桌面应用口径（模型 C）进行。Qt6 目标能力状态为 available 是积极信号，但大量桌面集成、音频 I/O、视频编解码生态目标状态为 unknown，导致整体置信度降至 medium。若最终目标仅为将 libVLC 作为库移植供 ArkTS 应用调用（模型 B），则需额外通过 Node-API 封装，工作量与约束更严苛。"
}

report["meta"] = {
    "schema_version": "1.0",
    "analyzer": "pc-lib-analyzer",
    "counter_tool": metrics["code_metrics"]["tool"],
    "confidence_overall": "medium",
    "warnings": [
        "仓库为 shallow clone，未包含完整 git 历史；bindings/ 目录在当前 shallow checkout 中不存在（README 提到的 C++/Python/C# 绑定位于独立仓库）。",
        "harmony_adapted.js 对 Qt6 的精确包名未返回已适配结果，但 references/harmony-pc-capabilities.json 中 Qt 能力状态为 available；dim-9 评估以目标能力文件为准。"
    ],
    "observations": [
        {"dimension": "function_summary", "field": "kind", "kind": "new_value", "value": "application_with_embeddable_engine", "rationale": "VLC 既是终端用户启动的播放器（application），也对外提供 libVLC 引擎；报告按 application 定级，但 categories 同时体现引擎能力。"},
        {"dimension": "dependencies", "field": "acquisition", "kind": "new_value", "value": "contrib_build_system", "rationale": "VLC 通过 extras/tools 与 contrib/ 构建系统为缺失依赖自动下载源码并构建，介于 vendored 与 download_build 之间，现有 acquisition 词表未完全覆盖。"},
        {"dimension": "native_api", "field": "category", "kind": "ambiguity", "value": "audio_output_as_platform", "rationale": "ALSA/PulseAudio/WASAPI 等音频后端既是平台 API（换平台即没有），也可视为硬件/设备访问；本报告统一归为 platform。"},
        {"dimension": "harmony_adaptation", "field": "recommended_path", "kind": "new_value", "value": "qt_ohos_rebuild", "rationale": "对于 Qt 桌面应用移植鸿蒙，推荐路径为基于 Qt 鸿蒙版重编并重写平台后端，现有 recommended_path 推荐值未直接覆盖。"}
    ]
}

# Write report
with open(REPORT_PATH, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"Wrote {REPORT_PATH}")
