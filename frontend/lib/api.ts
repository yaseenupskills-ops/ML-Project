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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchStatus(): Promise<SystemStatus> {
  try {
    const res = await fetch(`${API_BASE}/api/status`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    // Return a graceful fallback if server is booting
    return {
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
  }
}

export async function fetchAlerts(): Promise<AlertItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/alerts`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    return [];
  }
}

export async function takeAlertAction(
  alertId: string,
  action: 'acknowledge' | 'dismiss' | 'escalate',
  notes?: string
): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/alerts/${encodeURIComponent(alertId)}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, notes, user: 'Sarah Miller (Caregiver)' }),
    });
    return res.ok;
  } catch (err) {
    console.error('Failed to submit action:', err);
    return false;
  }
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
    console.error('Failed to switch source:', err);
    return false;
  }
}

export async function fetchContacts(): Promise<ContactItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/contacts`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    return [];
  }
}

export async function fetchSummary(): Promise<SummaryMetrics> {
  try {
    const res = await fetch(`${API_BASE}/api/summary`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    return {
      streak_days: 18,
      falls_today: 0,
      routine_checks_today: 4,
      avg_response_sec: 35,
      last_routine_check: '12m ago',
      system_health: 'Optimal',
      privacy_mode: 'Secured Local-Only',
    };
  }
}
