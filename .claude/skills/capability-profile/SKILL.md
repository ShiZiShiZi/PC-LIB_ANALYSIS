---
name: capability-profile
description: Flag the HarmonyOS-adaptation-heavy scenarios a library or application touches — GUI/desktop UI, 3D rendering, media (audio/video), and hardware/device dependence — as a structured profile, by synthesizing the already-computed native_api / runtime_surface / dependencies / function_summary blocks. Use for dimension 10 of PC library/application analysis. Model synthesis; feeds dim-9.
---

# Capability profile — adaptation-heavy scenario flags (model synthesis)

A focused lens that answers **"是否涉及 GUI / 3D 渲染 / 媒体 / 特定硬件"**. These scenarios
are the ones that most strongly drive HarmonyOS-PC porting cost or infeasibility. dim-9
then turns these flags into 修改量/能否移植 (porting_class/blockers/person_days). **职责分工**：
本维度只标"是否涉及 + 涉及什么 + 鸿蒙是否支持"，**不**下移植结论（那是 dim-9）。

## 主旨与原则

**输出契约（下方 Output）是唯一硬约束。** 推荐场景集（gui/rendering_3d/media/hardware）是
**起点而非封闭清单**——若发现别的鸿蒙适配重点场景（如打印/扫描、剪贴板/拖放、系统托盘通知、
传感器定位），照常 coin 一个简短小写 `key`、`present` 标出，并记入 `meta.observations`。

**这是综合维度，不要重扫源码。** 复用本次分析**已算出**的：
- `native_api`（GPU/图形 `category=hardware`、`type=opengl/directx`；GUI 的 win32/x11/cocoa 组；设备/syscall）
- `runtime_surface.devices`（/dev、GPU、串口/USB、摄像头/音频）
- `dependencies`（Qt/GTK/wxWidgets/SDL/FFmpeg/GStreamer/PortAudio/OpenCV/CUDA…）+ `native_api.dynamic_libraries`
- `function_summary`（README/能力分类里"这是个 GUI 工具/播放器/渲染引擎"之类的定性）
按场景归纳，引用它们的 `evidence`（file:line）即可，必要时再点开一两个关键文件确认。

**生产代码口径**：只统计库自身**生产代码**触及的场景，排除测试/示例/demo（与其它维度一致）。

## 输出契约（Output，fills report `capability_profile`）

```json
{
  "summary": "中文：本项目触及的鸿蒙适配重点场景概览",
  "scenarios": [
    {"key": "gui", "present": true, "kind": ["qt6", "x11"],
     "via": ["Qt6", "libQt6Widgets.so"], "harmony_status": "partial",
     "adaptation": "界面层需用 ArkUI 重写，业务逻辑可复用", "evidence": ["src/ui/main.cpp:42"]},
    {"key": "rendering_3d", "present": true, "kind": ["opengl"],
     "via": ["libGL", "glfw"], "harmony_status": "unknown",
     "adaptation": "依赖鸿蒙 PC 的 OpenGL/EGL 可用性（目标事实未核实）", "evidence": ["src/render/gl.c:88"]},
    {"key": "media", "present": false},
    {"key": "hardware", "present": true, "kind": ["gpu_cuda"], "specific_hardware": true,
     "via": ["libcudart"], "harmony_status": "unavailable",
     "adaptation": "CUDA 为 NVIDIA 专有，鸿蒙无等价，相关功能无法移植", "evidence": ["src/kernel.cu:10"]}
  ]
}
```

- `key`/`present`/`harmony_status`/`specific_hardware` 是**闭轴**；`kind`/`via`/`adaptation` 开放。
- `present:false` 的场景可省略或保留占位；纯计算库 `scenarios` 可为 `[]`。

## 思路（Approach，可调整）

1. **gui**：有窗口/控件工具包或窗口系统调用 → present。`kind` 填工具包(qt/gtk/wx/sdl/imgui/swing/
   javafx/electron/tk/win32/wpf) + 窗口栈(x11/wayland/win32/cocoa)。来源多在 dependencies / native_api 平台组。
2. **rendering_3d**：OpenGL/EGL/Vulkan/DirectX/Metal/WebGPU 调用或着色器管线 → present，`kind` 填具体图形 API。
   注意区分纯 2D 绘图（Cairo/Skia 2D，可归 gui 或单列 `key:"rendering_2d"` 自创）与 3D。
3. **media**：音视频编解码/播放/采集（FFmpeg/GStreamer/PortAudio/ALSA/WASAPI/CoreAudio、摄像头采集）→ present，
   `kind` 填 video_decode/audio_capture/codec 等。
4. **hardware**：GPU 通用计算(CUDA/OpenCL/ROCm)、USB/串口、蓝牙、传感器、摄像头、NPU/FPGA → present。
   **`specific_hardware`**：依赖特定/不可替代硬件（CUDA/NPU/FPGA、特定采集卡）置 true——这是 dim-9 判 infeasible 的强信号。
5. 每个 present 场景对照 `references/harmony-pc-capabilities.json`（3D/媒体/硬件/GUI 段）判 `harmony_status`：
   目标事实 available→不阻碍；partial→部分；unavailable→阻碍；**查不到对应事实→`unknown`**（诚实，别臆断），
   dim-9 会据 unknown 下调 confidence。`adaptation` 一句话点出修改量/路径。
   可用鸿蒙文档技能（opencode 全局 `harmonyos-sdk-api-lookup`，run prompt 会提示可用性）核实对应
   Kit/@ohos API 的**存在性**，方法与口径护栏见 harmony-adaptation SKILL.md「目标侧 API 事实核查」——
   **文档存在 ≠ PC 可用，caps JSON 优先**；caps 查不到且文档也检索无果 → 倾向 unavailable/unknown 如实标注。

## 常见情形（recall aids，非穷举）

- GUI 工具包→依赖名/动态库：`Qt*`/`libQt*`、`gtk`/`libgtk`、`wxWidgets`、`SDL2`、`glfw`、`imgui`、
  Python `PySide*/PyQt*/tkinter/wx`、Java `swing/javafx/swt`、JS `electron`。
- 3D：`libGL/libEGL/libGLES`、`vulkan`/`libvulkan`、`d3d11/d3d12/dxgi`、`Metal`、`OpenGL.framework`、着色器 `.glsl/.spv`。
- 媒体：`ffmpeg/libav*`、`gstreamer`、`portaudio/libasound/pulse`、`libvpx/x264/openh264`、`opencv`(含视频)、摄像头 `v4l2`/`AVFoundation`/`DirectShow`。
- 硬件：`cuda/cudart/nvcc`、`opencl`、`libusb`、串口 `termios`/`SetupComm`、蓝牙 `bluez`/`Winsock BT`、传感器/`/dev/*`。

## 自我发现（反哺）

清单外的场景或拿不准的归类→在 `meta.observations` 记 `{dimension:"capability_profile", field, kind, value, rationale}`，
供人工评审是否纳入推荐集。
