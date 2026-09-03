import { defineConfig } from "vite";
import electron from "vite-plugin-electron/simple";

// The renderer is ./index.html + ./src; the plugin builds electron/main.ts and
// electron/preload.ts into ./dist-electron and (re)launches Electron in dev.
export default defineConfig(async () => ({
  base: "./",
  server: { host: "127.0.0.1" },
  build: { outDir: "dist-web", emptyOutDir: true },
  plugins: [
    await electron({
      main: { entry: "electron/main.ts" },
      preload: { input: "electron/preload.ts" },
    }),
  ],
}));
