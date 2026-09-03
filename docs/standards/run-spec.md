# Oriphim run spec — the setup the model fills

After a brief is approved, the model does not write solver code. It fills a **RunSpec**:
a typed, validated description of one run. Oriphim's verified core reads it and does the
numerics. For why the split is shaped this way, see `docs/standards/visualization.md`.
The reference implementation is `src/oriphim/core/execute/spec.py`; each domain's block
lives beside its brief block (`src/oriphim/domains/<domain>/spec.py`).

One RunSpec, one run. It pairs a domain-general shell with a domain block, exactly as the
brief's `Envelope` pairs domain-general fields with a domain block.

---

## Why it's a document, not a program

1. **The numerics stay auditable.** The integrator, the field solve, the stability
   criterion, the conservation checks — all live in code that was reviewed once and does
   not change per run. A RunSpec cannot introduce a numerical bug because it contains no
   numerical method.
2. **The surface is closed.** Every model here sets `extra="forbid"`. A key the core does
   not recognise is a validation error. The model cannot widen the contract by writing a
   field that sounds plausible.
3. **The timestep is not the model's.** The model asks for physical time and a frame
   cadence. The core derives `dt` from a stability criterion (CFL). An override exists
   but must carry a reason, so a reviewer sees the automatic choice was set aside.
4. **The run is reproducible.** `seed` feeds every stochastic draw. Run the same spec
   twice, get the same DATA.

---

## The shell

```json
{
  "run_id": "…",              // identical to the approved brief's run_id
  "brief_revision": 2,        // the brief revision this spec was built from
  "domain": "plasma",
  "grid":  { "cells": [128], "extent_m": [[0.0, 1e-4]], "boundaries": ["periodic"] },
  "time":  { "physical_time_s": 1e-12, "frame_interval_s": 1e-14 },
  "ladder": { "levels": 3, "ratio": 2.0, "refine": "both" },
  "diagnostics": { "fields": ["E_y", "B_z"], "reductions": ["field_energy"],
                   "spatial_stride": 2, "particle_tracks": { "electron": 4000 } },
  "budget": { "max_wall_time_s": 300, "max_memory_mb": 2048, "max_frames": 1200 },
  "seed": 0,
  "glue": null,
  "block": { … domain-specific … },
  "notes": ""
}
```

### grid

`cells`, `extent_m`, and `boundaries` are parallel arrays, one entry per active axis;
their length (1–3) is the dimensionality. `extent_m` entries are `[low, high]` in metres,
strictly increasing. `boundaries` values: `periodic`, `reflecting`, `absorbing`, `open` —
the domain gives each its physics (an `absorbing` EM boundary and an `absorbing` particle
boundary are both "absorbing" here). This is the *base* grid; the core builds the
refinement ladder up from it.

### time

`physical_time_s` is how long to simulate; `frame_interval_s` is the DATA frame cadence,
in `(0, physical_time_s]`. `dt_override_s` is optional and, if set, requires
`dt_override_reason`.

### ladder

The refinement ladder the convergence check runs on. `levels` ≥ 3 (a Grid Convergence
Index study needs three). Proposed by the model; the core may widen it.

### diagnostics

`fields` and `reductions` name quantities in the domain's vocabulary — the core rejects
names it does not produce. `spatial_stride` keeps every Nth cell in DATA. `particle_tracks`
maps a species name to how many macroparticles to subsample for the render (0 = none).

### budget

Hard caps the sandbox enforces. The core stops rather than exceed them.

### glue

`null` on the main path. Set it only when the RunSpec genuinely cannot express the run:

```json
"glue": {
  "justification": "…why the schema was insufficient, for the reviewer…",
  "entrypoint": "run_glue:build",
  "source": "def build(core):\n    …calls core.* ; never reimplements numerics…\n",
  "reviewed_by": null
}
```

`bind` refuses to run glue with `reviewed_by` unset. The module runs sandboxed and is
never imported into the engine process.

---

## The plasma block

`src/oriphim/domains/plasma/spec.py`. The brief block (`PlasmaBlock`) says what the paper
poses; this says what to run.

```json
{
  "normalization": "laser",            // "si" | "plasma" | "laser"
  "species": [
    { "name": "electron", "charge_e": -1.0, "mass_me": 1.0,
      "density": { "kind": "uniform", "reference_m3": 1e25, "params": {} },
      "temperature_ev": 50.0, "drift_velocity_c": [0, 0, 0],
      "particles_per_cell": 64, "brief_source": "block.key_parameters.2" }
  ],
  "laser": {
    "a0": 2.0, "wavelength_m": 8e-7, "polarization": "linear_y",
    "envelope": "gaussian", "duration_s": 3e-14, "injection_boundary": "x_lo",
    "brief_source": "block.key_parameters.0"
  },
  "external_b_tesla": [0, 0, 0],
  "external_e_vm": [0, 0, 0]
}
```

- `charge_e` is in elementary charges (electron `-1`); `mass_me` in electron masses
  (proton ≈ 1836).
- `density.kind` is `uniform`, `linear_ramp`, `step`, or `gaussian`; `params` carries the
  shape (`ramp_start_m`, `sigma_m`, …).
- `drift_velocity_c` is a fraction of c, per axis.
- `laser` is optional (omit for an unpumped plasma). `a0`, `wavelength_m`, `duration_s`
  all > 0.
- `brief_source` is the dotted path to the brief field a number came from. Advisory in
  1.0.0 — `bind` does not yet resolve it — but fill it: it is where the traceability
  check will land.
- At least one species; species names unique.

---

## Rules for the model

1. **Every physical number traces to the approved brief.** If it is not in the brief,
   it does not belong in the spec — go back to the brief.
2. **Do not set `dt`.** Ask for `physical_time_s` and `frame_interval_s`. Use
   `dt_override_s` only when the source pins the timestep, and say so in the reason.
3. **Prefer the schema.** Reach for `glue` only when a field genuinely has nowhere to go,
   and write the `justification` for the human who has to approve it.
4. **One normalization per run.** Pick the one the paper works in.
5. **Name diagnostics the core knows.** If unsure a name is supported, it probably is not
   — check the domain's vocabulary rather than guessing.
6. **`seed` is not decoration.** Leave it at `0` unless a run needs a specific draw.

---

## The bind check

`oriphim.core.execute.bind.bind_spec_to_brief(spec, brief)` runs before anything else. It
raises `SpecBriefMismatch` unless: the brief is approved; `spec.run_id == brief.run_id`;
`spec.domain == brief.domain`; `spec.brief_revision == brief.revision` (edit the brief,
rebuild the spec); and any `glue` has a `reviewed_by`. It is the RunSpec's counterpart to
`render/link.py` for the SCENE/DATA pair.
