import { create } from 'zustand';
import type { User } from '@/types';

interface AppState {
  user: User | null;
  isLoggedIn: boolean;
  serverTimeOffset: number; // ms offset: server_time - client_time
  setUser: (user: User | null) => void;
  setServerTimeOffset: (offset: number) => void;
  logout: () => void;
}

export const useStore = create<AppState>((set) => ({
  user: null,
  isLoggedIn: false,
  serverTimeOffset: 0,
  setUser: (user) => set({ user, isLoggedIn: !!user }),
  setServerTimeOffset: (offset) => set({ serverTimeOffset: offset }),
  logout: () => set({ user: null, isLoggedIn: false, serverTimeOffset: 0 }),
}));

export type { User };