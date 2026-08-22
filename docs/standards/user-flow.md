# User flow

Six states. Only two of them are real screens.

1. Intake. A prose box — "describe the system and the question" — plus attachments: CAD or mesh, a requirements or environments document, prior analysis. No forms. No wizard. The prose box is the promise of the product; the moment you replace it with 40 required fields you've become a worse Femap.

2. Clarification. Veil asks 3–6 questions, only where the ambiguity actually changes the answer. This is a discipline, not a feature: if Veil can answer it by inference, it should infer and mark it inferred rather than ask. Every question you ask is a small tax on the user's belief that Veil understands the system. Keep it under five.

3. Run brief review. The product. Structured spec — objective, geometry, materials, boundary conditions, load cases, solver settings, quantities of interest, planned checks. Provenance-marked. Fully editable. Corrections captured with reasons. Nothing runs until a human clicks approve.

That gate is load-bearing in three separate ways: it prevents the expensive silent failure, it's where your corpus comes from, and it's the moment the customer takes ownership. Do not add a "skip review, just run it" button, no matter who asks — that button destroys the asset and transfers the liability to you.

4. Execution. A status list of the checks as they complete. Minimal UI. Email when done. Nobody watches this screen and you shouldn't design as if they do.

5. Evidence report. As above.

6. Signature. A named person, a role, a timestamp, a statement of what they're attesting to. The customer's engineer signs, not you. Then the artifact is frozen and hashed, and any subsequent change forks a new version.

And the loop that makes it a product rather than a service: when a report comes back and the engineer disagrees, they go back to the brief, change the disputed assumption, and re-run. The second report shows a diff against the first — what changed, and whether the conclusion moved. That's the retention mechanic. The first report is impressive; the second one is when they find out whether their conclusion was ever stable, and that's what makes them come back.

**Subject to change**