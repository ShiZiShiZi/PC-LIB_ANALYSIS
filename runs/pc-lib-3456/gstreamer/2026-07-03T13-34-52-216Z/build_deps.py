#!/usr/bin/env python3
"""Generate dependencies.json for GStreamer with curated major deps."""
import json, os
from pathlib import Path

ROOT = Path('repos/pc-lib-3456/gstreamer')
RUN = Path('runs/pc-lib-3456/gstreamer/2026-07-03T13-34-52-216Z')
raw = json.loads((RUN / 'meson_deps_raw.json').read_text())

# map name -> list of declared_in files
decl = {}
for r in raw:
    decl.setdefault(r['name'], []).append(r['file'])

subprojects = {p.name for p in (ROOT / 'subprojects').glob('*.wrap')}

def has_wrap(name):
    # map common pkg-config names to wrap filenames
    candidates = [name, name.replace('-', '_'), name.replace('.', '-')]
    for c in candidates:
        if f'{c}.wrap' in subprojects:
            return True
    # known mappings
    known = {
        'glib-2.0':'glib.wrap', 'gobject-2.0':'glib.wrap', 'gmodule-no-export-2.0':'glib.wrap',
        'gio-2.0':'glib.wrap', 'gio-unix-2.0':'glib.wrap', 'gio-windows-2.0':'glib.wrap',
        'gstreamer':'gstreamer.wrap', 'gst-plugins-base':'gst-plugins-base.wrap',
        'ffmpeg':'FFmpeg.wrap', 'libavcodec':'FFmpeg.wrap', 'libavformat':'FFmpeg.wrap',
        'libavutil':'FFmpeg.wrap', 'libavfilter':'FFmpeg.wrap',
        'libpng':'libpng.wrap', 'libjpeg':'libjpeg-turbo.wrap',
        'libjpeg-turbo':'libjpeg-turbo.wrap', 'json-glib-1.0':'json-glib.wrap',
        'libsoup-2.4':'libsoup.wrap', 'libsoup-3.0':'libsoup.wrap',
        'orc-0.4':'orc.wrap', 'soundtouch-1.0':'soundtouch.wrap',
    }
    if name in known:
        return known[name] in subprojects
    return False

def acq_locality(name):
    if name in ['m','rt','socket','nsl','atomic','dl','execinfo','pthread','log','Threads','threads']:
        return 'system', 'system'
    if has_wrap(name):
        return 'meson_subproject', 'remote'
    return 'system', 'system'

