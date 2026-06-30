#!/usr/bin/env python3
"""Assemble the DGL analysis report from metrics + reasoned blocks."""
import json
import os
from datetime import datetime, timezone

RUN_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = "repos/pc-lib-84/dgl"

with open(os.path.join(RUN_DIR, "metrics.json"), "r") as f:
    metrics = json.load(f)

# ISO timestamp for analyzed_at
analyzed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

report = {
    "library": {
        "name": "dgl",
        "kind": "library",
        "package_name": "dgl",
        "aliases": ["Deep Graph Library"],
        "import_names": ["dgl"],
        "source_url": "https://github.com/dmlc/dgl.git",
        "analyzed_at": analyzed_at,
        "commit": "3d16000b4170fa741ed9e9667f22ba84d3493026",
        "one_liner": "面向图神经网络（GNN）的高性能 Python 库，提供图数据结构、消息传递原语、图采样与分布式训练能力。",
        "ecosystem": "python",
        "bindings": []
    },
    "function_summary": {
        "summary": "DGL（Deep Graph Library）是一个面向图神经网络（GNN）的高性能、可扩展 Python 库。它提供图与异构图数据结构、消息传递（message passing）原语、丰富的 GNN 模块、图采样与邻居采样、分布式图训练，以及稀疏矩阵与多深度学习后端（PyTorch/MXNet/TensorFlow）张量适配能力。目标用户为机器学习研究者、GNN 算法开发者及需要在图数据上构建深度学习模型的工程师。",
        "categories": [
            {
                "name": "图数据结构与异构图",
                "description": "提供同构图、异构图、子图、批处理图等核心数据结构，支持节点/边特征存储与图变换操作。",
                "evidence": ["python/dgl/heterograph.py", "python/dgl/graph_index.py", "src/graph/heterograph.cc", "src/graph/unit_graph.cc"]
            },
            {
                "name": "消息传递与 GNN 算子",
                "description": "实现基于消息传递范式的图神经网络计算原语，并内置常见 GNN 层（GCN、GAT、GraphSAGE 等）。",
                "evidence": ["python/dgl/nn/pytorch/conv/", "src/graph/graph_op.cc", "src/scheduler/scheduler.cc"]
            },
            {
                "name": "图采样与小批量训练",
                "description": "提供邻居采样、随机游走、负采样、时序采样等机制，支持大图上的小批量训练。",
                "evidence": ["python/dgl/dataloading/", "graphbolt/src/fused_csc_sampling_graph.cc", "src/graph/sampling/"]
            },
            {
                "name": "分布式图训练",
                "description": "支持多机多卡分布式图存储、采样与训练，通过 socket 通信在多个服务器/客户端间协同。",
                "evidence": ["python/dgl/distributed/", "src/rpc/network/tcp_socket.cc", "src/rpc/rpc.cc"]
            },
            {
                "name": "稀疏矩阵与张量适配",
                "description": "提供稀疏矩阵运算（dgl.sparse）及与 PyTorch 等框架的张量零拷贝适配（tensoradapter）。",
                "evidence": ["python/dgl/sparse/", "dgl_sparse/", "tensoradapter/pytorch/"]
            },
            {
                "name": "多后端框架支持",
                "description": "核心接口后端可切换为 PyTorch、Apache MXNet 或 TensorFlow，通过统一张量抽象适配不同框架。",
                "evidence": ["python/dgl/backend/", "python/dgl/ndarray.py"]
            }
        ],
        "domain": "machine_learning",
        "target_users": "GNN 研究人员、机器学习工程师及需要在图数据上构建深度学习应用的上层库开发者。"
    },
    "languages": metrics["languages"],
    "code_metrics": metrics["code_metrics"],
    "tests": metrics["tests"],
    "license": {
        "spdx": "Apache-2.0",
        "name": "Apache License 2.0",
        "confidence": "high",
        "is_dual_licensed": False,
        "license_files": ["LICENSE"],
        "evidence": "仓库根目录 LICENSE 为完整 Apache-2.0 文本；README 与 python/setup.py classifiers 均声明 Apache Software License。",
        "notes": "宽松型许可。vendored 的第三方子模块（third_party/*）各自保留原许可，不影响主体判定。"
    },
    "dependencies": {
        "count": 0,  # set below
        "manifests": ["python/setup.py", "dglgo/setup.py", "CMakeLists.txt", "graphbolt/CMakeLists.txt", "dgl_sparse/CMakeLists.txt", ".gitmodules", "conda/dgl/meta.yaml"],
        "by_ecosystem": {},
        "dependencies": [],
        "notes": "生产代码依赖分为 Python 运行时、C/C++ 原生构建依赖及 vendored/git submodule 依赖。部分未在 OpenHarmony PC 镜像中提供官方 ohos 轮子的 Python 包（如 networkx、requests）为纯 Python 实现，可在已移植 Python 上直接运行。"
    },
    "native_api": {
        "summary": "DGL 在 C++ 核心中对平台 API 做了较充分的跨平台封装：POSIX/Win32 共享内存、套接字、动态库加载均有条件编译分支；同时深度依赖 OpenMP 并行、CUDA GPU 计算（可选）以及 Linux 特有的 epoll/io_uring（分布式训练与 GraphBolt 磁盘 I/O）。",
        "groups": [],
        "dynamic_libraries": [],
        "platform_dependence": "mixed"
    },
    "runtime_surface": {
        "summary": "运行期主要读取大量 DGL_*、PYTORCH_*、OMP_NUM_THREADS 等环境变量；使用 socket 进行分布式训练通信；通过 ctypes/torch.classes 加载本仓构建的原生共享库；可选使用 CUDA 设备和 POSIX 共享内存。",
        "network": [
            {
                "detail": "TCP socket 分布式训练通信（server/client 模式）",
                "purpose": "多机分布式图训练时的进程间 RPC 通信",
                "evidence": ["src/rpc/network/tcp_socket.cc:29", "python/dgl/distributed/rpc_client.py:29"]
            },
            {
                "detail": "HTTP/HTTPS 数据集下载（requests）",
                "purpose": "从远程仓库下载图数据集与预训练资源",
                "evidence": ["python/dgl/graphbolt/internal_utils.py:253", "python/dgl/data/utils.py:57"]
            }
        ],
        "filesystem": [
            {
                "detail": "$DGL_CACHE_DIR / $XDG_CACHE_HOME / $HOME 缓存目录",
                "purpose": "存放下载的数据集与编译缓存",
                "evidence": ["src/runtime/file_util.cc:74"]
            },
            {
                "detail": "$DGL_DOWNLOAD_DIR 下载目录",
                "purpose": "数据集默认下载路径",
                "evidence": ["python/dgl/data/utils.py:314"]
            },
            {
                "detail": "POSIX 共享内存文件（/dev/shm/ 下）",
                "purpose": "跨进程共享图数据与特征",
                "evidence": ["src/runtime/shared_mem.cc:81"]
            }
        ],
        "env_vars": [
            {"name": "DGL_LIBRARY_PATH", "purpose": "自定义 libdgl 等原生库搜索路径", "evidence": ["python/dgl/_ffi/libinfo.py:34"]},
            {"name": "LD_LIBRARY_PATH", "purpose": "Linux 动态库搜索路径补充", "evidence": ["python/dgl/_ffi/libinfo.py:37"]},
            {"name": "DYLD_LIBRARY_PATH", "purpose": "macOS 动态库搜索路径补充", "evidence": ["python/dgl/_ffi/libinfo.py:43"]},
            {"name": "DGL_BIND_THREADS", "purpose": "是否绑定工作线程到 CPU 核心", "evidence": ["src/runtime/threading_backend.cc:64"]},
            {"name": "DGL_NUM_THREADS", "purpose": "设置 DGL 线程池线程数", "evidence": ["src/runtime/threading_backend.cc:201"]},
            {"name": "OMP_NUM_THREADS", "purpose": "OpenMP 线程数", "evidence": ["src/runtime/threading_backend.cc:203"]},
            {"name": "DGL_CACHE_DIR", "purpose": "编译/数据缓存目录", "evidence": ["src/runtime/file_util.cc:74"]},
            {"name": "DGL_DOWNLOAD_DIR", "purpose": "数据集下载目录", "evidence": ["python/dgl/data/utils.py:314"]},
            {"name": "DGL_REPO", "purpose": "数据集下载镜像地址", "evidence": ["python/dgl/data/utils.py:57"]},
            {"name": "DGLBACKEND", "purpose": "选择深度学习后端（pytorch/mxnet/tensorflow）", "evidence": ["python/dgl/data/citation_graph.py:36", "python/dgl/backend/__init__.py:104"]},
            {"name": "PYTORCH_CUDA_ALLOC_CONF", "purpose": "GraphBolt 运行时调整 PyTorch CUDA 内存分配器配置", "evidence": ["python/dgl/graphbolt/__init__.py:14"]},
            {"name": "DGL_DIST_MODE", "purpose": "分布式模式开关", "evidence": ["python/dgl/distributed/dist_context.py:49"]},
            {"name": "DGL_ROLE", "purpose": "分布式角色（client/server）", "evidence": ["python/dgl/distributed/dist_context.py:251"]},
            {"name": "DGL_SERVER_ID", "purpose": "分布式服务器 ID", "evidence": ["python/dgl/distributed/dist_context.py:273"]},
            {"name": "DGL_IP_CONFIG", "purpose": "分布式 IP 配置", "evidence": ["python/dgl/distributed/dist_context.py:274"]},
            {"name": "DGL_NUM_SERVER", "purpose": "分布式服务器数量", "evidence": ["python/dgl/distributed/dist_context.py:275"]},
            {"name": "DGL_NUM_CLIENT", "purpose": "分布式客户端数量", "evidence": ["python/dgl/distributed/dist_context.py:276"]},
            {"name": "DGL_CONF_PATH", "purpose": "分布式配置路径", "evidence": ["python/dgl/distributed/dist_context.py:277"]},
            {"name": "DGL_NUM_SAMPLER", "purpose": "分布式采样进程数", "evidence": ["python/dgl/distributed/dist_context.py:284"]},
            {"name": "DGL_GROUP_ID", "purpose": "分布式组 ID", "evidence": ["python/dgl/distributed/dist_context.py:286"]},
            {"name": "DGL_SOCKET_MAX_THREAD_COUNT", "purpose": "socket 通信最大线程数", "evidence": ["python/dgl/distributed/rpc.py:149"]},
            {"name": "DGL_DIST_MAX_TRY_TIMES", "purpose": "分布式连接重试次数", "evidence": ["python/dgl/distributed/rpc_server.py:101", "python/dgl/distributed/rpc_client.py:181"]},
            {"name": "DGL_LOG_DEBUG", "purpose": "调试日志开关", "evidence": ["python/dgl/logging.py:33"]},
            {"name": "DGL_FFI", "purpose": "FFI 模式选择", "evidence": ["python/dgl/_ffi/base.py:53"]},
            {"name": "DGL_PREFETCHER_TIMEOUT", "purpose": "DataLoader prefetcher 超时", "evidence": ["python/dgl/dataloading/dataloader.py:51"]}
        ],
        "subprocess": [
            {
                "command": "Python multiprocessing spawn/fork",
                "purpose": "多进程 DataLoader、分布式采样与多 GPU 训练",
                "evidence": ["python/dgl/distributed/dist_context.py:6", "python/dgl/multiprocessing/pytorch.py:8"]
            }
        ],
        "devices": [
            {
                "detail": "NVIDIA GPU / CUDA 设备（可选）",
                "purpose": "GPU 上图计算与训练加速",
                "evidence": ["src/runtime/cuda/cuda_device_api.cc:33", "python/dgl/graphbolt/__init__.py:14"]
            }
        ],
        "services": []
    },
    "build_env": {
        "language_standard": "C++17",
        "runtime_version": "Python >= 3（setup.py 标注 Python 3；conda 构建未指定下限）",
        "build_system": "CMake + setuptools",
        "compiler_extensions": [
            {"detail": "OpenMP 并行指令（#pragma omp parallel / atomic / barrier）", "purpose": "CPU 图操作并行化", "evidence": ["src/array/cpu/spmat_op_impl_coo.cc:120", "src/array/cpu/spmm.h:190"]},
            {"detail": "GCC/Clang 链接器标志 -Wl,--exclude-libs,ALL", "purpose": "避免第三方符号外泄", "evidence": ["CMakeLists.txt:374"]},
            {"detail": "MSVC 专用宏 WIN32_LEAN_AND_MEAN、NOMINMAX、_CRT_SECURE_NO_WARNINGS", "purpose": "Windows 编译适配", "evidence": ["CMakeLists.txt:162", "graphbolt/CMakeLists.txt:13"]},
            {"detail": "LIBXSMM CPU 指令集检测（AVX2/AVX512）", "purpose": "在 x86 上选择高性能 GEMM 内核", "evidence": ["src/runtime/config.cc:21", "src/array/cpu/spmm.h:147"]}
        ],
        "platforms": [
            {"os": "linux", "arch": "x86_64", "evidence": ["python/setup.py:42", ".github/workflows/"]},
            {"os": "linux", "arch": "aarch64", "evidence": ["README.md:43（NVIDIA NGC ARM container）"]},
            {"os": "windows", "arch": "x86_64", "evidence": ["CMakeLists.txt:161", "python/setup.py:46"]},
            {"os": "macos", "arch": "x86_64/arm64", "evidence": ["python/setup.py:44", "CMakeLists.txt:154"]}
        ],
        "entry_points": [],
        "packaging": "通过 pip（bdist_wheel/sdist）与 conda 分发；wheel 内包含 libdgl.so、tensoradapter、dgl_sparse、graphbolt 等本仓构建的原生共享库；未捆绑 Python 运行时。",
        "notes": "CUDA 为可选构建特性（USE_CUDA=OFF 可禁用）。"
    },
    "capability_profile": {
        "summary": "DGL 是计算型机器学习库，不涉及 GUI、3D 渲染或媒体编解码；核心触及的鸿蒙适配重点场景是 GPU 通用计算（CUDA）加速，该能力在鸿蒙 PC 无等价实现。",
        "scenarios": [
            {
                "key": "hardware",
                "present": True,
                "kind": ["gpu_cuda"],
                "specific_hardware": True,
                "via": ["CUDA", "cuBLAS", "cuSparse", "cuRAND", "libcudart"],
                "harmony_status": "unavailable",
                "adaptation": "CUDA 为 NVIDIA 专有硬件/软件栈，鸿蒙 PC 无等价实现；需降级为 CPU 路径或放弃 GPU 加速功能。",
                "evidence": ["src/runtime/cuda/cuda_common.h:9", "CMakeLists.txt:22", "src/runtime/cuda/cuda_device_api.cc:33"]
            }
        ]
    },
    "harmony_adaptation": {
        "target": "HarmonyOS NEXT PC（库默认跑在已移植的 Python 3.12 运行时上；原生扩展经 OHOS NDK/musl 重编；自研内核，无 Linux ABI）",
        "feasibility": "hard",
        "porting_class": "needs_adaptation_partial",
        "effort": {"person_days": [15, 40]},
        "confidence": "medium",
        "recommended_path": "run_on_ported_runtime + OHOS NDK 重编 C++ 扩展；关闭 USE_CUDA 走 CPU 后端；liburing 磁盘 I/O 路径回退到同步/线程池实现；epoll socket pool 使用单连接 fallback 或替换为 poll。",
        "summary": "DGL 主体为 Python + C++ 扩展库。鸿蒙 PC 已移植 Python 与 PyTorch，纯 Python 逻辑和已适配依赖（numpy/scipy/pandas/psutil/torch）可直接复用。主要工作量在：1) 用 OHOS NDK 重编 libdgl、tensoradapter、dgl_sparse、graphbolt 等本仓原生模块；2) CUDA GPU 加速功能在鸿蒙无等价，必须降级为 CPU 路径；3) Linux 特有 io_uring/epoll 路径需条件编译回退；4) x86_64 目标支持状态尚未核实。",
        "unadaptable_apis": [
            {
                "id": "ua:cuda_ops",
                "caused_by": ["ta:cuda"],
                "api": "CUDA runtime / cuBLAS / cuSparse / cuRAND / CUDA kernel launch",
                "public_entry": "dgl.ndarray.copy_to / dgl.to('cuda') / GPU graph operators",
                "reason": "CUDA 为 NVIDIA 专有硬件/软件栈，鸿蒙 PC 无 CUDA 运行时，相关 GPU 算子无法直接适配。",
                "blocking_native_api": "cudaMalloc / cudaMemcpy / cuSparse / cuBLAS / cuRAND / kernel launch",
                "category": "hardware",
                "evidence": ["src/runtime/cuda/cuda_common.h:9", "src/runtime/cuda/cuda_device_api.cc:33", "src/runtime/ndarray.cc:225"]
            },
            {
                "id": "ua:io_uring",
                "caused_by": ["ta:io_uring"],
                "api": "io_uring_queue_init / io_uring_prep_read / io_uring_submit / __NR_io_uring_register",
                "public_entry": "torch.ops.graphbolt.ondisk_npy_array / torch.ops.graphbolt.detect_io_uring",
                "reason": "io_uring 为 Linux 5.1+ 内核特有异步 I/O 接口，鸿蒙自研内核无等价实现。",
                "blocking_native_api": "io_uring_queue_init / io_uring_submit / io_uring_wait_cqe_nr",
                "category": "platform",
                "evidence": ["graphbolt/src/io_uring.cc:25", "graphbolt/src/cnumpy.cc:77"]
            }
        ],
        "target_assumptions": [
            {
                "id": "ta:python",
                "capability": "Python 3 运行时已在鸿蒙 PC 移植",
                "required": True,
                "target_status": "available",
                "impact": "Python 主体可直接运行",
                "source": "harmony-pc-capabilities.json#runtimes.python"
            },
            {
                "id": "ta:pytorch",
                "capability": "PyTorch 已在鸿蒙 PC 提供 ohos 轮子",
                "required": True,
                "target_status": "available",
                "impact": "tensoradapter、dgl_sparse、graphbolt 所依赖的 PyTorch C++ API 可复用",
                "source": "harmony-pc-capabilities.json#runtimes.python + scripts/harmony_adapted.js"
            },
            {
                "id": "ta:cuda",
                "capability": "GPU 通用计算 CUDA",
                "required": True,
                "target_status": "unavailable",
                "impact": "不支持则 GPU 加速功能无法运行，必须降级为 CPU 路径",
                "source": "harmony-pc-capabilities.json#hardware_devices.gpu_compute_cuda"
            },
            {
                "id": "ta:io_uring",
                "capability": "Linux io_uring 异步 I/O",
                "required": True,
                "target_status": "unavailable",
                "impact": "GraphBolt 磁盘特征读取的高性能路径不可用，需回退到同步/线程池实现",
                "source": "代码中 HAVE_LIBRARY_LIBURING 仅 Linux 启用"
            },
            {
                "id": "ta:epoll",
                "capability": "Linux epoll I/O 多路复用",
                "required": True,
                "target_status": "partial",
                "impact": "分布式 socket pool 多连接并发能力受限；当前代码有非 epoll 单连接 fallback",
                "source": "src/rpc/network/socket_pool.cc"
            },
            {
                "id": "ta:x86_64",
                "capability": "x86_64 架构支持",
                "required": True,
                "target_status": "unknown",
                "impact": "若目标设备为 x86_64 且鸿蒙 PC 未覆盖，则无法直接运行预编译产物",
                "source": "harmony-pc-capabilities.json#arch.x86_64"
            },
            {
                "id": "ta:posix_shm",
                "capability": "POSIX 共享内存（shm_open/mmap）",
                "required": True,
                "target_status": "available",
                "impact": "跨进程共享图数据功能可保留",
                "source": "OHOS NDK 基于 musl，musl 支持 POSIX shm"
            }
        ],
        "required_permissions": [
            {
                "permission": "ohos.permission.INTERNET",
                "reason": "分布式训练 socket 通信与数据集下载需要网络访问",
                "source_capability": "hardware",
                "harmony_status": "unknown",
                "evidence": ["src/rpc/network/tcp_socket.cc:29", "python/dgl/graphbolt/internal_utils.py:253"]
            }
        ],
        "blockers": [
            {
                "id": "bk:cuda",
                "issue": "CUDA GPU 加速功能在鸿蒙 PC 无等价实现，必须整体降级为 CPU 路径",
                "severity": "blocker",
                "adaptability": "unadaptable",
                "category": "hardware_unavailable",
                "source_dimension": "capability_profile",
                "harmony_status": "unavailable",
                "remediation": "构建时关闭 USE_CUDA，运行时强制使用 CPU 设备；评估 CPU 路径性能是否满足场景需求。",
                "caused_by": ["ta:cuda"],
                "manifests_as": ["ua:cuda_ops"],
                "evidence": ["src/runtime/cuda/cuda_common.h:9", "CMakeLists.txt:22"]
            },
            {
                "id": "bk:io_uring",
                "issue": "GraphBolt 的 io_uring 磁盘 I/O 路径仅 Linux 可用，鸿蒙无等价实现",
                "severity": "major",
                "adaptability": "partial",
                "category": "linux_only_api",
                "source_dimension": "native_api",
                "harmony_status": "unavailable",
                "remediation": "在 HAVE_LIBRARY_LIBURING 未定义时回退到现有同步 read / 线程池实现；当前 IsAvailable() 已返回 false，需验证 fallback 覆盖完整。",
                "caused_by": ["ta:io_uring"],
                "manifests_as": ["ua:io_uring"],
                "evidence": ["graphbolt/src/io_uring.cc:22", "graphbolt/src/cnumpy.cc:66"]
            },
            {
                "id": "bk:epoll",
                "issue": "分布式 socket pool 依赖 Linux epoll 实现多连接并发，鸿蒙 POSIX 子集可能缺失完整 epoll 支持",
                "severity": "major",
                "adaptability": "partial",
                "category": "posix_subset_gap",
                "source_dimension": "native_api",
                "harmony_status": "partial",
                "remediation": "使用 USE_EPOLL=OFF 编译，启用单连接 fallback 路径；或对鸿蒙内核实现 poll/select 多路复用。",
                "caused_by": ["ta:epoll"],
                "evidence": ["src/rpc/network/socket_pool.cc:12", "CMakeLists.txt:60"]
            },
            {
                "id": "bk:arch_unknown",
                "issue": "鸿蒙 PC x86_64 架构覆盖情况未核实",
                "severity": "major",
                "adaptability": "adaptable",
                "category": "toolchain",
                "source_dimension": "build_env",
                "harmony_status": "unknown",
                "remediation": "确认目标设备架构；arm64 已确认支持，x86_64 需核实后决定是否提供预编译包或仅支持 arm64。",
                "caused_by": ["ta:x86_64"],
                "evidence": ["harmony-pc-capabilities.json#arch.x86_64"]
            },
            {
                "id": "bk:native_rebuild",
                "issue": "libdgl、tensoradapter、dgl_sparse、graphbolt 等本仓原生模块需用 OHOS NDK 重编",
                "severity": "major",
                "adaptability": "adaptable",
                "category": "native_dependency",
                "source_dimension": "dependencies",
                "harmony_status": "replace_with_ohos",
                "remediation": "使用 ohos.toolchain.cmake + clang/musl 交叉编译所有 C++17 模块；链接鸿蒙版 PyTorch、OpenMP、METIS/GKlib 等未鸿蒙化依赖。",
                "evidence": ["CMakeLists.txt:8", "tensoradapter/pytorch/CMakeLists.txt:1", "graphbolt/CMakeLists.txt:1"]
            },
            {
                "id": "bk:unadapted_deps",
                "issue": "部分 Python 依赖（networkx、requests、pydantic、pyyaml、tqdm、packaging）未在 OpenHarmony PC 镜像中提供官方 ohos 轮子",
                "severity": "minor",
                "adaptability": "adaptable",
                "category": "dependency_availability",
                "source_dimension": "dependencies",
                "harmony_status": "replace_with_ohos",
                "remediation": "这些包多为纯 Python 实现，可继续在已移植 Python 上安装；必要时随包携带或源码安装。",
                "evidence": ["python/setup.py:222", "scripts/harmony_adapted.js output"]
            },
            {
                "id": "bk:libxsmm_arch",
                "issue": "LIBXSMM 与 x86 AVX2/AVX512 指令集绑定，非 x86 架构需禁用",
                "severity": "minor",
                "adaptability": "adaptable",
                "category": "arch_specific",
                "source_dimension": "native_api",
                "harmony_status": "replace_with_ohos",
                "remediation": "在 arm64 构建中设置 USE_LIBXSMM=OFF，回退到通用 OpenMP/BLAS 路径。",
                "evidence": ["CMakeLists.txt:188", "src/runtime/config.cc:21"]
            }
        ],
        "compatible": [
            {
                "aspect": "Python 层图数据结构与 GNN API",
                "note": "纯 Python 逻辑可直接跑在鸿蒙已移植 Python 上，无需改动。",
                "evidence": ["python/dgl/heterograph.py", "python/dgl/nn/"]
            },
            {
                "aspect": "已鸿蒙化的 Python 依赖",
                "note": "numpy、scipy、pandas、psutil、torch 已有官方 ohos 轮子，可直接复用。",
                "evidence": ["scripts/harmony_adapted.js output"]
            },
            {
                "aspect": "POSIX 共享内存与 mmap",
                "note": "OHOS NDK musl 支持 POSIX shm_open/mmap，跨进程共享内存功能可保留。",
                "evidence": ["src/runtime/shared_mem.cc:81"]
            },
            {
                "aspect": "标准 socket 通信",
                "note": "基础 TCP socket API 属于标准 POSIX，鸿蒙 NDK 应可支持。",
                "evidence": ["src/rpc/network/tcp_socket.cc:29"]
            }
        ],
        "key_tasks": [
            "用 OHOS NDK 交叉编译 libdgl、tensoradapter、dgl_sparse、graphbolt 为 arm64（及核实后的 x86_64）.so",
            "关闭 USE_CUDA、USE_LIBXSMM、USE_LIBURING、USE_EPOLL 等 Linux/x86 专有选项，验证 CPU 路径功能完整",
            "为 GraphBolt 磁盘 I/O 实现 io_uring 缺失时的同步/线程池 fallback，确保 ondisk_npy_array 可用",
            "将未鸿蒙化的纯 Python 依赖（networkx、requests 等）纳入安装清单或源码安装流程",
            "在鸿蒙 Python + PyTorch 上跑通核心单元测试，验证图操作、采样、分布式单机多进程路径"
        ],
        "notes": "评估按模型 A（库跑在鸿蒙已移植 Python 运行时上）。DGL 核心 CPU 功能可移植，但 GPU 加速与部分 Linux 特有 I/O/网络优化路径无法直接适配，因此 porting_class 为 needs_adaptation_partial。confidence 为 medium 主要因为 x86_64 支持状态及 OHOS NDK 对 epoll 的完整兼容度尚未核实。若目标为 ArkTS 沙箱应用（模型 B），则 Python 运行时不可用，结论将变为 infeasible 或需整体用 Node-API/C++ 重写。"
    },
    "meta": {
        "schema_version": "1.0",
        "analyzer": "pc-lib-analyzer",
        "counter_tool": metrics["code_metrics"]["tool"],
        "confidence_overall": "medium",
        "warnings": [],
        "observations": [
            {
                "dimension": "dependencies",
                "field": "acquisition",
                "kind": "new_value",
                "value": "externalproject_build",
                "rationale": "graphbolt 对 liburing 使用 CMake ExternalProject_Add 在构建时从本仓 third_party/liburing 源码编译并安装到构建目录，既非典型 fetchcontent 也非纯 vendored 链接。"
            },
            {
                "dimension": "native_api",
                "field": "type",
                "kind": "new_value",
                "value": "linux_io_uring",
                "rationale": "io_uring 作为 Linux 特有异步 I/O 机制，独立于 epoll，应单独成组以便 dim-9 识别为 Linux-only blocker。"
            },
            {
                "dimension": "harmony_adaptation",
                "field": "porting_class",
                "kind": "ambiguity",
                "value": "needs_adaptation_partial",
                "rationale": "DGL 是库而非应用，CUDA 虽为重要特性但非唯一路径；CPU 路径完整可运行，因此未判 infeasible，而是按部分功能无法适配定级。"
            }
        ]
    }
}

