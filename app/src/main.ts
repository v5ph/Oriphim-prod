// oriphim desktop shell — interaction only. The Oriphim engine is reached
// through `window.oriphim` (see electron/preload.ts); most of it is still
// stubbed, so the composer echoes a canned reply.
import "./app.css";

// ---- dom helpers -------------------------------------------------------
const $ = <T extends Element = HTMLElement>(sel: string, root: ParentNode = document): T | null =>
  root.querySelector<T>(sel);

/** Required element: the shell can't function without it, so a miss is fatal. */
const el = <T extends Element = HTMLElement>(sel: string, root: ParentNode = document): T => {
  const found = root.querySelector<T>(sel);
  if (!found) throw new Error(`oriphim shell: missing element ${sel}`);
  return found;
};

const store = {
  get<T>(key: string, fallback: T): T {
    try {
      const raw = localStorage.getItem("oriphim." + key);
      return raw === null ? fallback : (JSON.parse(raw) as T);
    } catch {
      return fallback;
    }
  },
  set(key: string, value: unknown): void {
    try {
      localStorage.setItem("oriphim." + key, JSON.stringify(value));
    } catch {
      /* ignore */
    }
  },
  del(key: string): void {
    try {
      localStorage.removeItem("oriphim." + key);
    } catch {
      /* ignore */
    }
  },
};

const ESCAPES: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" };
const esc = (s: string): string => s.replace(/[&<>"]/g, (c) => ESCAPES[c] ?? c);

// ---- seed content (the paper queue, roughly) -------------------------
type Bucket = "Today" | "Yesterday" | "This week" | "Earlier";
type SortMode = "recent" | "name";

/** A folder. Runs are filed into at most one project; unfiled runs live in History. */
interface Project {
  id: string;
  name: string;
  open: boolean;
}
interface Run {
  id: string;
  title: string;
  bucket: Bucket;
  projectId: string | null;
}

const SEED_PROJECTS: Project[] = [
  { id: "p-diffpic", name: "Diff-PIC — laser-plasma PIC", open: true },
  { id: "p-disc", name: "Warped accretion disc", open: false },
];
const SEED_RUNS: Run[] = [
  { id: "r1", title: "Diff-PIC brief review", bucket: "Today", projectId: "p-diffpic" },
  { id: "r2", title: "Reproduce the field-energy history", bucket: "This week", projectId: "p-diffpic" },
  { id: "r3", title: "Convergence — supersonic ramp inlet", bucket: "Yesterday", projectId: "p-diffpic" },
  { id: "r4", title: "Which equations govern a twisted disc?", bucket: "Today", projectId: "p-disc" },
  { id: "r5", title: "RAFM steel: what does electropulsing change?", bucket: "Yesterday", projectId: null },
  { id: "r6", title: "Grid Convergence Index, worked example", bucket: "Earlier", projectId: null },
  { id: "r7", title: "Verification vs validation — where's the line?", bucket: "This week", projectId: null },
  {
    id: "r8",
    title: "Analysis of fusion propulsion using an ejection mass tokamak design",
    bucket: "Earlier",
    projectId: null,
  },
];
const BUCKETS: Bucket[] = ["Today", "Yesterday", "This week", "Earlier"];

let projects: Project[] = store.get<Project[]>("projects", SEED_PROJECTS);
let runs: Run[] = store.get<Run[]>("runs", SEED_RUNS);
function persist(): void {
  store.set("projects", projects);
  store.set("runs", runs);
}

// Rail titles get a hard character cap; the full text stays on the `title` tooltip.
const TITLE_CAP = 28;
const cap = (s: string): string =>
  s.length > TITLE_CAP ? s.slice(0, TITLE_CAP).trimEnd() + "…" : s;

const crumb = el("#crumb");
const runStatus = el("#sb-run");
const sbDot = el("#sb-dot");
const transcript = el("#transcript");

// ---- rail: project folders + unfiled history ------------------------
const projectList = el<HTMLUListElement>("#project-list");
const historyGroups = el("#history-groups");
const sortToggle = el<HTMLButtonElement>(".sort-toggle");
const railAdd = el<HTMLButtonElement>(".rail-add");
const railScroll = el(".rail-scroll");
let sortMode = store.get<SortMode>("sort", "recent");
sortToggle.dataset["sort"] = sortMode;
sortToggle.textContent = sortMode;

function projectsInOrder(): Project[] {
  const rows = [...projects];
  if (sortMode === "name") rows.sort((a, b) => a.name.localeCompare(b.name));
  return rows; // "recent" keeps insertion order — newest folders sit on top
}
function runsInProject(projectId: string): Run[] {
  return runs.filter((r) => r.projectId === projectId);
}

function makeRunRow(r: Run, flashId?: string): HTMLLIElement {
  const li = document.createElement("li");
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "rail-item";
  btn.dataset["id"] = r.id;
  btn.dataset["kind"] = "run";
  const name = document.createElement("span");
  name.className = "item-name";
  name.textContent = cap(r.title);
  name.title = r.title;
  btn.appendChild(name);
  btn.addEventListener("click", () => selectItem(btn, r.title, r.title));
  btn.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    openRunMenu(e, r);
  });
  if (r.id === flashId) {
    btn.classList.add("just-added");
    btn.addEventListener("animationend", () => btn.classList.remove("just-added"), { once: true });
  }
  li.appendChild(btn);
  return li;
}

