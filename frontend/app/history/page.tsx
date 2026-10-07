'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  History,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Filter,
  ArrowLeft,
  Calendar,
  Clock,
  Sparkles,
  Download,
  Search,
  FileText,
  X,
  ChevronRight,
  TrendingDown,
  ShieldCheck,
} from 'lucide-react';
import {
  fetchAlerts,
  takeAlertAction,
  saveAlertNote,
  exportAlertsToCSV,
  AlertItem,
} from '@/lib/api';
import { playSound } from '@/lib/sound';

export default function HistoryPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'attended' | 'dismissed'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<AlertItem | null>(null);
  const [noteEdit, setNoteEdit] = useState('');

  useEffect(() => {
    loadAlerts();
  }, []);

  async function loadAlerts() {
    setLoading(true);
    const data = await fetchAlerts();
    setAlerts(data);
    setLoading(false);
  }

  const triggerToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const handleAction = async (id: string, action: 'acknowledge' | 'dismiss' | 'escalate') => {
    const success = await takeAlertAction(id, action);
    if (success) {
      playSound(action === 'acknowledge' ? 'resolved' : 'ping');
      triggerToast(`Event recorded: ${action.toUpperCase()}`);
      if (selectedAlert && selectedAlert.id === id) {
        setSelectedAlert(null);
      }
      loadAlerts();
    }
  };

  const handleSaveNote = async () => {
    if (!selectedAlert) return;
    playSound('ping');
    await saveAlertNote(selectedAlert.id, noteEdit);
    setSelectedAlert({ ...selectedAlert, notes: noteEdit });
    setAlerts((prev) => prev.map((a) => (a.id === selectedAlert.id ? { ...a, notes: noteEdit } : a)));
    triggerToast('Caregiver observation saved to event log.');
  };

  const handleExportCSV = () => {
    playSound('click');
    exportAlertsToCSV(filteredAlerts);
    triggerToast(`Exported ${filteredAlerts.length} events to CSV.`);
  };

  // Filter & Search Logic
  const filteredAlerts = alerts.filter((a) => {
    // Tab filter
    if (filter === 'pending' && a.status !== 'pending') return false;
    if (filter === 'attended' && !['acknowledged', 'escalated'].includes(a.status)) return false;
    if (filter === 'dismissed' && !['dismissed', 'cancelled'].includes(a.status)) return false;

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const match =
        a.plain_status.toLowerCase().includes(q) ||
        a.room.toLowerCase().includes(q) ||
        a.subject.toLowerCase().includes(q) ||
        (a.notes && a.notes.toLowerCase().includes(q)) ||
        a.exact_time.toLowerCase().includes(q);
      if (!match) return false;
    }

    return true;
  });

  // Calculate metrics
  const totalEvents = alerts.length;
  const attendedCount = alerts.filter((a) => a.status === 'acknowledged').length;
  const dismissedCount = alerts.filter((a) => a.status === 'dismissed' || a.status === 'cancelled').length;
  const falseAlarmRate = totalEvents > 0 ? Math.round((dismissedCount / totalEvents) * 100) : 0;

  return (
    <div className="animate-fade-in" style={{ paddingTop: '1.2rem' }}>
      {toastMsg && (
        <div
          className="animate-scale-up"
          style={{
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
            fontWeight: 600,
          }}
        >
          <Sparkles size={18} color="#5eead4" />
          <span>{toastMsg}</span>
        </div>
      )}

      {/* Header */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          marginBottom: '1.6rem',
        }}
      >
        <div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              color: '#5eead4',
              fontSize: '0.85rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              marginBottom: '0.3rem',
            }}
          >
            <History size={16} />
            <span>Care Log & Timeline</span>
          </div>
          <h1
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '2.1rem',
              fontWeight: 800,
              color: '#fff',
              letterSpacing: '-0.03em',
            }}
          >
            Resident Activity & Safety History
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', marginTop: '0.2rem' }}>
            Transparent, local records of posture stability events and caregiver response logs.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            onClick={handleExportCSV}
            className="hud-control-btn"
            title="Download records as CSV spreadsheet"
            style={{
              padding: '0.6rem 1rem',
              background: 'rgba(20, 184, 166, 0.15)',
              borderColor: 'rgba(20, 184, 166, 0.35)',
              color: '#5eead4',
            }}
          >
            <Download size={15} />
            <span>Export CSV</span>
          </button>

          <Link
            href="/"
            onClick={() => playSound('click')}
            className="action-btn btn-secondary-quiet"
            style={{ fontSize: '0.85rem', padding: '0.55rem 1rem' }}
          >
            <ArrowLeft size={16} />
            <span>Home</span>
          </Link>
        </div>
      </div>

      {/* Interactive Metric Summary Bar */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
          marginBottom: '1.6rem',
        }}
      >
        <div className="stat-pill">
          <div className="stat-val">{totalEvents}</div>
          <div className="stat-desc">Total Monitored Incidents</div>
        </div>
        <div className="stat-pill">
          <div className="stat-val" style={{ color: '#10b981' }}>
            {attendedCount}
          </div>
          <div className="stat-desc">Caregiver Attended Checks</div>
        </div>
        <div className="stat-pill">
          <div className="stat-val" style={{ color: '#38bdf8' }}>
            {falseAlarmRate}%
          </div>
          <div className="stat-desc">Filtered False Positives</div>
        </div>
        <div className="stat-pill">
          <div className="stat-val" style={{ color: '#a78bfa' }}>
            &lt; 35s
          </div>
          <div className="stat-desc">Avg Attention Speed</div>
        </div>
      </div>

      {/* Interactive Search & Filter Bar */}
      <div
        className="glass-panel"
        style={{
          padding: '1.1rem 1.4rem',
          marginBottom: '1.4rem',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
        }}
      >
        {/* Search Bar */}
        <div className="search-input-wrap" style={{ maxWidth: 380 }}>
          <Search
            size={16}
            color="var(--text-subtle)"
            style={{ position: 'absolute', left: 14 }}
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by room, keyword, or note..."
            className="search-input"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              style={{
                position: 'absolute',
                right: 12,
                background: 'none',
                border: 'none',
                color: 'var(--text-subtle)',
                cursor: 'pointer',
              }}
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Filter Pills */}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {[
            { key: 'all', label: `All (${alerts.length})` },
            {
              key: 'pending',
              label: `Needs Attention (${alerts.filter((a) => a.status === 'pending').length})`,
            },
            { key: 'attended', label: `Attended (${attendedCount})` },
            { key: 'dismissed', label: `Resolved (${dismissedCount})` },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => {
                setFilter(tab.key as any);
                playSound('click');
              }}
              className={`tab-filter-btn ${filter === tab.key ? 'active' : ''}`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Events Timeline / List */}
      {loading ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          Loading safety history...
        </div>
      ) : filteredAlerts.length === 0 ? (
        <div className="glass-panel" style={{ padding: '3.5rem 2rem', textAlign: 'center' }}>
          <CheckCircle2 size={44} color="#10b981" style={{ margin: '0 auto 1rem' }} />
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff' }}>No Events Found</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.3rem' }}>
            {searchQuery
              ? `No records match "${searchQuery}". Try clearing search.`
              : 'All is peaceful. No events recorded in this category.'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {filteredAlerts.map((item) => (
            <div
              key={item.id}
              onClick={() => {
                setSelectedAlert(item);
                setNoteEdit(item.notes || '');
                playSound('click');
              }}
              className="event-card"
              style={{
                cursor: 'pointer',
                borderLeft:
                  item.status === 'pending'
                    ? '4px solid #f43f5e'
                    : item.status === 'escalated'
                    ? '4px solid #f59e0b'
                    : '4px solid #10b981',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
                <div
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: '12px',
                    background:
                      item.status === 'pending'
                        ? 'rgba(244, 63, 94, 0.15)'
                        : item.status === 'escalated'
                        ? 'rgba(245, 158, 11, 0.15)'
                        : 'rgba(16, 185, 129, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color:
                      item.status === 'pending'
                        ? '#f43f5e'
                        : item.status === 'escalated'
                        ? '#f59e0b'
                        : '#10b981',
                  }}
                >
                  {item.status === 'pending' ? (
                    <AlertTriangle size={22} />
                  ) : item.status === 'dismissed' ? (
                    <XCircle size={22} />
                  ) : (
                    <CheckCircle2 size={22} />
                  )}
                </div>

                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <span style={{ fontWeight: 800, fontSize: '1.02rem', color: '#fff' }}>
                      {item.plain_status}
                    </span>
                    <span
                      style={{
                        padding: '0.2rem 0.55rem',
                        borderRadius: '6px',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        background: 'rgba(255, 255, 255, 0.06)',
                        color: 'var(--text-muted)',
                        border: '1px solid var(--border-light)',
                      }}
                    >
                      {item.room}
                    </span>
                    <span
                      style={{
                        padding: '0.2rem 0.55rem',
                        borderRadius: '6px',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        background:
                          item.severity === 'High Risk'
                            ? 'rgba(244,63,94,0.15)'
                            : 'rgba(255,255,255,0.06)',
                        color: item.severity === 'High Risk' ? '#fda4af' : '#94a3b8',
                      }}
                    >
                      {item.severity}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#5eead4', fontWeight: 600 }}>
                      {item.confidence_pct}% AI Confidence
                    </span>
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '1rem',
                      marginTop: '0.35rem',
                      fontSize: '0.82rem',
                      color: 'var(--text-muted)',
                    }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <Calendar size={13} />
                      {item.date_formatted}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <Clock size={13} />
                      {item.exact_time} ({item.time_formatted})
                    </span>
                    {item.acknowledged_by && (
                      <span style={{ color: '#5eead4' }}>
                        Handled by: {item.acknowledged_by}
                      </span>
                    )}
                  </div>

                  {item.notes && (
                    <div
                      style={{
                        marginTop: '0.35rem',
                        fontSize: '0.8rem',
                        color: '#94a3b8',
                        fontStyle: 'italic',
                      }}
                    >
                      "{item.notes}"
                    </div>
                  )}
                </div>
              </div>

              {/* Action Buttons if Still Pending */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                {item.status === 'pending' ? (
                  <>
                    <button
                      className="action-btn btn-attending"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAction(item.id, 'acknowledge');
                      }}
                      style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                    >
                      Attending
                    </button>
                    <button
                      className="action-btn btn-secondary-quiet"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAction(item.id, 'dismiss');
                      }}
                      style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                    >
                      False Alarm
                    </button>
                  </>
                ) : (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                      fontSize: '0.8rem',
                      color: 'var(--text-subtle)',
                    }}
                  >
                    <span>View Report</span>
                    <ChevronRight size={14} />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ─── Event Detail Drawer ────────────────────────────────────────── */}
      {selectedAlert && (
        <div className="drawer-overlay" onClick={() => setSelectedAlert(null)}>
          <div
            className="drawer-panel animate-slide-right"
            onClick={(e) => e.stopPropagation()}
            style={{ padding: '1.8rem 1.6rem' }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '1.2rem',
                borderBottom: '1px solid var(--border-light)',
              }}
            >
              <div>
                <span
                  style={{
                    fontSize: '0.72rem',
                    textTransform: 'uppercase',
                    color: '#5eead4',
                    fontWeight: 700,
                    letterSpacing: '0.08em',
                  }}
                >
                  Incident Log #{selectedAlert.id}
                </span>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff', marginTop: '0.2rem' }}>
                  {selectedAlert.plain_status}
                </h3>
              </div>
              <button
                onClick={() => setSelectedAlert(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: 4,
                }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ marginTop: '1.4rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  borderRadius: '14px',
                  padding: '1rem 1.2rem',
                  border: '1px solid var(--border-light)',
                }}
              >
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Location & Resident</div>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', marginTop: '0.15rem' }}>
                  {selectedAlert.subject} · {selectedAlert.room}
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-subtle)', marginTop: '0.35rem' }}>
                  Timestamp: {selectedAlert.date_formatted} at {selectedAlert.exact_time}
                </div>
              </div>

              {/* Confidence Gauge */}
              <div
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  borderRadius: '14px',
                  padding: '1rem 1.2rem',
                  border: '1px solid var(--border-light)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '0.82rem',
                    marginBottom: '0.5rem',
                  }}
                >
                  <span style={{ color: 'var(--text-muted)' }}>Detection Confidence</span>
                  <span style={{ fontWeight: 700, color: '#5eead4' }}>
                    {selectedAlert.confidence_pct}%
                  </span>
                </div>
                <div
                  style={{
                    width: '100%',
                    height: 8,
                    background: 'rgba(255, 255, 255, 0.1)',
                    borderRadius: 999,
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${selectedAlert.confidence_pct}%`,
                      height: '100%',
                      background: 'linear-gradient(90deg, #10b981, #14b8a6, #f43f5e)',
                      borderRadius: 999,
                    }}
                  />
                </div>
              </div>

              {/* Kinematics Telemetry */}
              {selectedAlert.pose_telemetry && (
                <div
                  style={{
                    background: 'rgba(255, 255, 255, 0.04)',
                    borderRadius: '14px',
                    padding: '1rem 1.2rem',
                    border: '1px solid var(--border-light)',
                  }}
                >
                  <div
                    style={{
                      fontSize: '0.82rem',
                      fontWeight: 700,
                      color: '#e2e8f0',
                      marginBottom: '0.6rem',
                    }}
                  >
                    AI Kinematics Analysis
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem' }}>
                    <div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Torso Angle</div>
                      <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#fff' }}>
                        {selectedAlert.pose_telemetry.torso_angle_deg}°
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Impact Velocity</div>
                      <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#fff' }}>
                        {selectedAlert.pose_telemetry.fall_velocity} m/s
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Caregiver Notes Input */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.4rem' }}>
                <label
                  style={{
                    fontSize: '0.82rem',
                    fontWeight: 700,
                    color: '#e2e8f0',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                  }}
                >
                  <FileText size={15} color="#5eead4" />
                  <span>Caregiver Observation Notes</span>
                </label>
                <textarea
                  value={noteEdit}
                  onChange={(e) => setNoteEdit(e.target.value)}
                  placeholder="Record observations or follow-up notes for the care log..."
                  rows={4}
                  style={{
                    width: '100%',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-light)',
                    borderRadius: '12px',
                    padding: '0.75rem',
                    color: '#fff',
                    fontFamily: 'inherit',
                    fontSize: '0.85rem',
                    outline: 'none',
                    resize: 'vertical',
                  }}
                />
                <button
                  onClick={handleSaveNote}
                  className="action-btn btn-attending"
                  style={{ padding: '0.6rem 1rem', fontSize: '0.85rem', alignSelf: 'flex-start' }}
                >
                  <span>Save Note</span>
                </button>
              </div>

              {/* Actions if pending */}
              {selectedAlert.status === 'pending' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', marginTop: '1rem' }}>
                  <button
                    onClick={() => handleAction(selectedAlert.id, 'acknowledge')}
                    className="action-btn btn-attending"
                    style={{ width: '100%' }}
                  >
                    <span>Mark Attended</span>
                  </button>
                  <button
                    onClick={() => handleAction(selectedAlert.id, 'dismiss')}
                    className="action-btn btn-secondary-quiet"
                    style={{ width: '100%' }}
                  >
                    <span>Mark False Alarm</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
