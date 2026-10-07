'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Users,
  PhoneCall,
  Mail,
  ShieldAlert,
  ArrowLeft,
  Bell,
  Sliders,
  CheckCircle,
  Sparkles,
} from 'lucide-react';
import { fetchContacts, ContactItem } from '@/lib/api';

export default function ContactsPage() {
  const [contacts, setContacts] = useState<ContactItem[]>([]);
  const [graceSec, setGraceSec] = useState(20);
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [smsAlerts, setSmsAlerts] = useState(true);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  useEffect(() => {
    fetchContacts().then(setContacts);
  }, []);

  const triggerToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

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
            <Users size={16} />
            <span>Care Circle</span>
          </div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 800, color: '#fff', letterSpacing: '-0.03em' }}>
            Care Team & Emergency Contacts
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', marginTop: '0.2rem' }}>
            Instant contacts and notification preferences for Eleanor Vance.
          </p>
        </div>

        <Link href="/" className="action-btn btn-secondary-quiet" style={{ fontSize: '0.85rem', padding: '0.5rem 1rem' }}>
          <ArrowLeft size={16} />
          <span>Back to Home</span>
        </Link>
      </div>

      {/* Emergency Immediate Dispatch Card */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(244,63,94,0.18) 0%, rgba(20,24,38,0.9) 100%)',
        border: '1px solid rgba(244,63,94,0.4)',
        borderRadius: '24px',
        padding: '1.6rem 2rem',
        marginBottom: '2rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1.2rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
          <div style={{
            width: 52,
            height: 52,
            borderRadius: '16px',
            background: 'linear-gradient(135deg, #f43f5e 0%, #e11d48 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            boxShadow: '0 8px 20px rgba(244,63,94,0.4)',
          }}>
            <ShieldAlert size={28} />
          </div>
          <div>
            <div style={{ fontSize: '0.78rem', color: '#fda4af', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              Immediate Emergency Services
            </div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff' }}>
              Local Emergency Medical Dispatch (911)
            </h2>
            <p style={{ fontSize: '0.86rem', color: '#fecdd3' }}>
              Direct line to emergency services. Use if resident is unresponsive or injured.
            </p>
          </div>
        </div>

        <a
          href="tel:911"
          className="action-btn btn-primary-urgent"
          style={{ fontSize: '1.05rem', padding: '0.9rem 1.8rem' }}
        >
          <PhoneCall size={20} />
          <span>Call 911 Direct</span>
        </a>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '1.8rem' }}>
        {/* Left Column: Contact Cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', fontWeight: 700, color: '#fff', marginBottom: '0.4rem' }}>
            Primary Care Circle
          </h2>

          {contacts.map((c) => (
            <div key={c.id} className="contact-card">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span style={{ fontWeight: 800, fontSize: '1.1rem', color: '#fff' }}>
                    {c.name}
                  </span>
                  <span style={{
                    padding: '0.2rem 0.6rem',
                    borderRadius: '999px',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    background: c.is_primary ? 'rgba(16,185,129,0.18)' : 'rgba(255,255,255,0.06)',
                    color: c.is_primary ? '#34d399' : '#94a3b8',
                    border: '1px solid var(--border-light)',
                  }}>
                    {c.badge}
                  </span>
                </div>

                <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  {c.role}
                </div>

                <div style={{ fontSize: '0.88rem', color: '#5eead4', marginTop: '0.5rem', fontWeight: 600 }}>
                  {c.phone}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <a
                  href={`tel:${c.phone.replace(/[^0-9]/g, '')}`}
                  className="action-btn btn-attending"
                  style={{ padding: '0.55rem 0.9rem', fontSize: '0.82rem' }}
                >
                  <PhoneCall size={15} />
                  <span>Call</span>
                </a>
                {c.email && (
                  <a
                    href={`mailto:${c.email}`}
                    className="action-btn btn-secondary-quiet"
                    style={{ padding: '0.55rem 0.9rem', fontSize: '0.82rem' }}
                  >
                    <Mail size={15} />
                    <span>Email</span>
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Right Column: Notification Preferences */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.2rem' }}>
              <Sliders size={20} color="#5eead4" />
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', fontWeight: 700, color: '#fff' }}>
                Alert Preferences
              </h2>
            </div>

            {/* Grace Period Slider */}
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.88rem', color: '#fff', fontWeight: 600 }}>Grace Period Countdown</span>
                <span style={{ fontSize: '0.88rem', color: '#5eead4', fontWeight: 700 }}>{graceSec} Seconds</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.7rem' }}>
                Time given to Eleanor to cancel false alarms before caregivers are alerted.
              </p>
              <input
                type="range"
                min="10"
                max="45"
                step="5"
                value={graceSec}
                onChange={(e) => {
                  setGraceSec(Number(e.target.value));
                  triggerToast(`Grace period updated to ${e.target.value}s`);
                }}
                style={{ width: '100%', accentColor: '#14b8a6', cursor: 'pointer' }}
              />
            </div>

            {/* Toggles */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.8rem 1rem',
                borderRadius: '12px',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--border-light)',
              }}>
                <div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#fff' }}>SMS Urgent Notifications</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Send text message on verified fall</div>
                </div>
                <input
                  type="checkbox"
                  checked={smsAlerts}
                  onChange={(e) => {
                    setSmsAlerts(e.target.checked);
                    triggerToast(`SMS notifications ${e.target.checked ? 'enabled' : 'disabled'}`);
                  }}
                  style={{ width: 18, height: 18, accentColor: '#14b8a6', cursor: 'pointer' }}
                />
              </div>

              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.8rem 1rem',
                borderRadius: '12px',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--border-light)',
              }}>
                <div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#fff' }}>Email Alert Digest</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Send event summary to family</div>
                </div>
                <input
                  type="checkbox"
                  checked={emailAlerts}
                  onChange={(e) => {
                    setEmailAlerts(e.target.checked);
                    triggerToast(`Email notifications ${e.target.checked ? 'enabled' : 'disabled'}`);
                  }}
                  style={{ width: 18, height: 18, accentColor: '#14b8a6', cursor: 'pointer' }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
