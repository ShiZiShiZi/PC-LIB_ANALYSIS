#!/usr/bin/env python3
import json
from pathlib import Path

RUN = Path('runs/pc-lib-3456/gstreamer/2026-07-03T13-34-52-216Z')
data = json.loads((RUN / 'blocks/runtime_surface.json').read_text())
(RUN / 'blocks/runtime_surface.json').write_text(json.dumps(data['runtime_surface'], indent=2, ensure_ascii=False))
(RUN / 'blocks/build_env.json').write_text(json.dumps(data['build_env'], indent=2, ensure_ascii=False))
print('split done')
