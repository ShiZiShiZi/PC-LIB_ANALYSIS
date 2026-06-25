#!/usr/bin/env python3
"""Generate report.json for eslint analysis."""
import json
from pathlib import Path

ROOT = Path("/Users/yt/task/pc-lib-analysis")
REPO = ROOT / "repos/software84/eslint"
RUN = ROOT / "runs/software84/eslint/2026-06-25T11-36-24-342Z"

metrics = json.loads((RUN / "metrics.json").read_text())

# ---------- library ----------
library = {
    "name": "eslint",
    "kind": "tool",
    "package_name": "eslint",
    "aliases": [],
    "import_names": ["eslint"],
    "source_url": "https://github.com/eslint/eslint.git",
    "analyzed_at": "2026-06-25T11:36:24.342Z",
    "commit": "6a42034a57a816b0a313720b3b9df09455bd0b5e",
    "one_liner": "基于 AST 的可插拔 JavaScript/ECMAScript 代码模式检查与自动修复工具，提供 CLI 与程序化 API。",
    "ecosystem": "nodejs",
    "bindings": []
}

# ---------- function_summary ----------
function_summary = {
    "summary": "ESLint 是一款面向 JavaScript/ECMAScript 的静态代码分析工具，通过 Espree 解析器生成 AST，并基于可插拔规则对代码中的潜在问题、风格违规与逻辑错误进行检查和自动修复。它既可以直接通过 CLI 运行（npx eslint），也可以作为 Node.js 库被集成到编辑器、CI 流水线或其他构建工具中。",
    "categories": [
        {
            "name": "JavaScript 解析与 AST 抽象",
            "description": "使用 Espree 将源码解析为 ESTree AST，并提供 SourceCode、TokenStore、Traverser 等抽象，用于规则访问节点、token 和注释。",
            "evidence": ["lib/languages/js/index.js", "lib/languages/js/source-code/source-code.js", "lib/shared/traverser.js"]
        },
        {
            "name": "规则引擎与 Lint 执行",
            "description": "Linter 负责加载并执行规则监听器，生成 lint 消息；内置数百条核心规则覆盖语法、风格、最佳实践与潜在错误。",
            "evidence": ["lib/linter/linter.js", "lib/rules/", "lib/linter/source-code-traverser.js"]
        },
        {
            "name": "配置加载与合并",
            "description": "基于 Flat Config 的配置数组系统，支持 eslint.config.js、extends、plugins、ignore 模式与级联合并。",
            "evidence": ["lib/config/config-loader.js", "lib/config/flat-config-array.js", "lib/config/config.js"]
        },
        {
            "name": "自动修复（Autofix）",
            "description": "SourceCodeFixer 根据规则返回的 fixer 对象计算并应用最小文本替换，实现代码自动修复。",
            "evidence": ["lib/linter/source-code-fixer.js"]
        },
        {
            "name": "CLI 与格式化输出",
            "description": "bin/eslint.js 与 lib/cli.js 提供命令行参数解析、结果格式化、输出文件写入、退出码控制与版本/环境信息展示。",
            "evidence": ["bin/eslint.js", "lib/cli.js", "lib/options.js"]
        },
        {
            "name": "多线程并行 Lint",
            "description": "ESLint 类在并发模式下通过 Node.js worker_threads 创建多个 Worker 分片处理文件，以加速大量文件的 lint 过程。",
            "evidence": ["lib/eslint/eslint.js", "lib/eslint/worker.js"]
        },
        {
            "name": "规则测试工具",
            "description": "RuleTester 为规则作者提供 Valid/Invalid 测试用例运行与断言封装，是插件开发生态的重要组成部分。",
            "evidence": ["lib/rule-tester/rule-tester.js"]
        }
    ],
    "domain": "static analysis / developer tooling",
    "target_users": "JavaScript/TypeScript 开发者、构建工具与编辑器插件作者"
}

# ---------- license ----------
license = {
    "spdx": "MIT",
    "name": "MIT License",
    "confidence": "high",
    "is_dual_licensed": False,
    "license_files": ["LICENSE"],
    "evidence": "LICENSE 文件为 MIT 许可完整文本；package.json 中 license 字段声明为 MIT。",
    "notes": "宽松许可，需保留版权声明。"
}

