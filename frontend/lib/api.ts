export interface AlertItem {
  id: string;
  timestamp: number;
  time_formatted: string;
  exact_time: string;
  date_formatted: string;
  subject: string;
  room: string;
  status: 'pending' | 'acknowledged' | 'dismissed' | 'escalated' | 'cancelled';
  plain_status: string;
  severity: 'High Risk' | 'Moderate Risk' | 'Minor Event';
  confidence_pct: number;
  notes: string;
  acknowledged_by?: string;
  video_clip?: string | null;
  pose_telemetry?: {
    torso_angle_deg?: number;
    fall_velocity?: number;
    recovery_detected?: boolean;
    sensor_location?: string;
  };
}

export interface SystemStatus {
  resident_name: string;
  room: string;
  resident_status: 'safe' | 'grace_period' | 'alert';
  camera_online: boolean;
  active_source: 'webcam' | 'demo';
  detection_active: boolean;
  grace_seconds_remaining: number;
  active_alert: AlertItem | null;
  last_checked_at: string;
}

export interface ContactItem {
  id: string;
  name: string;
  role: string;
  phone: string;
  email: string;
  is_primary: boolean;
  badge: string;
}

export interface SummaryMetrics {
  streak_days: number;
  falls_today: number;
  routine_checks_today: number;
  avg_response_sec: number;
  last_routine_check: string;
  system_health: string;
  privacy_mode: string;
}

// Same-origin by default: requests go through the Next `/api/:path*` rewrite
// so the auth cookie flows without CORS. Cross-origin URLs would break auth.
const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

// Fallback seed data for interactive demo when backend is offline
const INITIAL_DEMO_ALERTS: AlertItem[] = [
  {
    id: 'alt-1029',
    timestamp: 1711900000000,
    time_formatted: '18m ago',
    exact_time: '07:12:05 PM',
    date_formatted: 'Today',
    subject: 'Eleanor Vance',
    room: 'Living Room (North)',
    status: 'acknowledged',
    plain_status: 'Attended by Sarah',
    severity: 'Moderate Risk',
    confidence_pct: 82,
    notes: 'Eleanor sat down quickly onto carpet near sofa. Confirmed OK, helped to armchair.',
    acknowledged_by: 'Sarah Miller',
    pose_telemetry: {
      torso_angle_deg: 68,
      fall_velocity: 1.42,
      recovery_detected: true,
      sensor_location: 'Edge Sensor Living Room #1',
    },
  },
  {
    id: 'alt-1028',
    timestamp: 1711890000000,
    time_formatted: '2h ago',
    exact_time: '05:10:44 PM',
    date_formatted: 'Today',
    subject: 'Eleanor Vance',
    room: 'Reading Corner',
    status: 'dismissed',
    plain_status: 'False Alarm',
    severity: 'Minor Event',
    confidence_pct: 64,
    notes: 'Reaching down to pick up knitting wool ball. Fast movement triggered grace countdown.',
    acknowledged_by: 'Eleanor (Console Cancel)',
    pose_telemetry: {
      torso_angle_deg: 54,
      fall_velocity: 0.98,
      recovery_detected: true,
      sensor_location: 'Edge Sensor Living Room #1',
    },
  },
  {
    id: 'alt-1025',
    timestamp: 1711800000000,
    time_formatted: 'Yesterday',
    exact_time: '03:45:10 PM',
    date_formatted: 'Yesterday',
    subject: 'Eleanor Vance',
    room: 'Living Room Hallway',
    status: 'acknowledged',
    plain_status: 'Attended',
    severity: 'Minor Event',
    confidence_pct: 59,
    notes: 'Routine stability stumble, gripped corridor handrail.',
    acknowledged_by: 'Nurse Jackson',
    pose_telemetry: {
      torso_angle_deg: 42,
      fall_velocity: 0.75,
      recovery_detected: true,
      sensor_location: 'Hallway Edge Sensor #2',
    },
  },
];

