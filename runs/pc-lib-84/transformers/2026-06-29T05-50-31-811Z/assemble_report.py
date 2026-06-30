#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble the pc-lib-analyzer report for transformers."""
import json
from pathlib import Path

RUN_DIR = Path(__file__).parent
METRICS = json.loads((RUN_DIR / "metrics.json").read_text())

def dep(name, scope, version, purpose, adapted=False, adapted_source=None,
        source_repo=None, import_names=None, used_symbols=None, declared_in=None):
    d = {
        "name": name,
        "ecosystem": "python",
        "scope": scope,
        "version": version,
        "purpose": purpose,
        "acquisition": "package_manager",
        "locality": "remote",
        "source": "PyPI 注册表",
        "declared_in": declared_in or ["setup.py"],
        "harmony_adapted": adapted,
        "harmony_adapted_source": adapted_source,
    }
    if source_repo:
        d["source_repo"] = source_repo
    if import_names:
        d["import_names"] = import_names
    if used_symbols:
        d["used_symbols"] = used_symbols
    return d

DEPENDENCIES = [
    # runtime
    dep("huggingface-hub", "runtime", ">=1.5.0,<2.0",
        "从 Hugging Face Hub 下载、缓存与管理模型/分词器版本",
        source_repo="https://github.com/huggingface/huggingface_hub",
        used_symbols=["hf_hub_download", "snapshot_download", "HfApi", "try_to_load_from_cache", "constants.HF_HOME"]),
    dep("numpy", "runtime", ">=1.17", "张量与数值计算底层",
        adapted=True, adapted_source="OpenHarmony PC PyPI 镜像 (pypi.cnb.cool/OpenHarmonyPCDeveloper)",
        source_repo="https://github.com/numpy/numpy", used_symbols=["ndarray", "array"]),
    dep("packaging", "runtime", ">=20.0", "版本比较与 PyPA 依赖工具", used_symbols=["version.Version", "version.parse"]),
    dep("pyyaml", "runtime", ">=5.1", "读取模型卡与配置 YAML", used_symbols=["safe_load"]),
    dep("regex", "runtime", ">=2025.10.22", "GPT 类分词器所需正则",
        adapted=True, adapted_source="OpenHarmony PC PyPI 镜像 (pypi.cnb.cool/OpenHarmonyPCDeveloper)"),
    dep("tokenizers", "runtime", ">=0.22.0,<=0.23.0", "Rust 实现的高速分词器",
        adapted=True, adapted_source="OpenHarmony PC PyPI 镜像 (pypi.cnb.cool/OpenHarmonyPCDeveloper)",
        source_repo="https://github.com/huggingface/tokenizers", used_symbols=["PreTrainedTokenizerFast", "Tokenizer"]),
    dep("typer", "runtime", None, "transformers CLI 命令行框架", import_names=["typer"]),
    dep("safetensors", "runtime", ">=0.8.0", "安全/零拷贝加载模型权重",
        adapted=True, adapted_source="OpenHarmony PC PyPI 镜像 (pypi.cnb.cool/OpenHarmonyPCDeveloper)",
        source_repo="https://github.com/huggingface/safetensors", used_symbols=["safe_open", "save_file"]),
    dep("tqdm", "runtime", ">=4.60", "模型下载与训练进度条", used_symbols=["tqdm.auto.tqdm"]),

    # optional core
    dep("torch", "optional", ">=2.4", "PyTorch 后端：模型定义、推理与训练",
        adapted=True, adapted_source="OpenHarmony PC PyPI 镜像 (pypi.cnb.cool/OpenHarmonyPCDeveloper)",
        source_repo="https://github.com/pytorch/pytorch",
        used_symbols=["torch.cuda.is_available", "torch.nn.Module", "torch.load", "torch.device", "torch.tensor"]),
    dep("accelerate", "optional", ">=1.1.0", "分布式训练与设备放置",
        source_repo="https://github.com/huggingface/accelerate"),
    dep("torchvision", "optional", None, "视觉模型与图像变换",
        source_repo="https://github.com/pytorch/vision"),
    dep("Pillow", "optional", ">=10.0.1,<=15.0", "图像解码与预处理",
        adapted=True, adapted_source="OpenHarmony PC PyPI 镜像 (pypi.cnb.cool/OpenHarmonyPCDeveloper)",
        source_repo="https://github.com/python-pillow/Pillow", import_names=["PIL"]),
    dep("torchaudio", "optional", None, "音频数据加载与特征",
        source_repo="https://github.com/pytorch/audio"),
    dep("librosa", "optional", None, "音频特征（梅尔频谱等）",
        source_repo="https://github.com/librosa/librosa"),
    dep("av", "optional", None, "PyAV 音视频解码",
        adapted=True, adapted_source="OpenHarmony PC PyPI 镜像 (pypi.cnb.cool/OpenHarmonyPCDeveloper)",
        source_repo="https://github.com/PyAV-Org/PyAV", import_names=["av"]),
    dep("sentencepiece", "optional", ">=0.1.91,!=0.1.92", "SentencePiece 分词器",
        adapted=True, adapted_source="OpenHarmony PC PyPI 镜像 (pypi.cnb.cool/OpenHarmonyPCDeveloper)",
        source_repo="https://github.com/google/sentencepiece"),
    dep("protobuf", "optional", None, "序列化配置与模型定义",
        adapted=True, adapted_source="OpenHarmony PC PyPI 镜像 (pypi.cnb.cool/OpenHarmonyPCDeveloper)",
        source_repo="https://github.com/protocolbuffers/protobuf"),
    dep("datasets", "optional", ">=2.15.0", "训练数据集加载与处理",
        source_repo="https://github.com/huggingface/datasets"),
    dep("scipy", "optional", None, "科学计算与稀疏矩阵",
        adapted=True, adapted_source="OpenHarmony PC PyPI 镜像 (pypi.cnb.cool/OpenHarmonyPCDeveloper)",
        source_repo="https://github.com/scipy/scipy"),
    dep("scikit-learn", "optional", None, "评估指标与预处理",
        adapted=True, adapted_source="OpenHarmony PC PyPI 镜像 (pypi.cnb.cool/OpenHarmonyPCDeveloper)",
        source_repo="https://github.com/scikit-learn/scikit-learn"),
    dep("timm", "optional", ">=1.0.23", "视觉骨干网络与图像模型",
        source_repo="https://github.com/huggingface/pytorch-image-models", import_names=["timm"]),
    dep("peft", "optional", ">=0.19.0", "参数高效微调（LoRA 等）",
        source_repo="https://github.com/huggingface/peft"),

    # advanced/integrations
    dep("deepspeed", "optional", ">=0.9.3", "ZeRO 分布式训练",
        source_repo="https://github.com/microsoft/DeepSpeed"),
    dep("optuna", "optional", None, "超参搜索",
        source_repo="https://github.com/optuna/optuna"),
    dep("ray", "optional", "[tune]>=2.7.0", "分布式调参",
        source_repo="https://github.com/ray-project/ray"),
    dep("codecarbon", "optional", ">=2.8.1", "训练碳排放追踪"),
    dep("openai", "optional", ">=1.98.0", "OpenAI 兼容 serving 端点"),
    dep("sagemaker", "optional", ">=2.31.0", "Amazon SageMaker 训练集成",
        source_repo="https://github.com/aws/sagemaker-python-sdk"),

    # serving
    dep("fastapi", "optional", None, "serving HTTP API 框架",
        source_repo="https://github.com/tiangolo/fastapi"),
    dep("uvicorn", "optional", None, "ASGI 服务器",
        source_repo="https://github.com/encode/uvicorn"),
    dep("pydantic", "optional", ">=2", "请求/配置数据校验",
        source_repo="https://github.com/pydantic/pydantic"),
    dep("starlette", "optional", None, "ASGI 工具集"),
    dep("rich", "optional", None, "CLI 富文本输出",
        source_repo="https://github.com/Textualize/rich"),

    # other optional
    dep("jinja2", "optional", ">=3.1.0", "chat_template 渲染",
        source_repo="https://github.com/pallets/jinja"),
    dep("tiktoken", "optional", None, "OpenAI tiktoken 分词"),

    # dev/test/build (representative)
    dep("pytest", "dev", ">=7.2.0,<9.0.0", "测试框架"),
    dep("pytest-asyncio", "dev", ">=1.2.0", "异步测试"),
    dep("pytest-xdist", "dev", None, "并行测试"),
    dep("pytest-rerunfailures", "dev", "<16.0", "失败重跑"),
    dep("pytest-timeout", "dev", None, "测试超时"),
    dep("pytest-env", "dev", None, "测试环境变量"),
    dep("ruff", "dev", "==0.14.10", "代码风格检查"),
    dep("GitPython", "dev", "<3.1.19", "版本管理与 quality 工具"),
    dep("transformers-mlinter", "dev", "==0.1.1", "自定义 lint 规则"),
    dep("ty", "dev", "==0.0.20", "类型检查"),
    dep("libcst", "dev", None, "代码重构/格式化"),
    dep("hf-doc-builder", "dev", None, "文档构建"),
]

