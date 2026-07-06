#!/usr/bin/env python3
import json
from pathlib import Path

RUN = Path('runs/pc-lib-3456/gstreamer/2026-07-03T13-34-52-216Z')

native = {
    "summary": "GStreamer 核心跨平台并大量依赖 GLib；平台/系统耦合主要集中在音视频采集渲染插件（V4L2/OSS/ALSA/PulseAudio/X11/Wayland/Win32/CoreAudio/AVFoundation）与 GPU 加速路径（OpenGL/EGL/Vulkan/D3D11/D3D12/CUDA）。",
    "groups": [
        {
            "type": "glib",
            "category": "standard",
            "platform": "portable",
            "apis": [
                {"name": "g_module_open", "purpose": "加载插件或外部动态库", "count": 30, "evidence": ["subprojects/gstreamer/gst/gstplugin.c:879", "subprojects/gstreamer/gst/gst.c:632", "subprojects/gst-plugins-bad/gst-libs/gst/cuda/gstcudaloader.cpp:41"]},
                {"name": "g_module_symbol", "purpose": "从模块获取导出符号", "count": 10, "evidence": ["subprojects/gstreamer/gst/gstplugin.c:902", "subprojects/gstreamer/gst/gst.c:635"]},
                {"name": "g_module_close", "purpose": "关闭动态模块", "count": 10, "evidence": ["subprojects/gstreamer/gst/gstplugin.c:921", "subprojects/gstreamer/gst/gst.c:639"]},
                {"name": "g_object_new", "purpose": "实例化 GObject/Gst 对象", "count": 100, "evidence": ["subprojects/gstreamer/gst/gstelementfactory.c:819", "subprojects/gstreamer/gst/gstpipeline.c:347"]},
                {"name": "g_main_loop_run", "purpose": "运行 GLib 主事件循环", "count": 20, "evidence": ["subprojects/gstreamer/tools/gst-launch.c"]}
            ]
        },
        {
            "type": "posix",
            "category": "platform",
            "platform": "posix",
            "apis": [
                {"name": "mmap", "purpose": "V4L2/OSS 等视频/音频缓冲区映射", "count": 15, "evidence": ["subprojects/gst-plugins-good/sys/v4l2/gstv4l2object.c:659", "subprojects/gst-plugins-good/sys/v4l2/gstv4l2allocator.c:851"], "conditional": True},
                {"name": "munmap", "purpose": "释放映射的缓冲区", "count": 10, "evidence": ["subprojects/gst-plugins-good/sys/v4l2/gstv4l2allocator.c:404"], "conditional": True},
                {"name": "pthread_mutex_lock", "purpose": "原生互斥锁（validate fault injection 等）", "count": 8, "evidence": ["subprojects/gst-devtools/validate/plugins/fault_injection/socket_interposer.c:86"], "conditional": True},
                {"name": "pthread_mutex_unlock", "purpose": "释放原生互斥锁", "count": 8, "evidence": ["subprojects/gst-devtools/validate/plugins/fault_injection/socket_interposer.c:99"], "conditional": True},
                {"name": "socket", "purpose": "创建 Unix/AF_INET 套接字", "count": 10, "evidence": ["subprojects/gst-plugins-bad/sys/shm/shmpipe.c:209", "subprojects/gst-plugins-bad/sys/dvb/camswclient.c:90", "subprojects/gst-plugins-bad/ext/festival/gstfestival.c:359"], "conditional": True},
                {"name": "poll", "purpose": "I/O 多路复用", "count": 10, "evidence": ["subprojects/gstreamer/gst/gstpoll.c:1488", "subprojects/gst-plugins-good/ext/raw1394/gsthdv1394src.c:387"], "conditional": True},
                {"name": "ppoll", "purpose": "高精度 I/O 多路复用", "count": 2, "evidence": ["subprojects/gstreamer/gst/gstpoll.c:1468"], "conditional": True}
            ]
        },
        {
            "type": "linux_ioctl",
            "category": "system",
            "platform": "linux",
            "apis": [
                {"name": "ioctl", "purpose": "V4L2/OSS/DMA-BUF 设备控制", "count": 200, "evidence": ["subprojects/gst-plugins-good/sys/v4l2/gstv4l2object.c:951", "subprojects/gst-plugins-base/gst-libs/gst/allocators/gstdmabuf.c:72", "subprojects/gst-plugins-base/gst-libs/gst/video/gstvideodmabufpool.c:106", "subprojects/gst-plugins-good/sys/oss4/oss4-audio.c:606"], "conditional": True}
            ]
        },
        {
            "type": "linux_syscall",
            "category": "system",
            "platform": "linux",
            "apis": [
                {"name": "futex", "purpose": "GstSystemClock 条件变量等待/唤醒", "count": 6, "evidence": ["subprojects/gstreamer/gst/gstsystemclock.c:261", "subprojects/gstreamer/gst/gstsystemclock.c:279"], "conditional": True},
                {"name": "syscall(SYS_gettid)", "purpose": "获取当前线程 ID 用于日志", "count": 1, "evidence": ["subprojects/gstreamer/gst/gstinfo.c:1842"], "conditional": True},
                {"name": "syscall(SYS_getrandom)", "purpose": "PTP 助手获取随机数", "count": 1, "evidence": ["subprojects/gstreamer/libs/gst/helpers/ptp/rand.rs:36"], "conditional": True}
            ]
        },
        {
            "type": "linux_pseudofs",
            "category": "system",
            "platform": "linux",
            "apis": [
                {"name": "procfs (/proc/self/exe)", "purpose": "读取自身可执行文件路径", "count": 1, "evidence": ["subprojects/gstreamer/gst/gst.c:322"], "conditional": True},
                {"name": "procfs (/proc/sndstat, /proc/asound/sndstat)", "purpose": "OSS 音频设备枚举", "count": 2, "evidence": ["subprojects/gst-plugins-good/sys/oss/gstossdeviceprovider.c:95"], "conditional": True},
                {"name": "procfs (/proc/mounts)", "purpose": "读取挂载点以定位 configfs", "count": 1, "evidence": ["subprojects/gst-plugins-bad/sys/uvcgadget/configfs.c:417"], "conditional": True},
                {"name": "sysfs (/sys/class/drm)", "purpose": "Intel QSV/VPL GPU 设备识别", "count": 2, "evidence": ["subprojects/gst-plugins-bad/sys/qsv/libmfx/dispatcher/vpl/mfx_dispatcher_vpl_msdk.cpp:518"], "conditional": True},
                {"name": "sysfs (/sys/class/udc)", "purpose": "UVC gadget 设备枚举", "count": 2, "evidence": ["subprojects/gst-plugins-bad/sys/uvcgadget/configfs.c:237"], "conditional": True}
            ]
        },
        {
            "type": "win32",
            "category": "platform",
            "platform": "windows",
            "apis": [
                {"name": "LoadLibraryW", "purpose": "Windows 插件加载 / 解析 kernel32 函数", "count": 5, "evidence": ["subprojects/gstreamer/gst/gstplugin.c:774", "subprojects/gstreamer/gst/gsttask.c:171"], "conditional": True},
                {"name": "GetProcAddress", "purpose": "获取 SetThreadDescription 等函数指针", "count": 3, "evidence": ["subprojects/gstreamer/gst/gsttask.c:174"], "conditional": True},
                {"name": "FreeLibrary", "purpose": "释放动态加载的模块", "count": 2, "evidence": ["subprojects/gstreamer/gst/gsttask.c:177"], "conditional": True},
                {"name": "RaiseException", "purpose": "传统方式设置线程名", "count": 1, "evidence": ["subprojects/gstreamer/gst/gsttask.c:157"], "conditional": True}
            ]
        },
        {
            "type": "apple",
            "category": "platform",
            "platform": "macos",
            "apis": [
                {"name": "AVFoundation", "purpose": "macOS/iOS 音视频采集/编码", "count": 1, "evidence": ["subprojects/gst-plugins-bad/sys/applemedia/meson.build"], "conditional": True},
                {"name": "CoreMedia", "purpose": "Core Media 缓冲与格式", "count": 1, "evidence": ["subprojects/gst-plugins-bad/sys/applemedia/meson.build"], "conditional": True},
                {"name": "CoreVideo", "purpose": "视频缓冲管理", "count": 1, "evidence": ["subprojects/gst-plugins-bad/sys/applemedia/meson.build"], "conditional": True},
                {"name": "VideoToolbox", "purpose": "硬件编解码", "count": 1, "evidence": ["subprojects/gst-plugins-bad/sys/applemedia/meson.build"], "conditional": True},
                {"name": "IOSurface", "purpose": "GPU 共享表面", "count": 1, "evidence": ["subprojects/gst-plugins-bad/sys/applemedia/meson.build"], "conditional": True},
                {"name": "Metal", "purpose": "Metal GPU 纹理/Vulkan 互操作", "count": 1, "evidence": ["subprojects/gst-plugins-bad/sys/applemedia/meson.build", "subprojects/gst-plugins-bad/sys/applemedia/videotexturecache-vulkan.mm:25"], "conditional": True}
            ]
        },
        {
            "type": "opengl",
            "category": "hardware",
            "platform": "portable",
            "apis": [
                {"name": "glGenTextures", "purpose": "生成 OpenGL 纹理", "count": 5, "evidence": ["subprojects/gst-plugins-good/sys/osxvideo/cocoawindow.m:456", "subprojects/gst-plugins-base/gst-libs/gst/gl/gstglcontext.c:106"]},
                {"name": "glBindTexture", "purpose": "绑定纹理", "count": 10, "evidence": ["subprojects/gst-plugins-good/sys/osxvideo/cocoawindow.m:464", "subprojects/gst-plugins-good/sys/osxvideo/cocoawindow.m:503"]},
                {"name": "glTexImage2D", "purpose": "上传 2D 纹理数据", "count": 5, "evidence": ["subprojects/gst-plugins-good/sys/osxvideo/cocoawindow.m:486"]},
                {"name": "glTexSubImage2D", "purpose": "更新子区域纹理", "count": 5, "evidence": ["subprojects/gst-plugins-good/sys/osxvideo/cocoawindow.m:509"]},
                {"name": "glClear", "purpose": "清除帧缓冲", "count": 5, "evidence": ["subprojects/gst-plugins-good/sys/osxvideo/cocoawindow.m:546"]},
                {"name": "glViewport", "purpose": "设置视口", "count": 5, "evidence": ["subprojects/gst-plugins-good/sys/osxvideo/cocoawindow.m:548"]}
            ]
        },
        {
            "type": "egl",
            "category": "hardware",
            "platform": "portable",
            "apis": [
                {"name": "eglGetDisplay", "purpose": "获取 EGL 显示连接", "count": 5, "evidence": ["subprojects/gst-plugins-base/gst-libs/gst/gl/egl/gstglcontext_egl.c:1342"]},
                {"name": "eglInitialize", "purpose": "初始化 EGL", "count": 5, "evidence": ["subprojects/gst-plugins-base/gst-libs/gst/gl/gbm/gstglwindow_gbm_egl.c:325"]},
                {"name": "eglCreateContext", "purpose": "创建 EGL 上下文", "count": 5, "evidence": ["subprojects/gst-plugins-base/gst-libs/gst/gl/egl/gstglcontext_egl.c"]},
                {"name": "eglMakeCurrent", "purpose": "绑定 EGL 上下文", "count": 5, "evidence": ["subprojects/gst-plugins-base/gst-libs/gst/gl/egl/gstglcontext_egl.c"]},
                {"name": "eglSwapBuffers", "purpose": "交换 EGL 缓冲", "count": 5, "evidence": ["subprojects/gst-plugins-base/gst-libs/gst/gl/gbm/gstglwindow_gbm_egl.c:215"]}
            ]
        },
        {
            "type": "vulkan",
            "category": "hardware",
            "platform": "portable",
            "apis": [
                {"name": "vkCreateInstance", "purpose": "创建 Vulkan 实例", "count": 2, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/vulkan/gstvkinstance.c"]},
                {"name": "vkEnumeratePhysicalDevices", "purpose": "枚举物理设备", "count": 5, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/vulkan/gstvkphysicaldevice.c:1168"]},
                {"name": "vkCreateDevice", "purpose": "创建逻辑设备", "count": 2, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/vulkan/gstvkdevice.c:29"]},
                {"name": "vkCreateCommandPool", "purpose": "创建命令池", "count": 3, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/vulkan/gstvkqueue.c:138"]},
                {"name": "vkBeginCommandBuffer", "purpose": "开始命令缓冲记录", "count": 5, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/vulkan/gstvkswapper.c:1070"]},
                {"name": "vkCmdPipelineBarrier", "purpose": "插入管线屏障", "count": 10, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/vulkan/gstvkswapper.c:1092"]},
                {"name": "vkQueueSubmit", "purpose": "提交命令队列", "count": 5, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/vulkan/gstvkswapper.c:1346"]}
            ]
        },
        {
            "type": "direct3d",
            "category": "hardware",
            "platform": "windows",
            "apis": [
                {"name": "D3D11CreateDevice", "purpose": "创建 D3D11 设备与上下文", "count": 8, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/d3d11/gstd3d11device.cpp:1110"], "conditional": True},
                {"name": "D3D12CreateDevice", "purpose": "创建 D3D12 设备", "count": 3, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/d3d12/gstd3d12device.cpp:1217"], "conditional": True},
                {"name": "CreateDXGIFactory1/2", "purpose": "枚举 DXGI 适配器", "count": 5, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/d3d12/gstd3d12device.cpp:1198", "subprojects/gst-plugins-bad/gst-libs/gst/cuda/gstcudacontext.cpp:319"], "conditional": True}
            ]
        },
        {
            "type": "cuda",
            "category": "hardware",
            "platform": "portable",
            "apis": [
                {"name": "cuInit", "purpose": "初始化 CUDA 驱动", "count": 3, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/hip/gsthiploader.cpp:431", "subprojects/gst-plugins-bad/gst-libs/gst/hip/gsthiploader.cpp:496"]},
                {"name": "cuDeviceGetAttribute", "purpose": "查询 CUDA 设备属性", "count": 5, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/hip/gsthiploader.cpp:887"]},
                {"name": "cuModuleLoadData", "purpose": "加载 CUDA 模块", "count": 2, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/hip/gsthiploader.cpp:1081"]},
                {"name": "cuLaunchKernel", "purpose": "启动 CUDA kernel", "count": 2, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/hip/gsthiploader.cpp:1126"]},
                {"name": "cuTexObjectCreate", "purpose": "创建 CUDA 纹理对象", "count": 2, "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/hip/gsthiploader.cpp:1208"]}
            ]
        }
    ],
    "dynamic_libraries": [
        {
            "name": "libgst*.so / gst*.dll",
            "mechanism": "g_module_open (dlopen / LoadLibraryW)",
            "acquisition": "self_build",
            "source": "本仓构建的 GStreamer 插件（.so/.dll）",
            "description": "GStreamer 核心通过插件扫描器运行时加载各插件",
            "optional": False,
            "evidence": ["subprojects/gstreamer/gst/gstplugin.c:879", "subprojects/gstreamer/gst/gstplugin.c:774"]
        },
        {
            "name": "libGL.so.1 / opengl32.dll",
            "mechanism": "g_module_open",
            "acquisition": "system",
            "source": "系统 OpenGL 驱动",
            "description": "OpenGL 视频转换/渲染上下文",
            "optional": True,
            "evidence": ["subprojects/gst-plugins-base/gst-libs/gst/gl/gstglcontext.c:106", "subprojects/gst-plugins-base/gst-libs/gst/gl/gstglcontext.c:113"]
        },
        {
            "name": "libEGL.so.1",
            "mechanism": "g_module_open",
            "acquisition": "system",
            "source": "系统 EGL 库",
            "description": "EGL 显示与上下文管理",
            "optional": True,
            "evidence": ["subprojects/gst-plugins-base/gst-libs/gst/gl/egl/gstglcontext_egl.c:1342"]
        },
        {
            "name": "libGLESv2.so.2",
            "mechanism": "g_module_open",
            "acquisition": "system",
            "source": "系统 OpenGL ES 驱动",
            "description": "OpenGL ES 2.0 渲染上下文",
            "optional": True,
            "evidence": ["subprojects/gst-plugins-base/gst-libs/gst/gl/gstglcontext.c:134"]
        },
        {
            "name": "libcuda.so.1 / nvcuda.dll",
            "mechanism": "g_module_open",
            "acquisition": "system",
            "source": "NVIDIA CUDA 驱动",
            "description": "CUDA 驱动 API 动态加载",
            "optional": True,
            "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/cuda/gstcudaloader.cpp:41", "subprojects/gst-plugins-bad/gst-libs/gst/hip/gsthiploader.cpp:296"]
        },
        {
            "name": "libcudart.so",
            "mechanism": "g_module_open",
            "acquisition": "system",
            "source": "NVIDIA CUDA 运行时",
            "description": "CUDA 运行时 API 动态加载",
            "optional": True,
            "evidence": ["subprojects/gst-plugins-bad/gst-libs/gst/hip/gsthiploader.cpp:333"]
        },
        {
            "name": "dbghelp.dll",
            "mechanism": "g_module_open",
            "acquisition": "system",
            "source": "Windows 调试帮助库",
            "description": "堆栈回溯与符号解析",
            "optional": True,
            "evidence": ["subprojects/gstreamer/gst/gstinfo.c:4280"]
        },
        {
            "name": "kernel32.dll",
            "mechanism": "LoadLibraryW",
            "acquisition": "system",
            "source": "Windows 核心库",
            "description": "运行时获取 SetThreadDescription",
            "optional": True,
            "evidence": ["subprojects/gstreamer/gst/gsttask.c:171"]
        },
        {
            "name": "gstreamer-1.0-0.dll",
            "mechanism": "P/Invoke (DllImport)",
            "acquisition": "self_build",
            "source": "本仓 C 核心库",
            "description": "C# 绑定调用 GStreamer C API",
            "optional": False,
            "evidence": ["subprojects/gstreamer-sharp/sources/generated/Gst/Bus.cs:16"]
        }
    ],
    "platform_dependence": "mixed"
}

(RUN / 'blocks/native_api.json').write_text(json.dumps(native, indent=2, ensure_ascii=False))
print('Wrote native_api.json')
