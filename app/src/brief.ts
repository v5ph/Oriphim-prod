// oriphim brief review — renders a draft Envelope for a human to check, correct,
// and approve before anything runs. Provenanced fields are editable; editing one
// that was inferred or defaulted asks for a correction category, and the record
// captured carries no value — only that the field was corrected.

export type Provenance = "stated" | "inferred" | "defaulted" | "corrected";

export interface Provenanced {
  value: string;
  provenance: Provenance;
  inference_note: string | null;
  source: string | null;
}

export interface PlasmaBlock {
  governing_equations: string[];
  key_parameters: Provenanced[];
  dimensionless_groups: Record<string, number>;
  domain_geometry: string;
  regime_notes: string;
}

export interface BriefDoc {
  run_id: string;
  title: string;
  revision: number;
  created_at: string;
  objective: Provenanced;
  quantities_of_interest: Provenanced[];
  assumptions: Provenanced[];
  checks_planned: string[];
  tier: "verification" | "validation";
  domain: string;
  block: PlasmaBlock;
  approved_by: string | null;
  approved_at: string | null;
}

export type CorrectionCategory =
  | "wrong_value"
  | "wrong_assumption"
  | "not_applicable"
  | "missing"
  | "too_conservative"
  | "not_conservative_enough";

export interface CorrectionRec {
  field_path: string;
  original_provenance: Exclude<Provenance, "corrected" | "stated">;
  category: CorrectionCategory;
}

export interface ApprovePayload {
  brief: BriefDoc;
  corrections: CorrectionRec[];
}

export interface RenderOpts {
  debt?: [number, number];
  /** Approve the current edits. Resolve `true` once locked, `false` on failure. */
  onApprove?: (payload: ApprovePayload) => Promise<boolean>;
}

export interface BriefController {
  element: HTMLElement;
  lock(approvedBy: string, approvedAt: string): void;
  collectBrief(): BriefDoc;
  collectCorrections(): CorrectionRec[];
}

/** (fields still marked inferred, total provenanced fields) — mirrors Envelope.review_debt. */
export function reviewDebt(doc: BriefDoc): [number, number] {
  const fields = [doc.objective, ...doc.quantities_of_interest, ...doc.assumptions];
  const inferred = fields.filter((f) => f.provenance === "inferred").length;
  return [inferred, fields.length];
}

// ---- dom helpers ----------------------------------------------------
function h<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  cls?: string,
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

function badge(p: Provenance): HTMLElement {
  return h("span", `prov prov-${p}`, p);
}

const CATEGORY_LABELS: Record<CorrectionCategory, string> = {
  wrong_value: "wrong value",
  wrong_assumption: "wrong assumption",
  not_applicable: "not applicable",
  missing: "missing / incomplete",
  too_conservative: "too conservative",
  not_conservative_enough: "not conservative enough",
};

