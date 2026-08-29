# oriphim

oriphim turns a described physical system into a computational experiment, and produces the evidence needed to judge whether its results can be believed.

**The user brings the idea.** They articulate a physical system and the questions they want answered, in their own terms, at whatever level of formality they have. They do not supply equations. oriphim interprets the intent, determines what system is actually being posed, and derives or identifies the governing equations. That work is oriphim's, not the user's.

**Papers don't require explicit equations.** A document describes a system; it is not a specification to transcribe. Recognizing that a prose account of a twisted disc fed by variable-direction accretion is governed by a particular angular-momentum evolution equation — and that the ratio of its viscous timescales determines every result that follows — is interpretation, and interpretation is the work. The same holds for results oriphim did not produce.

**oriphim generates, runs, checks, and argues.** It builds the model and the runnable simulation. It executes it. It subjects the result to every check the available reality permits. And it assembles the argument: why these equations, what regime they hold in, what was assumed, what was neglected, where that neglect breaks, and what the numbers do and do not license the user to conclude.

**There are two tiers of evidence, and oriphim never conflates them.**

*Verification* asks whether the mathematics was solved correctly. Numerical error budgets, convergence under refinement, conservation, integrator cross-agreement, dimensional consistency, internal contradiction between a paper's stated mechanism and its stated implementation, and sensitivity of the conclusion to every free parameter. This tier requires no reference data and is available for any system a user can describe. Most published computational work has never received it.

*Validation* asks how far the model is from reality. Discrepancy against measurement, with uncertainty carried on both sides — not a single representative run compared to an experimental mean and called reasonable. This tier requires reality to compare against: published benchmarks, inter-laboratory experiments, a customer's own test campaign, or in time, a live measurement stream. Where it exists, oriphim quantifies the discrepancy. Where it does not, oriphim performs verification and states the limit explicitly.

**The model never produces numeric metrics.** A model may propose a brief and may write interpretive prose. All numbers in a report come from deterministic computation.

**oriphim does not claim a model is correct.** At the verification tier it claims the model was solved to a stated accuracy and that its conclusions are or are not stable under stated perturbations. At the validation tier it claims the model is wrong by a quantified amount under stated conditions. Both are defensible. Neither is "good agreement."

**Critique is oriphim's function, not the user's.** oriphim identifies what is structurally wrong or questionable about a proposed system — for any user, not only for someone already expert enough to catch it. A plausible result that is silently wrong is the failure mode worth engineering against. So is a quantified error the authors named and never integrated. Surfacing these is part of the argument, and oriphim distinguishes real defects from transcription artifacts rather than reporting noise as a finding.

**Judgment stays with a named person.** oriphim produces the model, the run, the checks, and the argument in hours instead of months. A person reviews it, corrects it, and owns it. oriphim captures every correction. Where credibility frameworks require a practitioner's signature, that requirement is the product specification, not a constraint on it.

**CAD and FEA are features.** FEA is one solver backend. CAD is one geometry input. Both matter when a system has geometry and are irrelevant when it doesn't. A warped accretion disc has no mesh, no machinery, and no CAD model, and oriphim handles it natively. Any framing that centers geometry describes a mechanical engineering tool. oriphim is a physics solver; mechanical systems are one case.

**Scope.** Verification is bounded only by the user's ability to describe a system. Validation is bounded by available reality and earned one domain at a time. oriphim says which tier a report belongs to on the report, and does not produce a report it cannot stand behind.
