export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}${endpoint}`;
  const headers: Record<string, string> = {};
  if (options.headers) {
    Object.assign(headers, options.headers as Record<string, string>);
  }
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(url, {
    ...options,
    headers: {
      ...headers,
      ...(options.headers as Record<string, string> | undefined),
    },
    credentials: 'include',
  });

  if (!res.ok) {
    let data: unknown;
    try {
      data = await res.json();
    } catch {
      data = await res.text();
    }
    const detail =
      data && typeof data === 'object' && 'detail' in (data as Record<string, unknown>)
        ? String((data as Record<string, { detail: string }>).detail)
        : `Request failed with status ${res.status}`;
    throw new ApiError(detail, res.status, data);
  }

  if (res.status === 204) {
    return {} as T;
  }

  const text = await res.text();
  if (!text) return {} as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    return text as unknown as T;
  }
}

// ─── Types (match API.md) ───────────────────────────────────────────────────

export interface Health {
  status: string;
  camera: boolean;
  time: number;
}

export interface Metrics {
  camera_online: boolean;
  camera_available: boolean;
  fps: number;
  capture_latency_ms: number;
  pipeline_latency_ms: number;
  pipeline_running: boolean;
  frames_processed: number;
  windows_evaluated: number;
  alerts_triggered: number;
  fall_candidates: number;
  false_positives_cancelled: number;
  recorded_segments: number;
  recording_active: boolean;
  last_frame_ts: number | null;
  started_at: number;
  last_update: number;
  uptime_sec: number;
  falls_per_min: number;
  last_frame_age_sec: number | null;
}

export type AlertTier = 'high' | 'medium' | 'low';
export type AlertStatus = 'pending' | 'acknowledged' | 'dismissed' | 'escalated';
export type AlertAction = 'acknowledge' | 'dismiss' | 'escalate';

export interface Alert {
  timestamp: number;
  subject_id: string;
  clip_id: string;
  confidence: number;
  tier: AlertTier;
  outcome: string;
  response_time: number | null;
  status: AlertStatus;
  acknowledged_by: string | null;
  acknowledged_at: number | null;
  video_clip_path: string | null;
  datetime: string | null;
}

export interface AlertsList {
  alerts: Alert[];
  total: number;
}

export interface AlertsParams {
  tier?: AlertTier;
  status?: AlertStatus;
  subject_id?: string;
  from?: string;
  to?: string;
}

export interface AlertActionResponse {
  ok: boolean;
  timestamp: number;
  status: string;
}

export interface BulkActionResponse {
  ok: boolean;
  updated: number[];
}

export interface AnalyticsSummary {
  total: number;
  pending: number;
  acknowledged: number;
  escalated: number;
  dismissed: number;
  high_risk: number;
  high_confidence: number;
  avg_confidence: number;
  by_tier: Record<string, number>;
  by_status: Record<string, number>;
  confidence_histogram: { range_pct: string; count: number }[];
  heatmap: number[][];
  week_over_week: {
    this_week: number;
    last_week: number;
    delta: number;
    pct_change: number;
    daily_avg: number;
  };
  escalation_funnel: {
    stages: { stage: string; count: number }[];
    acknowledged_rate_pct: number;
    escalated_rate_pct: number;
  };
}

export interface SubjectTrend {
  subject_id: string;
  alerts: number;
  high_risk: number;
  avg_response_min: number | null;
  escalation_rate_pct: number;
  avg_confidence: number;
  trend: { date: string; count: number }[];
}

export interface ResponseTimes {
  mean_min: number | null;
  median_min: number | null;
  p95_min: number | null;
  n_actioned: number;
  histogram: { range_min: string; count: number }[];
}

export interface Recording {
  name: string;
  path: string;
  size_mb: number;
  created: number;
  alerts: {
    offset_sec: number;
    tier: AlertTier;
    subject_id: string;
    confidence: number;
    timestamp: number;
  }[];
}

export interface RecordingInfo {
  name: string;
  size_mb: number;
  duration_sec: number;
  fps: number;
  width: number;
  height: number;
  frame_count: number;
  segment_start: number | null;
}

export interface RecordAction {
  ok: boolean;
  recording: boolean;
  path: string | null;
  error: string | null;
}

export interface Me {
  username: string;
  role: string;
  display_name: string;
}

// ─── Endpoints ──────────────────────────────────────────────────────────────

export function getHealth(): Promise<Health> {
  return apiFetch<Health>('/health');
}

export function getMetrics(): Promise<Metrics> {
  return apiFetch<Metrics>('/metrics');
}

export function getAlerts(params: AlertsParams = {}): Promise<AlertsList> {
  const qs = new URLSearchParams();
  if (params.tier) qs.set('tier', params.tier);
  if (params.status) qs.set('status', params.status);
  if (params.subject_id) qs.set('subject_id', params.subject_id);
  if (params.from) qs.set('from', params.from);
  if (params.to) qs.set('to', params.to);
  const q = qs.toString();
  return apiFetch<AlertsList>(`/alerts${q ? `?${q}` : ''}`);
}

export function patchAlert(id: number, action: AlertAction): Promise<AlertActionResponse> {
  return apiFetch<AlertActionResponse>(`/alerts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ action }),
  });
}

export function bulkAlertAction(ids: number[], action: AlertAction): Promise<BulkActionResponse> {
  return apiFetch<BulkActionResponse>('/alerts/bulk', {
    method: 'POST',
    body: JSON.stringify({ ids, action }),
  });
}

export function getAnalyticsSummary(): Promise<AnalyticsSummary> {
  return apiFetch<AnalyticsSummary>('/analytics/summary');
}

export function getAnalyticsSubjects(): Promise<SubjectTrend[]> {
  return apiFetch<SubjectTrend[]>('/analytics/subjects');
}

export function getAnalyticsResponseTimes(): Promise<ResponseTimes> {
  return apiFetch<ResponseTimes>('/analytics/response-times');
}

export async function downloadAnalyticsCsv(): Promise<void> {
  const res = await fetch(`${API_URL}/analytics/export.csv`, { credentials: 'include' });
  if (!res.ok) {
    throw new ApiError(`Export failed with status ${res.status}`, res.status);
  }
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = res.headers.get('Content-Disposition')?.match(/filename="?([^";]+)/)?.[1] ?? 'fall_alerts.csv';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);
}

export function getRecordings(): Promise<Recording[]> {
  return apiFetch<Recording[]>('/recordings');
}

export function getRecordingInfo(name: string): Promise<RecordingInfo> {
  return apiFetch<RecordingInfo>(`/recordings/${encodeURIComponent(name)}/info`);
}

export function startRecording(): Promise<RecordAction> {
  return apiFetch<RecordAction>('/record/start', { method: 'POST' });
}

export function stopRecording(): Promise<RecordAction> {
  return apiFetch<RecordAction>('/record/stop', { method: 'POST' });
}

export function getMe(): Promise<Me> {
  return apiFetch<Me>('/me');
}

export function getVideoFeedUrl(): string {
  return `${API_URL}/video_feed`;
}

export function getFrameUrl(): string {
  return `${API_URL}/frame`;
}

export function getRecordingVideoUrl(name: string): string {
  return `${API_URL}/recordings/${encodeURIComponent(name)}/video`;
}