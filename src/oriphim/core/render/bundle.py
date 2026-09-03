"""Wrap a SCENE + DATA + the vendored renderer into one self-contained HTML file.

That file is what the desktop app's webview loads and what a user exports. The
renderer JS is inlined, so the export needs no server and no network.
"""

from __future__ import annotations

import html
import json
from importlib import resources
from pathlib import Path
from typing import Any

from oriphim.core.render.data import RenderData
from oriphim.core.render.scene import Scene

_RENDERER_ASSET = "oriphim-render-1.0.0.js"

_CSS = """\
html,body{margin:0;height:100%;background:#c2391b;overflow:hidden}
.oriphim-stage{position:absolute;inset:0}
.oriphim-canvas{position:absolute;inset:0;width:100%;height:100%;
  background:transparent;image-rendering:pixelated;pointer-events:none;display:block}
.oriphim-grab{position:absolute;border-radius:50%;pointer-events:auto;touch-action:none;
  cursor:grab;background:transparent}
.oriphim-grab:active{cursor:grabbing}"""


def renderer_source() -> str:
    """The vendored renderer JS, read from the packaged asset."""
    return (
        resources.files("oriphim.assets")
        .joinpath(_RENDERER_ASSET)
        .read_text(encoding="utf-8")
    )


def render_bundle(scene: Scene, data: RenderData) -> str:
    """Return a complete HTML document that animates `data` under `scene`."""
    scene_json = _embed_json(scene.for_renderer())
    data_json = _embed_json(data.for_renderer())
    label = scene.provenance.get("figure") or scene.provenance.get("run_id") or ""
    figure = html.escape(str(label))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ORIPHIM RENDER {figure}</title>
<style>
{_CSS}
</style>
</head>
<body>
<div class="oriphim-stage" id="stage"></div>
<script type="application/json" id="oriphim-scene">
{scene_json}
</script>
<script type="application/json" id="oriphim-data">
{data_json}
</script>
<script>
{renderer_source()}
</script>
</body>
</html>
"""


def write_bundle(path: Path, scene: Scene, data: RenderData) -> Path:
    """Write `render_bundle(scene, data)` to `path` and return it."""
    path.write_text(render_bundle(scene, data), encoding="utf-8")
    return path


def _embed_json(obj: Any) -> str:
    # `<\/` keeps a stray "</script>" inside a string from closing the tag; it
    # is still valid JSON (\/ is a permitted escape for /).
    return json.dumps(obj).replace("</", "<\\/")
