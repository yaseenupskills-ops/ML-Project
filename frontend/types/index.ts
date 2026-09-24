// === Enums / Unions ===
export type UserRole = 'caregiver' | 'admin' | 'ml_engineer' | 'operator';

export type EventState = 'PENDING' | 'CANCELLED' | 'CONFIRMED';

export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'DISMISSED' | 'ESCALATED';

export type EventTier = 'HIGH' | 'MEDIUM' | 'LOW';

export type DeviceStatus = 'HEALTHY' | 'DEGRADED' | 'OFFLINE' | 'ERROR';

export type DeviceType = 'edge_device' | 'hub';

export type NotificationChannel = 'EMAIL' | 'SMS' | 'PUSH';
export type NotificationKind = 'ALERT' | 'ESCALATION' | 'SYSTEM';
export type NotificationStatus = 'PENDING' | 'SENT' | 'FAILED' | 'RETRIED';

export type FeedbackType = 'TRUE_FALL' | 'FALSE_POSITIVE' | 'UNCERTAIN' | 'SYSTEM_FAILURE';

export type ModelStatus = 'registered' | 'candidate' | 'approved' | 'production' | 'retired';

export type CameraStatus = 'ONLINE' | 'OFFLINE' | 'ERROR';

// === Core entities ===

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  must_change_password: boolean;
  // Fields returned by /auth/me (new backend)
  assigned_subject_ids?: string[];   // UUIDs from MeResponse
  // Normalized alias (populated by auth service)
  assigned_subjects?: string[];
  // Legacy / optional fields — not returned by new auth endpoints
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Subject {
  id: string;
  display_name: string;
  location?: string;
  status: 'active' | 'inactive';
  assigned_caregivers: string[];
  device_id?: string;
  created_at: string;
  updated_at: string;
}

export interface Device {
  id: string;
  name: string;
  type: DeviceType;
  location?: string;
  status: DeviceStatus;
  last_seen?: string;
  software_version?: string;
  model_version?: string;
  subject_id?: string;
  is_revoked: boolean;
  created_at: string;
  updated_at: string;
}

export interface Camera {
  id: string;
  device_id: string;
  name: string;
  status: CameraStatus;
  fps?: number;
  last_frame?: string;
  created_at: string;
}

export interface DeviceHealth {
  device_id: string;
  camera_status: CameraStatus;
  camera_fps?: number;
  last_frame_at?: string;
  inference_latency_ms?: number;
  model_loaded: boolean;
  cpu_percent?: number;
  memory_percent?: number;
  temperature_c?: number;
  queue_depth?: number;
  backend_connected: boolean;
  timestamp: string;
}

export interface DeviceHealthHistory {
  timestamps: string[];
  cpu_percent: (number | null)[];
  memory_percent: (number | null)[];
  inference_latency_ms: (number | null)[];
  temperature_c: (number | null)[];
}

export interface EvidenceItem {
  label: string;
  detected: boolean;
  value?: string | number;
}

export interface TimelineEntry {
  timestamp: string;
  action: string;
  actor?: string;
  detail?: string;
}

export interface Alert {
  id: string;
  event_id: string;
  status: AlertStatus;
  acknowledged_by?: string;
  acknowledged_at?: string;
  dismissed_by?: string;
  dismissed_at?: string;
  escalated_at?: string;
  escalation_note?: string;
  response_time_seconds?: number;
  created_at: string;
}

export interface FallEvent {
  id: string;
  device_id: string;
  subject_id?: string;
  subject_display_name?: string;
  device_name?: string;
  device_location?: string;
  state: EventState;
  tier: EventTier;
  confidence: number;
  confidence_calibrated: boolean;
  model_version?: string;
  feature_version?: string;
  track_id?: string;
  evidence: EvidenceItem[];
  evidence_summary?: string;
  pose_quality?: number;
  grace_deadline?: string;
  grace_outcome?: 'cancelled' | 'confirmed';
  grace_resolved_by?: string;
  grace_resolved_at?: string;
  alert?: Alert | null;
  notifications?: Notification[];
  feedback?: CaregiverFeedback | null;
  timeline: TimelineEntry[];
  created_at: string;
  updated_at: string;
}

export interface Notification {
  id: string;
  event_id: string;
  channel: NotificationChannel;
  kind: NotificationKind;
  status: NotificationStatus;
  recipient?: string;
  attempts: number;
  last_attempt_at?: string;
  error_code?: string;
  created_at: string;
}

export interface CaregiverFeedback {
  id: string;
  event_id: string;
  user_id: string;
  feedback_type: FeedbackType;
  comment?: string;
  created_at: string;
  updated_at: string;
}

export interface ModelRecord {
  id: string;
  name: string;
  version: string;
  type: string;
  feature_version?: string;
  dataset_version?: string;
  status: ModelStatus;
  metrics_json?: Record<string, number>;
  release_gate_checklist?: Record<string, boolean>;
  approved_by?: string;
  approved_at?: string;
  approver_note?: string;
  created_at: string;
  updated_at: string;
}

// === API request/response types ===

export interface LoginRequest {
  email: string;
  password: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface EventFilters {
  state?: EventState;
  alert_status?: AlertStatus;
  tier?: EventTier;
  date_from?: string;
  date_to?: string;
  subject_id?: string;
  device_id?: string;
  sort_by?: 'timestamp' | 'tier' | 'response_time';
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface BulkAlertAction {
  alert_ids: string[];
  action: 'acknowledge' | 'dismiss' | 'escalate';
  note?: string;
}

export interface BulkActionResult {
  succeeded: string[];
  failed: { id: string; reason: string }[];
}

export interface CreateDeviceRequest {
  name: string;
  type: DeviceType;
  location?: string;
  subject_id?: string;
}

export interface CreateDeviceResponse {
  device: Device;
  api_key: string; // shown once
}

export interface RotateKeyResponse {
  api_key: string; // shown once
}

export interface CreateSubjectRequest {
  display_name: string;
  location?: string;
  status?: 'active' | 'inactive';
  device_id?: string;
}

export interface CreateUserRequest {
  name: string;
  email: string;
  role: UserRole;
}

export interface CreateUserResponse {
  user: User;
  temporary_password: string;
}

export interface ResetPasswordResponse {
  temporary_password: string;
}

export interface FeedbackRequest {
  event_id: string;
  feedback_type: FeedbackType;
  comment?: string;
}

export interface PromoteModelRequest {
  approver_note?: string;
}

// === Analytics ===

export interface AnalyticsSummary {
  total_events: number;
  confirmed_events: number;
  cancelled_events: number;
  open_alerts: number;
  escalated_alerts: number;
  response_time_avg_seconds: number;
  response_time_median_seconds: number;
  response_time_p95_seconds: number;
  active_devices: number;
  offline_devices: number;
  notification_failures: number;
  false_positive_feedback: number;
  true_fall_feedback: number;
  uncertain_feedback: number;
}

export interface AlertsOverTime {
  dates: string[];
  high: number[];
  medium: number[];
  low: number[];
}

export interface StateBreakdown {
  pending: number;
  cancelled: number;
  confirmed: number;
}

export interface ResponseTimeHistogram {
  buckets: string[];
  counts: number[];
}

export interface AlertsBySubject {
  subjects: string[];
  counts: number[];
}

export interface FeedbackBreakdown {
  true_fall: number;
  false_positive: number;
  uncertain: number;
  system_failure: number;
}

export interface ModelVersionDistribution {
  versions: string[];
  device_counts: number[];
}

// === System ===

export interface SystemHealth {
  database: 'ok' | 'error';
  worker_last_tick?: string;
  server_time: string;
}
