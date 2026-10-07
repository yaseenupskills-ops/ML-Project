'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import {
  ShieldCheck,
  AlertTriangle,
  Bell,
  Eye,
  EyeOff,
  Video,
  VideoOff,
  PhoneCall,
  CheckCircle2,
  XCircle,
  Clock,
  Sparkles,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import {
  fetchStatus,
  fetchAlerts,
  takeAlertAction,
  switchCameraSource,
  fetchSummary,
  SystemStatus,
  AlertItem,
  SummaryMetrics,
} from '@/lib/api';

export default function CaregiverHomePage() {
  const [status, setStatus] = useState<SystemStatus>({
    resident_name: 'Eleanor Vance',
    room: 'Living Room',
    resident_status: 'safe',
    camera_online: true,
    active_source: 'webcam',
    detection_active: true,
    grace_seconds_remaining: 0,
    active_alert: null,
    last_checked_at: 'Just now',
  });

  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [summary, setSummary] = useState<SummaryMetrics>({
    streak_days: 18,
    falls_today: 0,
    routine_checks_today: 4,
    avg_response_sec: 38,
    last_routine_check: '10m ago',
    system_health: 'Optimal',
    privacy_mode: 'Secured Local-Only',
  });

  const [privacyShield, setPrivacyShield] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [switchingSource, setSwitchingSource] = useState(false);
  const [feedbackToast, setFeedbackToast] = useState<string | null>(null);

  // Poll status and alerts regularly
  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      const [st, al, sm] = await Promise.all([
        fetchStatus(),
        fetchAlerts(),
        fetchSummary(),
      ]);
      if (isMounted) {
        setStatus(st);
        setAlerts(al.slice(0, 4));
        setSummary(sm);
      }
    }

    loadData();
    const interval = setInterval(loadData, 2500);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const triggerToast = (msg: string) => {
    setFeedbackToast(msg);
    setTimeout(() => setFeedbackToast(null), 3500);
  };

  const handleAction = async (action: 'acknowledge' | 'dismiss' | 'escalate') => {
    if (!status.active_alert) return;
    setActionLoading(true);
    const success = await takeAlertAction(status.active_alert.id, action);
    setActionLoading(false);
    if (success) {
      const text =
        action === 'acknowledge'
          ? "Attending: Marked as attended. Thank you!"
          : action === 'dismiss'
          ? 'Dismissed: Marked as false alarm.'
          : 'Escalated: Emergency notification triggered!';
      triggerToast(text);
      // Instant refresh
      const newStatus = await fetchStatus();
      setStatus(newStatus);
    }
  };

  const handleSourceSwitch = async (source: 'webcam' | 'demo') => {
    setSwitchingSource(true);
    const ok = await switchCameraSource(source);
    setSwitchingSource(false);
    if (ok) {
      triggerToast(
        source === 'demo'
          ? 'Switched to Fall Simulation Clip. Watch for detection!'
          : 'Switched to Live Camera.'
      );
      const newStatus = await fetchStatus();
      setStatus(newStatus);
    }
  };

  const isSafe = status.resident_status === 'safe';
  const isGrace = status.resident_status === 'grace_period';
  const isAlert = status.resident_status === 'alert';

  return (
    <div className="animate-fade-in" style={{ paddingTop: '0.5rem' }}>
      {/* Toast Notification */}
      {feedbackToast && (
        <div style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          zIndex: 100,
          background: 'rgba(15, 23, 42, 0.95)',
          color: '#fff',
          padding: '0.9rem 1.4rem',
          borderRadius: '14px',
          border: '1px solid rgba(94, 234, 212, 0.4)',
          boxShadow: '0 12px 35px rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          fontSize: '0.92rem',
          fontWeight: 600,
        }}>
          <Sparkles size={18} color="#5eead4" />
          <span>{feedbackToast}</span>
        </div>
      )}

      {/* ─── Hero Peace-of-Mind Status Banner ─────────────────────────────── */}
      <section className={`hero-status ${isSafe ? 'safe' : isGrace ? 'grace' : 'alert'}`}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '1.5rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.8rem' }}>
              <div className={`status-badge ${isSafe ? 'safe' : isGrace ? 'grace' : 'alert'}`}>
                <span className={`status-orb ${isSafe ? 'safe' : isGrace ? 'grace' : 'alert'}`} />
                {isSafe ? 'Resident Safe & Calm' : isGrace ? 'Possible Fall Detected' : 'Attention Required'}
              </div>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Updated {status.last_checked_at}
              </span>
            </div>

            <h1 style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'clamp(1.9rem, 3.2vw, 2.7rem)',
              fontWeight: 800,
              letterSpacing: '-0.035em',
              lineHeight: 1.15,
              marginBottom: '0.6rem',
              color: '#fff',
            }}>
              {isSafe
                ? 'All is peaceful. Eleanor is safe.'
                : isGrace
                ? `Fall candidate detected. Waiting ${status.grace_seconds_remaining}s...`
                : 'Fall Confirmed — Immediate Action Needed!'}
            </h1>

            <p style={{
              fontSize: '1.02rem',
              color: isSafe ? 'var(--text-muted)' : '#fde68a',
              maxWidth: 620,
              lineHeight: 1.5,
            }}>
              {isSafe
                ? `Normal gentle activity in ${status.room}. Privacy shield is protecting personal dignity.`
                : isGrace
                ? 'A fall candidate occurred. If Eleanor is alright, cancel below to prevent dispatching alerts.'
                : 'A high-confidence fall was detected. Please check on Eleanor or tap Attending.'}
            </p>
          </div>

          {/* Emergency 1-Tap Actions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', minWidth: 260 }}>
            {isSafe ? (
              <div style={{
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                padding: '1.1rem 1.4rem',
                borderRadius: '18px',
                textAlign: 'center',
              }}>
                <div style={{ fontSize: '0.8rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>
                  Active Caregiver
                </div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginTop: '0.2rem' }}>
                  Sarah Miller (Daughter)
                </div>
                <div style={{ fontSize: '0.78rem', color: '#10b981', marginTop: '0.3rem', fontWeight: 600 }}>
                  ● On Duty & Receiving Alerts
                </div>
              </div>
            ) : isGrace ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                <button
                  className="action-btn btn-attending"
                  onClick={() => handleAction('dismiss')}
                  disabled={actionLoading}
                  style={{ width: '100%', fontSize: '1rem', padding: '1rem' }}
                >
                  <CheckCircle2 size={20} />
                  <span>I'm OK — False Alarm</span>
                </button>
                <button
                  className="action-btn btn-primary-urgent"
                  onClick={() => handleAction('escalate')}
                  disabled={actionLoading}
                  style={{ width: '100%' }}
                >
                  <AlertTriangle size={18} />
                  <span>Alert Care Team Immediately</span>
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                <button
                  className="action-btn btn-attending"
                  onClick={() => handleAction('acknowledge')}
                  disabled={actionLoading}
                  style={{ width: '100%', fontSize: '1.05rem', padding: '1rem' }}
                >
                  <CheckCircle2 size={22} />
                  <span>I'm Attending / Checking</span>
                </button>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem' }}>
                  <button
                    className="action-btn btn-primary-urgent"
                    onClick={() => handleAction('escalate')}
                    disabled={actionLoading}
                  >
                    <PhoneCall size={16} />
                    <span>Call 911</span>
                  </button>
                  <button
                    className="action-btn btn-secondary-quiet"
                    onClick={() => handleAction('dismiss')}
                    disabled={actionLoading}
                  >
                    <XCircle size={16} />
                    <span>False Alarm</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ─── Main Content Grid: Live View & Care Insights ─────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.65fr) minmax(0, 1fr)', gap: '1.8rem', marginTop: '1.5rem' }}>
        
        {/* Left Column: Live Visual Check-In */}
        <div>
          <div className="glass-panel" style={{ padding: '1.4rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.1rem' }}>
              <div>
                <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>
                  Live Visual Check-In
                </h2>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                  {status.room} · Local Camera Feed
                </p>
              </div>

              {/* Controls */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <button
                  onClick={() => setPrivacyShield(!privacyShield)}
                  className="action-btn btn-secondary-quiet"
                  style={{ padding: '0.45rem 0.85rem', fontSize: '0.82rem' }}
                  title="Toggle Privacy Shield"
                >
                  {privacyShield ? <EyeOff size={15} color="#5eead4" /> : <Eye size={15} />}
                  <span>{privacyShield ? 'Shield: Active' : 'Shield: Off'}</span>
                </button>

                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  background: 'rgba(255,255,255,0.06)',
                  borderRadius: '10px',
                  padding: '3px',
                }}>
                  <button
                    onClick={() => handleSourceSwitch('webcam')}
                    disabled={switchingSource}
                    style={{
                      background: status.active_source === 'webcam' ? '#14b8a6' : 'transparent',
                      color: status.active_source === 'webcam' ? '#fff' : 'var(--text-muted)',
                      border: 'none',
                      borderRadius: '8px',
                      padding: '0.4rem 0.75rem',
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Live Cam
                  </button>
                  <button
                    onClick={() => handleSourceSwitch('demo')}
                    disabled={switchingSource}
                    style={{
                      background: status.active_source === 'demo' ? '#f59e0b' : 'transparent',
                      color: status.active_source === 'demo' ? '#fff' : 'var(--text-muted)',
                      border: 'none',
                      borderRadius: '8px',
                      padding: '0.4rem 0.75rem',
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    🎬 Fall Demo
                  </button>
                </div>
              </div>
            </div>

            {/* Video Player Frame */}
            <div className="video-frame">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                key={status.active_source}
                src={`http://localhost:8000/api/stream/feed?t=${status.active_source}`}
                alt="Room Live Stream"
                style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
                onError={(e) => {
                  // Fallback to rapid snapshot polling if MJPEG stream is interrupted
                  const target = e.target as HTMLImageElement;
                  target.src = `http://localhost:8000/api/stream/snapshot?t=${Date.now()}`;
                  setTimeout(() => {
                    target.src = `http://localhost:8000/api/stream/feed?t=${Date.now()}`;
                  }, 1200);
                }}
              />

              {/* Privacy Shield Overlay */}
              {privacyShield && (
                <div className="privacy-overlay">
                  <div className="privacy-pill">
                    <ShieldCheck size={14} />
                    <span>Dignity & Privacy Shield Enabled</span>
                  </div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>
                    Movement & Posture Monitored in Background
                  </div>
                  <p style={{ maxWidth: 360, fontSize: '0.84rem' }}>
                    Video feed is gently blurred to preserve personal privacy while AI continues pose safety checks.
                  </p>
                  <button
                    onClick={() => setPrivacyShield(false)}
                    className="action-btn btn-secondary-quiet"
                    style={{ fontSize: '0.8rem', padding: '0.45rem 0.9rem' }}
                  >
                    <Eye size={14} /> Reveal Feed Temporarily
                  </button>
                </div>
              )}

              {/* Floating Camera Meta */}
              <div style={{
                position: 'absolute',
                top: 14,
                left: 14,
                background: 'rgba(7, 13, 25, 0.85)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '999px',
                padding: '0.35rem 0.8rem',
                fontSize: '0.75rem',
                fontWeight: 700,
                color: '#5eead4',
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem',
                letterSpacing: '0.04em',
              }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#5eead4' }}></span>
                {status.active_source === 'demo' ? 'DEMO FALL SIMULATION' : 'LIVE WEBCAM'}
              </div>
            </div>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginTop: '0.9rem',
              fontSize: '0.82rem',
              color: 'var(--text-subtle)',
            }}>
              <span>Device: Local FallGuard Edge Sensor #1</span>
              <span>15 FPS · Zero Cloud Uploads</span>
            </div>
          </div>
        </div>

        {/* Right Column: Daily Peace-of-Mind Stats & Recent Activity */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.4rem' }}>
          {/* Peace of Mind Grid */}
          <div className="glass-panel" style={{ padding: '1.4rem' }}>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.15rem', fontWeight: 700, color: '#fff', marginBottom: '1rem' }}>
              Peace-of-Mind Summary
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.85rem' }}>
              <div className="stat-pill">
                <div className="stat-val" style={{ color: '#10b981' }}>{summary.streak_days} Days</div>
                <div className="stat-desc">Incident-Free Streak</div>
              </div>
              <div className="stat-pill">
                <div className="stat-val" style={{ color: '#38bdf8' }}>{summary.avg_response_sec}s</div>
                <div className="stat-desc">Avg Response Time</div>
              </div>
              <div className="stat-pill">
                <div className="stat-val">{summary.routine_checks_today}</div>
                <div className="stat-desc">Checks Today</div>
              </div>
              <div className="stat-pill">
                <div className="stat-val" style={{ color: '#a78bfa' }}>Optimal</div>
                <div className="stat-desc">Local AI Sensor</div>
              </div>
            </div>
          </div>

          {/* Recent Events Snippet */}
          <div className="glass-panel" style={{ padding: '1.4rem', flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.15rem', fontWeight: 700, color: '#fff' }}>
                Recent Care Activity
              </h2>
              <Link href="/history" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.82rem', color: '#5eead4', fontWeight: 600 }}>
                <span>View All</span>
                <ArrowRight size={14} />
              </Link>
            </div>

            {alerts.length === 0 ? (
              <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-subtle)', fontSize: '0.88rem' }}>
                <CheckCircle2 size={32} color="#10b981" style={{ margin: '0 auto 0.5rem' }} />
                <div>No incidents recorded. Everything is peaceful.</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                {alerts.map((item) => (
                  <div key={item.id} className="event-card" style={{ padding: '0.9rem 1.1rem', margin: 0 }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{
                          fontWeight: 700,
                          fontSize: '0.9rem',
                          color: item.status === 'pending' ? '#f43f5e' : item.status === 'escalated' ? '#f59e0b' : '#34d399',
                        }}>
                          {item.plain_status}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-subtle)' }}>· {item.room}</span>
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                        {item.time_formatted} ({item.exact_time})
                      </div>
                    </div>
                    <span style={{
                      padding: '0.25rem 0.6rem',
                      borderRadius: '999px',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      background: item.severity === 'High Risk' ? 'rgba(244,63,94,0.15)' : 'rgba(255,255,255,0.06)',
                      color: item.severity === 'High Risk' ? '#fda4af' : '#94a3b8',
                      border: '1px solid var(--border-light)',
                    }}>
                      {item.severity}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