# ---------- dependencies ----------
deps_data = [
    ("@eslint-community/eslint-utils", "^4.8.0", "https://github.com/eslint/eslint-utils", ["findVariable", "getStaticValue", "ReferenceTracker", "CALL"]),
    ("@eslint-community/regexpp", "^4.12.2", "https://github.com/eslint-community/regexpp", ["RegExpParser", "visitRegExpAST", "RegExpValidator"]),
    ("@eslint/config-array", "^0.23.5", "https://github.com/eslint/config-array", ["ConfigArray", "ConfigArraySymbol"]),
    ("@eslint/config-helpers", "^0.6.0", "https://github.com/eslint/config-helpers", ["defineConfig", "globalIgnores", "includeIgnoreFile"]),
    ("@eslint/core", "^1.2.1", "https://github.com/eslint/core", ["Language", "RuleDefinition", "SourceRange"]),
    ("@eslint/plugin-kit", "^0.7.2", "https://github.com/eslint/plugin-kit", ["ConfigCommentParser", "VisitNodeStep", "CallMethodStep", "Directive"]),
    ("@humanfs/node", "^0.16.6", None, ["hfs.walk", "hfs.isDirectory"]),
    ("@humanwhocodes/module-importer", "^1.0.1", "https://github.com/humanwhocodes/module-importer", ["ModuleImporter"]),
    ("@humanwhocodes/retry", "^0.4.2", "https://github.com/humanwhocodes/retry", ["Retrier"]),
    ("@types/estree", "^1.0.6", "https://github.com/DefinitelyTyped/DefinitelyTyped", []),
    ("ajv", "^6.14.0", "https://github.com/ajv-validator/ajv", ["Ajv"]),
    ("cross-spawn", "^7.0.6", "https://github.com/moxystudio/node-cross-spawn", ["spawn.sync"]),
    ("debug", "^4.3.2", "https://github.com/debug-js/debug", ["debug", "createDebug"]),
    ("escape-string-regexp", "^4.0.0", "https://github.com/sindresorhus/escape-string-regexp", ["escapeRegExp"]),
    ("eslint-scope", "^9.1.2", "https://github.com/eslint/eslint-scope", ["eslint-scope"]),
    ("eslint-visitor-keys", "^5.0.1", "https://github.com/eslint/eslint-visitor-keys", ["VisitorKeys"]),
    ("espree", "^11.2.0", "https://github.com/eslint/espree", ["espree.parse"]),
    ("esquery", "^1.7.0", "https://github.com/estools/esquery", ["esquery"]),
    ("esutils", "^2.0.2", "https://github.com/estools/esutils", ["esutils"]),
    ("fast-deep-equal", "^3.1.3", "https://github.com/epoberezkin/fast-deep-equal", ["equal"]),
    ("file-entry-cache", "^8.0.0", "https://github.com/royriojas/file-entry-cache", ["create", "getFileDescriptor", "reconcile"]),
    ("find-up", "^5.0.0", "https://github.com/sindresorhus/find-up", ["findUp"]),
    ("glob-parent", "^6.0.2", "https://github.com/gulpjs/glob-parent", ["globParent"]),
    ("ignore", "^5.2.0", "https://github.com/kaelzhang/node-ignore", ["ignore"]),
    ("imurmurhash", "^0.1.4", None, ["imurmurhash"]),
    ("is-glob", "^4.0.0", "https://github.com/micromatch/is-glob", ["isGlob"]),
    ("json-stable-stringify-without-jsonify", "^1.0.1", None, ["stringify"]),
    ("minimatch", "^10.2.4", "https://github.com/isaacs/minimatch", ["minimatch", "Minimatch"]),
    ("natural-compare", "^1.4.0", None, ["naturalCompare"]),
    ("optionator", "^0.9.3", "https://github.com/gkz/optionator", ["optionator"]),
]

dependencies = {
    "count": len(deps_data) + 1,  # plus jiti peer
    "manifests": ["package.json"],
    "by_ecosystem": {"nodejs": len(deps_data) + 1},
    "dependencies": []
}

for name, version, repo, used in deps_data:
    dependencies["dependencies"].append({
        "name": name,
        "ecosystem": "nodejs",
        "registry_name": name,
        "source_repo": repo,
        "import_names": [name],
        "aliases": [],
        "scope": "runtime",
        "version": version,
        "purpose": "运行时依赖",
        "acquisition": "package_manager",
        "locality": "remote",
        "source": "npm registry",
        "declared_in": ["package.json"],
        "used_symbols": used,
        "harmony_adapted": False,
        "harmony_adapted_source": None
    })