# Curated list: (name, ecosystem, scope, purpose)
curated = [
    # core / mandatory
    ('glib-2.0', 'cpp', 'runtime', 'GStreamer 核心对象与事件循环基础库'),
    ('gobject-2.0', 'cpp', 'runtime', 'GLib 对象系统，GstObject/GstElement 基类'),
    ('gmodule-no-export-2.0', 'cpp', 'runtime', '模块加载支持，插件扫描'),
    ('gio-2.0', 'cpp', 'runtime', 'I/O 与网络抽象'),
    ('gio-unix-2.0', 'cpp', 'runtime', 'Unix 特定的 GIO 后端（fd 传递等）'),
    ('gio-windows-2.0', 'cpp', 'runtime', 'Windows 特定的 GIO 后端'),
    ('zlib', 'cpp', 'runtime', '压缩/解压支持'),
    ('libffi', 'cpp', 'runtime', 'FFI 调用支持（GObject 闭包等）'),
    ('proxy-libintl', 'cpp', 'runtime', '国际化 gettext 支持'),
    ('m', 'cpp', 'runtime', '数学库'),
    ('rt', 'cpp', 'runtime', 'POSIX realtime（timer/clock_gettime）'),
    ('dl', 'cpp', 'runtime', 'dladdr 等动态链接信息'),
    ('atomic', 'cpp', 'runtime', 'C11 原子操作链接库'),
    ('orc-0.4', 'cpp', 'optional', '运行时编译器，优化音视频处理循环'),
    ('bash-completion', 'other', 'optional', 'bash 命令补全数据'),
    ('gobject-introspection-1.0', 'other', 'build', '生成 GObject 内省元数据'),
    # media codecs / container
    ('libavcodec', 'cpp', 'optional', 'FFmpeg 音视频解码/编码'),
    ('libavformat', 'cpp', 'optional', 'FFmpeg 容器格式复用/解复用'),
    ('libavutil', 'cpp', 'optional', 'FFmpeg 通用工具库'),
    ('libavfilter', 'cpp', 'optional', 'FFmpeg 滤镜图'),
    ('x264', 'cpp', 'optional', 'H.264 视频编码器'),
    ('x265', 'cpp', 'optional', 'HEVC/H.265 视频编码器'),
    ('openh264', 'cpp', 'optional', 'Cisco OpenH264 H.264 编解码器'),
    ('aom', 'cpp', 'optional', 'AV1 编解码器'),
    ('dav1d', 'cpp', 'optional', 'AV1 解码器'),
    ('vpx', 'cpp', 'optional', 'VP8/VP9 编解码器'),
    ('opus', 'cpp', 'optional', 'Opus 音频编解码器'),
    ('flac', 'cpp', 'optional', 'FLAC 无损音频'),
    ('ogg', 'cpp', 'optional', 'Ogg 容器'),
    ('vorbis', 'cpp', 'optional', 'Vorbis 音频'),
    ('vorbisenc', 'cpp', 'optional', 'Vorbis 音频编码'),
    ('theora', 'cpp', 'optional', 'Theora 视频'),
    ('mp3lame', 'cpp', 'optional', 'MP3 音频编码'),
    ('twolame', 'cpp', 'optional', 'MP2 音频编码'),
    ('wavpack', 'cpp', 'optional', 'WavPack 无损音频'),
    ('speex', 'cpp', 'optional', 'Speex 语音编解码器'),
    ('soundtouch', 'cpp', 'optional', '音频 pitch/tempo 处理'),
    ('taglib', 'cpp', 'optional', '音频文件元数据解析'),
    ('libcdio', 'cpp', 'optional', 'CD 音频读取'),
    ('cdparanoia-3', 'cpp', 'optional', 'CD 音轨抓取'),
    # network / streaming
    ('libsoup-2.4', 'cpp', 'optional', 'HTTP 客户端/服务器'),
    ('libsoup-3.0', 'cpp', 'optional', '新版 libsoup HTTP'),
    ('libcurl', 'cpp', 'optional', 'HTTP/FTP 传输'),
    ('libssh2', 'cpp', 'optional', 'SFTP 传输'),
    ('srt', 'cpp', 'optional', 'SRT 可靠流媒体传输'),
    ('librtmp', 'cpp', 'optional', 'RTMP 推/拉流'),
    ('nice', 'cpp', 'optional', 'ICE/STUN/TURN 网络穿透'),
    ('libsrtp2', 'cpp', 'optional', 'SRTP 加密 RTP'),
    ('webrtc-audio-processing-1', 'cpp', 'optional', 'WebRTC 音频处理'),
    ('webrtc-audio-processing-2', 'cpp', 'optional', 'WebRTC 音频处理（新版）'),
    ('google_cloud_cpp_storage', 'cpp', 'optional', 'Google Cloud Storage 上传/下载'),
    # platform audio/video capture & display
    ('alsa', 'cpp', 'optional', 'Linux ALSA 音频采集/播放'),
    ('libpulse', 'cpp', 'optional', 'PulseAudio 音频采集/播放'),
    ('libv4l2', 'cpp', 'optional', 'Video4Linux2 视频采集'),
    ('x11', 'cpp', 'optional', 'X11 窗口/显示集成'),
    ('xv', 'cpp', 'optional', 'XVideo 硬件缩放输出'),
    ('x11-xcb', 'cpp', 'optional', 'X11 XCB 绑定'),
    ('xext', 'cpp', 'optional', 'X11 扩展'),
    ('xi', 'cpp', 'optional', 'X11 输入扩展'),
    ('xfixes', 'cpp', 'optional', 'X11 修复扩展'),
    ('xdamage', 'cpp', 'optional', 'X11 损坏区域扩展'),
    ('xtst', 'cpp', 'optional', 'X11 测试/录制扩展'),
    ('wayland-client', 'cpp', 'optional', 'Wayland 客户端协议'),
    ('wayland-cursor', 'cpp', 'optional', 'Wayland 光标'),
    ('wayland-egl', 'cpp', 'optional', 'Wayland EGL 集成'),
    ('wayland-server', 'cpp', 'optional', 'Wayland 合成器服务端'),
    ('wayland-protocols', 'cpp', 'optional', 'Wayland 协议定义'),
    # graphics / 2d / 3d
    ('opengl', 'cpp', 'optional', 'OpenGL 视频转换/渲染'),
    ('egl', 'cpp', 'optional', 'EGL 窗口/上下文'),
    ('glesv2', 'cpp', 'optional', 'OpenGL ES 2.0'),
    ('glx', 'cpp', 'optional', 'X11 OpenGL 上下文'),
    ('vulkan', 'cpp', 'optional', 'Vulkan 视频处理/渲染'),
    ('libdrm', 'cpp', 'optional', 'Direct Rendering Manager'),
    ('libva', 'cpp', 'optional', 'Video Acceleration (VA-API)'),
    ('libva-drm', 'cpp', 'optional', 'VA-API DRM 后端'),
    ('cairo', 'cpp', 'optional', '2D 矢量图形绘制'),
    ('cairo-gobject', 'cpp', 'optional', 'Cairo GObject 集成'),
    ('pango', 'cpp', 'optional', '文本布局与渲染'),
    ('pangocairo', 'cpp', 'optional', 'Pango Cairo 后端'),
    ('graphene-gobject-1.0', 'cpp', 'optional', '3D/图形数学库'),
    ('gdk-pixbuf-2.0', 'cpp', 'optional', '图像加载'),
    ('librsvg-2.0', 'cpp', 'optional', 'SVG 渲染'),
    ('libpng', 'cpp', 'optional', 'PNG 图像'),
    ('libjpeg', 'cpp', 'optional', 'JPEG 图像'),
    ('libwebp', 'cpp', 'optional', 'WebP 图像'),
    ('lcms2', 'cpp', 'optional', '色彩管理'),
    # GUI toolkits / bindings
    ('gtk+-3.0', 'cpp', 'optional', 'GTK3 窗口与示例播放器'),
    ('gtk+-x11-3.0', 'cpp', 'optional', 'GTK3 X11 后端'),
    ('qt5', 'cpp', 'optional', 'Qt5 QML 视频项'),
    ('qt6', 'cpp', 'optional', 'Qt6/D3D11 视频项'),
    ('gtk-sharp-3.0', 'dotnet', 'optional', 'C# GTK# 绑定构建依赖'),
    ('pygobject-3.0', 'python', 'optional', 'Python GObject 绑定'),
    # misc / hardware / ML
    ('libxml-2.0', 'cpp', 'optional', 'XML 解析（编辑服务等）'),
    ('json-glib-1.0', 'cpp', 'optional', 'JSON 解析'),
    ('openssl', 'cpp', 'optional', 'TLS/DTLS 加密'),
    ('libcrypto', 'cpp', 'optional', 'OpenSSL 加密原语'),
    ('libusb-1.0', 'cpp', 'optional', 'USB 视频摄像机'),
    ('bluez', 'cpp', 'optional', '蓝牙 A2DP'),
    ('libopenni2', 'cpp', 'optional', 'OpenNI2 3D 深度相机'),
    ('opencv', 'cpp', 'optional', 'OpenCV 计算机视觉插件'),
    ('opencv4', 'cpp', 'optional', 'OpenCV 4 计算机视觉插件'),
    ('libonnxruntime', 'cpp', 'optional', 'ONNX 推理运行时'),
    ('tensorflow-lite', 'cpp', 'optional', 'TensorFlow Lite 推理'),
    # Windows / Apple platform-specific
    ('DirectX-Headers', 'cpp', 'optional', 'DirectX 12 头文件'),
    ('DirectXMath', 'cpp', 'optional', 'DirectXMath 数学库'),
]

