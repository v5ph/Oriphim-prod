oriphim/
├── src/oriphim/
│   ├── brief/            THE PRODUCT
│   │   ├── schema.py       domain-general: objective, assumptions,
│   │   │                   QoI, checks planned, tier
│   │   ├── mechanical.py   domain block: materials, BCs, load cases
│   │   └── provenance.py   stated | inferred | defaulted
│   │
│   ├── corrections/      THE MOAT
│   │   ├── schema.py       field path, provenance, reason, domain tag
│   │   │                   — no values, redacted by construction
│   │   └── capture.py
│   │
│   ├── interpret/        THE ONLY PLACE THAT CALLS A MODEL
│   │   ├── client.py       provider-agnostic
│   │   ├── ingest.py       document → text (pdf, html)
│   │   └── propose.py      prose + paper text → draft brief (typed out, never prose)
│   │
│   ├── execute/          THE SEAM — approved brief → run
│   │   ├── spec.py         RunSpec: the declarative setup the LLM fills — never solver code
│   │   └── bind.py         RunSpec ↔ approved-brief cross-check
│   │
│   ├── checks/           VERIFICATION TIER
│   │   ├── convergence.py  refinement + GCI
│   │   ├── handcalc.py     independent-method cross-check
│   │   ├── sensitivity.py  tornado
│   │   ├── conservation.py
│   │   └── dimensional.py
│   │
│   ├── render/            SCENE + DATA → exhibit
│   │   ├── scene.py         SCENE schema (model-written, declarative)
│   │   ├── data.py          DATA schema (solver output; never model-written)
│   │   ├── link.py          scene ↔ data cross-check
│   │   ├── stamp.py         renderer version + hashes + resolved scale
│   │   └── bundle.py        self-contained HTML for the webview / export
│   │
│   ├── report/
│   │   ├── tier.py         VERIFICATION | VALIDATION, never both
│   │   └── assemble.py
│   │
│   ├── store/              runs, artifacts, hashing
│   ├── assets/             oriphim-render-1.0.0.js — vendored, audited, never regenerated
│   ├── cli.py
│   └── api.py              THE DESKTOP BRIDGE — FastAPI over the engine, spawned as a sidecar
├── app/                    THE DESKTOP SHELL — Electron + Vite + TypeScript
│   ├── electron/main.ts      frameless BrowserWindow, app lifecycle, native dialogs
│   ├── electron/preload.ts   window.oriphim — the seam to the Python engine (stubbed)
│   ├── src/main.ts           the renderer (interaction only; talks to window.oriphim)
│   ├── src/app.css           VS-Code-grey palette, IBM Plex Mono, Jacquard 12 wordmark
│   └── index.html            three panes under a custom title bar
├── benchmarks/             known-answer systems
└── tests/