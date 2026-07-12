#!/usr/bin/env python3
"""Extract declared external dependencies from GStreamer's own meson.build files.
Excludes test/example directories and internal gstreamer subprojects."""
import json, re, os
from pathlib import Path

ROOT = Path('repos/pc-lib-3456/gstreamer')
RUN = Path('runs/pc-lib-3456/gstreamer/2026-07-03T13-34-52-216Z')

# Load metrics to know top_dirs categories (optional)
metrics = json.loads((RUN / 'metrics.json').read_text())
test_dirs = set(metrics.get('code_metrics', {}).get('test_example_dirs', []))

def is_excluded(p: Path) -> bool:
    parts = p.relative_to(ROOT).parts
    # Exclude external fallback sources if present
    if parts[:1] == ('subprojects',):
        # Keep only project modules (gst-*/gstreamer/gst-*) and top-level
        if len(parts) > 1 and not parts[1].startswith(('gst-', 'gstreamer')):
            return True
    # Exclude obvious test/example dirs by path token
    lower = '/'.join(parts).lower()
    for token in ('/tests/', '/test/', '/examples/', '/demos/', '/docs/', '/ci/'):
        if token in lower:
            return True
    return False

# Regexes for meson declarations
# dependency('name', ...) or dependency("name", ...)
dep_re = re.compile(r"dependency\s*\(\s*['\"]([^'\"]+)['\"]")
# cc.find_library('name', ...)
findlib_re = re.compile(r"find_library\s*\(\s*['\"]([^'\"]+)['\"]")
# pkg_check_modules(prefix, 'name' ...) or pkg_check_modules('name', ...)
pkg_re = re.compile(r"pkg_check_modules\s*\(\s*(?:['\"][^'\"]+['\"]\s*,\s*)?((?:\s*['\"][^'\"]+['\"]\s*,?\s*)+)\)")
# dependency('name', fallback : ...)

results = []
for buildfile in sorted(ROOT.rglob('meson.build')):
    if is_excluded(buildfile):
        continue
    try:
        text = buildfile.read_text(errors='ignore')
    except Exception:
        continue
    rel = str(buildfile.relative_to(ROOT))
    for m in dep_re.finditer(text):
        results.append({'kind': 'dependency', 'name': m.group(1), 'file': rel})
    for m in findlib_re.finditer(text):
        results.append({'kind': 'find_library', 'name': m.group(1), 'file': rel})
    for m in pkg_re.finditer(text):
        # split quoted tokens
        tokens = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
        for t in tokens:
            results.append({'kind': 'pkg_check_modules', 'name': t, 'file': rel})

# Deduplicate by (kind, name)
seen = set()
uniq = []
for r in results:
    key = (r['kind'], r['name'])
    if key in seen:
        continue
    seen.add(key)
    uniq.append(r)

# Filter out project-internal dependency names and meson builtins
internal_prefixes = ('gst', 'gstreamer', 'gobject-introspection', 'gir-')
# Also remove names that are clearly internal modules, but keep e.g. 'glib-2.0'
filtered = []
for r in uniq:
    name = r['name']
    if name.startswith('gst') or name.startswith('gstreamer'):
        continue
    # Skip placeholder / computed names (variables)
    if not name or name.startswith('$'):
        continue
    filtered.append(r)

filtered.sort(key=lambda x: (x['kind'], x['name']))
(RUN / 'meson_deps_raw.json').write_text(json.dumps(filtered, indent=2))
print(f"Found {len(filtered)} unique declarations from {len(set(r['file'] for r in results))} files")
