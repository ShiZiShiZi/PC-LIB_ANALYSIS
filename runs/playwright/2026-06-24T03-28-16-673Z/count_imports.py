import re, os, json
root = r'repos/playwright/packages'
patterns = {
  'fs': r"import\s+.*\s+from\s+['\"]fs['\"]|import\s+.*\s+from\s+['\"]node:fs['\"]|require\(['\"]fs['\"]\)",
  'path': r"import\s+.*\s+from\s+['\"]path['\"]|import\s+.*\s+from\s+['\"]node:path['\"]|require\(['\"]path['\"]\)",
  'os': r"import\s+.*\s+from\s+['\"]os['\"]|import\s+.*\s+from\s+['\"]node:os['\"]|require\(['\"]os['\"]\)",
  'child_process': r"import\s+.*\s+from\s+['\"]child_process['\"]|import\s+.*\s+from\s+['\"]node:child_process['\"]|require\(['\"]child_process['\"]\)",
  'net': r"import\s+.*\s+from\s+['\"]net['\"]|import\s+.*\s+from\s+['\"]node:net['\"]|require\(['\"]net['\"]\)",
  'http': r"import\s+.*\s+from\s+['\"]http['\"]|import\s+.*\s+from\s+['\"]node:http['\"]|require\(['\"]http['\"]\)",
  'https': r"import\s+.*\s+from\s+['\"]https['\"]|import\s+.*\s+from\s+['\"]node:https['\"]|require\(['\"]https['\"]\)",
  'crypto': r"import\s+.*\s+from\s+['\"]crypto['\"]|import\s+.*\s+from\s+['\"]node:crypto['\"]|require\(['\"]crypto['\"]\)",
  'stream': r"import\s+.*\s+from\s+['\"]stream['\"]|import\s+.*\s+from\s+['\"]node:stream['\"]|require\(['\"]stream['\"]\)",
  'util': r"import\s+.*\s+from\s+['\"]util['\"]|import\s+.*\s+from\s+['\"]node:util['\"]|require\(['\"]util['\"]\)",
  'events': r"import\s+.*\s+from\s+['\"]events['\"]|import\s+.*\s+from\s+['\"]node:events['\"]|require\(['\"]events['\"]\)",
  'zlib': r"import\s+.*\s+from\s+['\"]zlib['\"]|import\s+.*\s+from\s+['\"]node:zlib['\"]|require\(['\"]zlib['\"]\)",
  'readline': r"import\s+.*\s+from\s+['\"]readline['\"]|import\s+.*\s+from\s+['\"]node:readline['\"]|require\(['\"]readline['\"]\)",
  'url': r"import\s+.*\s+from\s+['\"]url['\"]|import\s+.*\s+from\s+['\"]node:url['\"]|require\(['\"]url['\"]\)",
  'http2': r"import\s+.*\s+from\s+['\"]http2['\"]|import\s+.*\s+from\s+['\"]node:http2['\"]|require\(['\"]http2['\"]\)",
}
counts = {k:0 for k in patterns}
for dirpath, _, files in os.walk(root):
    for f in files:
        if not f.endswith('.ts'): continue
        p = os.path.join(dirpath, f)
        try:
            text = open(p, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        for name, pat in patterns.items():
            counts[name] += len(re.findall(pat, text))
print(json.dumps(counts, indent=2))
