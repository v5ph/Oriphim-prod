veil/
├── src/veil/
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
│   │   └── propose.py      prose → draft brief (typed out, never prose)
│   │
│   ├── execute/          THE SEAM
│   │   ├── contract.py     brief → results; never assumes same process
│   │   ├── calculix.py
│   │   └── local.py
│   │
│   ├── checks/           VERIFICATION TIER
│   │   ├── convergence.py  refinement + GCI
│   │   ├── handcalc.py     independent-method cross-check
│   │   ├── sensitivity.py  tornado
│   │   ├── conservation.py
│   │   └── dimensional.py
│   │
│   ├── report/
│   │   ├── tier.py         VERIFICATION | VALIDATION, never both
│   │   └── assemble.py
│   │
│   ├── store/              runs, artifacts, hashing
│   └── cli.py
├── benchmarks/             known-answer systems
└── tests/