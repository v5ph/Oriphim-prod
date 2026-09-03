import { app, BrowserWindow, ipcMain, dialog } from "electron";
import path from "node:path";

const PRELOAD = path.join(__dirname, "preload.js");
const DEV_URL = process.env.VITE_DEV_SERVER_URL;

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

// A real native file picker for the composer's attach button.
ipcMain.handle("oriphim:openPaper", async () => {
  const result = await dialog.showOpenDialog({
    title: "Attach a paper",
    properties: ["openFile"],
    filters: [{ name: "Papers", extensions: ["pdf", "html", "htm", "txt", "md"] }],
  });
  const file = result.filePaths[0];
  return result.canceled || !file ? null : { path: file, name: path.basename(file) };
});

void app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
