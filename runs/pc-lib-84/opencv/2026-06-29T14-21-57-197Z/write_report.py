#!/usr/bin/env python3
import json, os, sys

out_path = sys.argv[1]

report = {
  "library": {
    "name": "opencv",
    "kind": "library",
    "package_name": "opencv",
    "aliases": ["OpenCV", "cv2", "opencv4"],
    "import_names": ["cv2", "opencv2"],
    "source_url": "https://github.com/opencv/opencv",
    "analyzed_at": "2026-06-29T14:21:57Z",
    "commit": "a16c4a9fe22a5e0aec30e4a02e9ee98c026bbc5d",
    "one_liner": "开源计算机视觉库，提供图像处理、视频分析、目标检测、3D重建等核心视觉算法",
    "ecosystem": "cpp",
    "bindings": ["python", "java", "nodejs"]
  },
  "function_summary": {
    "summary": "OpenCV（Open Source Computer Vision Library）是一个跨平台的开源计算机视觉与机器学习软件库，提供数百种计算机视觉算法。核心模块涵盖图像处理（滤波、几何变换、色彩空间转换）、特征检测与描述、相机标定与3D重建、视频分析（运动估计、目标跟踪）、深度神经网络推理、机器学习算法，以及图像/视频的编解码与GUI显示。该库被广泛用于机器人、自动驾驶、医学影像、工业检测等领域。",
    "categories": [
      {"name": "核心数据结构与基础运算", "description": "提供 Mat 矩阵类、算术运算、线性代数、随机数、并行框架等基础设施", "evidence": ["modules/core/include/opencv2/core.hpp", "modules/core/include/opencv2/core/mat.hpp"]},
      {"name": "图像处理", "description": "图像滤波、几何变换、色彩空间转换、直方图、边缘检测、形态学操作等", "evidence": ["modules/imgproc/include/opencv2/imgproc.hpp"]},
      {"name": "特征检测与描述", "description": "SIFT/SURF/ORB/AKAZE 等特征检测器与描述子提取、特征匹配", "evidence": ["modules/features2d/include/opencv2/features2d.hpp"]},
      {"name": "相机标定与3D重建", "description": "相机内参标定、立体视觉、深度图重建、姿态估计", "evidence": ["modules/calib3d/include/opencv2/calib3d.hpp"]},
      {"name": "视频分析与目标跟踪", "description": "光流计算、运动估计、目标跟踪、背景减除", "evidence": ["modules/video/include/opencv2/video.hpp"]},
      {"name": "深度神经网络推理", "description": "加载预训练 DNN 模型（Caffe/TensorFlow/ONNX/Torch）并执行推理，支持 CUDA/OpenCL/Vulkan 加速", "evidence": ["modules/dnn/include/opencv2/dnn.hpp"]},
      {"name": "机器学习", "description": "SVM、决策树、K近邻、随机森林、Boosting 等传统 ML 算法", "evidence": ["modules/ml/include/opencv2/ml.hpp"]},
      {"name": "图像与视频编解码", "description": "读取/写入多种图像格式和视频捕获/写入（FFmpeg/GStreamer/Media Foundation/AVFoundation/V4L2）", "evidence": ["modules/imgcodecs/include/opencv2/imgcodecs.hpp", "modules/videoio/include/opencv2/videoio.hpp"]},
      {"name": "图形界面与可视化", "description": "窗口显示、鼠标/键盘事件、OpenGL 交互、Qt/GTK/Win32 后端", "evidence": ["modules/highgui/include/opencv2/highgui.hpp"]}
    ],
    "domain": "计算机视觉 / 机器学习",
    "target_users": "计算机视觉与机器学习应用开发者、机器人/自动驾驶/工业检测工程师"
  }
}

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("part1 done")