dependencies["dependencies"].append({
    "name": "jiti",
    "ecosystem": "nodejs",
    "registry_name": "jiti",
    "source_repo": "https://github.com/unjs/jiti",
    "import_names": ["jiti"],
    "aliases": [],
    "scope": "peer",
    "version": "*",
    "purpose": "可选 peer dependency，用于在需要时加载 TypeScript 配置文件",
    "acquisition": "package_manager",
    "locality": "remote",
    "source": "npm registry（可选 peer dependency）",
    "declared_in": ["package.json"],
    "used_symbols": [],
    "harmony_adapted": False,
    "harmony_adapted_source": None
})

dependencies["notes"] = "仅列出 package.json dependencies 与可选 peerDependencies；devDependencies 为构建/测试工具，未计入运行时依赖。"

# ---------- native_api ----------
native_api = {
    "summary": "仅使用 Node.js 标准库与进程 API，无平台专有或硬件 API；整体跨平台。",
    "groups": [
        {
            "type": "node_fs",
            "category": "standard",
            "platform": "portable",
            "apis": [
                {"name": "fs.readFileSync", "purpose": "读取被 lint 文件或缓存源文本", "count": 2, "evidence": ["lib/cli-engine/lint-result-cache.js:129", "lib/rule-tester/rule-tester.js:697"]},
                {"name": "fs.promises.readFile", "purpose": "读取抑制文件内容", "count": 1, "evidence": ["lib/services/suppressions-service.js:217"]},
                {"name": "fs.promises.writeFile", "purpose": "将修复后的代码写回磁盘", "count": 1, "evidence": ["lib/eslint/eslint.js:825"]},
                {"name": "fs.promises.writeFile", "purpose": "写入抑制文件", "count": 1, "evidence": ["lib/services/suppressions-service.js:240"]},
                {"name": "fs.promises.unlink", "purpose": "删除缓存文件", "count": 1, "evidence": ["lib/eslint/eslint.js:1017"]},
                {"name": "fs.promises.stat", "purpose": "获取配置文件修改时间", "count": 1, "evidence": ["lib/config/config-loader.js:205"]},
                {"name": "fs.promises.mkdir", "purpose": "创建输出文件所在目录", "count": 1, "evidence": ["lib/cli.js:132"]},
                {"name": "fs.existsSync", "purpose": "检查缓存/抑制文件是否存在", "count": 3, "evidence": ["lib/cli.js:408", "lib/cli.js:422", "lib/eslint/eslint.js:777"]}
            ]
        },
        {
            "type": "node_path",
            "category": "standard",
            "platform": "portable",
            "apis": [
                {"name": "path.resolve", "purpose": "将相对路径解析为绝对路径", "count": 20, "evidence": ["lib/cli.js:121", "lib/eslint/eslint.js:1161", "lib/eslint/eslint-helpers.js:570"]},
                {"name": "path.join", "purpose": "拼接文件路径", "count": 5, "evidence": ["lib/eslint/eslint.js:248", "lib/eslint/eslint.js:1364"]},
                {"name": "path.isAbsolute", "purpose": "判断路径是否为绝对路径", "count": 2, "evidence": ["lib/eslint/eslint.js:152", "lib/eslint/eslint.js:821"]},
                {"name": "path.extname", "purpose": "获取文件扩展名", "count": 2, "evidence": ["lib/linter/linter.js:912", "lib/eslint/eslint.js:937"]},
                {"name": "path.dirname", "purpose": "获取文件所在目录", "count": 1, "evidence": ["lib/eslint/eslint.js:257"]},
                {"name": "path.relative", "purpose": "计算相对路径", "count": 3, "evidence": ["lib/shared/runtime-info.js:36", "lib/eslint/eslint-helpers.js:208"]},
                {"name": "path.sep", "purpose": "根据平台选择路径分隔符", "count": 1, "evidence": ["lib/eslint/eslint-helpers.js:194"]}
            ]
        },
        {
            "type": "node_url",
            "category": "standard",
            "platform": "portable",
            "apis": [
                {"name": "pathToFileURL", "purpose": "将文件路径转换为 file:// URL，用于 Worker/模块加载", "count": 7, "evidence": ["lib/eslint/eslint.js:464", "lib/cli.js:69", "lib/config/config-loader.js:15"]}
            ]
        },
        {
            "type": "node_process",
            "category": "standard",
            "platform": "portable",
            "apis": [
                {"name": "process.cwd", "purpose": "获取当前工作目录作为配置/输出基准", "count": 6, "evidence": ["lib/linter/linter.js:717", "lib/cli.js:186", "lib/eslint/eslint-helpers.js:775"]},
                {"name": "process.argv", "purpose": "读取命令行参数", "count": 6, "evidence": ["bin/eslint.js:18", "bin/eslint.js:122", "lib/cli.js:201"]},
                {"name": "process.stdin", "purpose": "读取标准输入的待 lint 文本", "count": 2, "evidence": ["bin/eslint.js:52"]},
                {"name": "process.hrtime.bigint", "purpose": "高精度计时用于性能统计", "count": 5, "evidence": ["lib/eslint/eslint.js:81", "lib/eslint/worker.js:8", "lib/eslint/eslint-helpers.js:34"]},
                {"name": "process.exitCode", "purpose": "设置进程退出码", "count": 4, "evidence": ["bin/eslint.js:87", "bin/eslint.js:143", "bin/eslint.js:209"]},
                {"name": "process.on", "purpose": "监听未捕获异常与未处理 Promise 拒绝", "count": 3, "evidence": ["bin/eslint.js:165", "bin/eslint.js:166"]},
                {"name": "process.version", "purpose": "展示 Node 版本信息", "count": 2, "evidence": ["lib/shared/runtime-info.js:153", "lib/cli-engine/lint-result-cache.js:31"]},
                {"name": "process.kill", "purpose": "转发子进程信号", "count": 1, "evidence": ["bin/eslint.js:83"]}
            ]
        },
        {
            "type": "node_os",
            "category": "standard",
            "platform": "portable",
            "apis": [
                {"name": "os.availableParallelism", "purpose": "计算并发 Worker 数量", "count": 1, "evidence": ["lib/eslint/eslint.js:420"]},
                {"name": "os.platform", "purpose": "获取操作系统平台用于环境信息输出", "count": 1, "evidence": ["lib/shared/runtime-info.js:157"]},
                {"name": "os.release", "purpose": "获取操作系统版本用于环境信息输出", "count": 1, "evidence": ["lib/shared/runtime-info.js:157"]}
            ]
        },
        {
            "type": "node_worker_threads",
            "category": "standard",
            "platform": "portable",
            "apis": [
                {"name": "Worker", "purpose": "创建并发 lint Worker", "count": 1, "evidence": ["lib/eslint/eslint.js:489"]},
                {"name": "SHARE_ENV", "purpose": "Worker 共享环境变量", "count": 1, "evidence": ["lib/eslint/eslint.js:17"]},
                {"name": "parentPort.postMessage", "purpose": "Worker 向主线程回传结果", "count": 1, "evidence": ["lib/eslint/worker.js:172"]},
                {"name": "isMainThread", "purpose": "区分主线程与 Worker 线程的日志标签", "count": 1, "evidence": ["lib/eslint/eslint-helpers.js:14"]},
                {"name": "workerData", "purpose": "向 Worker 传递待处理文件索引", "count": 1, "evidence": ["lib/eslint/worker.js:70"]}
            ]
        },
        {
            "type": "node_child_process",
            "category": "system",
            "platform": "portable",
            "apis": [
                {"name": "spawn.sync (via cross-spawn)", "purpose": "启动 npm/npx 子进程（--init/--inspect-config/环境信息）", "count": 5, "evidence": ["bin/eslint.js:71", "lib/shared/runtime-info.js:53", "lib/cli.js:269"], "conditional": False}
            ]
        }
    ],
    "dynamic_libraries": [],
    "platform_dependence": "cross-platform"
}