# Populate dependencies
python_runtime_deps = [
    ("networkx", "networkx>=2.1", "runtime", "图算法与图数据处理", "package_manager", "remote", "PyPI", ["python/setup.py:223"], []),
    ("numpy", "numpy>=1.14.0", "runtime", "多维数组与张量基础", "package_manager", "remote", "PyPI", ["python/setup.py:224"], ["numpy.ndarray"]),
    ("packaging", "packaging", "runtime", "版本解析与比较", "package_manager", "remote", "PyPI", ["python/setup.py:225"], []),
    ("pandas", "pandas", "runtime", "表格数据处理", "package_manager", "remote", "PyPI", ["python/setup.py:226"], ["pandas.DataFrame"]),
    ("psutil", "psutil>=5.8.0", "runtime", "系统与进程信息查询", "package_manager", "remote", "PyPI", ["python/setup.py:227"], []),
    ("pydantic", "pydantic>=2.0", "runtime", "数据模型校验", "package_manager", "remote", "PyPI", ["python/setup.py:228"], ["pydantic.BaseModel"]),
    ("pyyaml", "pyyaml", "runtime", "YAML 配置解析", "package_manager", "remote", "PyPI", ["python/setup.py:229"], []),
    ("requests", "requests>=2.19.0", "runtime", "HTTP 数据集下载", "package_manager", "remote", "PyPI", ["python/setup.py:230"], ["requests.get"]),
    ("scipy", "scipy>=1.1.0", "runtime", "稀疏矩阵与科学计算", "package_manager", "remote", "PyPI", ["python/setup.py:231"], ["scipy.sparse"]),
    ("tqdm", "tqdm", "runtime", "进度条", "package_manager", "remote", "PyPI", ["python/setup.py:232"], ["tqdm.auto.tqdm"]),
]