function renderRail(flashId?: string): void {
  // ---- projects: collapsible folders, each nesting its runs ----
  projectList.innerHTML = "";
  for (const p of projectsInOrder()) {
    const li = document.createElement("li");
    li.className = p.open ? "project" : "project collapsed";

    const head = document.createElement("button");
    head.type = "button";
    head.className = "rail-item project-head";
    head.dataset["id"] = p.id;
    head.dataset["kind"] = "project";
    const nm = document.createElement("span");
    nm.className = "item-name";
    nm.textContent = cap(p.name);
    nm.title = p.name;
    const count = document.createElement("span");
    count.className = "item-meta";
    count.textContent = String(runsInProject(p.id).length);
    head.append(nm, count);
    head.addEventListener("click", () => {
      p.open = !p.open;
      persist();
      renderRail();
    });
    head.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      openProjectMenu(e, p);
    });

    const sub = document.createElement("ul");
    sub.className = "rail-list project-runs";
    const inside = runsInProject(p.id);
    if (inside.length === 0) {
      const empty = document.createElement("li");
      empty.className = "project-empty";
      empty.textContent = "empty — right-click a run to move it here";
      sub.appendChild(empty);
    } else {
      for (const r of inside) sub.appendChild(makeRunRow(r, flashId));
    }

    li.append(head, sub);
    projectList.appendChild(li);
  }

  // ---- history: only unfiled runs, still grouped by time ----
  historyGroups.innerHTML = "";
  const unfiled = runs.filter((r) => r.projectId === null);
  for (const bucket of BUCKETS) {
    const items = unfiled.filter((r) => r.bucket === bucket);
    if (items.length === 0) continue;
    const group = document.createElement("div");
    group.className = "history-group";
    const label = document.createElement("button");
    label.type = "button";
    label.className = "history-bucket";
    label.textContent = bucket;
    label.addEventListener("click", () => group.classList.toggle("collapsed"));
    const ul = document.createElement("ul");
    ul.className = "rail-list";
    for (const r of items) ul.appendChild(makeRunRow(r, flashId));
    group.append(label, ul);
    historyGroups.appendChild(group);
  }
  if (unfiled.length === 0) {
    const none = document.createElement("p");
    none.className = "project-empty";
    none.textContent = "no unfiled runs";
    historyGroups.appendChild(none);
  }
}

function setSort(mode: SortMode): void {
  sortMode = mode;
  store.set("sort", sortMode);
  sortToggle.dataset["sort"] = sortMode;
  sortToggle.textContent = sortMode;
  renderRail();
}
sortToggle.addEventListener("click", () => setSort(sortMode === "recent" ? "name" : "recent"));
railAdd.addEventListener("click", () => {
  const p = createProject();
  renameProject(p);
});

// ---- rail mutations -------------------------------------------------
function createProject(name = "New project"): Project {
  const p: Project = { id: "p" + Date.now(), name, open: true };
  projects.unshift(p);
  persist();
  renderRail();
  return p;
}
function deleteProject(p: Project): void {
  for (const r of runs) if (r.projectId === p.id) r.projectId = null; // runs fall back to History
  projects = projects.filter((x) => x.id !== p.id);
  persist();
  renderRail();
}
function moveRun(r: Run, projectId: string | null): void {
  r.projectId = projectId;
  if (projectId) {
    const p = projects.find((x) => x.id === projectId);
    if (p) p.open = true;
  }
  persist();
  renderRail(r.id);
}
function deleteRun(r: Run): void {
  runs = runs.filter((x) => x.id !== r.id);
  persist();
  renderRail();
}
function newProjectWith(r: Run): void {
  const p = createProject();
  r.projectId = p.id;
  persist();
  renderRail();
  renameProject(p);
}