BY_ECOSYSTEM = {"python": [d["name"] for d in DEPENDENCIES]}

report = {
    "library": {
        "name": "transformers",
        "kind": "framework",
        "package_name": "transformers",
        "aliases": ["huggingface-transformers"],
        "import_names": ["transformers"],
        "source_url": "https://github.com/huggingface/transformers",
        "analyzed_at": "2026-06-29T05:50:31.811Z",
        "commit": "39f89b91dec56a8b1c0e1912db32e9ec3c442396",
        "one_liner": "Hugging Face Transformers 是面向文本、视觉、音频及多模态模型的预训练 Transformer 推理与训练框架。",
        "ecosystem": "python",
        "bindings": []
    },
    "function_summary": {
        "summary": "Transformers 是 Hugging Face 推出的模型定义框架，为文本、计算机视觉、音频、视频及多模态任务提供统一的预训练 Transformer 模型接口。它既支持通过 Pipeline 一行代码完成推理，也提供 AutoModel/AutoTokenizer 自动加载、Trainer 训练循环、生成解码控制、量化与 Hub 集成等能力，主要面向机器学习研究者、算法工程师与应用开发者。",
        "categories": [
            {"name": "Pipeline 高级推理", "description": "提供 task-driven 的高层推理 API，支持文本生成、自动语音识别、图像分类、视觉问答等多模态任务。", "evidence": ["src/transformers/pipelines/base.py:Pipeline", "src/transformers/pipelines/__init__.py"]},
            {"name": "模型架构与自动加载", "description": "集中维护百余种 Transformer 架构的模型定义，并通过 AutoModel/AutoTokenizer/AutoProcessor 按配置自动路由到对应实现。", "evidence": ["src/transformers/models/auto/modeling_auto.py:AutoModel", "src/transformers/core_model_loading.py"]},
            {"name": "分词与预处理", "description": "提供基于 Rust tokenizers、SentencePiece、BPE 等多种后端的分词器，以及图像、音频、视频的特征提取与预处理工具。", "evidence": ["src/transformers/tokenization_utils_base.py", "src/transformers/tokenization_utils_tokenizers.py", "src/transformers/image_processing_utils.py"]},
            {"name": "训练与微调", "description": "通过 Trainer、TrainingArguments 及回调体系，支持在 PyTorch 上进行完整训练、评估、分布式与超参搜索。", "evidence": ["src/transformers/trainer.py:Trainer", "src/transformers/training_args.py:TrainingArguments"]},
            {"name": "生成与解码控制", "description": "提供 GenerationConfig、logits 处理器、采样/束搜索/约束解码等机制，控制语言模型文本生成行为。", "evidence": ["src/transformers/generation/configuration_utils.py:GenerationConfig", "src/transformers/generation/logits_process.py"]},
            {"name": "量化与优化", "description": "集成 bitsandbytes、GPTQ、AWQ、EETQ 等量化后端，以及 torch.compile、融合算子等运行期优化。", "evidence": ["src/transformers/quantizers/quantizer_bnb_4bit.py", "src/transformers/optimization.py"]},
            {"name": "Hub 集成与 CLI", "description": "内置 Hugging Face Hub 下载、缓存、上传与版本管理，并提供 transformers chat/serve/download/env 等命令行入口。", "evidence": ["src/transformers/utils/hub.py", "src/transformers/cli/transformers.py"]}
        ],
        "domain": "machine learning",
        "target_users": "机器学习研究者、算法工程师与应用开发者"
    },
    "languages": METRICS["languages"],
    "code_metrics": METRICS["code_metrics"],
    "tests": {**METRICS["tests"], "notes": METRICS["tests"].get("note", "")},
    "license": {
        "spdx": "Apache-2.0",
        "name": "Apache License 2.0",
        "confidence": "high",
        "is_dual_licensed": False,
        "license_files": ["LICENSE"],
        "evidence": "仓库根目录 LICENSE 文件为 Apache-2.0 全文，且 setup.py:334 声明 license='Apache 2.0 License'。",
        "notes": ""
    },
    "dependencies": {
        "count": len(DEPENDENCIES),
        "manifests": ["setup.py", "pyproject.toml"],
        "by_ecosystem": BY_ECOSYSTEM,
        "dependencies": DEPENDENCIES,
        "notes": "以上为 setup.py 中声明的第一层依赖的代表性子集（install_requires + 常用 extras + 主要 dev/test 工具）。完整依赖列表见 setup.py 的 _deps 与 extras_require。"
    },
    "native_api": {
        "summary": "Transformers 主体为纯 Python，直接调用的底层 API 以 Python 标准库为主；平台耦合集中在 Linux-only 的 /proc/mounts 读取、跨平台分支判断、ffmpeg 子进程调用，以及通过 ctypes 查询 NVIDIA CUDA 运行时版本。",
        "groups": [
            {
                "type": "python_stdlib",
                "category": "standard",
                "platform": "portable",
                "apis": [
                    {"name": "os.path.join / os.path.realpath / os.fspath", "purpose": "路径拼接与解析，用于缓存路径和模型文件定位", "count": 30, "evidence": ["src/transformers/utils/hub.py:107", "src/transformers/modeling_utils.py:322"]},
                    {"name": "os.getenv / os.environ", "purpose": "读取 HF_HOME、TOKENIZERS_PARALLELISM、TRANSFORMERS_VERBOSITY 等环境变量", "count": 30, "evidence": ["src/transformers/utils/hub.py:107", "src/transformers/utils/logging.py:64"]},
                    {"name": "pathlib.Path", "purpose": "面向对象的路径操作", "count": 15, "evidence": ["src/transformers/__init__.py:26", "src/transformers/utils/hub.py:24"]},
                    {"name": "json.loads / json.load", "purpose": "解析模型卡、配置与 ECS 元数据", "count": 10, "evidence": ["src/transformers/utils/hub.py:18", "src/transformers/utils/hub.py:185"]},
                    {"name": "tempfile.mkdtemp", "purpose": "创建临时目录用于下载/解压", "count": 3, "evidence": ["src/transformers/utils/hub.py:22"]},
                    {"name": "importlib.import_module", "purpose": "延迟加载后端与动态模块", "count": 8, "evidence": ["src/transformers/__init__.py:23", "src/transformers/dynamic_module_utils.py"]}
                ]
            },
            {
                "type": "python_subprocess",
                "category": "standard",
                "platform": "portable",
                "apis": [
                    {"name": "subprocess.Popen", "purpose": "启动 ffmpeg 进行音视频解码/麦克风采集", "count": 4, "evidence": ["src/transformers/pipelines/audio_utils.py:33", "src/transformers/pipelines/audio_utils.py:268", "src/transformers/pipelines/audio_classification.py:54"]},
                    {"name": "subprocess.check_output", "purpose": "检测 ninja 构建工具版本", "count": 1, "evidence": ["src/transformers/utils/import_utils.py:998"]},
                    {"name": "subprocess.run", "purpose": "CLI add_new_model_like 中调用仓库维护脚本", "count": 5, "evidence": ["src/transformers/cli/add_new_model_like.py:604"]}
                ]
            },
            {
                "type": "platform_detection",
                "category": "platform",
                "platform": "portable",
                "apis": [
                    {"name": "sys.platform.startswith('linux')", "purpose": "Linux-only 的 hf-mount FUSE 检测分支", "count": 1, "evidence": ["src/transformers/modeling_utils.py:319"], "conditional": True},
                    {"name": "platform.system()", "purpose": "音频 pipeline 根据 Linux/Darwin/Windows 选择 ffmpeg 输入后端", "count": 3, "evidence": ["src/transformers/pipelines/audio_utils.py:91", "src/transformers/cli/system.py:101"], "conditional": True},
                    {"name": "pwd 模块", "purpose": "非 Windows 平台下读取用户主目录信息", "count": 1, "evidence": ["src/transformers/cli/chat.py:41-42"], "conditional": True}
                ]
            },
            {
                "type": "linux_procfs",
                "category": "system",
                "platform": "linux",
                "apis": [
                    {"name": "procfs (/proc/mounts)", "purpose": "读取 Linux 挂载表以检测 hf-mount FUSE 文件系统，避免并行 mmap 死锁", "count": 1, "evidence": ["src/transformers/modeling_utils.py:323"], "conditional": True}
                ]
            },
            {
                "type": "ctypes_ffi",
                "category": "ffi",
                "platform": "portable",
                "apis": [
                    {"name": "ctypes.CDLL", "purpose": "运行时加载 libcudart.so 查询 CUDA 版本", "count": 1, "evidence": ["src/transformers/utils/import_utils.py:238"]},
                    {"name": "ctypes.c_int / ctypes.byref", "purpose": "构造 C 类型参数调用 cudaRuntimeGetVersion", "count": 2, "evidence": ["src/transformers/utils/import_utils.py:251-252"]}
                ]
            },
            {
                "type": "pytorch_cuda",
                "category": "hardware",
                "platform": "portable",
                "apis": [
                    {"name": "torch.cuda.is_available", "purpose": "探测 CUDA GPU 是否可用", "count": 30, "evidence": ["src/transformers/utils/import_utils.py:213", "src/transformers/trainer_utils.py:712"]},
                    {"name": "torch.cuda.empty_cache", "purpose": "释放 GPU 显存缓存", "count": 5, "evidence": ["src/transformers/trainer.py:2775", "src/transformers/trainer_utils.py:714"]},
                    {"name": "torch.cuda.get_device_properties", "purpose": "获取 GPU 计算能力以启用特定内核", "count": 3, "evidence": ["src/transformers/utils/import_utils.py:639", "src/transformers/quantizers/quantizer_finegrained_fp8.py:48"]}
                ]
            }
        ],
        "dynamic_libraries": [
            {
                "name": "libcudart.so",
                "mechanism": "ctypes.CDLL",
                "acquisition": "third_party",
                "source": "NVIDIA CUDA 运行时库（pip 安装的 torch 可能自带 bundled 版本）",
                "description": "运行时加载以查询 CUDA runtime 版本；加载失败会回退到 torch.version.cuda。",
                "optional": True,
                "evidence": ["src/transformers/utils/import_utils.py:238-252"]
            }
        ],
        "platform_dependence": "cross-platform"
    },
    "runtime_surface": {
        "summary": "运行时主要通过网络从 Hugging Face Hub 下载模型与配置，缓存在本地文件系统；读取大量环境变量控制日志、缓存、设备与后端；部分音频/视频能力通过子进程调用 ffmpeg 实现；GPU 加速通过 PyTorch CUDA/XPU/HPU 后端间接使用。",
        "network": [
            {"detail": "HTTP(S) 访问 Hugging Face Hub（hf.co）与 S3/CloudFront 静态资源", "purpose": "下载模型权重、分词器、配置文件", "evidence": ["src/transformers/utils/hub.py:29-41", "src/transformers/utils/hub.py:111-112"]},
            {"detail": "ECS_CONTAINER_METADATA_URI", "purpose": "Amazon ECS 容器元数据查询（SageMaker 环境）", "evidence": ["src/transformers/utils/hub.py:178"]}
        ],
        "filesystem": [
            {"detail": "HF_HOME / ~/.cache/huggingface/hub 缓存目录", "purpose": "持久化存储下载的模型、分词器和配置文件", "evidence": ["src/transformers/utils/hub.py:107"]},
            {"detail": "临时目录 tempfile.mkdtemp", "purpose": "下载/解压期间的临时存储", "evidence": ["src/transformers/utils/hub.py:22"]},
            {"detail": "模型检查点文件 (.bin/.safetensors)", "purpose": "加载权重到内存", "evidence": ["src/transformers/modeling_utils.py:337"]},
            {"detail": "chat_template.jinja / additional_chat_templates", "purpose": "加载对话模板", "evidence": ["src/transformers/utils/hub.py:65-67"]}
        ],
        "env_vars": [
            {"name": "HF_HOME", "purpose": "Hugging Face 缓存与配置根目录", "evidence": ["src/transformers/utils/hub.py:107"]},
            {"name": "HF_MODULES_CACHE", "purpose": "动态模块缓存路径", "evidence": ["src/transformers/utils/hub.py:107"]},
            {"name": "TRANSFORMERS_VERBOSITY", "purpose": "控制日志详细程度", "evidence": ["src/transformers/utils/logging.py:64"]},
            {"name": "TRANSFORMERS_NO_ADVISORY_WARNINGS", "purpose": "关闭建议性警告", "evidence": ["src/transformers/utils/logging.py:322"]},
            {"name": "TOKENIZERS_PARALLELISM", "purpose": "控制分词器多进程", "evidence": ["src/transformers/pipelines/base.py:1193-1195"]},
            {"name": "TRUST_REMOTE_CODE", "purpose": "是否允许执行仓库中的远程自定义代码", "evidence": ["src/transformers/models/rag/retrieval_rag.py:134"]},
            {"name": "CUDA_VISIBLE_DEVICES / CUDA_LAUNCH_BLOCKING / CUBLAS_WORKSPACE_CONFIG", "purpose": "控制 CUDA 设备与确定性行为", "evidence": ["src/transformers/training_args.py:1876", "src/transformers/trainer_utils.py:166-167"]},
            {"name": "ACCELERATE_TORCH_DEVICE / ACCELERATE_MIXED_PRECISION / ACCELERATE_USE_DEEPSPEED", "purpose": "Accelerate 集成的设备与训练配置", "evidence": ["src/transformers/training_args.py:1554", "src/transformers/training_args.py:1876"]},
            {"name": "HF_HUB_DOWNLOAD_TIMEOUT", "purpose": "Hub 下载超时", "evidence": ["pyproject.toml:101"]}
        ],
        "subprocess": [
            {"command": "ffmpeg", "purpose": "音频/视频解码与麦克风采集", "evidence": ["src/transformers/pipelines/audio_utils.py:33", "src/transformers/pipelines/audio_utils.py:105-106", "src/transformers/pipelines/audio_classification.py:54"]},
            {"command": "ninja --version", "purpose": "检测 ninja 构建工具", "evidence": ["src/transformers/utils/import_utils.py:998"]},
            {"command": "python utils/...", "purpose": "CLI add_new_model_like 调用仓库维护脚本（开发工具）", "evidence": ["src/transformers/cli/add_new_model_like.py:604-621"]}
        ],
        "devices": [
            {"detail": "GPU（CUDA/XPU/HPU）", "purpose": "通过 PyTorch 后端进行模型推理/训练加速", "evidence": ["src/transformers/utils/import_utils.py:213", "src/transformers/cli/system.py:112-119"]},
            {"detail": "麦克风", "purpose": "音频 pipeline 实时采集", "evidence": ["src/transformers/pipelines/audio_utils.py:91-106"]}
        ],
        "services": []
    },
    "build_env": {
        "language_standard": "Python >= 3.10",
        "runtime_version": "Python 3.10 – 3.14（setup.py SUPPORTED_PYTHON_VERSIONS）",
        "build_system": "setuptools",
        "compiler_extensions": [],
        "platforms": [
            {"os": "linux", "arch": "x86_64", "evidence": ["setup.py:350 OS Independent", ".github/workflows 多平台 CI", "src/transformers/modeling_utils.py:319 sys.platform"]},
            {"os": "linux", "arch": "arm64", "evidence": ["setup.py:350 OS Independent", "PyTorch aarch64 wheel"]},
            {"os": "macos", "arch": "x86_64", "evidence": ["setup.py:350 OS Independent", "src/transformers/pipelines/audio_utils.py:97 Darwin 分支"]},
            {"os": "macos", "arch": "arm64", "evidence": ["setup.py:350 OS Independent", "PyTorch arm64 wheel"]},
            {"os": "windows", "arch": "x86_64", "evidence": ["setup.py:350 OS Independent", "src/transformers/cli/chat.py:41/666 Windows 分支", "src/transformers/pipelines/audio_utils.py:99 Windows 分支"]}
        ],
        "entry_points": [
            {"type": "console_script", "name": "transformers", "command": "transformers <subcommand>（chat/serve/download/env/version/add_new_model_like）", "evidence": ["setup.py:342", "src/transformers/cli/transformers.py:25-35"]}
        ],
        "packaging": "通过 setuptools 打包为 PyPI wheel/sdist 分发；不捆绑 Python 运行时，终端用户通过 pip/uv 安装。",
        "notes": "仓库为纯 Python 包，不含需要编译的 C/C++ 扩展；可选依赖如 tokenizers/safetensors/torch 提供各自预编译 wheel。"
    },
    "capability_profile": {
        "summary": "本项目不涉及桌面 GUI 与 3D 渲染；触及媒体（音视频解码/麦克风采集）与硬件（GPU 加速）场景，其中 CUDA 为明确不可适配的专有硬件。",
        "scenarios": [
            {"key": "gui", "present": False},
            {"key": "rendering_3d", "present": False},
            {
                "key": "media",
                "present": True,
                "kind": ["audio_decode", "video_decode", "audio_capture"],
                "via": ["av", "librosa", "torchaudio", "ffmpeg"],
                "harmony_status": "partial",
                "adaptation": "音视频 I/O 与编解码依赖外部 ffmpeg/PyAV；在鸿蒙上可替换为 @ohos.multimedia.audio/video，或确认 ffmpeg 可在 OHOS NDK 交叉编译",
                "evidence": ["src/transformers/pipelines/audio_utils.py:33", "src/transformers/pipelines/audio_utils.py:91-106", "src/transformers/pipelines/audio_classification.py:54"]
            },
            {
                "key": "hardware",
                "present": True,
                "kind": ["gpu_cuda"],
                "specific_hardware": True,
                "via": ["torch", "libcudart.so"],
                "harmony_status": "unavailable",
                "adaptation": "CUDA 为 NVIDIA 专有运行时，鸿蒙无等价；仅影响 GPU 加速路径，CPU 路径仍可运行",
                "evidence": ["src/transformers/utils/import_utils.py:238", "src/transformers/trainer.py:3175"]
            }
        ]
    },
    "harmony_adaptation": {
        "target": "HarmonyOS NEXT PC（模型 A：库跑在已移植的 Python 3.12 运行时上；原生扩展经 OHOS NDK/musl 重编；arm64/x86_64；自研内核，无 Linux ABI）",
        "porting_class": "needs_adaptation_partial",
        "feasibility": "hard",
        "effort": {"person_days": [10, 25]},
        "confidence": "medium",
        "recommended_path": "run_on_ported_runtime",
        "summary": "Transformers 主体为纯 Python，且 PyTorch、tokenizers、safetensors、numpy 等核心依赖已确认在 OpenHarmony PC PyPI 镜像有 ohos 构建，因此 CPU 推理/训练路径具备移植基础。主要障碍是 NVIDIA CUDA 加速路径在鸿蒙上无解，以及音视频 pipeline 依赖外部 ffmpeg/PyAV、网络/存储权限授予方式未核实。",
        "target_assumptions": [
            {"id": "ta:python", "capability": "Python 3.10+ 运行时", "required": True, "target_status": "available", "impact": "纯 Python 代码可直接运行在鸿蒙 Python 上", "source": "references/harmony-pc-capabilities.json#runtimes.python"},
            {"id": "ta:pytorch", "capability": "PyTorch 运行时与 CPU 算子后端", "required": True, "target_status": "available", "impact": "核心模型推理/训练依赖 torch；OpenHarmony PC PyPI 镜像已提供 torch-*-ohos wheel", "source": "scripts/harmony_adapted.js（OpenHarmony PC PyPI 镜像）"},
            {"id": "ta:cuda", "capability": "NVIDIA CUDA 运行时", "required": False, "target_status": "unavailable", "impact": "CUDA 加速路径无法移植，但 CPU 路径可用", "source": "references/harmony-pc-capabilities.json#hardware_devices.gpu_compute_cuda"},
            {"id": "ta:internet", "capability": "互联网访问（ohos.permission.INTERNET）", "required": True, "target_status": "unknown", "impact": "默认从 Hugging Face Hub 下载模型；若权限不可授予，需预置本地缓存", "source": "references/harmony-pc-capabilities.json#permissions.perm_internet"},
            {"id": "ta:storage", "capability": "本地文件/存储访问", "required": True, "target_status": "unknown", "impact": "模型缓存与配置文件落盘需要存储权限或沙箱允许", "source": "references/harmony-pc-capabilities.json#permissions.perm_storage"},
            {"id": "ta:media", "capability": "音视频解码与麦克风采集（外部 ffmpeg/PyAV）", "required": False, "target_status": "unknown", "impact": "仅影响 audio/video pipeline；可用 @ohos.multimedia 替换或放弃该功能", "source": "references/harmony-pc-capabilities.json#media"}
        ],
        "unadaptable_apis": [
            {
                "id": "ua:cudart",
                "caused_by": ["ta:cuda"],
                "api": "libcudart.so / cudaRuntimeGetVersion",
                "public_entry": "transformers.utils.import_utils.get_cuda_runtime_version",
                "reason": "CUDA 为 NVIDIA 专有运行时，鸿蒙 PC 无等价实现；通过 ctypes 加载 libcudart.so 查询版本在鸿蒙上必然失败，GPU 加速路径不可用",
                "blocking_native_api": "ctypes.CDLL('libcudart.so') / cudaRuntimeGetVersion",
                "category": "hardware",
                "evidence": ["src/transformers/utils/import_utils.py:238-252"]
            }
        ],
        "required_permissions": [
            {"permission": "ohos.permission.INTERNET", "reason": "默认从 Hugging Face Hub 拉取模型权重与配置", "harmony_status": "unknown", "evidence": ["src/transformers/utils/hub.py:29-41"]},
            {"permission": "读写存储", "reason": "缓存下载的模型、分词器与配置文件到本地文件系统", "harmony_status": "unknown", "evidence": ["src/transformers/utils/hub.py:107"]},
            {"permission": "ohos.permission.MICROPHONE", "reason": "audio_utils 实时采集麦克风输入用于语音 pipeline", "source_capability": "media", "harmony_status": "unknown", "evidence": ["src/transformers/pipelines/audio_utils.py:91-106"]}
        ],
        "blockers": [
            {
                "id": "bk:cuda",
                "issue": "NVIDIA CUDA GPU 加速路径在鸿蒙 PC 上无法运行",
                "severity": "blocker",
                "adaptability": "unadaptable",
                "category": "hardware/cuda",
                "source_dimension": "native_api",
                "harmony_status": "unavailable",
                "remediation": "模型加载/训练默认使用 CPU（或 torch 在鸿蒙支持的其它后端）；涉及 CUDA 的量化器与训练特性需禁用或做条件降级",
                "caused_by": ["ta:cuda"],
                "manifests_as": ["ua:cudart"],
                "evidence": ["src/transformers/utils/import_utils.py:238", "src/transformers/trainer.py:3175"]
            },
            {
                "id": "bk:media",
                "issue": "音频/视频 pipeline 依赖外部 ffmpeg 命令与 PyAV，鸿蒙上可用性未确认",
                "severity": "major",
                "adaptability": "partial",
                "category": "media/ffmpeg",
                "source_dimension": "runtime_surface",
                "harmony_status": "partial",
                "remediation": "音频采集/解码可替换为 @ohos.multimedia.audio/video；或确认 ffmpeg/PyAV 能在 OHOS NDK 上交叉编译；非核心文本/视觉路径不受影响",
                "caused_by": ["ta:media"],
                "evidence": ["src/transformers/pipelines/audio_utils.py:33", "src/transformers/pipelines/audio_utils.py:91-106"]
            },
            {
                "id": "bk:internet",
                "issue": "从 Hugging Face Hub 下载模型依赖互联网权限，鸿蒙 PC 授予方式未核实",
                "severity": "major",
                "adaptability": "partial",
                "category": "permission/network",
                "source_dimension": "runtime_surface",
                "harmony_status": "needs_permission",
                "remediation": "声明 ohos.permission.INTERNET；若权限受限则预下载模型到本地缓存并设置 local_files_only=True",
                "caused_by": ["ta:internet"],
                "evidence": ["src/transformers/utils/hub.py:29-41"]
            },
            {
                "id": "bk:storage",
                "issue": "本地缓存模型文件需要存储访问权限，鸿蒙 PC 权限模型未核实",
                "severity": "major",
                "adaptability": "partial",
                "category": "permission/storage",
                "source_dimension": "runtime_surface",
                "harmony_status": "needs_permission",
                "remediation": "声明读写存储权限或使用鸿蒙沙箱允许的缓存目录；预置资源可降低运行期依赖",
                "caused_by": ["ta:storage"],
                "evidence": ["src/transformers/utils/hub.py:107"]
            }
        ],
        "compatible": [
            {"aspect": "纯 Python 模型定义与配置逻辑", "note": "不依赖平台 API，可直接在鸿蒙 Python 上运行", "evidence": ["src/transformers/__init__.py", "src/transformers/configuration_utils.py"]},
            {"aspect": "已鸿蒙化的核心依赖", "note": "numpy/tokenizers/safetensors/torch/scipy/scikit-learn/Pillow/sentencepiece/protobuf/av/regex 已在 OpenHarmony PC PyPI 镜像提供 ohos wheel", "evidence": ["scripts/harmony_adapted.js 输出"]},
            {"aspect": "Hub 下载/缓存逻辑", "note": "只需网络和存储权限即可复用，无需重写核心逻辑", "evidence": ["src/transformers/utils/hub.py"]}
        ],
        "key_tasks": [
            "在鸿蒙 Python 上安装并验证 torch/ohos 与核心依赖的模型加载/推理路径",
            "对 CUDA 路径做运行时降级：默认 device='cpu'，禁用依赖 torch.cuda 的量化器与训练特性",
            "评估并替换音频/视频 pipeline 中的 ffmpeg/PyAV 调用为 @ohos.multimedia 或交叉编译方案",
            "声明 ohos.permission.INTERNET 与读写存储权限，并给出离线缓存/预置模型方案",
            "验证未鸿蒙化的纯 Python 依赖（huggingface-hub、tqdm、pyyaml、packaging 等）是否可直接运行",
            "跑通核心单元测试子集，确认 CPU 路径稳定性"
        ],
        "notes": "评估基于生产代码，测试与示例已排除。核心模型推理/训练因 torch 已鸿蒙化而具备较高可行性，但 CUDA 加速、媒体 I/O 以及网络/存储权限是当前主要不确定点，故 confidence 为 medium。若目标部署形态改为 ArkTS 沙箱应用（模型 B），Python 运行时不可用，结论将显著收紧。"
    },
    "meta": {
        "schema_version": "1.0",
        "analyzer": "pc-lib-analyzer",
        "counter_tool": METRICS["code_metrics"]["tool"],
        "confidence_overall": "medium",
        "warnings": [],
        "observations": [
            {"dimension": "function_summary", "field": "kind", "kind": "new_value", "value": "framework", "rationale": "Transformers 作为模型定义框架被训练/推理框架消费，而非单纯被调用的库，故使用 framework 比 library 更准确。"},
            {"dimension": "capability_profile", "field": "scenarios", "kind": "new_value", "value": "media", "rationale": "Transformers 生产代码通过 ffmpeg/PyAV 处理音视频并采集麦克风，符合 media 场景；该场景由音频/视觉 pipeline 引入。"},
            {"dimension": "capability_profile", "field": "scenarios", "kind": "new_value", "value": "hardware", "rationale": "生产代码直接通过 ctypes 加载 libcudart.so 并通过 torch.cuda 探测 GPU，因此 hardware 场景 present 且 specific_hardware=true。"}
        ]
    }
}

out = RUN_DIR / "report.json"
out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
print(f"Wrote {out}")
