import json

with open('runs/pc-lib-3456/mpg123/2026-07-11T00-16-51-712Z/metrics.json', 'rb') as f:
    raw = f.read()

# Replace garbled UTF-8 bytes that appear in Chinese notes fields
# The garbled bytes are in positions where CJK characters should be
# We'll just replace with clean ASCII notes
text = raw.decode('utf-8', errors='replace')

# Parse with replacements
data = json.loads(text)

# Fix the notes fields with clean ASCII
data['code_metrics']['platform_adaptation']['notes'] = (
    "Mechanical count: C/C++ source lines wrapped in platform-specific "
    "#ifdef/_WIN32/__APPLE__/__linux__ macros. #ifndef excluded. "
    "Comments and string literals excluded."
)
data['code_metrics']['platform_branches']['notes'] = (
    "Mechanical count: runtime platform branch occurrences "
    "(sys.platform/os.name/process.platform/runtime.GOOS/cfg!/RuntimeInformation). "
    "C/C++ preprocessor covered by platform_adaptation. "
    "Comments and string literals excluded."
)
data['code_metrics']['arch_specific']['notes'] = (
    "Mechanical count: architecture-specific code - assembly files (.s/.asm, "
    "LOC by path keywords x86/arm/riscv/generic), SIMD intrinsics headers, "
    "SIMD intrinsic uses (_mm*/__m256/vld1q/*), inline asm (__asm__/asm!). "
    "Comments and string literals excluded. "
    "x86-only SIMD without arm equivalent = adaptation gap for arm64 HarmonyOS PC."
)

with open('runs/pc-lib-3456/mpg123/2026-07-11T00-16-51-712Z/metrics.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Fixed metrics.json")