// Inline rename. All characters allowed — only trimmed, and empty is rejected.
function beginRename(id: string, current: string, commit: (next: string) => void): void {
  renderRail();
  const row = $(`.rail-item[data-id="${id}"]`);
  if (!row) return;
  const input = document.createElement("input");
  input.type = "text";
  input.className = "rename-input";
  input.value = current;
  row.replaceWith(input);
  input.focus();
  input.select();
  let done = false;
  const finish = (save: boolean): void => {
    if (done) return;
    done = true;
    const next = input.value.trim();
    if (save && next && next !== current) commit(next);
    else renderRail();
  };
  input.addEventListener("keydown", (e) => {
    e.stopPropagation();
    if (e.key === "Enter") {
      e.preventDefault();
      finish(true);
    } else if (e.key === "Escape") {
      e.preventDefault();
      finish(false);
    }
  });
  input.addEventListener("blur", () => finish(true));
}
function renameRun(r: Run): void {
  beginRename(r.id, r.title, (next) => {
    r.title = next;
    persist();
    renderRail();
  });
}
function renameProject(p: Project): void {
  beginRename(p.id, p.name, (next) => {
    p.name = next;
    persist();
    renderRail();
  });
}

// ---- right-click context menu ------------------------------------
interface MenuItem {
  label: string;
  act?: () => void;
  sub?: MenuItem[];
  danger?: boolean;
  sep?: boolean;
}
const ctxMenu = el("#ctx-menu");

function closeCtxMenu(): void {
  ctxMenu.hidden = true;
  ctxMenu.innerHTML = "";
  ctxMenu.classList.remove("flip");
}
function buildMenu(items: MenuItem[]): HTMLUListElement {
  const ul = document.createElement("ul");
  for (const it of items) {
    const li = document.createElement("li");
    if (it.sep) {
      li.className = "ctx-sep";
      li.setAttribute("aria-hidden", "true");
      ul.appendChild(li);
      continue;
    }
    li.textContent = it.label;
    li.setAttribute("role", "menuitem");
    if (it.danger) li.classList.add("danger");
    if (it.sub && it.sub.length) {
      li.classList.add("has-sub");
      li.appendChild(buildMenu(it.sub));
    } else if (it.act) {
      const act = it.act;
      li.addEventListener("click", (e) => {
        e.stopPropagation();
        closeCtxMenu();
        act();
      });
    }
    ul.appendChild(li);
  }
  return ul;
}
function openMenu(x: number, y: number, items: MenuItem[]): void {
  ctxMenu.innerHTML = "";
  ctxMenu.classList.toggle("flip", x > window.innerWidth - 340);
  ctxMenu.appendChild(buildMenu(items));
  ctxMenu.hidden = false;
  const mw = ctxMenu.offsetWidth;
  const mh = ctxMenu.offsetHeight;
  ctxMenu.style.left = Math.max(6, Math.min(x, window.innerWidth - mw - 6)) + "px";
  ctxMenu.style.top = Math.max(6, Math.min(y, window.innerHeight - mh - 6)) + "px";
}
function openRunMenu(e: MouseEvent, r: Run): void {
  const moveSub: MenuItem[] = [];
  if (r.projectId !== null) {
    moveSub.push({ label: "Remove from project", act: () => moveRun(r, null) });
    moveSub.push({ label: "", sep: true });
  }
  for (const p of projects) {
    if (p.id === r.projectId) continue;
    moveSub.push({ label: p.name, act: () => moveRun(r, p.id) });
  }
  if (moveSub.length && !moveSub[moveSub.length - 1]?.sep) moveSub.push({ label: "", sep: true });
  moveSub.push({ label: "New project…", act: () => newProjectWith(r) });

  openMenu(e.clientX, e.clientY, [
    { label: "Rename", act: () => renameRun(r) },
    { label: "Move to project", sub: moveSub },
    { label: "", sep: true },
    { label: "Delete run", danger: true, act: () => deleteRun(r) },
  ]);
}
function openProjectMenu(e: MouseEvent, p: Project): void {
  openMenu(e.clientX, e.clientY, [
    { label: "Rename", act: () => renameProject(p) },
    { label: "New project", act: () => renameProject(createProject()) },
    { label: "", sep: true },
    { label: "Delete project", danger: true, act: () => deleteProject(p) },
  ]);
}
document.addEventListener(
  "pointerdown",
  (e) => {
    if (!ctxMenu.hidden && !ctxMenu.contains(e.target as Node)) closeCtxMenu();
  },
  true,
);
window.addEventListener("blur", closeCtxMenu);
window.addEventListener("resize", closeCtxMenu);
railScroll.addEventListener("scroll", closeCtxMenu, { passive: true });