dglgo_deps = [
    ("typer", "typer>=0.4.0", "runtime", "DGL-Go CLI 命令行框架", "package_manager", "remote", "PyPI", ["dglgo/setup.py:13"], []),
    ("isort", "isort>=5.10.1", "runtime", "代码格式化工具集成", "package_manager", "remote", "PyPI", ["dglgo/setup.py:14"], []),
    ("autopep8", "autopep8>=1.6.0", "runtime", "代码格式化工具集成", "package_manager", "remote", "PyPI", ["dglgo/setup.py:15"], []),
    ("numpydoc", "numpydoc>=1.1.0", "runtime", "文档生成", "package_manager", "remote", "PyPI", ["dglgo/setup.py:16"], []),
    ("pydantic", "pydantic>=1.9.0", "runtime", "DGL-Go 配置模型校验", "package_manager", "remote", "PyPI", ["dglgo/setup.py:17"], []),
    ("ruamel.yaml", "ruamel.yaml>=0.17.20", "runtime", "YAML 配置读写", "package_manager", "remote", "PyPI", ["dglgo/setup.py:18"], []),
    ("PyYAML", "PyYAML>=5.1", "runtime", "YAML 配置读写", "package_manager", "remote", "PyPI", ["dglgo/setup.py:19"], []),
    ("ogb", "ogb>=1.3.3", "runtime", "Open Graph Benchmark 数据集", "package_manager", "remote", "PyPI", ["dglgo/setup.py:20"], []),
    ("rdkit-pypi", "rdkit-pypi", "runtime", "分子化学信息学（DGL-Go 生命科学示例）", "package_manager", "remote", "PyPI", ["dglgo/setup.py:21"], []),
    ("scikit-learn", "scikit-learn>=0.20.0", "runtime", "传统机器学习工具", "package_manager", "remote", "PyPI", ["dglgo/setup.py:22"], []),
]

