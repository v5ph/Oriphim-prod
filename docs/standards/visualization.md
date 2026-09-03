# Oriphim visualization — from any system to an exhibit

Every physical system Oriphim can pose and solve, it can render. Not as a feature bolted
onto certain domains, but as a consequence of how the pipeline is shaped: rendering is
strictly downstream of DATA, and DATA is physics-agnostic. This document is the
domain-general contract for that. `docs/standards/run-spec.md` is the format the model
fills to set up a run; `docs/standards/scene-spec.md` is the format the fixed renderer
consumes; this is the story of how a described system reaches both.

---

## The split — a verified core, and declarative glue

Oriphim is not a wrapper around a model that writes simulators. The numerics — the part
of a run that is *right or wrong* rather than *rough or sharp* — are Oriphim's, written
once and verified once against convergence, conservation, and known limits. That body of
code is **the verified core**.

What the model supplies, per run, is **glue**: a bounded, typed description of *this*
system — grid, duration, species, driver, what to record. It is a document, not a
program. The model states what to integrate and over what; it never writes the
integrator. The test this passes that "let the model write the solver" does not: swap in
a weaker model and the output gets rougher — a clumsier scene, a missed diagnostic —
never *wrong*. A wrong timestep is not reachable from here, because the timestep is not
the model's to set.

The glue takes one of two forms:

- **A RunSpec** (`docs/standards/run-spec.md`) — the main path. A schema-validated object:
  every key is something the core supports, and `extra="forbid"` means a key the core
  does not recognise is a validation error, not a silently honoured instruction. The
  model fills it; `bind` checks it against the approved brief; the core runs it.
- **Escape-hatch code** — the minority path. When a run genuinely needs something the
  RunSpec cannot say, the model writes a small module *against the core API* (it calls
  the core's verified pieces; it does not reimplement them). It is flagged for human
  review — `bind` refuses to run glue with no reviewer's name on it — and it runs
  sandboxed, like any solver. Most runs never touch this.

---

## The pipeline, end to end

```
brief  ──►  RunSpec  ──►  verified core  ──►  DATA  ──►  checks  ──►  SCENE  ──►  renderer  ──►  exhibit
        (model-written,  (Oriphim's;       (fixed    (verification) (model-      (vendored,
         declarative,     verified once,    schema)                  written,     audited
         schema-checked)  sandboxed run)                             declarative) 1.0.0)
```

- **The brief** is Oriphim's interpretation of the paper: what system is posed, what
  equations govern it, what will be checked. Reviewed and approved by a human first.
- **The RunSpec** is the model's setup for the run — resolved numbers, one normalization,
  concrete species and driver, the diagnostics to record. Declarative. Cross-checked
  against the brief it was built from (`oriphim.core.execute.bind`): same run, approved,
  current revision, same domain.
- **The verified core** consumes the RunSpec and integrates the governing equations. It
  chooses the timestep from a stability criterion; it owns the refinement ladder the
  convergence check needs. It runs in a sandboxed subprocess — no network; CPU, memory,
  and wall-time capped; a scratch directory and nothing else.
- **DATA** is the core's output in one fixed schema: named tracks, each a list of
  per-frame position arrays, with optional per-frame per-element scalar arrays.
- **Checks** run against DATA, not against a picture. A figure that displays a quantity
  is only admitted to a report after the section containing the checks that cover that
  quantity (report-format §12).
- **SCENE** is a small declarative document the model writes: which tracks to draw, as
  what, with which scalar mapped to colour, at what world scale. It contains no motion.
- **The renderer** is `oriphim-render-1.0.0.js`, vendored and audited once. It is never
  regenerated, never edited to fit a run. A new capability means a new version and a new
  audit, not model-authored rendering code.

Where the model is free: the RunSpec and the SCENE — both declarative, both bounded by a
schema. Where it is not: it never writes the core, it never writes the renderer, and it
never invents a position. Anything that moves in the exhibit moved because the core put
it there.

---

## The core → DATA adapter

The core does not hand-write DATA JSON. It fills a fixed `solve()` contract that returns
arrays — positions per track per step, and any scalars alongside — and a vendored adapter
serializes those to the DATA schema. The adapter enforces what the renderer relies on:

- element count per track is constant across frames (1.0.0);
- every scalar array is parallel to its track's positions;
- `frames` matches the number of position frames on every track;
- units are the core's own; the SCENE's `world.scale` (or `fit: "once"`) maps them into
  the render box, resolved once and recorded in the stamp.

Keeping DATA emission in a fixed adapter means the schema is enforced by audited code,
and the core only has to produce numbers.

---

## Mapping physical things to tracks — by field

The roadmap order, with the concrete mapping for each. "Not in 1.0.0" rows are the honest
gaps — where a report says so in its *checks not applied* section rather than
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