source_repo_map = {
    'glib-2.0':'https://gitlab.gnome.org/GNOME/glib',
    'gobject-2.0':'https://gitlab.gnome.org/GNOME/glib',
    'gmodule-no-export-2.0':'https://gitlab.gnome.org/GNOME/glib',
    'gio-2.0':'https://gitlab.gnome.org/GNOME/glib',
    'gio-unix-2.0':'https://gitlab.gnome.org/GNOME/glib',
    'gio-windows-2.0':'https://gitlab.gnome.org/GNOME/glib',
    'zlib':'https://github.com/madler/zlib',
    'libffi':'https://github.com/libffi/libffi',
    'proxy-libintl':'https://github.com/frida/proxy-libintl',
    'orc-0.4':'https://gitlab.freedesktop.org/gstreamer/orc',
    'libavcodec':'https://git.ffmpeg.org/ffmpeg',
    'libavformat':'https://git.ffmpeg.org/ffmpeg',
    'libavutil':'https://git.ffmpeg.org/ffmpeg',
    'libavfilter':'https://git.ffmpeg.org/ffmpeg',
    'x264':'https://github.com/videolan/x264',
    'x265':'https://github.com/videolan/x265',
    'openh264':'https://github.com/cisco/openh264',
    'aom':'https://aomedia.googlesource.com/aom',
    'dav1d':'https://github.com/videolan/dav1d',
    'vpx':'https://github.com/webmproject/libvpx',
    'opus':'https://gitlab.xiph.org/xiph/opus',
    'flac':'https://github.com/xiph/flac',
    'ogg':'https://gitlab.xiph.org/xiph/ogg',
    'vorbis':'https://gitlab.xiph.org/xiph/vorbis',
    'theora':'https://gitlab.xiph.org/xiph/theora',
    'mp3lame':'https://github.com/lameproject/lame',
    'twolame':'https://github.com/njh/twolame',
    'wavpack':'https://github.com/dbry/WavPack',
    'speex':'https://gitlab.xiph.org/xiph/speex',
    'soundtouch':'https://gitlab.com/soundtouch/soundtouch',
    'taglib':'https://github.com/taglib/taglib',
    'libsoup-2.4':'https://gitlab.gnome.org/GNOME/libsoup',
    'libsoup-3.0':'https://gitlab.gnome.org/GNOME/libsoup',
    'libcurl':'https://github.com/curl/curl',
    'libssh2':'https://github.com/libssh2/libssh2',
    'srt':'https://github.com/Haivision/srt',
    'librtmp':'https://git.ffmpeg.org/rtmpdump',
    'nice':'https://gitlab.freedesktop.org/libnice/libnice',
    'libsrtp2':'https://github.com/cisco/libsrtp',
    'webrtc-audio-processing-1':'https://gitlab.freedesktop.org/pulseaudio/webrtc-audio-processing',
    'webrtc-audio-processing-2':'https://gitlab.freedesktop.org/pulseaudio/webrtc-audio-processing',
    'google_cloud_cpp_storage':'https://github.com/googleapis/google-cloud-cpp',
    'alsa':'https://github.com/alsa-project/alsa-lib',
    'libpulse':'https://gitlab.freedesktop.org/pulseaudio/pulseaudio',
    'libv4l2':'https://git.linuxtv.org/v4l-utils.git',
    'x11':'https://gitlab.freedesktop.org/xorg/lib/libx11',
    'xv':'https://gitlab.freedesktop.org/xorg/lib/libxext',
    'wayland-client':'https://gitlab.freedesktop.org/wayland/wayland',
    'opengl':'https://gitlab.freedesktop.org/mesa/mesa',
    'egl':'https://gitlab.freedesktop.org/mesa/mesa',
    'glesv2':'https://gitlab.freedesktop.org/mesa/mesa',
    'vulkan':'https://github.com/KhronosGroup/Vulkan-Loader',
    'libdrm':'https://gitlab.freedesktop.org/mesa/drm',
    'libva':'https://github.com/intel/libva',
    'cairo':'https://gitlab.freedesktop.org/cairo/cairo',
    'pango':'https://gitlab.gnome.org/GNOME/pango',
    'gdk-pixbuf-2.0':'https://gitlab.gnome.org/GNOME/gdk-pixbuf',
    'librsvg-2.0':'https://gitlab.gnome.org/GNOME/librsvg',
    'libpng':'https://github.com/glennrp/libpng',
    'libjpeg':'https://github.com/libjpeg-turbo/libjpeg-turbo',
    'libwebp':'https://github.com/webmproject/libwebp',
    'lcms2':'https://github.com/mm2/Little-CMS',
    'gtk+-3.0':'https://gitlab.gnome.org/GNOME/gtk',
    'qt5':'https://github.com/qt/qtbase',
    'qt6':'https://github.com/qt/qtbase',
    'gtk-sharp-3.0':'https://github.com/GtkSharp/GtkSharp',
    'pygobject-3.0':'https://gitlab.gnome.org/GNOME/pygobject',
    'libxml-2.0':'https://gitlab.gnome.org/GNOME/libxml2',
    'json-glib-1.0':'https://gitlab.gnome.org/GNOME/json-glib',
    'openssl':'https://github.com/openssl/openssl',
    'libusb-1.0':'https://github.com/libusb/libusb',
    'bluez':'https://git.kernel.org/pub/scm/bluetooth/bluez.git',
    'opencv':'https://github.com/opencv/opencv',
    'opencv4':'https://github.com/opencv/opencv',
    'libonnxruntime':'https://github.com/microsoft/onnxruntime',
    'tensorflow-lite':'https://github.com/tensorflow/tensorflow',
    'DirectX-Headers':'https://github.com/microsoft/DirectX-Headers',
    'DirectXMath':'https://github.com/microsoft/DirectXMath',
}

