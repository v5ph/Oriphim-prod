import { contextBridge, ipcRenderer } from "electron";

/**
 * The seam between the renderer and the Oriphim engine. Everything except the
 * native file dialog is stubbed until the Python side (a local FastAPI process)
 * is wired in — the renderer already degrades to canned responses.
 */
const bridge = {
  platform: process.platform as NodeJS.Platform,

  /** Native "attach a paper" dialog. Returns null if cancelled. */
  openPaper: (): Promise<{ path: string; name: string } | null> =>
    ipcRenderer.invoke("oriphim:openPaper"),

  /** prose (+ optional paper) -> draft run brief. Stubbed. */
  propose: async (
    description: string,
    paperPath?: string,
  ): Promise<{ wired: false; description: string; paperPath: string | null; message: string }> => ({
    wired: false,
    description,
    paperPath: paperPath ?? null,
    message:
      "The interpretation step isn't connected to this shell yet. When it is, the draft run " +
      "brief appears in the right pane — provenance-marked, nothing executed until you approve it.",
  }),
};

contextBridge.exposeInMainWorld("oriphim", bridge);

export type OriphimBridge = typeof bridge;
