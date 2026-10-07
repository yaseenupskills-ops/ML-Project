'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  BarChart3,
  ArrowLeft,
  AlertTriangle,
  Clock,
  Activity,
  Lock,
  Loader2,
} from 'lucide-react';
import { fetchSummary, SummaryMetrics } from '@/lib/api';
import { playSound } from '@/lib/sound';

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<SummaryMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      const sm = await fetchSummary();
      if (isMounted) {
        setSummary(sm);
        setLoading(false);
      }
    }

    load();
    const interval = setInterval(load, 3000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const primaryStats: { value: string; label: string; color: string }[] = summary
    ? [
        { value: `${summary.streak_days} Days`, label: 'Incident-Free Streak', color: '#10b981' },
        { value: `${summary.avg_response_sec}s`, label: 'Avg Response Time', color: '#38bdf8' },
        { value: `${summary.routine_checks_today}`, label: 'Routine Checks Today', color: '#f8fafc' },
        { value: summary.system_health.split('·')[0].trim(), label: 'Local AI Sensor Health', color: '#a78bfa' },
      ]
    : [];

  const secondaryStats: { icon: React.ReactNode; value: string; label: string; color: string }[] = summary
    ? [
        {
          icon: <AlertTriangle size={16} />,
          value: `${summary.falls_today}`,
          label: 'Falls Today',
          color: summary.falls_today > 0 ? '#f43f5e' : '#10b981',
        },
        {
          icon: <Clock size={16} />,
          value: summary.last_routine_check,
          label: 'Last Routine Check',
          color: '#38bdf8',
        },
        {
          icon: <Activity size={16} />,
          value: summary.system_health,
          label: 'System Health',
          color: '#10b981',
        },
        {
          icon: <Lock size={16} />,
          value: summary.privacy_mode,
          label: 'Privacy Mode',
          color: '#5eead4',
        },
      ]
    : [];

  return (
    <div style={{ paddingTop: '1.5rem' }}>
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
            <BarChart3 size={16} />
            <span>Analytics & Wellness</span>
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
            Peace-of-Mind Summary
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', marginTop: '0.2rem' }}>
            Local-only safety metrics, caregiver response trends, and system wellness at a glance.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <span
            style={{
              fontSize: '0.8rem',
              color: '#10b981',
              fontWeight: 700,
              padding: '0.55rem 0.9rem',
              background: 'var(--safe-green-bg)',
              border: '1px solid var(--safe-green-glow)',
              borderRadius: 'var(--radius-sm)',
              whiteSpace: 'nowrap',
            }}
          >
            ● Active Protection
          </span>

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

      {loading && !summary ? (
        <div
          className="glass-panel"
          style={{ padding: '3.5rem 2rem', textAlign: 'center', color: 'var(--text-muted)' }}
        >
          <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto 0.7rem' }} />
          <div style={{ fontSize: '0.9rem' }}>Loading wellness metrics…</div>
        </div>
      ) : (
        <>
          {/* Primary Peace-of-Mind Stats */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '1rem',
              marginBottom: '1.6rem',
            }}
          >
            {primaryStats.map((stat) => (
              <div className="stat-pill" key={stat.label}>
                <div className="stat-val" style={{ color: stat.color }}>
                  {stat.value}
                </div>
                <div className="stat-desc">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* Secondary Wellness Metrics */}
          <div className="glass-panel" style={{ padding: '1.4rem' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '1rem',
              }}
            >
              <h2
                style={{
                  fontFamily: 'var(--font-display)',
                  fontSize: '1.15rem',
                  fontWeight: 700,
                  color: '#fff',
                }}
              >
                System & Privacy Wellness
              </h2>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-subtle)' }}>
                Refreshed every 3s · processed on-device
              </span>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '0.85rem',
              }}
            >
              {secondaryStats.map((stat) => (
                <div
                  key={stat.label}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.7rem',
                    padding: '0.85rem 0.95rem',
                    background: 'var(--bg-subtle)',
                    border: '1px solid var(--border-light)',
                    borderRadius: 'var(--radius-sm)',
                  }}
                >
                  <div
                    style={{
                      width: 34,
                      height: 34,
                      borderRadius: 'var(--radius-sm)',
                      background: 'rgba(255, 255, 255, 0.04)',
                      border: '1px solid var(--border-light)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: stat.color,
                      flexShrink: 0,
                    }}
                  >
                    {stat.icon}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: '0.92rem',
                        fontWeight: 700,
                        color: '#f8fafc',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {stat.value}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{stat.label}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