// ---- render -------------------------------------------------------
export function renderBrief(host: HTMLElement, doc: BriefDoc, opts: RenderOpts = {}): BriefController {
  const state: BriefDoc = structuredClone(doc);
  const corrections = new Map<string, CorrectionRec>();
  let locked = Boolean(state.approved_by);

  host.innerHTML = "";
  const root = h("div", "brief-doc");
  if (locked) root.classList.add("is-locked");

  const editables: HTMLElement[] = [];
  const selects: HTMLSelectElement[] = [];

  /** An inline, plain-text editable bound to a setter. */
  function edit(initial: string, onInput: (v: string) => void, cls = ""): HTMLElement {
    const span = h("span", `brief-edit ${cls}`.trim());
    span.textContent = initial;
    span.setAttribute("contenteditable", locked ? "false" : "plaintext-only");
    span.setAttribute("role", "textbox");
    span.addEventListener("input", () => onInput(span.textContent ?? ""));
    editables.push(span);
    return span;
  }

  /** A provenanced list row: editable value + badge + (revealed) category picker. */
  function provRow(field: Provenanced, path: string): HTMLElement {
    const li = h("li", "brief-item");
    const line = h("div", "brief-item-line");

    const badgeHost = h("span", "brief-badge-host");
    badgeHost.append(badge(field.provenance));

    const picker = h("select", "brief-cat") as HTMLSelectElement;
    picker.hidden = true;
    picker.disabled = locked;
    picker.append(new Option("why? …", ""));
    (Object.keys(CATEGORY_LABELS) as CorrectionCategory[]).forEach((k) =>
      picker.append(new Option(CATEGORY_LABELS[k], k)),
    );
    selects.push(picker);

    const correctable = field.provenance === "inferred" || field.provenance === "defaulted";
    const origProv = field.provenance as CorrectionRec["original_provenance"];

    const value = edit(field.value, (v) => {
      field.value = v;
      if (correctable && !corrections.has(path)) picker.hidden = false;
    });

    picker.addEventListener("change", () => {
      const cat = picker.value as CorrectionCategory | "";
      if (!cat) {
        corrections.delete(path);
        field.provenance = origProv;
      } else {
        corrections.set(path, { field_path: path, original_provenance: origProv, category: cat });
        field.provenance = "corrected";
      }
      badgeHost.replaceChildren(badge(field.provenance));
    });

    line.append(value, badgeHost, picker);
    li.append(line);
    if (field.provenance === "inferred" && field.inference_note) {
      li.append(h("p", "brief-note", field.inference_note));
    }
    if (field.source) li.append(h("p", "brief-note", `source: ${field.source}`));
    return li;
  }

  function plainRow(initial: string, onInput: (v: string) => void): HTMLElement {
    const li = h("li", "brief-item");
    li.append(edit(initial, onInput));
    return li;
  }

  function sectionEl(title: string): HTMLElement {
    const sec = h("section", "brief-section");
    sec.append(h("h2", "brief-section-title", title));
    return sec;
  }

  // ---- header ----
  const head = h("header", "brief-head");
  head.append(edit(state.title, (v) => (state.title = v), "brief-title"));

  const meta = h("div", "brief-meta");
  const tierSel = h("select", "brief-chip brief-tier brief-tier-select") as HTMLSelectElement;
  tierSel.disabled = locked;
  tierSel.append(new Option("verification", "verification"), new Option("validation", "validation"));
  tierSel.value = state.tier;
  tierSel.addEventListener("change", () => (state.tier = tierSel.value as BriefDoc["tier"]));
  selects.push(tierSel);
  meta.append(
    tierSel,
    h("span", "brief-chip", state.domain),
    h("span", "brief-chip brief-id", state.run_id.slice(0, 8)),
    h("span", "brief-chip", `rev ${state.revision}`),
  );
  head.append(meta);

  const [needing, total] = opts.debt ?? reviewDebt(state);
  head.append(
    h(
      "p",
      "brief-debt",
      needing > 0
        ? `${needing} of ${total} provenanced fields inferred — check these first.`
        : `All ${total} provenanced fields stated. Still your call.`,
    ),
  );
  const legend = h("div", "prov-legend");
  (["stated", "inferred", "defaulted", "corrected"] as Provenance[]).forEach((p) =>
    legend.append(badge(p)),
  );
  head.append(legend);
  root.append(head);

  // ---- objective ----
  const objSec = sectionEl("Objective");
  const objList = h("ul", "brief-list");
  objList.append(provRow(state.objective, "objective"));
  objSec.append(objList);
  root.append(objSec);

  // ---- provenanced lists ----
  const qoiSec = sectionEl("Quantities of interest");
  const qoiList = h("ul", "brief-list");
  state.quantities_of_interest.forEach((f, i) =>
    qoiList.append(provRow(f, `quantities_of_interest.${i}`)),
  );
  qoiSec.append(qoiList);
  root.append(qoiSec);

  const asmSec = sectionEl("Assumptions");
  const asmList = h("ul", "brief-list");
  state.assumptions.forEach((f, i) => asmList.append(provRow(f, `assumptions.${i}`)));
  asmSec.append(asmList);
  root.append(asmSec);

  // ---- checks (plain strings) ----
  const chkSec = sectionEl("Checks planned");
  const chkList = h("ul", "brief-list");
  state.checks_planned.forEach((c, i) =>
    chkList.append(plainRow(c, (v) => (state.checks_planned[i] = v))),
  );
  chkSec.append(chkList);
  root.append(chkSec);

  // ---- domain block ----
  const blockSec = sectionEl(`${state.domain} block`);

  const geq = h("div", "brief-sub");
  geq.append(h("h3", "brief-sub-title", "Governing equations"));
  const geqList = h("ul", "brief-list");
  state.block.governing_equations.forEach((e, i) =>
    geqList.append(plainRow(e, (v) => (state.block.governing_equations[i] = v))),
  );
  geq.append(geqList);
  blockSec.append(geq);

  const kp = h("div", "brief-sub");
  kp.append(h("h3", "brief-sub-title", "Key parameters"));
  const kpList = h("ul", "brief-list");
  state.block.key_parameters.forEach((f, i) =>
    kpList.append(provRow(f, `block.key_parameters.${i}`)),
  );
  kp.append(kpList);
  blockSec.append(kp);

  const dg = h("div", "brief-sub");
  dg.append(h("h3", "brief-sub-title", "Dimensionless groups"));
  const dgEntries = Object.entries(state.block.dimensionless_groups);
  if (dgEntries.length === 0) {
    dg.append(h("p", "brief-empty", "none derived"));
  } else {
    const dgList = h("ul", "brief-list");
    dgEntries.forEach(([k, v]) => dgList.append(h("li", "brief-item brief-kv", `${k} = ${v}`)));
    dg.append(dgList);
  }
  blockSec.append(dg);

  const geo = h("div", "brief-sub");
  geo.append(h("h3", "brief-sub-title", "Domain geometry"));
  geo.append(edit(state.block.domain_geometry, (v) => (state.block.domain_geometry = v), "brief-para"));
  blockSec.append(geo);

  const reg = h("div", "brief-sub");
  reg.append(h("h3", "brief-sub-title", "Regime notes"));
  reg.append(edit(state.block.regime_notes, (v) => (state.block.regime_notes = v), "brief-para"));
  blockSec.append(reg);

  root.append(blockSec);

  // ---- footer ----
  const foot = h("footer", "brief-foot");
  const status = h(
    "p",
    "brief-status",
    state.approved_by
      ? `Approved by ${state.approved_by}${state.approved_at ? ` · ${fmt(state.approved_at)}` : ""}`
      : "Draft — not approved. Nothing runs until you sign off.",
  );
  const approveBtn = h("button", "brief-approve", "Approve") as HTMLButtonElement;
  approveBtn.type = "button";
  approveBtn.disabled = locked || !opts.onApprove;
  approveBtn.addEventListener("click", async () => {
    if (!opts.onApprove || locked) return;
    approveBtn.disabled = true;
    approveBtn.textContent = "Approving…";
    const ok = await opts.onApprove({ brief: collectBrief(), corrections: collectCorrections() });
    if (!ok && !locked) {
      approveBtn.disabled = false;
      approveBtn.textContent = "Approve";
    }
  });
  foot.append(status, approveBtn);
  root.append(foot);

  host.append(root);

  function collectBrief(): BriefDoc {
    const out = structuredClone(state);
    for (const f of [
      out.objective,
      ...out.quantities_of_interest,
      ...out.assumptions,
      ...out.block.key_parameters,
    ]) {
      if (f.provenance === "corrected") f.provenance = "stated"; // the human owns it now
    }
    return out;
  }
  function collectCorrections(): CorrectionRec[] {
    return [...corrections.values()];
  }

  return {
    element: root,
    collectBrief,
    collectCorrections,
    lock(approvedBy, approvedAt) {
      locked = true;
      root.classList.add("is-locked");
      editables.forEach((e) => e.setAttribute("contenteditable", "false"));
      selects.forEach((s) => (s.disabled = true));
      status.textContent = `Approved by ${approvedBy} · ${fmt(approvedAt)}`;
      approveBtn.disabled = true;
      approveBtn.textContent = "Approved";
    },
  };
}