cpp_deps = [
    ("torch", None, "runtime", "PyTorch C++ API（tensoradapter、dgl_sparse、graphbolt 的核心依赖）", "package_manager", "remote", "PyPI / PyTorch 官方", ["tensoradapter/pytorch/CMakeLists.txt:26", "graphbolt/CMakeLists.txt:42", "dgl_sparse/CMakeLists.txt:37"], ["torch::Tensor", "at::Tensor", "c10::intrusive_ptr"]),
    ("dmlc-core", None, "runtime", "日志、序列化、配置解析等基础工具库", "submodule", "local", "本仓 third_party/dmlc-core（git submodule）", [".gitmodules", "CMakeLists.txt:316"], ["dmlc::LogMessage"]),
    ("dlpack", None, "runtime", "张量内存布局跨框架交换标准", "submodule", "local", "本仓 third_party/dlpack（git submodule）", [".gitmodules", "CMakeLists.txt:287"], ["DLTensor"]),
    ("METIS", None, "runtime", "图划分", "submodule", "local", "本仓 third_party/METIS（git submodule）", [".gitmodules", "CMakeLists.txt:353"], ["METIS_PartGraphKway"]),
    ("GKlib", None, "runtime", "METIS 依赖的基础库", "submodule", "local", "本仓 third_party/GKlib（git submodule）", [".gitmodules", "CMakeLists.txt:356"], []),
    ("nanoflann", None, "runtime", "KD-Tree / 最近邻搜索", "submodule", "local", "本仓 third_party/nanoflann（git submodule）", [".gitmodules", "CMakeLists.txt:328"], ["nanoflann::KDTreeSingleIndexAdaptor"]),
    ("libxsmm", None, "optional", "x86 上高性能小矩阵 GEMM", "submodule", "local", "本仓 third_party/libxsmm（git submodule）", [".gitmodules", "CMakeLists.txt:331"], ["libxsmm_gemm"]),
    ("pcg", None, "runtime", "随机数生成器", "submodule", "local", "本仓 third_party/pcg（git submodule）", [".gitmodules", "CMakeLists.txt:322"], []),
    ("cccl", None, "runtime", "CUDA C++ 核心库（thrust/cub/libcudacxx）", "submodule", "local", "本仓 third_party/cccl（git submodule）", [".gitmodules", "CMakeLists.txt:144"], []),
    ("cuCollections", None, "runtime", "CUDA 并发数据结构", "submodule", "local", "本仓 third_party/cuco（git submodule）", [".gitmodules", "graphbolt/CMakeLists.txt:149"], []),
    ("taskflow", None, "runtime", "C++ 并行任务调度", "submodule", "local", "本仓 third_party/taskflow（git submodule）", [".gitmodules", "graphbolt/CMakeLists.txt:86"], []),
    ("tsl_robin_map", None, "runtime", "高性能哈希表", "submodule", "local", "本仓 third_party/tsl_robin_map（git submodule）", [".gitmodules", "CMakeLists.txt:323"], []),
    ("liburing", None, "optional", "Linux io_uring 异步 I/O", "externalproject_build", "local", "构建时从本仓 third_party/liburing 源码编译", ["graphbolt/CMakeLists.txt:96"], ["io_uring_queue_init", "io_uring_submit"]),
    ("googletest", None, "test", "C++ 单元测试框架", "submodule", "local", "本仓 third_party/googletest（git submodule）", [".gitmodules", "CMakeLists.txt:448"], []),
    ("HugeCTR", None, "runtime", "NVIDIA GPU embedding cache", "submodule", "local", "本仓 third_party/HugeCTR（非 submodule，源码复制）", ["CMakeLists.txt:382"], []),
    ("OpenMP", None, "runtime", "CPU 并行", "system", "system", "系统预装 / 编译器自带，CMake find_package(OpenMP)", ["CMakeLists.txt:222", "graphbolt/CMakeLists.txt:91"], ["omp_get_max_threads", "omp_get_thread_num"]),
]