# ---------- runtime_surface ----------
runtime_surface = {
    "summary": "运行时主要与本地文件系统交互；无外网请求；可选地通过 cross-spawn 调用 npm/npx；读取 TIMING/ESLINT_FLAGS 环境变量。",
    "network": [],
    "filesystem": [
        {"detail": "lint 目标文件与 glob 匹配结果", "purpose": "读取并分析用户指定的 JS/TS 等源码文件", "evidence": ["lib/eslint/eslint-helpers.js:303", "lib/eslint/eslint-helpers.js:365"]},
        {"detail": "eslint.config.js / 配置文件", "purpose": "加载并合并 flat config 配置", "evidence": ["lib/config/config-loader.js:205", "lib/config/config-loader.js:324"]},
        {"detail": ".eslintcache 缓存文件", "purpose": "缓存 lint 结果以加速增量检查", "evidence": ["lib/cli-engine/lint-result-cache.js:92", "lib/cli-engine/lint-result-cache.js:216"]},
        {"detail": "suppressions 文件", "purpose": "读取/写入问题抑制记录", "evidence": ["lib/services/suppressions-service.js:120", "lib/services/suppressions-service.js:217", "lib/services/suppressions-service.js:240"]},
        {"detail": "CLI --output-file 输出文件", "purpose": "将格式化后的 lint 结果写入磁盘", "evidence": ["lib/cli.js:121", "lib/cli.js:132", "lib/cli.js:133"]},
        {"detail": "标准输入（--stdin）", "purpose": "从管道读取待 lint 代码文本", "evidence": ["bin/eslint.js:52"]}
    ],
    "env_vars": [
        {"name": "TIMING", "purpose": "启用规则性能计时", "evidence": ["lib/linter/timing.js:44", "lib/linter/timing.js:56", "lib/linter/timing.js:60"]},
        {"name": "ESLINT_FLAGS", "purpose": "通过环境变量注入 ESLint 功能标志", "evidence": ["lib/eslint/eslint-helpers.js:1326", "lib/eslint/eslint-helpers.js:1330"]}
    ],
    "subprocess": [
        {"command": "npm init @eslint/config@latest", "purpose": "--init 旧命令透传到 @eslint/create-config", "evidence": ["bin/eslint.js:169", "bin/eslint.js:175"]},
        {"command": "npx @eslint/mcp@latest", "purpose": "--mcp 命令透传到 @eslint/mcp", "evidence": ["bin/eslint.js:180", "bin/eslint.js:185"]},
        {"command": "npx @eslint/config-inspector@latest", "purpose": "--inspect-config 调用配置检查器", "evidence": ["lib/cli.js:262", "lib/cli.js:274"]},
        {"command": "npm bin -g / npm ls --depth=0 --json eslint", "purpose": "--env-info 获取本地/全局 ESLint 版本信息", "evidence": ["lib/shared/runtime-info.js:53", "lib/shared/runtime-info.js:100"]}
    ],
    "devices": [],
    "services": []
}

