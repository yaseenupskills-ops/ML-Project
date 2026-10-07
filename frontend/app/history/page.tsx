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
} from 'lucide-react';
import { fetchAlerts, takeAlertAction, AlertItem } from '@/lib/api';

export default function HistoryPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'attended' | 'dismissed'>('all');
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  useEffect(() => {
    loadAlerts();
  }, []);

  async function loadAlerts() {
    setLoading(true);
    const data = await fetchAlerts();
    setAlerts(data);
    setLoading(false);
  }

  const handleAction = async (id: string, action: 'acknowledge' | 'dismiss' | 'escalate') => {
    const success = await takeAlertAction(id, action);
    if (success) {
      setToastMsg(`Action recorded: ${action.toUpperCase()}`);
      setTimeout(() => setToastMsg(null), 3000);
      loadAlerts();
    }
  };

  const filtered = alerts.filter((a) => {
    if (filter === 'pending') return a.status === 'pending';
    if (filter === 'attended') return a.status === 'acknowledged' || a.status === 'escalated';
    if (filter === 'dismissed') return a.status === 'dismissed' || a.status === 'cancelled';
    return true;
  });

  return (
    <div className="animate-fade-in" style={{ paddingTop: '1.2rem' }}>
      {toastMsg && (
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
        }}>
          <Sparkles size={18} color="#5eead4" />
          <span>{toastMsg}</span>
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.8rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: '#5eead4', fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '0.3rem' }}>
            <History size={16} />
            <span>Care Log & Timeline</span>
          </div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 800, color: '#fff', letterSpacing: '-0.03em' }}>
            Resident Activity Log
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', marginTop: '0.2rem' }}>
            Clear, plain-English record of all movements, alerts, and caregiver responses.
          </p>
        </div>

        <Link href="/" className="action-btn btn-secondary-quiet" style={{ fontSize: '0.85rem', padding: '0.5rem 1rem' }}>
          <ArrowLeft size={16} />
          <span>Back to Home</span>
        </Link>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '0.6rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        {[
          { key: 'all', label: `All Events (${alerts.length})` },
          { key: 'pending', label: `Needs Attention (${alerts.filter(a => a.status === 'pending').length})` },
          { key: 'attended', label: 'Attended & Escalated' },
          { key: 'dismissed', label: 'False Alarms & Resolved' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key as any)}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '999px',
              border: filter === tab.key ? '1px solid rgba(20, 184, 166, 0.4)' : '1px solid var(--border-light)',
              background: filter === tab.key ? 'rgba(20, 184, 166, 0.15)' : 'rgba(255, 255, 255, 0.04)',
              color: filter === tab.key ? '#fff' : 'var(--text-muted)',
              fontSize: '0.84rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Events List */}
      {loading ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          Loading care log...
        </div>
      ) : filtered.length === 0 ? (
        <div className="glass-panel" style={{ padding: '3.5rem 2rem', textAlign: 'center' }}>
          <CheckCircle2 size={44} color="#10b981" style={{ margin: '0 auto 1rem' }} />
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff' }}>No Events in This Category</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.3rem' }}>
            All is quiet and no matching events were recorded.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
          {filtered.map((item) => (
            <div key={item.id} className="event-card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
                <div style={{
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
                }}>
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
                    <span style={{
                      padding: '0.2rem 0.55rem',
                      borderRadius: '6px',
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      background: 'rgba(255, 255, 255, 0.06)',
                      color: 'var(--text-muted)',
                      border: '1px solid var(--border-light)',
                    }}>
                      {item.room}
                    </span>
                    <span style={{
                      padding: '0.2rem 0.55rem',
                      borderRadius: '6px',
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      background: item.severity === 'High Risk' ? 'rgba(244,63,94,0.15)' : 'rgba(255,255,255,0.06)',
                      color: item.severity === 'High Risk' ? '#fda4af' : '#94a3b8',
                    }}>
                      {item.severity}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '0.35rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
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
                </div>
              </div>

              {/* Action Buttons if Still Pending */}
              {item.status === 'pending' ? (
                <div style={{ display: 'flex', gap: '0.6rem' }}>
                  <button
                    className="action-btn btn-attending"
                    onClick={() => handleAction(item.id, 'acknowledge')}
                    style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                  >
                    Attending
                  </button>
                  <button
                    className="action-btn btn-secondary-quiet"
                    onClick={() => handleAction(item.id, 'dismiss')}
                    style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                  >
                    False Alarm
                  </button>
                </div>
              ) : (
                <div style={{ fontSize: '0.82rem', color: 'var(--text-subtle)', fontStyle: 'italic' }}>
                  Archived locally
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