// ---- thread ------------------------------------------------------
type Role = "user" | "oriphim";

function resetThread(): void {
  transcript.querySelector(".thread")?.remove();
  transcript.classList.remove("has-messages");
}
function thread(): Element {
  let t = transcript.querySelector(".thread");
  if (!t) {
    t = document.createElement("div");
    t.className = "thread";
    transcript.appendChild(t);
    transcript.classList.add("has-messages");
  }
  return t;
}
function addMessage(
  role: Role,
  text: string,
  opts: { pending?: boolean; attach?: string | null } = {},
): HTMLElement {
  const { pending = false, attach = null } = opts;
  const msg = document.createElement("article");
  msg.className = `msg from-${role}${pending ? " is-pending" : ""}`;
  msg.innerHTML =
    `<div class="msg-role">${role === "user" ? "You" : "oriphim"}</div>` +
    `<div class="msg-body">${esc(text)}</div>` +
    (attach ? `<div class="msg-attach">↟ ${esc(attach)}</div>` : "");
  thread().appendChild(msg);
  transcript.scrollTop = transcript.scrollHeight;
  return msg;
}
function setCrumb(text: string): void {
  crumb.textContent = text;
}

function selectItem(itemEl: HTMLElement, label: string, title: string): void {
  document.querySelectorAll(".rail-item.is-active").forEach((n) => n.classList.remove("is-active"));
  itemEl.classList.add("is-active");
  setCrumb(title);
  resetThread();
  addMessage(
    "oriphim",
    `Opened “${label}”. This shell isn't wired to stored runs yet — start a new prompt below.`,
  );
  closeDrawer();
}
function activateItemById(id: string): void {
  // make sure the target is on screen: open its folder / uncollapse its section
  const run = runs.find((r) => r.id === id);
  if (run?.projectId) {
    const parent = projects.find((p) => p.id === run.projectId);
    if (parent && !parent.open) {
      parent.open = true;
      persist();
    }
  }
  const proj = projects.find((p) => p.id === id);
  if (proj && !proj.open) {
    proj.open = true;
    persist();
  }
  renderRail();
  const btn = $(`.rail-item[data-id="${id}"]`);
  if (!btn) return;
  btn.closest(".rail-block")?.classList.remove("collapsed");
  btn.closest(".history-group")?.classList.remove("collapsed");
  if (run) btn.click(); // a project head toggles on click, so only fire for runs
  btn.scrollIntoView({ block: "nearest" });
}

// ---- composer + draft persistence ---------------------------------
const form = el<HTMLFormElement>("#composer");
const promptEl = el<HTMLTextAreaElement>("#prompt");
const sendBtn = el<HTMLButtonElement>(".send");
const autoGrow = (): void => {
  promptEl.style.height = "auto";
  promptEl.style.height = Math.min(promptEl.scrollHeight, 168) + "px";
};
const syncSend = (): void => {
  sendBtn.disabled = promptEl.value.trim() === "";
};

promptEl.value = store.get<string>("draft", "");

function submitPrompt(): void {
  const text = promptEl.value.trim();
  if (!text) return;
  addMessage("user", text, { attach: staged });
  promptEl.value = "";
  store.del("draft");
  autoGrow();
  syncSend();
  clearAttachment();
  const words = text.split(/\s+/);
  setCrumb(words.slice(0, 6).join(" ") + (words.length > 6 ? "…" : ""));
  runStatus.textContent = "reading…";
  sbDot.classList.add("is-active");

  const pending = addMessage("oriphim", "Reading…", { pending: true });
  window.setTimeout(() => {
    pending.classList.remove("is-pending");
    const body = pending.querySelector(".msg-body");
    if (body) {
      body.textContent =
        "The interpretation step isn't connected to this shell yet. When it is, the draft run " +
        "brief appears in the right pane — provenance-marked, nothing executed until you approve it.";
    }
    transcript.scrollTop = transcript.scrollHeight;
    runStatus.textContent = "draft brief — not wired";
    sbDot.classList.remove("is-active");
  }, 700);
}