let localAlertsCache: AlertItem[] = [...INITIAL_DEMO_ALERTS];
let localStatusOverride: Partial<SystemStatus> | null = null;

export async function fetchStatus(): Promise<SystemStatus> {
  let base: SystemStatus = {
    resident_name: 'Eleanor Vance',
    room: 'Living Room',
    resident_status: 'safe',
    camera_online: true,
    active_source: 'webcam',
    detection_active: true,
    grace_seconds_remaining: 0,
    active_alert: null,
    last_checked_at: 'Just now',
  };

  try {
    const res = await fetch(`${API_BASE}/api/status`, { cache: 'no-store' });
    if (res.ok) {
      base = await res.json();
    }
  } catch (err) {
    // API is offline, using offline realistic state
  }

  if (localStatusOverride) {
    return { ...base, ...localStatusOverride };
  }
  return base;
}

export function setLocalSimulationStatus(override: Partial<SystemStatus> | null) {
  localStatusOverride = override;
}

export async function fetchAlerts(): Promise<AlertItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/alerts`, { cache: 'no-store' });
    if (res.ok) {
      const serverAlerts = await res.json();
      if (serverAlerts && serverAlerts.length > 0) {
        return serverAlerts;
      }
    }
  } catch (err) {
    // Fallback to local cache
  }
  return localAlertsCache;
}

export async function takeAlertAction(
  alertId: string,
  action: 'acknowledge' | 'dismiss' | 'escalate',
  notes?: string
): Promise<boolean> {
  // Update local cache immediately
  localAlertsCache = localAlertsCache.map((item) => {
    if (item.id === alertId) {
      const updatedStatus =
        action === 'acknowledge'
          ? 'acknowledged'
          : action === 'dismiss'
          ? 'dismissed'
          : 'escalated';
      const plain =
        action === 'acknowledge'
          ? 'Attended by Caregiver'
          : action === 'dismiss'
          ? 'False Alarm'
          : 'Emergency Escalated';
      return {
        ...item,
        status: updatedStatus as AlertItem['status'],
        plain_status: plain,
        notes: notes !== undefined ? notes : item.notes,
        acknowledged_by: 'Sarah Miller (Caregiver)',
      };
    }
    return item;
  });

  // Clear simulated active alert if present
  if (localStatusOverride?.active_alert?.id === alertId) {
    localStatusOverride = {
      resident_status: 'safe',
      grace_seconds_remaining: 0,
      active_alert: null,
    };
  }

  try {
    const res = await fetch(`${API_BASE}/api/alerts/${encodeURIComponent(alertId)}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, notes, user: 'Sarah Miller (Caregiver)' }),
    });
    return res.ok;
  } catch (err) {
    // Local update succeeded anyway
    return true;
  }
}

export async function saveAlertNote(alertId: string, notes: string): Promise<boolean> {
  localAlertsCache = localAlertsCache.map((a) => (a.id === alertId ? { ...a, notes } : a));
  try {
    await fetch(`${API_BASE}/api/alerts/${encodeURIComponent(alertId)}/note`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });
  } catch (e) {
    // local saved
  }
  return true;
}

export async function switchCameraSource(source: 'webcam' | 'demo'): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/stream/switch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source }),
    });
    return res.ok;
  } catch (err) {
    console.warn('Backend stream switch not reached, simulation updated locally.');
    return true;
  }
}

