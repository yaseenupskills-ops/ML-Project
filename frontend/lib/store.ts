import { create } from 'zustand';
import { UserRole } from '../types';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
}

interface AppState {
  user: User | null;
  isLoggedIn: boolean;
  setUser: (user: User | null) => void;
  logout: () => void;
}

export const useStore = create<AppState>((set) => ({
  user: null,
  isLoggedIn: false,
  setUser: (user) => set({ user, isLoggedIn: !!user }),
  logout: () => set({ user: null, isLoggedIn: false }),
}));
