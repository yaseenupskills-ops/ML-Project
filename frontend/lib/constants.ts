export const APP_NAME = 'FallGuard';

// Polling intervals (ms)
export const POLL_ALERTS_LIST = 10_000;
export const POLL_EVENT_PENDING = 2_000;
export const POLL_EVENT_DEFAULT = 15_000;
export const POLL_DEVICE_HEALTH = 15_000;
export const POLL_ANALYTICS = 60_000;
export const POLL_DASHBOARD = 10_000;

export const STALE_FAILURE_THRESHOLD = 2;
export const DEFAULT_PAGE_SIZE = 25;

export const queryKeys = {
  auth: { me: ['auth', 'me'] as const },
  events: {
    all: ['events'] as const,
    list: (filters: Record<string, unknown>) => ['events', 'list', filters] as const,
    detail: (id: string) => ['events', 'detail', id] as const,
  },
  alerts: { all: ['alerts'] as const },
  devices: {
    all: ['devices'] as const,
    list: () => ['devices', 'list'] as const,
    detail: (id: string) => ['devices', 'detail', id] as const,
    health: (id: string) => ['devices', 'health', id] as const,
    healthHistory: (id: string, hours?: number) => ['devices', 'healthHistory', id, hours] as const,
  },
  subjects: {
    all: ['subjects'] as const,
    list: () => ['subjects', 'list'] as const,
    detail: (id: string) => ['subjects', 'detail', id] as const,
  },
  users: {
    all: ['users'] as const,
    list: () => ['users', 'list'] as const,
    detail: (id: string) => ['users', 'detail', id] as const,
  },
  analytics: {
    summary: (days?: number) => ['analytics', 'summary', days] as const,
    alertsOverTime: (days?: number) => ['analytics', 'alertsOverTime', days] as const,
    stateBreakdown: (days?: number) => ['analytics', 'stateBreakdown', days] as const,
    responseTimeHistogram: (days?: number) => ['analytics', 'responseTimeHistogram', days] as const,
    alertsBySubject: (days?: number) => ['analytics', 'alertsBySubject', days] as const,
    feedbackBreakdown: (days?: number) => ['analytics', 'feedbackBreakdown', days] as const,
    modelVersionDistribution: () => ['analytics', 'modelVersionDistribution'] as const,
  },
  models: {
    all: ['models'] as const,
    list: () => ['models', 'list'] as const,
    detail: (id: string) => ['models', 'detail', id] as const,
  },
  notifications: {
    all: ['notifications'] as const,
    list: (params?: Record<string, unknown>) => ['notifications', 'list', params] as const,
  },
  system: { health: ['system', 'health'] as const },
  feedback: { all: ['feedback'] as const },
} as const;