function fmt(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

/** A representative draft, for exercising the review surface without the engine. */
export function sampleBrief(): BriefDoc {
  const p = (
    value: string,
    provenance: Provenance = "stated",
    inference_note: string | null = null,
  ): Provenanced => ({ value, provenance, inference_note, source: null });
  return {
    run_id: "0f3c1a9e-sample",
    title: "Reproduce the Diff-PIC field-energy history for a warm plasma slab",
    revision: 1,
    created_at: new Date().toISOString(),
    objective: p(
      "Recover the total electromagnetic field-energy history of the reference PIC run",
      "inferred",
      "The paper frames the surrogate against this diagnostic; the run target is the PIC system it emulates.",
    ),
    quantities_of_interest: [
      p("Total field energy vs. time"),
      p("Longitudinal electric field spectrum E1, E2", "inferred", "Named in Fig. 3 without units."),
    ],
    assumptions: [
      p("Collisionless plasma", "inferred", "Standard for this regime; not stated outright."),
      p("Non-relativistic bulk motion"),
      p("Periodic 1D domain", "defaulted"),
    ],
    checks_planned: ["Energy conservation", "Grid convergence (GCI)", "Time-step refinement"],
    tier: "verification",
    domain: "plasma",
    block: {
      governing_equations: ["Vlasov equation", "Maxwell's equations (Ampère + Faraday)"],
      key_parameters: [
        p("Electron temperature Te = 100 eV"),
        p("Ion temperature Ti = 100 eV"),
        p("Laser intensity a0 = 2.0", "inferred", "Back-figured from the quoted intensity."),
      ],
      dimensionless_groups: { magnetization: 3.2 },
      domain_geometry: "One-dimensional periodic slab, length 100 Debye lengths.",
      regime_notes: "Collisionless, non-relativistic, unmagnetised background.",
    },
    approved_by: null,
    approved_at: null,
  };
}