# ---------- build_env ----------
build_env = {
    "language_standard": "JavaScript (Node.js LTS)",
    "runtime_version": "Node.js ^20.19.0 || ^22.13.0 || >=24",
    "build_system": "npm（配合自定义 Makefile.js 脚本）",
    "compiler_extensions": [],
    "platforms": [
        {"os": "linux", "arch": "x86_64", "evidence": [".github/workflows/ci.yml"]},
        {"os": "windows", "arch": "x86_64", "evidence": [".github/workflows/ci.yml"]},
        {"os": "macos", "arch": "x86_64", "evidence": [".github/workflows/ci.yml"]}
    ],
    "entry_points": [
        {"type": "launcher", "name": "bin/eslint.js", "command": "node bin/eslint.js [options] [file|dir|glob]*", "evidence": ["bin/eslint.js", "package.json bin.eslint"]}
    ],
    "packaging": "npm 包（tarball）分发，不捆绑 Node 运行时；目标环境需自行安装 Node.js。",
    "notes": "通过 npm / pnpm / yarn 安装；无原生二进制或 GUI 启动器。"
}

# ---------- capability_profile ----------
capability_profile = {
    "summary": "ESLint 为纯命令行/库形态工具，不涉及 GUI、3D 渲染、媒体编解码或特定硬件访问。",
    "scenarios": [
        {"key": "gui", "present": False},
        {"key": "rendering_3d", "present": False},
        {"key": "media", "present": False},
        {"key": "hardware", "present": False}
    ]
}

