import { spawn, execFile, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { app, BrowserWindow, ipcMain, dialog } from "electron";

const PRELOAD = path.join(__dirname, "preload.js");
const DEV_URL = process.env.VITE_DEV_SERVER_URL;

// __dirname is app/dist-electron/ ; the engine and its .venv live at the repo root.
const REPO_ROOT = path.resolve(__dirname, "..", "..");

// ---- the Python engine sidecar -------------------------------------------
// Electron spawns `oriphim-api` (a uvicorn server) bound to 127.0.0.1. The
// server prints `ORIPHIM_API_PORT=<n>` on stdout once it is listening; every
// bridge call waits on that. If it never comes up the app still runs — the
// renderer degrades to an "engine offline" state.

type EngineState = "starting" | "online" | "offline";

let engine: ChildProcess | null = null;
let engineState: EngineState = "starting";
let enginePort: number | null = null;
let resolvePort: (port: number | null) => void;
const portReady = new Promise<number | null>((resolve) => {
  resolvePort = resolve;
});

/** Minimal `.env` reader — `KEY=VALUE` lines, `#` comments, no interpolation. */
function readDotenv(file: string): Record<string, string> {
  const out: Record<string, string> = {};
  let text: string;
  try {
    text = fs.readFileSync(file, "utf-8");
  } catch {
    return out;
  }
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq === -1) continue;
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (key) out[key] = value;
  }
  return out;
}

function workspaceDir(): string {
  return app.isPackaged
    ? path.join(app.getPath("userData"), "workspace")
    : path.join(REPO_ROOT, ".oriphim-workspace");
}

function startEngine(): void {
  const pythonBin =
    process.env.ORIPHIM_PY || path.join(REPO_ROOT, ".venv", "bin", "python");
  const env = {
    ...process.env,
    ...readDotenv(path.join(REPO_ROOT, ".env")),
    ORIPHIM_WORKSPACE: workspaceDir(),
    PYTHONUNBUFFERED: "1",
  };

  let child: ChildProcess;
  try {
    child = spawn(pythonBin, ["-m", "oriphim.api"], { cwd: REPO_ROOT, env });
  } catch (err) {
    console.error("[engine] failed to spawn:", err);
    engineState = "offline";
    resolvePort(null);
    return;
  }
  engine = child;

  const timeout = setTimeout(() => {
    if (engineState === "starting") {
      console.error("[engine] no port after 15s — treating as offline");
      engineState = "offline";
      resolvePort(null);
    }
  }, 15_000);

  child.stdout?.on("data", (buf: Buffer) => {
    const text = buf.toString();
    const match = text.match(/ORIPHIM_API_PORT=(\d+)/);
    if (match && engineState === "starting") {
      enginePort = Number(match[1]);
      engineState = "online";
      clearTimeout(timeout);
      resolvePort(enginePort);
      console.log(`[engine] online on ${enginePort}`);
    }
  });
  child.stderr?.on("data", (buf: Buffer) => console.error(`[engine] ${buf.toString().trimEnd()}`));
  child.on("error", (err) => {
    console.error("[engine] process error:", err);
    engineState = "offline";
    clearTimeout(timeout);
    resolvePort(null);
  });
  child.on("exit", (code) => {
    console.log(`[engine] exited (${code})`);
    engine = null;
    if (engineState === "starting") {
      engineState = "offline";
      clearTimeout(timeout);
      resolvePort(null);
    }
  });
}

function stopEngine(): void {
  engine?.kill();
  engine = null;
}

/** POST helper: resolves to a discriminated result, never throws across IPC. */
async function engineFetch(
  route: string,
  body: unknown,
): Promise<{ ok: true; data: unknown } | { ok: false; error: { kind: string; message: string } }> {
  const port = await portReady;
  if (port === null) {
    return { ok: false, error: { kind: "offline", message: "The engine isn't running." } };
  }
  try {
    const res = await fetch(`http://127.0.0.1:${port}${route}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    if (res.ok) return { ok: true, data: payload };
    const detail = (payload.detail ?? {}) as { kind?: string; message?: string };
    return {
      ok: false,
      error: { kind: detail.kind ?? `http_${res.status}`, message: detail.message ?? res.statusText },
    };
  } catch (err) {
    return { ok: false, error: { kind: "unreachable", message: String(err) } };
  }
}

// ---- window ------------------------------------------------------------
function createWindow(): void {
  const win = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 900,
    minHeight: 600,
    show: false,
    backgroundColor: "#2d2d2d", // matches --chrome, so no white flash before load
    titleBarStyle: "hiddenInset",
    trafficLightPosition: { x: 16, y: 13 }, // into the 36px custom title bar
    webPreferences: {
      preload: PRELOAD,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  win.once("ready-to-show", () => win.show());

  if (DEV_URL) {
    void win.loadURL(DEV_URL);
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    void win.loadFile(path.join(__dirname, "../dist-web/index.html"));
  }
}

// ---- IPC: the window.oriphim surface ---------------------------------
ipcMain.handle("oriphim:openPaper", async () => {
  const result = await dialog.showOpenDialog({
    title: "Attach a paper",
    properties: ["openFile"],
    filters: [{ name: "Papers", extensions: ["pdf", "html", "htm", "txt", "md"] }],
  });
  const file = result.filePaths[0];
  return result.canceled || !file ? null : { path: file, name: path.basename(file) };
});

ipcMain.handle("oriphim:status", async () => {
  const port = await portReady;
  if (port === null) return { online: false, port: null, modelConfigured: false };
  try {
    const res = await fetch(`http://127.0.0.1:${port}/health`);
    const body = (await res.json()) as { model_configured?: boolean };
    return { online: true, port, modelConfigured: Boolean(body.model_configured) };
  } catch {
    return { online: false, port, modelConfigured: false };
  }
});

ipcMain.handle("oriphim:propose", async (_e, args: { description: string; paperPath?: string | null }) => {
  const result = await engineFetch("/propose", {
    description: args.description,
    paper_path: args.paperPath ?? null,
  });
  if (!result.ok) return result;
  const data = result.data as { brief: unknown; review_debt: [number, number] };
  return { ok: true, brief: data.brief, reviewDebt: data.review_debt };
});

ipcMain.handle(
  "oriphim:approve",
  async (_e, args: { brief: unknown; corrections: unknown[]; approvedBy: string }) => {
    const result = await engineFetch("/approve", {
      brief: args.brief,
      corrections: args.corrections,
      approved_by: args.approvedBy,
    });
    if (!result.ok) return result;
    return { ok: true, brief: (result.data as { brief: unknown }).brief };
  },
);

let cachedReviewer: string | null = null;
ipcMain.handle("oriphim:reviewer", async () => {
  if (cachedReviewer !== null) return cachedReviewer;
  cachedReviewer = await new Promise<string>((resolve) => {
    execFile("git", ["config", "user.name"], { cwd: REPO_ROOT }, (err, stdout) => {
      resolve(err ? "reviewer" : stdout.trim() || "reviewer");
    });
  });
  return cachedReviewer;
});

// ---- lifecycle -------------------------------------------------------
void app.whenReady().then(() => {
  startEngine();
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("before-quit", stopEngine);
app.on("window-all-closed", () => {
  stopEngine();
  if (process.platform !== "darwin") app.quit();
});
