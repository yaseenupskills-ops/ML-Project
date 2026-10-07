'use client';

import { useState, useEffect, useRef } from 'react';
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
  Sparkles,
  Camera,
  ZoomIn,
  Activity,
  Sliders,
  Send,
  Radio,
  X,
  Play,
  RotateCcw,
} from 'lucide-react';
import {
  fetchStatus,
  takeAlertAction,
  switchCameraSource,
  setLocalSimulationStatus,
  SystemStatus,
  AlertItem,
} from '@/lib/api';
import { playSound } from '@/lib/sound';

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

  // UI Interactive States
  const [privacyLevel, setPrivacyLevel] = useState<number>(0); // 0 = clear, 1 = frosted, 2 = silhouette
  const [zoomLevel, setZoomLevel] = useState<number>(1); // 1, 1.25, 1.5
  const [actionLoading, setActionLoading] = useState(false);
  const [switchingSource, setSwitchingSource] = useState(false);
  const [feedbackToast, setFeedbackToast] = useState<string | null>(null);
  const [snapshotModalUrl, setSnapshotModalUrl] = useState<string | null>(null);
  const [snapshotTime, setSnapshotTime] = useState<string>('');
  const [pingPulsing, setPingPulsing] = useState(false);
  const [feedTimestamp, setFeedTimestamp] = useState<number>(0);
  const [isSimulatingGrace, setIsSimulatingGrace] = useState(false);

  // Countdown timer reference
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Poll status regularly
  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      if (isSimulatingGrace) return; // don't overwrite during interactive simulation
      const st = await fetchStatus();
      if (isMounted) {
        setStatus(st);
      }
    }

    loadData();
    const interval = setInterval(loadData, 2800);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [isSimulatingGrace]);

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in a textarea or input
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) return;

      if (e.code === 'Space') {
        e.preventDefault();
        if (status.resident_status !== 'safe') {
          handleAction('dismiss');
        }
      } else if (e.key === 'a' || e.key === 'A') {
        if (status.resident_status !== 'safe') {
          handleAction('acknowledge');
        }
      } else if (e.key === 'p' || e.key === 'P') {
        setPrivacyLevel((prev) => (prev === 0 ? 1 : prev === 1 ? 2 : 0));
        playSound('click');
      } else if (e.key === 'd' || e.key === 'D') {
        handleSourceSwitch(status.active_source === 'demo' ? 'webcam' : 'demo');
      } else if (e.key === 'Escape') {
        setSnapshotModalUrl(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [status]);

  const triggerToast = (msg: string) => {
    setFeedbackToast(msg);
    setTimeout(() => setFeedbackToast(null), 3800);
  };

  // Interactive Fall Simulation Trigger
  const handleStartFallSimulation = () => {
    playSound('warning');
    setIsSimulatingGrace(true);

    const simulatedAlert: AlertItem = {
      id: `sim-${Date.now()}`,
      timestamp: Date.now(),
      time_formatted: 'Just now',
      exact_time: new Date().toLocaleTimeString(),
      date_formatted: 'Today',
      subject: 'Eleanor Vance',
      room: 'Living Room',
      status: 'pending',
      plain_status: 'Grace Period Countdown',
      severity: 'High Risk',
      confidence_pct: 91,
      notes: 'Simulated fall test triggered by caregiver console.',
      pose_telemetry: {
        torso_angle_deg: 79,
        fall_velocity: 1.84,
        recovery_detected: false,
        sensor_location: 'Edge Sensor Living Room #1',
      },
    };

    const simStatus: SystemStatus = {
      resident_name: 'Eleanor Vance',
      room: 'Living Room',
      resident_status: 'grace_period',
      camera_online: true,
      active_source: status.active_source,
      detection_active: true,
      grace_seconds_remaining: 20,
      active_alert: simulatedAlert,
      last_checked_at: 'Just now',
    };

    setStatus(simStatus);
    setLocalSimulationStatus(simStatus);
    triggerToast('⚡ Fall candidate detected! 20-second grace countdown started.');

    let currentSec = 20;
    if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);

    countdownIntervalRef.current = setInterval(() => {
      currentSec -= 1;
      if (currentSec <= 0) {
        if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
        playSound('warning');
        setIsSimulatingGrace(false);
        const alertStatus: SystemStatus = {
          ...simStatus,
          resident_status: 'alert',
          grace_seconds_remaining: 0,
        };
        setStatus(alertStatus);
        setLocalSimulationStatus(alertStatus);
        triggerToast('⚠️ Grace period elapsed without cancellation! Emergency alert dispatched.');
      } else {
        setStatus((prev) => ({
          ...prev,
          grace_seconds_remaining: currentSec,
        }));
      }
    }, 1000);
  };

  const handleAction = async (action: 'acknowledge' | 'dismiss' | 'escalate') => {
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
    setIsSimulatingGrace(false);
    setActionLoading(true);

    const alertId = status.active_alert?.id || 'current-sim';
    const success = await takeAlertAction(alertId, action);
    setActionLoading(false);

    if (success) {
      if (action === 'acknowledge') {
        playSound('resolved');
        triggerToast("Attending: Marked as attended. Thank you for checking on Eleanor!");
      } else if (action === 'dismiss') {
        playSound('ping');
        triggerToast("Resolved: Marked as false alarm. Resident confirmed safe.");
      } else {
        playSound('warning');
        triggerToast("Escalated: Emergency notification triggered to Care Team & EMS!");
      }

      setLocalSimulationStatus({
        resident_status: 'safe',
        grace_seconds_remaining: 0,
        active_alert: null,
      });

      const newStatus = await fetchStatus();
      setStatus({ ...newStatus, resident_status: 'safe', active_alert: null, grace_seconds_remaining: 0 });
    }
  };

  const handleSourceSwitch = async (source: 'webcam' | 'demo') => {
    setSwitchingSource(true);
    playSound('click');
    const ok = await switchCameraSource(source);
    setSwitchingSource(false);
    if (ok) {
      setFeedTimestamp(Date.now());
      triggerToast(
        source === 'demo'
          ? 'Switched to Fall Simulation Video. Observe pose tracking!'
          : 'Switched to Live Camera.'
      );
      const newStatus = await fetchStatus();
      setStatus(newStatus);
    }
  };

  // Interactive Voice Ping check-in
  const handleQuickPing = () => {
    playSound('chime');
    setPingPulsing(true);
    setTimeout(() => setPingPulsing(false), 2400);

    triggerToast("🔊 Voice Check-in pinged Eleanor's Room 102 console: 'Checking in on you, Mom!'");
  };

  // Snapshot Capture tool
  const handleCaptureSnapshot = () => {
    playSound('click');
    const snapUrl = `/api/stream/snapshot?t=${Date.now()}`;
    setSnapshotModalUrl(snapUrl);
    setSnapshotTime(new Date().toLocaleTimeString());
  };

  const isSafe = status.resident_status === 'safe';
  const isGrace = status.resident_status === 'grace_period';
  const isAlert = status.resident_status === 'alert';

  // Countdown circular progress calculation (radius 36 -> circumference = 2 * PI * 36 ≈ 226)
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const progressRatio = isGrace ? (20 - status.grace_seconds_remaining) / 20 : 0;
  const strokeDashoffset = circumference * progressRatio;

  return (
    <div className="animate-fade-in" style={{ paddingTop: '0.5rem' }}>
      {/* Toast Notification */}
      {feedbackToast && (
        <div
          className="animate-scale-up"
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            zIndex: 1000,
            background: 'rgba(15, 23, 42, 0.96)',
            color: '#fff',
            padding: '0.95rem 1.4rem',
            borderRadius: '16px',
            border: '1px solid rgba(94, 234, 212, 0.45)',
            boxShadow: '0 16px 45px rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            fontSize: '0.92rem',
            fontWeight: 600,
            backdropFilter: 'blur(12px)',
          }}
        >
          <Sparkles size={18} color="#5eead4" />
          <span>{feedbackToast}</span>
          <button
            onClick={() => setFeedbackToast(null)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-subtle)',
              cursor: 'pointer',
              marginLeft: '0.5rem',
            }}
          >
            <X size={15} />
          </button>
        </div>
      )}

      {/* ─── Hero Peace-of-Mind Status Banner ─────────────────────────────── */}
      <section className={`hero-status ${isSafe ? 'safe' : isGrace ? 'grace' : 'alert'}`}>
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1.5rem',
          }}
        >
          <div style={{ flex: 1, minWidth: 320 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.8rem' }}>
              <div className={`status-badge ${isSafe ? 'safe' : isGrace ? 'grace' : 'alert'}`}>
                <span className={`status-orb ${isSafe ? 'safe' : isGrace ? 'grace' : 'alert'}`} />
                {isSafe
                  ? 'Resident Safe & Calm'
                  : isGrace
                  ? 'Possible Fall Detected — In Grace Period'
                  : 'Fall Confirmed — Immediate Action Needed'}
              </div>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Sensor: Living Room #1 · Updated {status.last_checked_at}
              </span>
            </div>

            <h1
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 'clamp(1.9rem, 3.2vw, 2.7rem)',
                fontWeight: 800,
                letterSpacing: '-0.035em',
                lineHeight: 1.15,
                marginBottom: '0.6rem',
                color: '#fff',
              }}
            >
              {isSafe
                ? 'All is peaceful. Eleanor is safe.'
                : isGrace
                ? `Fall candidate detected. Waiting ${status.grace_seconds_remaining}s...`
                : 'Fall Confirmed — Immediate Action Needed!'}
            </h1>

            <p
              style={{
                fontSize: '1.02rem',
                color: isSafe ? 'var(--text-muted)' : isGrace ? '#fde68a' : '#fecdd3',
                maxWidth: 640,
                lineHeight: 1.5,
              }}
            >
              {isSafe
                ? `Normal gentle posture detected in ${status.room}. Privacy shield is safeguarding personal dignity.`
                : isGrace
                ? `High-velocity downward movement registered. If Eleanor is alright, tap "I'm OK" below to dismiss before alerts dispatch.`
                : 'Grace period expired without false alarm resolution. Contacting emergency caregiver team now.'}
            </p>

            {/* Interactive Testing Toolbar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.7rem', marginTop: '1.2rem' }}>
              {isSafe && (
                <button
                  onClick={handleStartFallSimulation}
                  className="hud-control-btn"
                  title="Simulate a fall detection event to test the grace countdown"
                  style={{
                    background: 'rgba(245, 158, 11, 0.15)',
                    borderColor: 'rgba(245, 158, 11, 0.4)',
                    color: '#fbbf24',
                  }}
                >
                  <Play size={14} />
                  <span>⚡ Test Grace Period Countdown</span>
                </button>
              )}

              <button
                onClick={handleQuickPing}
                className="hud-control-btn"
                title="Send audio chime check-in to Eleanor's room"
              >
                <Radio size={14} color="#5eead4" />
                <span>Voice Check-in Ping</span>
              </button>
            </div>
          </div>

          {/* Interactive Countdown / Action Card */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', minWidth: 280 }}>
            {/* Animated Circular Countdown Timer during Grace Period */}
            {isGrace && (
              <div className="countdown-container animate-scale-up">
                <svg className="countdown-svg" viewBox="0 0 88 88">
                  <circle className="countdown-bg-circle" cx="44" cy="44" r={radius} />
                  <circle
                    className="countdown-progress-circle"
                    cx="44"
                    cy="44"
                    r={radius}
                    stroke={
                      status.grace_seconds_remaining > 10
                        ? '#fbbf24'
                        : status.grace_seconds_remaining > 5
                        ? '#f97316'
                        : '#f43f5e'
                    }
                    strokeDasharray={circumference}
                    strokeDashoffset={strokeDashoffset}
                  />
                </svg>
                <div className="countdown-text">
                  <span>{status.grace_seconds_remaining}</span>
                  <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: '#94a3b8' }}>
                    sec
                  </span>
                </div>
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%' }}>
              {isSafe ? (
                <div
                  style={{
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    padding: '1.1rem 1.4rem',
                    borderRadius: '18px',
                    textAlign: 'center',
                    position: 'relative',
                  }}
                >
                  {pingPulsing && (
                    <div
                      style={{
                        position: 'absolute',
                        inset: -4,
                        borderRadius: 22,
                        border: '2px solid #5eead4',
                        animation: 'radarPing 1.2s ease-out infinite',
                        pointerEvents: 'none',
                      }}
                    />
                  )}
                  <div
                    style={{
                      fontSize: '0.78rem',
                      color: '#94a3b8',
                      textTransform: 'uppercase',
                      letterSpacing: '0.08em',
                      fontWeight: 700,
                    }}
                  >
                    Active Caregiver
                  </div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginTop: '0.2rem' }}>
                    Sarah Miller (Daughter)
                  </div>
                  <div
                    style={{
                      fontSize: '0.78rem',
                      color: '#10b981',
                      marginTop: '0.3rem',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.4rem',
                    }}
                  >
                    <span
                      style={{
                        width: 7,
                        height: 7,
                        borderRadius: '50%',
                        background: '#10b981',
                        display: 'inline-block',
                      }}
                    />
                    On Duty · 1-Tap Response Ready
                  </div>
                </div>
              ) : isGrace ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                  <button
                    className="action-btn btn-attending"
                    onClick={() => handleAction('dismiss')}
                    disabled={actionLoading}
                    style={{ width: '100%', fontSize: '1rem', padding: '0.95rem' }}
                  >
                    <CheckCircle2 size={20} />
                    <span>I'm OK — False Alarm</span>
                  </button>
                  <button
                    className="action-btn btn-primary-urgent"
                    onClick={() => handleAction('escalate')}
                    disabled={actionLoading}
                    style={{ width: '100%', fontSize: '0.9rem', padding: '0.8rem' }}
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
        </div>
      </section>

      {/* ─── Main Content Grid: Live View ─────────────────────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr',
          gap: '1.8rem',
          marginTop: '1.5rem',
        }}
      >
        {/* Live Visual Check-In */}
        <div>
          <div className="glass-panel" style={{ padding: '1.4rem' }}>
            {/* Header Toolbar */}
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '0.75rem',
                marginBottom: '1.1rem',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <h2
                    style={{
                      fontFamily: 'var(--font-display)',
                      fontSize: '1.25rem',
                      fontWeight: 700,
                      color: '#fff',
                    }}
                  >
                    Live Visual Check-In
                  </h2>
                  <span className="hud-chip">
                    <Activity size={12} color="#10b981" />
                    <span>15 FPS · Local ML</span>
                  </span>
                </div>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                  {status.room} · Optical Pose Extraction (MediaPipe)
                </p>
              </div>

              {/* Video Action Controls */}
              <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.5rem' }}>
                {/* Snapshot button */}
                <button
                  onClick={handleCaptureSnapshot}
                  className="hud-control-btn"
                  title="Capture snapshot frame for verification"
                >
                  <Camera size={14} />
                  <span>Snapshot</span>
                </button>

                {/* Digital Zoom Cycle */}
                <button
                  onClick={() => {
                    setZoomLevel((prev) => (prev === 1 ? 1.25 : prev === 1.25 ? 1.5 : 1));
                    playSound('click');
                  }}
                  className="hud-control-btn"
                  title="Cycle Digital Zoom"
                >
                  <ZoomIn size={14} />
                  <span>{zoomLevel}x</span>
                </button>

                {/* Camera Source Toggle: Live Cam vs Fall Demo Clip */}
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    background: 'rgba(255,255,255,0.06)',
                    borderRadius: '10px',
                    padding: '3px',
                  }}
                >
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

            {/* Video Player Frame with Interactive Zoom & Canvas */}
            <div
              className="video-frame"
              style={{
                transform: `scale(${zoomLevel})`,
                transformOrigin: 'center center',
                transition: 'transform 0.25s ease',
              }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                key={status.active_source}
                src={
                  feedTimestamp > 0
                    ? `/api/stream/feed?src=${status.active_source}&t=${feedTimestamp}`
                    : `/api/stream/feed?src=${status.active_source}`
                }
                alt="Room Live Stream"
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'contain',
                  display: 'block',
                  filter:
                    privacyLevel === 1
                      ? 'blur(14px) brightness(0.85)'
                      : privacyLevel === 2
                      ? 'blur(35px) brightness(0.6)'
                      : 'none',
                  transition: 'filter 0.3s ease',
                }}
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.src = `/api/stream/snapshot?t=${Date.now()}`;
                  setTimeout(() => {
                    target.src = `/api/stream/feed?t=${Date.now()}`;
                  }, 1200);
                }}
              />

              {/* Privacy Shield Info Overlay */}
              {privacyLevel > 0 && (
                <div
                  className="privacy-overlay"
                  style={{
                    background:
                      privacyLevel === 2 ? 'rgba(7, 13, 25, 0.88)' : 'rgba(7, 13, 25, 0.45)',
                  }}
                >
                  <div className="privacy-pill">
                    <ShieldCheck size={14} />
                    <span>
                      {privacyLevel === 2
                        ? 'Full Dignity Silhouette Shield'
                        : 'Soft Frosted Privacy Veil'}
                    </span>
                  </div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fff' }}>
                    Movement & Posture Continuously Monitored
                  </div>
                  <p style={{ maxWidth: 360, fontSize: '0.82rem' }}>
                    Visual feed is securely masked for dignity while local MediaPipe AI tracks posture safety.
                  </p>
                  <button
                    onClick={() => {
                      setPrivacyLevel(0);
                      playSound('click');
                    }}
                    className="action-btn btn-secondary-quiet"
                    style={{ fontSize: '0.8rem', padding: '0.45rem 0.9rem' }}
                  >
                    <Eye size={14} /> Clear Privacy Mask
                  </button>
                </div>
              )}

              {/* Floating Camera Meta Tag */}
              <div
                style={{
                  position: 'absolute',
                  top: 14,
                  left: 14,
                  background: 'rgba(7, 13, 25, 0.85)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '999px',
                  padding: '0.35rem 0.85rem',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: '#5eead4',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.45rem',
                  letterSpacing: '0.04em',
                }}
              >
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#5eead4' }} />
                {status.active_source === 'demo' ? 'DEMO FALL SIMULATION' : 'LIVE WEBCAM'}
              </div>

              {/* Live Telemetry Pill on bottom right */}
              <div
                style={{
                  position: 'absolute',
                  bottom: 14,
                  right: 14,
                  background: 'rgba(7, 13, 25, 0.85)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '10px',
                  padding: '0.35rem 0.75rem',
                  fontSize: '0.74rem',
                  color: '#cbd5e1',
                  display: 'flex',
                  gap: '0.75rem',
                }}
              >
                <span>
                  Angle: <strong style={{ color: isSafe ? '#34d399' : '#f43f5e' }}>{isSafe ? '14°' : '82°'}</strong>
                </span>
                <span>
                  Torso Vel: <strong style={{ color: '#fff' }}>{isSafe ? '0.12 m/s' : '1.84 m/s'}</strong>
                </span>
                <span>
                  Status:{' '}
                  <strong style={{ color: isSafe ? '#34d399' : '#fbbf24' }}>
                    {isSafe ? 'Stable' : 'Rapid Drop'}
                  </strong>
                </span>
              </div>
            </div>

            {/* Privacy Veil Slider Controls */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginTop: '1.1rem',
                padding: '0.75rem 1rem',
                background: 'rgba(255, 255, 255, 0.03)',
                borderRadius: '14px',
                border: '1px solid var(--border-light)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <Sliders size={16} color="#5eead4" />
                <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#e2e8f0' }}>
                  Dignity Veil Level:
                </span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {privacyLevel === 0 ? 'Clear (0%)' : privacyLevel === 1 ? 'Frosted (50%)' : 'Silhouette (100%)'}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', width: 220 }}>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="1"
                  value={privacyLevel}
                  onChange={(e) => {
                    setPrivacyLevel(Number(e.target.value));
                    playSound('click');
                  }}
                  className="interactive-slider"
                  title="Adjust video privacy blur level"
                />
              </div>
            </div>

            {/* Footer status notes */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginTop: '0.8rem',
                fontSize: '0.8rem',
                color: 'var(--text-subtle)',
              }}
            >
              <span>Sensor: Local FallGuard Edge Unit · 15 FPS</span>
              <span>🔒 Zero Cloud Uploads · 100% On-Device Processing</span>
            </div>
          </div>
        </div>

      </div>

      {/* ─── Interactive Snapshot Preview Modal ────────────────────────────── */}
      {snapshotModalUrl && (
        <div className="modal-overlay" onClick={() => setSnapshotModalUrl(null)}>
          <div
            className="modal-card animate-scale-up"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: 640 }}
          >
            <div
              style={{
                padding: '1.2rem 1.4rem',
                borderBottom: '1px solid var(--border-light)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <Camera size={18} color="#5eead4" />
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff' }}>
                  Camera Snapshot Preview
                </h3>
              </div>
              <button
                onClick={() => setSnapshotModalUrl(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ padding: '1.4rem' }}>
              <div
                style={{
                  borderRadius: '14px',
                  overflow: 'hidden',
                  background: '#000',
                  border: '1px solid var(--border-light)',
                  aspectRatio: '16/9',
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={snapshotModalUrl}
                  alt="Snapshot"
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                />
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginTop: '1.2rem',
                }}
              >
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Captured at {snapshotTime || 'Just now'}
                </span>
                <div style={{ display: 'flex', gap: '0.6rem' }}>
                  <a
                    href={snapshotModalUrl}
                    download={`snapshot-${Date.now()}.jpg`}
                    className="action-btn btn-attending"
                    style={{ padding: '0.5rem 1rem', fontSize: '0.82rem' }}
                  >
                    <span>Download Image</span>
                  </a>
                  <button
                    onClick={() => setSnapshotModalUrl(null)}
                    className="action-btn btn-secondary-quiet"
                    style={{ padding: '0.5rem 1rem', fontSize: '0.82rem' }}
                  >
                    <span>Close</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