promptEl.addEventListener("input", () => {
  autoGrow();
  syncSend();
  store.set("draft", promptEl.value);
});
promptEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    submitPrompt();
  }
});
form.addEventListener("submit", (e) => {
  e.preventDefault();
  submitPrompt();
});

// ---- attachment: file picker + drag-and-drop --------------------
const fileInput = el<HTMLInputElement>("#file-input");
const attachRow = el("#attach-row");
const attachName = el("#attach-name");
const dropOverlay = el("#drop-overlay");
const ACCEPT = /\.(pdf|html?|txt|md)$/i;
let staged: string | null = null;
let dragDepth = 0;

function stageAttachment(name: string): void {
  staged = name;
  attachName.textContent = name;
  attachRow.hidden = false;
}
function clearAttachment(): void {
  staged = null;
  attachRow.hidden = true;
  fileInput.value = "";
}
el(".attach").addEventListener("click", async () => {
  // native dialog in the desktop app; the hidden <input> is the browser fallback
  if (window.oriphim?.openPaper) {
    const picked = await window.oriphim.openPaper();
    if (picked) stageAttachment(picked.name);
  } else {
    fileInput.click();
  }
});
el(".attach-remove").addEventListener("click", clearAttachment);
fileInput.addEventListener("change", () => {
  const f = fileInput.files?.[0];
  if (f) stageAttachment(f.name);
});

window.addEventListener("dragenter", (e) => {
  const dt = e.dataTransfer;
  if (!dt || !dt.types.includes("Files")) return;
  dragDepth++;
  dropOverlay.hidden = false;
});
window.addEventListener("dragover", (e) => {
  if (!dropOverlay.hidden) e.preventDefault();
});
window.addEventListener("dragleave", () => {
  dragDepth = Math.max(0, dragDepth - 1);
  if (dragDepth === 0) dropOverlay.hidden = true;
});
window.addEventListener("drop", (e) => {
  e.preventDefault();
  dragDepth = 0;
  dropOverlay.hidden = true;
  const f = e.dataTransfer?.files?.[0];
  if (f && ACCEPT.test(f.name)) {
    stageAttachment(f.name);
    promptEl.focus();
  } else if (f) {
    addMessage("oriphim", `Can't attach ${f.name} — expecting a PDF, HTML, or text file.`);
  }
});

// ---- new run ---------------------------------------------------
function newRun(): void {
  document.querySelectorAll(".rail-item.is-active").forEach((n) => n.classList.remove("is-active"));
  resetThread();
  clearAttachment();
  setCrumb("new run");
  runStatus.textContent = "no active run";
  sbDot.classList.remove("is-active");
  const entry: Run = { id: "r" + Date.now(), title: "New run", bucket: "Today", projectId: null };
  runs.unshift(entry);
  persist();
  renderRail(entry.id);
  promptEl.focus();
  closeDrawer();
}
el(".new-chat").addEventListener("click", newRun);

// ---- panes: rail + context ----------------------------------
const wide = (): boolean => window.matchMedia("(min-width: 1081px)").matches;
const mobile = (): boolean => window.matchMedia("(max-width: 820px)").matches;
const scrim = el(".scrim");

type PaneName = "rail" | "ctx";

function reflectToggle(name: PaneName): void {
  const btn = $(`.pane-toggle[data-toggle="${name}"]`);
  if (!btn) return;
  const cl = document.body.classList;
  const visible =
    name === "rail"
      ? mobile()
        ? cl.contains("drawer-open")
        : !cl.contains("rail-collapsed")
      : mobile()
        ? false
        : wide()
          ? !cl.contains("ctx-collapsed")
          : cl.contains("ctx-open");
  btn.setAttribute("aria-pressed", String(visible));
}
function toggleRail(): void {
  if (mobile()) {
    const open = document.body.classList.toggle("drawer-open");
    scrim.hidden = !open;
  } else {
    store.set("rail-collapsed", document.body.classList.toggle("rail-collapsed"));
  }
  reflectToggle("rail");
}
function toggleCtx(): void {
  if (mobile()) return;
  if (wide()) store.set("ctx-collapsed", document.body.classList.toggle("ctx-collapsed"));
  else document.body.classList.toggle("ctx-open");
  reflectToggle("ctx");
}
function closeDrawer(): void {
  document.body.classList.remove("drawer-open");
  scrim.hidden = true;
  reflectToggle("rail");
}
document.querySelectorAll<HTMLElement>(".pane-toggle").forEach((btn) => {
  btn.addEventListener("click", () =>
    btn.dataset["toggle"] === "rail" ? toggleRail() : toggleCtx(),
  );
});
scrim.addEventListener("click", closeDrawer);
window.addEventListener("resize", () => {
  reflectToggle("rail");
  reflectToggle("ctx");
});