build_deps = [
    ("cmake", None, "build", "构建系统", "system", "system", "系统预装", ["CMakeLists.txt:1"], []),
    ("cython", None, "build", "Python C 扩展构建", "package_manager", "remote", "PyPI", ["python/setup.py:110"], []),
]

harmony_cache_python = {
    "networkx": False, "numpy": True, "packaging": False, "pandas": True,
    "psutil": True, "pydantic": False, "pyyaml": False, "requests": False,
    "scipy": True, "tqdm": False, "torch": True
}

all_deps = []
by_eco = {}

def add_dep(name, ecosystem, scope, version, purpose, acquisition, locality, source, declared_in, used_symbols, adapted=None):
    dep = {
        "name": name,
        "ecosystem": ecosystem,
        "scope": scope,
        "version": version,
        "purpose": purpose,
        "acquisition": acquisition,
        "locality": locality,
        "source": source,
        "declared_in": declared_in,
        "used_symbols": used_symbols if used_symbols else []
    }
    if ecosystem == "python" and name in harmony_cache_python:
        dep["harmony_adapted"] = harmony_cache_python[name]
        if harmony_cache_python[name]:
            dep["harmony_adapted_source"] = "OpenHarmony PC PyPI 镜像 (pypi.cnb.cool/OpenHarmonyPCDeveloper)"
    if name == "googletest":
        dep["harmony_adapted"] = True
        dep["harmony_adapted_source"] = "OpenHarmony PC C/C++ 预编译包 (gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs)"
    all_deps.append(dep)
    by_eco.setdefault(ecosystem, []).append(name)

