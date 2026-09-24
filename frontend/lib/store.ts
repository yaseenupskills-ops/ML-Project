import { create } from 'zustand';

export type GlobeTarget = {
  lat: number;
  lon: number;
  title?: string;
  severity?: string;
  desc?: string;
};

export type UserRole = 'meteorologist' | 'disaster_manager' | 'researcher' | 'operational' | 'general';
export type DisclosureLevel = 1 | 2 | 3 | 4 | 5;
export type BandwidthMode = 'normal' | 'low';

type AppState = {
  globeTarget: GlobeTarget | null;
  setGlobeTarget: (target: GlobeTarget) => void;
  clearGlobeTarget: () => void;
  viewMode: '3d' | '2d';
  setViewMode: (mode: '3d' | '2d') => void;
  
  routePath: [number, number][] | null;
  setRoutePath: (path: [number, number][]) => void;
  clearRoutePath: () => void;
  
  showGeofence: boolean;
  setShowGeofence: (show: boolean) => void;
  
  isLoggedIn: boolean;
  login: (role?: UserRole) => void;
  logout: () => void;
  
  eezGeoJSON: any | null;
  setEEZGeoJSON: (data: any) => void;
  
  pfzRawData: any | null;
  setPfzRawData: (data: any) => void;

  activeRole: UserRole;
  setActiveRole: (role: UserRole) => void;

  disclosureLevel: DisclosureLevel;
  setDisclosureLevel: (level: DisclosureLevel) => void;

  bandwidthMode: BandwidthMode;
  setBandwidthMode: (mode: BandwidthMode) => void;

  language: string;
  setLanguage: (lang: string) => void;

  userLocation: { lat: number; lng: number };
  setUserLocation: (loc: { lat: number; lng: number }) => void;
};

export const useAppStore = create<AppState>((set) => ({
  globeTarget: null,
  setGlobeTarget: (target) => set({ globeTarget: target, viewMode: '3d' }), // Auto-switch to map view
  clearGlobeTarget: () => set({ globeTarget: null }),
  
  viewMode: '3d',
  setViewMode: (mode) => set({ viewMode: mode }),
  
  routePath: null,
  setRoutePath: (path) => set({ routePath: path }),
  clearRoutePath: () => set({ routePath: null }),
  
  showGeofence: false,
  setShowGeofence: (show) => set({ showGeofence: show }),
  
  isLoggedIn: false,
  login: (role?: UserRole) => set((state) => ({ isLoggedIn: true, activeRole: role || state.activeRole })),
  logout: () => set({ isLoggedIn: false }),
  
  eezGeoJSON: null,
  setEEZGeoJSON: (data) => set({ eezGeoJSON: data }),
  
  pfzRawData: null,
  setPfzRawData: (data) => set({ pfzRawData: data }),

  activeRole: 'meteorologist',
  setActiveRole: (role) => set({ activeRole: role }),

  disclosureLevel: 2,
  setDisclosureLevel: (level) => set({ disclosureLevel: level }),

  bandwidthMode: 'normal',
  setBandwidthMode: (mode) => set({ bandwidthMode: mode }),

  language: 'en',
  setLanguage: (lang) => set({ language: lang }),

  userLocation: { lat: 19.0760, lng: 72.8777 }, // Mumbai / West Coast
  setUserLocation: (loc) => set({ userLocation: loc }),
}));
