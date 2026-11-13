"""Packs a built canvas's screenshots into one script per flow.

An artifact version holds at most 511 files, so a canvas with more screenshots
than that cannot publish them as separate images. This converts each PNG to
lossless WebP, writes `shots/<flow>.js` (a call to `window.__shots` with the
flow's images as data URIs), removes the PNGs, lists the bundles in the page's
`PACKED` constant, and rewrites files.json to the bundles.

    uv run --no-project --with pillow python pack.py <build dir>
"""

import base64
import io
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image

build = Path(sys.argv[1]).resolve()
shots = [entry["path"] for entry in json.loads((build / "files.json").read_text())]

by_flow: dict[str, dict[str, str]] = defaultdict(dict)
for path in shots:
	buffer = io.BytesIO()
	Image.open(build / path).save(buffer, "WEBP", lossless=True, method=4)
	by_flow[path.split("/", 1)[0]][path] = "data:image/webp;base64," + base64.b64encode(buffer.getvalue()).decode()

(build / "shots").mkdir(exist_ok=True)
bundles = []
for flow, images in by_flow.items():
	bundle = f"shots/{flow}.js"
	(build / bundle).write_text(f"window.__shots({json.dumps(flow)}, {json.dumps(images)});\n")
	bundles.append(bundle)
	shutil.rmtree(build / flow)

page = build / "canvas.html"
html = page.read_text()
marker = "const PACKED = [];"
if html.count(marker) != 1:
	sys.exit("canvas.html has no `const PACKED = [];` line; rebuild it from the current template")
page.write_text(html.replace(marker, f"const PACKED = {json.dumps(bundles)};"))
(build / "files.json").write_text(json.dumps([{"path": bundle} for bundle in bundles], indent="\t"))

size = sum((build / bundle).stat().st_size for bundle in bundles)
print(f"{len(shots)} screenshots -> {len(bundles)} bundles, {size / 1e6:.1f} MB")