const DEFAULT_CONTACTS: ContactItem[] = [
  {
    id: 'c1',
    name: 'Sarah Miller',
    role: 'Daughter / Primary Caregiver',
    phone: '(555) 234-5678',
    email: 'sarah.miller@example.com',
    is_primary: true,
    badge: 'On Duty & Alerted',
  },
  {
    id: 'c2',
    name: 'Dr. Robert Chen',
    role: 'Primary Care Geriatrician',
    phone: '(555) 876-5432',
    email: 'dr.chen@oakridgehealth.org',
    is_primary: false,
    badge: 'Physician',
  },
  {
    id: 'c3',
    name: 'Oakridge On-Site Nursing Desk',
    role: 'Floor 1 Medical Desk',
    phone: '(555) 991-0022',
    email: 'nursing@oakridgecare.com',
    is_primary: false,
    badge: 'Facility Care',
  },
  {
    id: 'c4',
    name: 'Emergency Medical Services',
    role: 'Local EMS / 911 Dispatch',
    phone: '911',
    email: '',
    is_primary: false,
    badge: 'Emergency Escalation',
  },
];

export async function fetchContacts(): Promise<ContactItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/contacts`, { cache: 'no-store' });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data)) return data;
    }
  } catch (err) {
    // backend offline: fall back to seed data
  }
  return DEFAULT_CONTACTS;
}

async function throwFromResponse(res: Response, fallback: string): Promise<never> {
  let detail = '';
  try {
    const body = await res.json();
    detail = typeof body?.detail === 'string' ? body.detail : '';
  } catch {
    // non-JSON error body
  }
  if (res.status === 403) {
    throw new Error(detail || 'Admin privileges required');
  }
  throw new Error(detail || fallback);
}

/** Add a contact on the backend (admin only; 403 for other roles). */
export async function createContact(contact: Omit<ContactItem, 'id'>): Promise<ContactItem> {
  const res = await fetch(`${API_BASE}/api/contacts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(contact),
  });
  if (!res.ok) await throwFromResponse(res, 'Failed to add contact');
  return (await res.json()) as ContactItem;
}

/** Remove a contact on the backend (admin only; 403 for other roles). */
export async function removeContact(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/contacts/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
  if (!res.ok) await throwFromResponse(res, 'Failed to remove contact');
}

export interface AppSettings {
  grace_period_sec: number;
  chime_volume: number;
  email_alerts: boolean;
  sms_alerts: boolean;
}

export async function fetchSettings(): Promise<AppSettings | null> {
  try {
    const res = await fetch(`${API_BASE}/api/settings`, { cache: 'no-store' });
    if (res.ok) return (await res.json()) as AppSettings;
  } catch (err) {
    // backend offline: keep defaults
  }
  return null;
}

/** Persist settings (admin only; 403 for other roles). Partial patches allowed. */
export async function saveSettings(patch: Partial<AppSettings>): Promise<AppSettings> {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });
  if (!res.ok) await throwFromResponse(res, 'Failed to save settings');
  return (await res.json()) as AppSettings;
}

export async function fetchSummary(): Promise<SummaryMetrics> {
  try {
    const res = await fetch(`${API_BASE}/api/summary`, { cache: 'no-store' });
    if (res.ok) return await res.json();
  } catch (err) {
    // fallback
  }
  return {
    streak_days: 18,
    falls_today: localAlertsCache.filter((a) => a.status === 'acknowledged').length,
    routine_checks_today: 5,
    avg_response_sec: 32,
    last_routine_check: '8m ago',
    system_health: 'Optimal · 15 FPS',
    privacy_mode: 'Secured Local-Only',
  };
}

export function exportAlertsToCSV(alerts: AlertItem[]): void {
  if (typeof window === 'undefined') return;

  const headers = ['ID', 'Date', 'Time', 'Resident', 'Room', 'Status', 'Severity', 'Confidence %', 'Notes', 'Attended By'];
  const rows = alerts.map((a) => [
    `"${a.id}"`,
    `"${a.date_formatted}"`,
    `"${a.exact_time}"`,
    `"${a.subject}"`,
    `"${a.room}"`,
    `"${a.plain_status}"`,
    `"${a.severity}"`,
    `"${a.confidence_pct}%"`,
    `"${(a.notes || '').replace(/"/g, '""')}"`,
    `"${a.acknowledged_by || ''}"`,
  ]);

  const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `FallGuard_Log_${new Date().toISOString().split('T')[0]}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
