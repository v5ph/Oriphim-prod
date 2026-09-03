# Oriphim visualization — from any system to an exhibit

Every physical system Oriphim can pose and solve, it can render. Not as a feature bolted
onto certain domains, but as a consequence of how the pipeline is shaped: rendering is
strictly downstream of DATA, and DATA is physics-agnostic. This document is the
domain-general contract for that. `docs/standards/scene-spec.md` is the format the fixed
renderer consumes; this is the story of how a described system reaches it.

---

## Why it generalizes

The renderer draws exactly three things:

- a **rigid body** — a centre that moves, drawn as a lit shell of a given radius;
- a set of **points** — one element each, optionally coloured by a scalar;
- a **polyline** — a path, optionally widened into a ribbon.

Nothing in that list is about plasma, or structures, or orbits. A point is a point
whether it is a PIC macroparticle, a finite-element node, a marker on a glacier surface,
a vertex of a cardiac mesh, a gravitating mass, or a parcel of accretion-disc fluid. A
polyline is a polyline whether it traces a magnetic field line, a bending beam's
neutral axis, a contaminant plume centreline, or a planetary orbit. The scalar carried
alongside a point track is temperature, or von Mises stress, or hydraulic head, or
specific orbital energy — the renderer neither knows nor cares.

So the reach of the visualization is exactly the reach of the solver. If Oriphim can
produce frames of positions for a system, it can show that system. The work of
generalizing rendering to a new field is not renderer work; it is deciding which
physical things become which track kind, and which quantities become scalars.

---

## The pipeline, end to end

```
brief  ──►  governing equations  ──►  solver  ──►  DATA  ──►  checks  ──►  SCENE  ──►  renderer  ──►  exhibit
        (Oriphim's interpretation)   (model-      (fixed    (verification)  (model-    (vendored,
                                      written,     schema)                   written,   audited
                                      verified,                              declarative) 1.0.0)
                                      sandboxed)
```

- **Governing equations** are already Oriphim's job — the interpretation step identifies
  what system is posed and what equations govern it.
- **The solver** is code the model writes to integrate those equations. It runs in a
  sandboxed subprocess (no network; CPU, memory, and wall-time capped; a scratch
  directory and nothing else). It is subject to every verification check the tier
  permits — convergence under refinement, conservation, integrator cross-agreement.
  Model-written solver code is verified code. This is the reason the split exists.
- **DATA** is the solver's output in one fixed schema: named tracks, each a list of
  per-frame position arrays, with optional per-frame per-element scalar arrays.
- **Checks** run against DATA, not against a picture. A figure that displays a quantity
  is only admitted to a report after the section containing the checks that cover that
  quantity (report-format §12).
- **SCENE** is a small declarative document the model writes: which tracks to draw, as
  what, with which scalar mapped to colour, at what world scale. It contains no motion.
- **The renderer** is `oriphim-render-1.0.0.js`, vendored and audited once. It is never
  regenerated, never edited to fit a run. A new capability means a new version and a new
  audit, not model-authored rendering code.

Where the model is free: the equations, the discretization, the solver approach, and the
SCENE. Where it is not: it never writes the renderer, and it never invents a position.
Anything that moves in the exhibit moved because the solver put it there.

---

## The solver → DATA adapter

The model's solver does not hand-write DATA JSON. It fills a fixed `solve()` contract
that returns arrays — positions per track per step, and any scalars alongside — and a
vendored adapter serializes those to the DATA schema. The adapter enforces what the
renderer relies on:

- element count per track is constant across frames (1.0.0);
- every scalar array is parallel to its track's positions;
- `frames` matches the number of position frames on every track;
- units are the solver's own; the SCENE's `world.scale` (or `fit: "once"`) maps them
  into the render box, resolved once and recorded in the stamp.

Keeping DATA emission in a fixed adapter rather than in model-written code means the
schema is enforced by audited code, and the model only has to produce numbers.

---

## Mapping physical things to tracks — by field