# ---------- harmony_adaptation ----------
harmony_adaptation = {
    "target": "HarmonyOS NEXT PC（跑在已移植的 Node.js 运行时上；arm64/x86_64；自研内核，无 Linux ABI）",
    "porting_class": "no_adaptation",
    "feasibility": "feasible",
    "effort": {"person_days": [0, 2]},
    "confidence": "high",
    "recommended_path": "run_on_ported_runtime",
    "summary": "ESLint 是纯 Node.js 工具，核心 lint/规则/配置逻辑均为 JavaScript，依赖的第三方包也均为 JS 包；鸿蒙 PC 已移植 Node.js，直接安装运行即可。仅有 --init/--inspect-config/--env-info 等旁路命令会调用 npm/npx，需目标环境具备 npm 生态，但不影响核心功能。",
    "blockers": [],
    "unadaptable_apis": [],
    "target_assumptions": [
        {
            "id": "ta:nodejs",
            "capability": "Node.js 运行时已移植到 HarmonyOS PC",
            "required": True,
            "target_status": "available",
            "impact": "ESLint 所有功能均依赖 Node.js，运行时已可用则无需代码级移植",
            "source": "references/harmony-pc-capabilities.json#runtimes.nodejs"
        },
        {
            "id": "ta:npm_cli",
            "capability": "npm / npx 命令在 HarmonyOS PC 上可用",
            "required": False,
            "target_status": "unknown",
            "impact": "仅 --init/--inspect-config/--env-info 等可选命令依赖；核心 lint 不依赖",
            "source": "references/harmony-pc-capabilities.json#process_security.spawn"
        }
    ],
    "required_permissions": [],
    "compatible": [
        {"aspect": "纯 JavaScript 规则引擎与 AST 遍历", "note": "不依赖平台 API，可直接在鸿蒙 Node.js 上运行", "evidence": ["lib/linter/linter.js", "lib/rules/"]},
        {"aspect": "Node.js 标准文件/路径/Worker API", "note": "均属于已移植运行时的标准能力", "evidence": ["lib/eslint/eslint.js", "lib/eslint/worker.js", "lib/eslint/eslint-helpers.js"]},
        {"aspect": "全部运行时依赖均为 JS 包", "note": "无原生扩展、无 N-API/ctypes，无需 OHOS NDK 重编", "evidence": ["package.json dependencies"]}
    ],
    "key_tasks": [
        "在鸿蒙 PC 上安装 Node.js 并运行 npm install eslint",
        "验证 worker_threads 多线程 lint 在鸿蒙 Node.js 上正常创建 Worker",
        "验证可选的 npm/npx 旁路命令（--init/--inspect-config/--env-info）在目标环境是否可用，必要时引导用户使用替代命令"
    ],
    "notes": "评估按模型 A（库/CLI 工具跑在已移植的 Node.js 运行时上）；tools/ 目录下的维护脚本未纳入运行时迁移阻碍。"
}

# ---------- meta ----------
meta = {
    "schema_version": "1.0",
    "analyzer": "pc-lib-analyzer",
    "counter_tool": metrics["code_metrics"]["tool"],
    "warnings": [],
    "confidence_overall": "high",
    "observations": [
        {
            "dimension": "native_api",
            "field": "production_scope",
            "kind": "gap",
            "value": "tools/ 目录为构建/维护脚本",
            "rationale": "metrics 脚本按目录名将 tools/ 判为 production，但该目录脚本（文档生成、fuzzer、check-emfile-handling 等）不参与 ESLint 运行时功能，本报告在 native_api / runtime_surface / harmony_adaptation 中按运行时库口径收敛，未将其平台判断分支（os.platform）作为迁移阻碍。"
        }
    ]
}

report = {
    "library": library,
    "function_summary": function_summary,
    "languages": metrics["languages"],
    "code_metrics": metrics["code_metrics"],
    "tests": {
        "test_files": metrics["tests"]["test_files"],
        "test_cases": metrics["tests"]["test_cases"],
        "frameworks": ["mocha"],
        "by_language": metrics["tests"]["by_language"],
        "notes": "测试框架为 Mocha；metrics 脚本识别出 jest/mocha 模式，实际仓库以 Mocha 为主。"
    },
    "license": license,
    "dependencies": dependencies,
    "native_api": native_api,
    "runtime_surface": runtime_surface,
    "build_env": build_env,
    "capability_profile": capability_profile,
    "harmony_adaptation": harmony_adaptation,
    "meta": meta
}

out = RUN / "report.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {out}")
