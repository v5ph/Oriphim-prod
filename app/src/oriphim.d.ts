import type { OriphimBridge } from "../electron/preload";

declare global {
  interface Window {
    oriphim: OriphimBridge;
  }
}

export {};
