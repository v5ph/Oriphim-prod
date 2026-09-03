# Oriphim scene spec — renderer 1.0.0

The renderer is fixed and versioned. It is audited once and does not change per run.
The audited reference implementation is vendored at
`src/oriphim/assets/oriphim-render-1.0.0.js`. For the upstream story — how *any*
posed physical system becomes something this renderer can draw — see
`docs/standards/visualization.md`.

Two JSON documents feed it:

- **SCENE** — what to draw and how. Small, declarative. *Written by the model.*
- **DATA** — solver output frames. *Written by the pipeline. Never by the model.*

The renderer invents no motion. Every position it draws came from DATA. A model
that wants something to move must ask the pipeline for a track containing it.

---

## Why it's split this way

A render that appears in a review-ready report is an exhibit. Three properties follow:

1. **The renderer is auditable.** One artifact, one version, reviewed once. If the
   model emitted a fresh renderer per run, every animation would be unverified code
   inside a verification product.
2. **The render is reproducible.** `renderer version + scene hash + data hash` fully
   determines the output. `oriphim.stamp()` returns exactly that; put it in the report.
3. **The render cannot lie by scaling.** Scalar ranges and world scale are resolved
   once and recorded, never re-fit per frame. A colour that means 400 K in frame 1
   means 400 K in frame 900.

---

## DATA format

```json
{
  "meta": { "run_id": "…", "solver": "…", "case": "…", "units": "m", "dt": 0.001 },
  "frames": 900,
  "tracks": {
    "vessel":  { "kind": "rigid",    "positions": [[x,y,z], …] },
    "plasma":  { "kind": "points",   "positions": [[x0,y0,z0, x1,y1,z1, …], …],
                 "scalars": { "temperature": [[t0,t1,…], …] } },
    "fieldline_07": { "kind": "polyline", "positions": [[x0,y0,z0, …], …] }
  }
}
```

- `positions` is an array of **frames**; each frame is a flat `[x,y,z,…]` array.
- `scalars` are per-frame, per-element, parallel to `positions`.
- Element count per track is fixed across frames in 1.0.0.
- Units are whatever the solver used. `world.scale` maps them into the render box.

---

## SCENE format

```json
{
  "version": "1.0.0",
  "style":    { "cell": 2, "voxpx": 1.8, "chroma": 1.0, "gamma": 0.88,
                "light": [-0.44, 0.55, 0.71], "depthFade": 0.38 },
  "camera":   { "size": 0.34, "zoom": 1, "tilt": -0.32, "yaw": 0,
                "spin": 0.45, "interactive": true },
  "playback": { "fps": 30, "speed": 1, "loop": true, "interpolate": false },
  "world":    { "scale": 1.0, "center": [0,0,0], "fit": "none" },
  "objects":  [ … ],
  "provenance": { "run_id": "…", "figure": "Fig 4.2" }
}
```

### style

| key | meaning |
|---|---|
| `cell` | device pixels per render pixel. 2 is the house look. |
| `voxpx` | voxel size in render pixels. Bigger = chunkier. |
| `chroma` | 0 = pure black and white; 1 = full per-channel dither split. |
| `gamma` | tone curve before quantisation. |
| `light` | key light direction in view space. |
| `depthFade` | how much far geometry dims. 0 disables. |

### camera

`size` is one world unit as a fraction of the viewport's short side at zoom 1.
`spin` is the idle rightward drift; it pauses while the user drags and eases back.
`interactive: false` removes the grab element entirely — use it for report figures.

### playback

`interpolate: false` (default) shows solver frames as they are. Set it true only
when the frame rate is genuinely too coarse to read, and know that the stamp records
`interpolated: true` so a reviewer can see that intermediate positions were drawn.

### world

`fit: "none"` uses `scale` as given — correct when comparing runs, since the scale
is then a stated constant. `fit: "once"` computes a scale from the full trajectory
at load and records it in the stamp. Never re-fit per frame.

---

## Objects

### `shell` — a body with a radius

```json
{ "id": "core", "type": "shell", "track": "vessel",
  "radius": 0.20, "points": 9000, "dark": false, "brightness": 1.0 }
```