// ---- malleable panes: drag the borders to resize --------------
type PaneVar = "--rail-w" | "--ctx-w";
const MIN_CHAT = 360;
const DEFAULT_W: Record<"rail" | "ctx", number> = { rail: 236, ctx: 320 };
const RANGE: Record<"rail" | "ctx", [number, number]> = { rail: [180, 460], ctx: [240, 560] };

const workspace = el(".workspace");
const rootStyle = document.documentElement.style;
const paneVar = (side: "rail" | "ctx"): PaneVar => (side === "rail" ? "--rail-w" : "--ctx-w");
const readVar = (v: PaneVar): number =>
  parseFloat(getComputedStyle(document.documentElement).getPropertyValue(v)) || 0;
const clamp = (px: number, [lo, hi]: [number, number]): number => Math.max(lo, Math.min(px, hi));

function setPaneWidth(side: "rail" | "ctx", px: number, persist = false): void {
  const w = Math.round(clamp(px, RANGE[side]));
  rootStyle.setProperty(paneVar(side), `${w}px`);
  if (persist) store.set(`${side}-w`, w);
}

setPaneWidth("rail", store.get<number>("rail-w", DEFAULT_W.rail));
setPaneWidth("ctx", store.get<number>("ctx-w", DEFAULT_W.ctx));

document.querySelectorAll<HTMLElement>(".resizer").forEach((rz) => {
  const side: "rail" | "ctx" = rz.dataset["resize"] === "ctx" ? "ctx" : "rail";
  rz.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    rz.setPointerCapture(e.pointerId);
    document.body.classList.add("resizing");
    const box = workspace.getBoundingClientRect();
    const onMove = (ev: PointerEvent): void => {
      const raw = side === "rail" ? ev.clientX - box.left : box.right - ev.clientX;
      const room = box.width - readVar(paneVar(side === "rail" ? "ctx" : "rail")) - MIN_CHAT;
      setPaneWidth(side, Math.min(raw, room));
    };
    const onUp = (ev: PointerEvent): void => {
      rz.releasePointerCapture(ev.pointerId);
      document.body.classList.remove("resizing");
      rz.removeEventListener("pointermove", onMove);
      rz.removeEventListener("pointerup", onUp);
      store.set(`${side}-w`, readVar(paneVar(side)));
    };
    rz.addEventListener("pointermove", onMove);
    rz.addEventListener("pointerup", onUp);
  });
  rz.addEventListener("dblclick", () => setPaneWidth(side, DEFAULT_W[side], true));
});

// ---- collapsible sections ------------------------------------
function wireCollapsible(trigger: HTMLElement, container: Element, key: string): void {
  const apply = (collapsed: boolean): void => {
    container.classList.toggle("collapsed", collapsed);
    trigger.setAttribute("aria-expanded", String(!collapsed));
  };
  apply(store.get<boolean>(key, false));
  trigger.addEventListener("click", () => {
    const collapsed = !container.classList.contains("collapsed");
    apply(collapsed);
    store.set(key, collapsed);
  });
}

document.querySelectorAll<HTMLElement>(".rail-block[data-section]").forEach((block) => {
  const label = block.querySelector<HTMLElement>(".rail-label");
  const name = block.dataset["section"];
  if (label && name) wireCollapsible(label, block, `sec.${name}`);
});
const ctxTitle = $<HTMLElement>(".ctx-title");
const ctxPane = $("#context");
if (ctxTitle && ctxPane) wireCollapsible(ctxTitle, ctxPane, "sec.ctx");

// ---- ⌘K command palette ------------------------------------
interface Command {
  label: string;
  group: string;
  run: () => void;
}

