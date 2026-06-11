import { create } from "zustand";

export type Page =
  | "chat"
  | "goals"
  | "inbox"
  | "timeline"
  | "memories"
  | "dashboard";

interface AppState {
  currentPage: Page;
  setPage: (page: Page) => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentPage: "chat",
  setPage: (page) => set({ currentPage: page }),
}));
