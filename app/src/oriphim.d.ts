import type { OriphimBridge } from "../electron/preload";

declare global {
  interface Window {
    // Injected by electron/preload.ts; absent when the renderer runs in a plain
    // browser (the Vite preview), so every call site guards for it.
    oriphim?: OriphimBridge;
  }
}

export {};