The roadmap order, with the concrete mapping for each. "Not in 1.0.0" columns are the
honest gaps — where a report says so in its *checks not applied* section rather than
substituting a figure that implies more than it shows.

### Climate and geophysics
Groundwater flow, glacier melt, coastal flooding, contaminant transport.

| Physical thing | Track kind | Object | Scalar |
|---|---|---|---|
| Surface / interface markers (ice surface, water table, shoreline) | `points` | `particles` | elevation, head, saturation |
| Tracer / plume particles | `points` | `particles` | concentration, age |
| Plume centreline, flow path, contour | `polyline` | `curve` | — |
| A rigid structure under assessment (well, caisson) | `rigid` | `shell` | — |

Not in 1.0.0: the field volume itself (a 3-D head or concentration field), isosurfaces
of it, and vertical section planes. These are the natural next renderer capability for
this field.

### Biomechanics and biology
Bone loading, implant stress, tissue mechanics, cardiovascular flow.

| Physical thing | Track kind | Object | Scalar |
|---|---|---|---|
| Mesh nodes of a bone, implant, or vessel wall | `points` | `particles` | von Mises stress, strain, displacement magnitude |
| Blood / fluid tracer particles | `points` | `particles` | velocity magnitude, residence time, WSS proxy |
| A device centreline, suture path, muscle line of action | `polyline` | `curve` | — |
| A rigid implant body moving as a unit | `rigid` | `shell` | — |

Not in 1.0.0: the solid part as a shaded surface (the mesh is drawn as its nodes, not
its faces). Triangle meshes are the first planned addition and this field is why.

### Chemistry and materials
Reaction setup, conformers, solvent models, irradiation damage.

| Physical thing | Track kind | Object | Scalar |
|---|---|---|---|
| Atoms of a molecule or lattice | `points` | `particles` | charge, displacement, coordination, damage energy |
| A reaction coordinate / trajectory in a reduced space | `polyline` | `curve` | — |
| A migrating defect or cluster centre | `rigid` | `shell` | — |

Not in 1.0.0: bonds as explicit connectors, isosurfaces of electron density or a damage
field. Bonds can be approximated as thin `curve` tracks in the interim, one per bond,
which is honest but verbose.

### Astrophysics and plasma
The Diff-PIC case, warped discs, tearing modes, N-body structure formation.

| Physical thing | Track kind | Object | Scalar |
|---|---|---|---|
| PIC macroparticles, disc fluid parcels, N-body masses | `points` | `particles` | energy, temperature, density, `field_energy` |
| Field lines, orbits, streamlines | `polyline` | `curve` | — |
| A star, planet, or compact object | `rigid` | `shell` (`dark: true` for a horizon) | — |

Not in 1.0.0: the field as a volume, isosurfaces of `|E|` or density, section planes
through a disc. Pure verification tier throughout — there is nothing to validate a
render against, and the renderer makes no validation claim.

---

## Honesty constraints (general form of the scene spec's rules)

1. **A render is an exhibit, not an illustration.** It appears in a report only after the
   checks that cover the quantities it displays, because a render is the most persuasive
   artifact in the document and therefore the most capable of laundering an unconverged
   result.
2. **State scalar ranges wherever the physics gives one.** An auto-ranged figure is
   legible but not comparable across runs, and the caption says so.
3. **One object per physical thing.** The report has to be able to name what it points at.
4. **The render is downstream of verification, never a substitute for it.** Section 7 of
   a report is the claim; a figure at validation tier shows the model only.
5. **The style is house identity, not a per-run choice.** `chroma` and `voxpx` move only
   when legibility demands it, and the reason goes in `provenance`.

---

## What a render never establishes

The renderer has no representation for uncertainty, no reference-data overlay, no error
bars. A side-by-side of model against measurement is not a validation exhibit; the
numeric comparison in the report is. When a figure would need something 1.0.0 cannot
draw, the report names the gap in *checks not applied* and does without the figure.
