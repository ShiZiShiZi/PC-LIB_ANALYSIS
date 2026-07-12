#!/usr/bin/env python3
import json
from pathlib import Path

RUN = Path('runs/pc-lib-3456/gstreamer/2026-07-03T13-34-52-216Z')
deps = json.loads((RUN / 'blocks/dependencies.json').read_text())

# Statuses from harmony_adapted.js (short names)
status = {
    'glib': True,
    'libffi': True,
    'zlib': True,
    'x11': True,
    'libdrm': True,
    'cairo': True,
    'pango': True,
    'gtk3': True,
    'openssl': True,
    'libcrypto': True,
    'libcurl': True,
    'flac': True,
    'ogg': True,
    'vorbis': True,
    'theora': True,
    'opus': True,
    'vpx': True,
    'x264': True,
    'openh264': True,
    'aom': True,
    'dav1d': True,
    'libpng': True,
    'libjpeg': True,
    'libwebp': True,
    'lcms2': True,
    'speex': True,
    'wavpack': True,
    'libxml2': True,
    'json-glib': True,
    'libsoup': True,
    'libusb': True,
    'opencv': True,
    'ffmpeg': True,
    # explicitly false / unknown
    'gobject': False,
    'gmodule': False,
    'gio': False,
    'libintl': False,
    'orc': False,
    'alsa': False,
    'pulse': False,
    'v4l2': False,
    'wayland': False,
    'opengl': False,
    'egl': False,
    'glesv2': False,
    'vulkan': False,
    'libva': False,
    'qt5': False,
    'qt6': False,
    'srt': False,
    'librtmp': False,
    'nice': False,
    'libsrtp2': False,
    'webrtc-audio-processing': False,
    'x265': False,
    'mp3lame': False,
    'twolame': False,
    'soundtouch': False,
    'taglib': False,
    'bluez': False,
    'onnxruntime': False,
    'tensorflow-lite': False,
    'graphene': False,
    'librsvg': False,
    'wayland-protocols': False,
}
source = "OpenHarmony PC C/C++ 预编译包 (gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs)"

# Mapping of dep names to short lookup keys
def lookup(name):
    # part of glib
    if name in ('glib-2.0','gobject-2.0','gmodule-no-export-2.0','gio-2.0','gio-unix-2.0','gio-windows-2.0'):
        return 'glib'
    if name == 'libffi': return 'libffi'
    if name == 'proxy-libintl': return 'libintl'
    if name == 'zlib': return 'zlib'
    if name == 'orc-0.4': return 'orc'
    if name.startswith('libav'): return 'ffmpeg'
    if name == 'x264': return 'x264'
    if name == 'x265': return 'x265'
    if name == 'openh264': return 'openh264'
    if name == 'aom': return 'aom'
    if name == 'dav1d': return 'dav1d'
    if name == 'vpx': return 'vpx'
    if name == 'opus': return 'opus'
    if name == 'flac': return 'flac'
    if name == 'ogg': return 'ogg'
    if name in ('vorbis','vorbisenc'): return 'vorbis'
    if name in ('theora','theoradec','theoraenc'): return 'theora'
    if name == 'mp3lame': return 'mp3lame'
    if name == 'twolame': return 'twolame'
    if name == 'wavpack': return 'wavpack'
    if name == 'speex': return 'speex'
    if name.startswith('soundtouch'): return 'soundtouch'
    if name == 'taglib': return 'taglib'
    if name == 'libpng': return 'libpng'
    if name == 'libjpeg': return 'libjpeg'
    if name == 'libwebp' or name == 'libwebpmux': return 'libwebp'
    if name == 'lcms2': return 'lcms2'
    if name == 'librsvg-2.0': return 'librsvg'
    if name.startswith('graphene'): return 'graphene'
    if name == 'alsa': return 'alsa'
    if name == 'libpulse': return 'pulse'
    if name == 'libv4l2': return 'v4l2'
    if name in ('x11','xv','x11-xcb','xext','xi','xfixes','xdamage','xtst'): return 'x11'
    if name.startswith('wayland'): return 'wayland'
    if name in ('opengl','glx'): return 'opengl'
    if name == 'egl': return 'egl'
    if name == 'glesv2': return 'glesv2'
    if name == 'vulkan': return 'vulkan'
    if name == 'libdrm': return 'libdrm'
    if name in ('libva','libva-drm','libva-win32'): return 'libva'
    if name in ('cairo','cairo-gobject','cairo-png'): return 'cairo'
    if name in ('pango','pangocairo'): return 'pango'
    if name.startswith('gtk+-'): return 'gtk3'
    if name == 'qt5': return 'qt5'
    if name == 'qt6': return 'qt6'
    if name in ('openssl','libcrypto'): return 'openssl' if name=='openssl' else 'libcrypto'
    if name == 'libcurl': return 'libcurl'
    if name == 'libssh2': return 'libcurl'  # same availability roughly
    if name == 'srt': return 'srt'
    if name == 'librtmp': return 'librtmp'
    if name == 'nice': return 'nice'
    if name == 'libsrtp2': return 'libsrtp2'
    if name.startswith('webrtc-audio-processing'): return 'webrtc-audio-processing'
    if name in ('libsoup-2.4','libsoup-3.0'): return 'libsoup'
    if name == 'libxml-2.0': return 'libxml2'
    if name == 'json-glib-1.0': return 'json-glib'
    if name == 'libusb-1.0': return 'libusb'
    if name == 'bluez': return 'bluez'
    if name in ('opencv','opencv4'): return 'opencv'
    if name == 'libonnxruntime': return 'onnxruntime'
    if name == 'tensorflow-lite': return 'tensorflow-lite'
    if name == 'DirectX-Headers': return None
    if name == 'DirectXMath': return None
    return None

adapted_count = 0
for e in deps['dependencies']:
    key = lookup(e['name'])
    if key is not None and key in status:
        e['harmony_adapted'] = status[key]
        if status[key]:
            e['harmony_adapted_source'] = source
        else:
            e['harmony_adapted_source'] = None
        adapted_count += 1
    else:
        e['harmony_adapted'] = None
        e['harmony_adapted_source'] = None

(RUN / 'blocks/dependencies.json').write_text(json.dumps(deps, indent=2, ensure_ascii=False))
print(f'Stamped {adapted_count} entries')