for name, ver, scope, purpose, acq, loc, src, decl, used in python_runtime_deps:
    add_dep(name, "python", scope, ver, purpose, acq, loc, src, decl, used)

for name, ver, scope, purpose, acq, loc, src, decl, used in dglgo_deps:
    add_dep(name, "python", scope, ver, purpose, acq, loc, src, decl, used)

for name, ver, scope, purpose, acq, loc, src, decl, used in cpp_deps:
    add_dep(name, "cpp", scope, ver, purpose, acq, loc, src, decl, used)

for name, ver, scope, purpose, acq, loc, src, decl, used in build_deps:
    add_dep(name, "python" if name == "cython" else "other", scope, ver, purpose, acq, loc, src, decl, used)

report["dependencies"]["count"] = len(all_deps)
report["dependencies"]["by_ecosystem"] = by_eco
report["dependencies"]["dependencies"] = all_deps

# Populate native_api groups
report["native_api"]["groups"] = [
    {
        "type": "cpp_stl",
        "category": "standard",
        "platform": "portable",
        "apis": [
            {"name": "std::thread", "purpose": "原生线程创建", "count": 5, "evidence": ["src/runtime/threading_backend.cc:32", "src/rpc/network/socket_communicator.cc:94"]},
            {"name": "std::mutex", "purpose": "线程互斥", "count": 6, "evidence": ["src/runtime/thread_pool.cc:137", "src/runtime/registry.cc:31"]},
            {"name": "std::condition_variable", "purpose": "线程条件等待", "count": 2, "evidence": ["src/runtime/thread_pool.cc:229", "src/rpc/network/msg_queue.h:166"]},
            {"name": "std::vector / std::unordered_map / std::shared_ptr", "purpose": "标准容器与智能指针", "count": 50, "evidence": ["src/runtime/ndarray.cc", "src/graph/unit_graph.cc"]},
            {"name": "std::filesystem path manipulation (libinfo)", "purpose": "路径解析", "count": 2, "evidence": ["python/dgl/_ffi/libinfo.py:70"]}
        ]
    },
    {
        "type": "ffi_ctypes_torch",
        "category": "ffi",
        "platform": "portable",
        "apis": [
            {"name": "ctypes.CDLL", "purpose": "Python 加载 libdgl 共享库", "count": 1, "evidence": ["python/dgl/_ffi/base.py:39"]},
            {"name": "torch.classes.load_library", "purpose": "加载 graphbolt/dgl_sparse 共享库", "count": 3, "evidence": ["python/dgl/graphbolt/__init__.py:76", "python/dgl/sparse/__init__.py:38"]},
            {"name": "DGLLoadTensorAdapter (C API)", "purpose": "运行时加载 tensoradapter 库", "count": 1, "evidence": ["python/dgl/_ffi/base.py:147"]},
            {"name": "TORCH_LIBRARY / m.def (pybind11/TorchScript)", "purpose": "注册 C++ 算子到 PyTorch", "count": 1, "evidence": ["graphbolt/src/python_binding.cc:32"]}
        ]
    },
    {
        "type": "posix_shm",
        "category": "platform",
        "platform": "posix",
        "apis": [
            {"name": "shm_open", "purpose": "创建/打开 POSIX 共享内存对象", "count": 3, "evidence": ["src/runtime/shared_mem.cc:81"], "conditional": True},
            {"name": "mmap", "purpose": "内存映射共享内存/文件", "count": 3, "evidence": ["src/runtime/shared_mem.cc:87"], "conditional": True},
            {"name": "munmap", "purpose": "解除内存映射", "count": 1, "evidence": ["src/runtime/shared_mem.cc:56"], "conditional": True},
            {"name": "ftruncate", "purpose": "调整共享内存对象大小", "count": 1, "evidence": ["src/runtime/shared_mem.cc:85"], "conditional": True},
            {"name": "shm_unlink", "purpose": "删除共享内存对象", "count": 1, "evidence": ["src/runtime/shared_mem.cc:34"], "conditional": True}
        ]
    },
    {
        "type": "win32_shm",
        "category": "platform",
        "platform": "windows",
        "apis": [
            {"name": "CreateFileMapping", "purpose": "Windows 共享内存创建", "count": 1, "evidence": ["src/runtime/shared_mem.cc:94"], "conditional": True},
            {"name": "MapViewOfFile", "purpose": "Windows 内存映射视图", "count": 2, "evidence": ["src/runtime/shared_mem.cc:100", "src/runtime/shared_mem.cc:126"], "conditional": True},
            {"name": "OpenFileMapping", "purpose": "Windows 打开已有共享内存", "count": 2, "evidence": ["src/runtime/shared_mem.cc:123", "src/runtime/shared_mem.cc:147"], "conditional": True},
            {"name": "UnmapViewOfFile", "purpose": "Windows 解除映射视图", "count": 1, "evidence": ["src/runtime/shared_mem.cc:68"], "conditional": True},
            {"name": "CloseHandle", "purpose": "Windows 关闭内核对象句柄", "count": 2, "evidence": ["src/runtime/shared_mem.cc:69", "src/runtime/shared_mem.cc:149"], "conditional": True}
        ]
    },
    {
        "type": "posix_socket",
        "category": "platform",
        "platform": "posix",
        "apis": [
            {"name": "socket", "purpose": "创建 TCP socket", "count": 1, "evidence": ["src/rpc/network/tcp_socket.cc:29"]},
            {"name": "bind / listen / accept", "purpose": "服务器端 socket 绑定与监听", "count": 3, "evidence": ["src/rpc/network/tcp_socket.cc:80", "src/rpc/network/tcp_socket.cc:94", "src/rpc/network/tcp_socket.cc:110"]},
            {"name": "connect", "purpose": "客户端连接服务器", "count": 1, "evidence": ["src/rpc/network/tcp_socket.cc:54"]},
            {"name": "send / recv", "purpose": "TCP 数据收发", "count": 2, "evidence": ["src/rpc/network/tcp_socket.cc:201", "src/rpc/network/tcp_socket.cc:214"]},
            {"name": "setsockopt", "purpose": "设置 socket 选项（SO_REUSEADDR / SO_RCVTIMEO）", "count": 2, "evidence": ["src/rpc/network/tcp_socket.cc:37", "src/rpc/network/tcp_socket.cc:174"]},
            {"name": "fcntl", "purpose": "设置 socket 非阻塞模式", "count": 1, "evidence": ["src/rpc/network/tcp_socket.cc:151"], "conditional": True},
            {"name": "close", "purpose": "关闭 socket", "count": 1, "evidence": ["src/rpc/network/tcp_socket.cc:191"], "conditional": True}
        ]
    },
    {
        "type": "win32_socket",
        "category": "platform",
        "platform": "windows",
        "apis": [
            {"name": "ioctlsocket", "purpose": "Windows socket 非阻塞控制", "count": 1, "evidence": ["src/rpc/network/tcp_socket.cc:140"], "conditional": True},
            {"name": "closesocket", "purpose": "Windows 关闭 socket", "count": 1, "evidence": ["src/rpc/network/tcp_socket.cc:189"], "conditional": True}
        ]
    },
    {
        "type": "linux_epoll",
        "category": "platform",
        "platform": "linux",
        "apis": [
            {"name": "epoll_create1", "purpose": "创建 epoll 实例", "count": 1, "evidence": ["src/rpc/network/socket_pool.cc:21"], "conditional": True},
            {"name": "epoll_ctl", "purpose": "增删 epoll 监听事件", "count": 4, "evidence": ["src/rpc/network/socket_pool.cc:44", "src/rpc/network/socket_pool.cc:61", "src/rpc/network/socket_pool.cc:70"], "conditional": True},
            {"name": "epoll_wait", "purpose": "等待 I/O 事件", "count": 1, "evidence": ["src/rpc/network/socket_pool.cc:101"], "conditional": True}
        ]
    },
    {
        "type": "linux_io_uring",
        "category": "platform",
        "platform": "linux",
        "apis": [
            {"name": "io_uring_queue_init", "purpose": "初始化 io_uring 队列", "count": 1, "evidence": ["graphbolt/src/cnumpy.cc:77"], "conditional": True},
            {"name": "io_uring_get_sqe / io_uring_prep_read", "purpose": "提交异步读请求", "count": 4, "evidence": ["graphbolt/src/cnumpy.cc:243", "graphbolt/src/cnumpy.cc:283"], "conditional": True},
            {"name": "io_uring_submit / io_uring_wait_cqe_nr", "purpose": "提交并等待 io_uring 完成事件", "count": 4, "evidence": ["graphbolt/src/cnumpy.cc:194", "graphbolt/src/cnumpy.cc:258"], "conditional": True},
            {"name": "syscall(__NR_io_uring_register)", "purpose": "探测 io_uring 可用性", "count": 1, "evidence": ["graphbolt/src/io_uring.cc:55"], "conditional": True}
        ]
    },
    {
        "type": "pthread_affinity",
        "category": "platform",
        "platform": "posix",
        "apis": [
            {"name": "pthread_setaffinity_np", "purpose": "绑定工作线程到指定 CPU 核心", "count": 2, "evidence": ["src/runtime/threading_backend.cc:114"], "conditional": True},
            {"name": "sched_setaffinity", "purpose": "Android 平台设置 CPU 亲和性", "count": 2, "evidence": ["src/runtime/threading_backend.cc:111", "src/runtime/threading_backend.cc:127"], "conditional": True}
        ]
    },
    {
        "type": "sysfs_cpufreq",
        "category": "system",
        "platform": "linux",
        "apis": [
            {"name": "sysfs (/sys/devices/system/cpu/cpu*/cpufreq/cpuinfo_max_freq)", "purpose": "读取 CPU 最大频率以排序大小核", "count": 1, "evidence": ["src/runtime/threading_backend.cc:143"], "conditional": True}
        ]
    },
    {
        "type": "openmp",
        "category": "standard",
        "platform": "portable",
        "apis": [
            {"name": "omp_get_max_threads / omp_get_thread_num / omp_get_num_threads", "purpose": "OpenMP 并行线程查询", "count": 30, "evidence": ["src/array/cpu/spmat_op_impl_coo.cc:454", "src/array/cpu/spmm.h:190", "src/graph/sampling/neighbor/neighbor.cc:449"]},
            {"name": "#pragma omp parallel / for / barrier / atomic", "purpose": "CPU 图操作并行化", "count": 50, "evidence": ["src/array/cpu/spmat_op_impl_coo.cc:120", "src/array/cpu/spmm.h:190"]}
        ]
    },
    {
        "type": "cuda",
        "category": "hardware",
        "platform": "portable",
        "apis": [
            {"name": "cudaMalloc / cudaFree / cudaMemcpy / cudaMemsetAsync", "purpose": "GPU 内存分配与拷贝", "count": 20, "evidence": ["src/runtime/cuda/cuda_device_api.cc:33"], "conditional": True},
            {"name": "CUDA kernel launch", "purpose": "启动 CUDA 图计算核函数", "count": 50, "evidence": ["src/array/cuda/*.cu", "src/kernel/cuda/*.cu"], "conditional": True},
            {"name": "cuBLAS / cuSparse / cuRAND", "purpose": "GPU 线性代数、稀疏矩阵与随机数", "count": 10, "evidence": ["src/runtime/cuda/cuda_common.h:9"], "conditional": True}
        ]
    },
    {
        "type": "dynamic_loader",
        "category": "platform",
        "platform": "posix",
        "apis": [
            {"name": "dlopen", "purpose": "POSIX 动态库加载", "count": 2, "evidence": ["src/runtime/dso_module.cc:88", "src/runtime/tensordispatch.cc:41"], "conditional": True},
            {"name": "dlsym", "purpose": "解析动态库符号", "count": 2, "evidence": ["src/runtime/dso_module.cc:92", "src/runtime/tensordispatch.cc:51"], "conditional": True},
            {"name": "LoadLibraryW / GetProcAddress", "purpose": "Windows 动态库加载与符号解析", "count": 2, "evidence": ["src/runtime/dso_module.cc:74", "src/runtime/tensordispatch.cc:31"], "conditional": True}
        ]
    }
]

