import { contextBridge, ipcRenderer, webUtils } from "electron";

/**
 * The seam between the renderer and the Oriphim engine. The engine runs as a
 * local sidecar the main process manages (see main.ts); every call here is
 * proxied through IPC and comes back as a discriminated result — a rejected
 * promise never crosses this boundary.
 */

export interface EngineError {
  kind: string;
  message: string;
}
export type ProposeResult =
  | { ok: true; brief: unknown; reviewDebt: [number, number] }
  | { ok: false; error: EngineError };
export type ApproveResult = { ok: true; brief: unknown } | { ok: false; error: EngineError };
export interface EngineStatus {
  online: boolean;
  port: number | null;
  modelConfigured: boolean;
}

const bridge = {
  platform: process.platform as NodeJS.Platform,

  /** Native "attach a paper" dialog. Returns null if cancelled. */
  openPaper: (): Promise<{ path: string; name: string } | null> =>
    ipcRenderer.invoke("oriphim:openPaper"),

  /** The real filesystem path of a dropped File (Electron removed File.path). */
  getPathForFile: (file: File): string => webUtils.getPathForFile(file),

  /** Is the engine up, and does it have model credentials? */
  engineStatus: (): Promise<EngineStatus> => ipcRenderer.invoke("oriphim:status"),

  /** The reviewer's name (git config user.name), for the approval record. */
  reviewer: (): Promise<string> => ipcRenderer.invoke("oriphim:reviewer"),

  /** prose (+ optional paper path) -> draft run brief. */
  propose: (description: string, paperPath?: string | null): Promise<ProposeResult> =>
    ipcRenderer.invoke("oriphim:propose", { description, paperPath: paperPath ?? null }),

  /** Lock a reviewed brief: edited envelope + valueless correction records. */
  approve: (args: {
    brief: unknown;
    corrections: unknown[];
    approvedBy: string;
  }): Promise<ApproveResult> => ipcRenderer.invoke("oriphim:approve", args),
};

contextBridge.exposeInMainWorld("oriphim", bridge);

export type OriphimBridge = typeof bridge;