Track must be `kind: "rigid"`; the first three numbers of each frame are its centre.
`dark: true` renders it near-black with a hard bright limb — event horizons, voids,
anything defined by its silhouette.

### `curve` — a polyline, optionally widened into a ribbon

```json
{ "id": "B_07", "type": "curve", "track": "fieldline_07",
  "width": 0.05, "across": 8, "twist": 1, "brightness": 1.0 }
```

`width: 0` draws a one-voxel thread. Above zero it becomes a flat strap of `across`
samples, lit on both faces. `twist` rotates the strap along its length. The frame is
parallel-transported, so it doesn't flip on curves that double back.
Use for field lines, orbits, trajectories, streamlines, contour paths.

### `particles` — one element per point

```json
{ "id": "plasma", "type": "particles", "track": "plasma",
  "scalar": "temperature", "range": [300, 12000],
  "radius": 0.004, "maxVoxels": 4, "floor": 0.26, "gain": 1.05 }
```

`scalar` maps to brightness and to the chroma split. **Give `range` explicitly**
whenever the physical range is known — it makes the figure comparable across runs.
Omit it and the renderer computes one range over the whole run and records it.
`radius` in world units; below one voxel it draws as a single splat, above that as a
lit voxel ball. `maxVoxels` caps that, which is what keeps deep zoom affordable.

---

## Worked example

Two bodies and a hole, with stripped material and a set of field lines:

```json
{
  "version": "1.0.0",
  "camera": { "size": 0.30, "tilt": -0.34, "spin": 0.45 },
  "playback": { "fps": 60, "loop": true },
  "world": { "scale": 1.0, "fit": "once" },
  "objects": [
    { "id":"hole", "type":"shell", "track":"bh", "radius":0.20, "dark":true },
    { "id":"m1",   "type":"shell", "track":"body1", "radius":0.30, "points":9000 },
    { "id":"m2",   "type":"shell", "track":"body2", "radius":0.26, "points":9000 },
    { "id":"stream","type":"particles", "track":"debris",
      "scalar":"specific_energy", "range":[-2.0, 0.5], "radius":0.004 },
    { "id":"L1", "type":"curve", "track":"orbit1", "width":0.0 },
    { "id":"L2", "type":"curve", "track":"orbit2", "width":0.0 }
  ],
  "provenance": { "run_id":"3B-0142", "figure":"Fig 6.1" }
}
```

---

## Rules for the model

1. **Never invent a position.** If it should move, it needs a DATA track. There is no
   procedural motion path in this renderer, by design.
2. **Give scalar ranges when the physics gives you one.** Auto-ranging is a fallback,
   not a default choice.
3. **Prefer `interpolate: false`.** Smoothness is not worth misrepresenting the
   temporal resolution the solver actually produced.
4. **One object per physical thing.** Don't merge two bodies into one particle track
   to save an entry — the report needs to name what it's pointing at.
5. **`interactive: false` for report figures**, true for the desktop app's live view.
6. **Don't restyle per run.** `style` is house identity. Change `chroma` or `voxpx`
   only when legibility demands it, and say why in `provenance`.

---

## Embedding

```html
<div class="oriphim-stage" id="stage"></div>
<script type="application/json" id="oriphim-scene"> … </script>
<script type="application/json" id="oriphim-data">  … </script>
<script src="oriphim-render-1.0.0.js"></script>
```

Or programmatically:

```js
const view = Oriphim.mount(document.getElementById('stage'), scene, data);
view.seek(120);          // frame index
view.pause();
const stamp = view.stamp();   // renderer version, hashes, ranges, world scale
const png   = view.png();     // still frame for the report
```

`stamp()` is the object that belongs in the figure caption or the report appendix.
It is what lets a reviewer regenerate the exhibit exactly.

---

## Not in 1.0.0

Triangle meshes (CAD geometry, solid parts). The rasteriser exists — it was built for
the faceted work — but meshes need a topology format and a normals convention, and
that's a decision worth making once rather than twice. Field volumes, isosurfaces and
2D section planes are the other obvious gaps.