entries = []
for name, eco, scope, purpose in curated:
    files = decl.get(name, [])
    # pick a representative declared_in
    if files:
        declared_in = [files[0]]
    else:
        declared_in = ['meson.build']
    acquisition, locality = acq_locality(name)
    if acquisition == 'meson_subproject':
        source = 'Meson subproject/wrap，缺省时自动下载源码构建'
    elif locality == 'system':
        if name in ['m','rt','socket','nsl','atomic','dl','execinfo','pthread','log']:
            source = '系统 C 库 / 链接器库'
        else:
            source = '系统预装库（pkg-config/find_library）'
    else:
        source = '系统预装库（pkg-config/find_library）'
    entry = {
        'name': name,
        'ecosystem': eco,
        'scope': scope,
        'version': None,
        'purpose': purpose,
        'acquisition': acquisition,
        'locality': locality,
        'source': source,
        'declared_in': declared_in,
    }
    sr = source_repo_map.get(name)
    if sr:
        entry['source_repo'] = sr
    entries.append(entry)

by_eco = {}
for e in entries:
    by_eco.setdefault(e['ecosystem'], []).append(e['name'])

out = {
    'count': len(entries),
    'manifests': ['meson.build', 'subprojects/*.wrap', 'subprojects/gst-*/meson.build'],
    'by_ecosystem': by_eco,
    'dependencies': entries,
    'notes': 'GStreamer 插件体系庞大，本清单列出核心与主要可选依赖；大量小众/平台专用插件依赖未逐一枚举。'
}

(RUN / 'blocks/dependencies.json').write_text(json.dumps(out, indent=2, ensure_ascii=False))
print(f'Wrote {len(entries)} dependencies')