const palette = el("#palette");
const paletteInput = el<HTMLInputElement>("#palette-input");
const paletteList = el("#palette-list");
let paletteCmds: Command[] = [];
let paletteSel = 0;

function buildCommands(): Command[] {
  const cmds: Command[] = [
    { label: "New run", group: "Action", run: newRun },
    { label: "Toggle sidebar", group: "View", run: toggleRail },
    { label: "Toggle context panel", group: "View", run: toggleCtx },
    { label: "Sort projects by recent", group: "View", run: () => setSort("recent") },
    { label: "Sort projects by name", group: "View", run: () => setSort("name") },
  ];
  for (const p of projects) {
    cmds.push({ label: p.name, group: "Project", run: () => activateItemById(p.id) });
  }
  for (const r of runs) {
    cmds.push({
      label: r.title,
      group: r.projectId ? "Run" : "History",
      run: () => activateItemById(r.id),
    });
  }
  return cmds;
}
/** Subsequence match; lower score is better, -1 means no match. */
function fuzzy(query: string, text: string): number {
  const q = query.toLowerCase();
  const t = text.toLowerCase();
  if (!q) return 0;
  let qi = 0;
  let score = 0;
  let lastHit = -1;
  for (let ti = 0; ti < t.length && qi < q.length; ti++) {
    if (t[ti] === q[qi]) {
      score += lastHit >= 0 ? ti - lastHit : ti;
      lastHit = ti;
      qi++;
    }
  }
  return qi === q.length ? score : -1;
}
function renderPalette(): void {
  const query = paletteInput.value.trim();
  const scored = paletteCmds
    .map((c) => ({ c, s: fuzzy(query, c.label) }))
    .filter((x) => x.s >= 0)
    .sort((a, b) => a.s - b.s || a.c.label.length - b.c.label.length)
    .slice(0, 40);
  paletteSel = 0;
  paletteList.innerHTML = "";
  if (!scored.length) {
    paletteList.innerHTML = `<li class="palette-empty">No match</li>`;
    return;
  }
  scored.forEach(({ c }, i) => {
    const li = document.createElement("li");
    li.setAttribute("role", "option");
    li.innerHTML = `<span>${esc(c.label)}</span><span class="cmd-group">${esc(c.group)}</span>`;
    li.addEventListener("mousemove", () => setPaletteSel(i));
    li.addEventListener("click", () => runPalette(c));
    paletteList.appendChild(li);
  });
  setPaletteSel(0);
}
function setPaletteSel(i: number): void {
  const items = paletteList.querySelectorAll<HTMLElement>("li[role='option']");
  if (!items.length) return;
  paletteSel = (i + items.length) % items.length;
  items.forEach((li, idx) => li.setAttribute("aria-selected", String(idx === paletteSel)));
  items[paletteSel]?.scrollIntoView({ block: "nearest" });
}
function runPalette(cmd: Command): void {
  closePalette();
  cmd.run();
}
function openPalette(): void {
  paletteCmds = buildCommands();
  palette.hidden = false;
  paletteInput.value = "";
  renderPalette();
  paletteInput.focus();
}
function closePalette(): void {
  palette.hidden = true;
}

paletteInput.addEventListener("input", renderPalette);
paletteInput.addEventListener("keydown", (e) => {
  if (e.key === "ArrowDown") {
    e.preventDefault();
    setPaletteSel(paletteSel + 1);
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    setPaletteSel(paletteSel - 1);
  } else if (e.key === "Enter") {
    e.preventDefault();
    paletteList.querySelectorAll<HTMLElement>("li[role='option']")[paletteSel]?.dispatchEvent(
      new MouseEvent("click"),
    );
  }
});
palette.addEventListener("click", (e) => {
  if (e.target === palette) closePalette();
});

document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    if (palette.hidden) openPalette();
    else closePalette();
  } else if (e.key === "Escape") {
    if (!ctxMenu.hidden) closeCtxMenu();
    else if (!palette.hidden) closePalette();
    else closeDrawer();
  }
});

// ---- go -----------------------------------------------------
if (!mobile()) {
  if (store.get("rail-collapsed", false)) document.body.classList.add("rail-collapsed");
  if (store.get("ctx-collapsed", false)) document.body.classList.add("ctx-collapsed");
}
renderRail();
autoGrow();
syncSend();
reflectToggle("rail");
reflectToggle("ctx");