report["native_api"]["dynamic_libraries"] = [
    {
        "name": "libdgl.so / libdgl.dylib / libdgl.dll",
        "mechanism": "ctypes.CDLL",
        "acquisition": "self_build",
        "source": "本仓 C++ 核心构建产物",
        "description": "DGL C++ 核心共享库，提供图数据、运行时与算子实现",
        "optional": False,
        "evidence": ["python/dgl/_ffi/base.py:39", "python/dgl/_ffi/libinfo.py:75"]
    },
    {
        "name": "libtensoradapter_pytorch_*.so / .dylib / .dll",
        "mechanism": "dlsym via DGL C API (DGLLoadTensorAdapter)",
        "acquisition": "self_build",
        "source": "tensoradapter/pytorch 子模块构建产物",
        "description": "DGL 与 PyTorch 张量之间的零拷贝适配库",
        "optional": True,
        "evidence": ["python/dgl/_ffi/base.py:126", "src/runtime/tensordispatch.cc:22"]
    },
    {
        "name": "libdgl_sparse_pytorch_*.so / .dylib / .dll",
        "mechanism": "torch.classes.load_library",
        "acquisition": "self_build",
        "source": "dgl_sparse 子模块构建产物",
        "description": "DGL 稀疏矩阵 PyTorch 扩展",
        "optional": True,
        "evidence": ["python/dgl/sparse/__init__.py:38"]
    },
    {
        "name": "libgraphbolt_pytorch_*.so / .dylib / .dll",
        "mechanism": "torch.classes.load_library",
        "acquisition": "self_build",
        "source": "graphbolt 子模块构建产物",
        "description": "GraphBolt 采样与数据加载 PyTorch 扩展",
        "optional": True,
        "evidence": ["python/dgl/graphbolt/__init__.py:76"]
    }
]

# Write report
with open(os.path.join(RUN_DIR, "report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print("Wrote", os.path.join(RUN_DIR, "report.json"))
