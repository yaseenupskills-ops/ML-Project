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
  UserPlus,
  Trash2,
  Copy,
  Check,
  Send,
  Volume2,
  X,
} from 'lucide-react';
import { fetchContacts, addLocalContact, deleteLocalContact, ContactItem } from '@/lib/api';
import { playSound } from '@/lib/sound';

export default function ContactsPage() {
  const [contacts, setContacts] = useState<ContactItem[]>([]);
  const [graceSec, setGraceSec] = useState(20);
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [smsAlerts, setSmsAlerts] = useState(true);
  const [chimeVolume, setChimeVolume] = useState(80);
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // New Contact Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [newName, setNewName] = useState('');
  const [newRole, setNewRole] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newBadge, setNewBadge] = useState('Care Team');

  // Test Dispatch state
  const [testingDispatch, setTestingDispatch] = useState(false);

  useEffect(() => {
    fetchContacts().then(setContacts);
  }, []);

  const triggerToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard?.writeText(text);
    setCopiedId(id);
    playSound('click');
    triggerToast(`Copied ${text}`);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleAddContact = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim() || !newPhone.trim()) {
      triggerToast('Please provide a name and phone number');
      return;
    }

    const created = addLocalContact({
      name: newName.trim(),
      role: newRole.trim() || 'Care Team Member',
      phone: newPhone.trim(),
      email: newEmail.trim(),
      is_primary: false,
      badge: newBadge,
    });

    setContacts((prev) => [created, ...prev]);
    setShowAddModal(false);
    setNewName('');
    setNewRole('');
    setNewPhone('');
    setNewEmail('');
    playSound('ping');
    triggerToast(`Added ${created.name} to Care Circle.`);
  };

  const handleDelete = (id: string, name: string) => {
    deleteLocalContact(id);
    setContacts((prev) => prev.filter((c) => c.id !== id));
    playSound('click');
    triggerToast(`Removed ${name} from Care Circle.`);
  };

  const handleTestDispatch = () => {
    playSound('warning');
    setTestingDispatch(true);
    triggerToast('Initiating mock emergency dispatch test...');

    setTimeout(() => {
      setTestingDispatch(false);
      playSound('resolved');
      triggerToast('✅ Mock alert dispatched successfully to Sarah Miller & Dr. Chen!');
    }, 1800);
  };

  return (
    <div className="animate-fade-in" style={{ paddingTop: '1.2rem' }}>
      {toastMsg && (
        <div
          className="animate-scale-up"
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            zIndex: 1000,
            background: 'rgba(15, 23, 42, 0.96)',
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
          marginBottom: '1.8rem',
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
            <Users size={16} />
            <span>Care Circle & Safety Network</span>
          </div>
          <h1
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '2rem',
              fontWeight: 800,
              color: '#fff',
              letterSpacing: '-0.03em',
            }}
          >
            Care Team & Emergency Contacts
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', marginTop: '0.2rem' }}>
            Direct voice lines and escalation notification settings for Eleanor Vance.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            onClick={() => {
              setShowAddModal(true);
              playSound('click');
            }}
            className="hud-control-btn"
            style={{
              background: 'rgba(20, 184, 166, 0.18)',
              borderColor: 'rgba(20, 184, 166, 0.4)',
              color: '#5eead4',
              padding: '0.6rem 1rem',
            }}
          >
            <UserPlus size={16} />
            <span>Add Contact</span>
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

      {/* Emergency Immediate Dispatch Card */}
      <div
        style={{
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
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: '16px',
              background: 'linear-gradient(135deg, #f43f5e 0%, #e11d48 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              boxShadow: '0 8px 20px rgba(244,63,94,0.4)',
            }}
          >
            <ShieldAlert size={28} />
          </div>
          <div>
            <div
              style={{
                fontSize: '0.78rem',
                color: '#fda4af',
                fontWeight: 700,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}
            >
              Emergency Priority Line
            </div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: '#fff' }}>
              Local Emergency Medical Dispatch (911)
            </h2>
            <p style={{ fontSize: '0.86rem', color: '#fecdd3' }}>
              Direct priority connection for emergency paramedics and ambulance support.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            onClick={handleTestDispatch}
            disabled={testingDispatch}
            className="hud-control-btn"
            style={{
              background: 'rgba(255, 255, 255, 0.08)',
              padding: '0.85rem 1.2rem',
              color: '#fff',
            }}
            title="Simulate SMS/Email dispatch"
          >
            <Send size={16} color="#fbbf24" />
            <span>{testingDispatch ? 'Testing Dispatch...' : '⚡ Test Dispatch Alert'}</span>
          </button>

          <a
            href="tel:911"
            className="action-btn btn-primary-urgent"
            style={{ fontSize: '1rem', padding: '0.85rem 1.6rem' }}
            onClick={() => playSound('warning')}
          >
            <PhoneCall size={18} />
            <span>Call 911 Direct</span>
          </a>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.5fr) minmax(0, 1fr)', gap: '1.8rem' }}>
        {/* Left Column: Contact Cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h2
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '1.2rem',
                fontWeight: 700,
                color: '#fff',
              }}
            >
              Primary Care Circle ({contacts.length})
            </h2>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-subtle)' }}>
              Ordered by alert priority
            </span>
          </div>

          {contacts.map((c) => (
            <div key={c.id} className="contact-card">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span style={{ fontWeight: 800, fontSize: '1.1rem', color: '#fff' }}>
                    {c.name}
                  </span>
                  <span
                    style={{
                      padding: '0.2rem 0.6rem',
                      borderRadius: '999px',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      background: c.is_primary
                        ? 'rgba(16,185,129,0.18)'
                        : 'rgba(255,255,255,0.06)',
                      color: c.is_primary ? '#34d399' : '#94a3b8',
                      border: '1px solid var(--border-light)',
                    }}
                  >
                    {c.badge}
                  </span>
                </div>

                <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  {c.role}
                </div>

                <div
                  style={{
                    fontSize: '0.88rem',
                    color: '#5eead4',
                    marginTop: '0.45rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                  }}
                >
                  <span>{c.phone}</span>
                  <button
                    onClick={() => handleCopy(c.id, c.phone)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-subtle)',
                      cursor: 'pointer',
                      padding: 2,
                    }}
                    title="Copy phone"
                  >
                    {copiedId === c.id ? <Check size={13} color="#34d399" /> : <Copy size={13} />}
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <a
                  href={`tel:${c.phone.replace(/[^0-9]/g, '')}`}
                  className="action-btn btn-attending"
                  style={{ padding: '0.55rem 0.9rem', fontSize: '0.82rem' }}
                  onClick={() => playSound('click')}
                >
                  <PhoneCall size={15} />
                  <span>Call</span>
                </a>
                {c.email && (
                  <a
                    href={`mailto:${c.email}`}
                    className="action-btn btn-secondary-quiet"
                    style={{ padding: '0.55rem 0.9rem', fontSize: '0.82rem' }}
                    onClick={() => playSound('click')}
                  >
                    <Mail size={15} />
                    <span>Email</span>
                  </a>
                )}
                {!c.is_primary && c.id !== 'c4' && (
                  <button
                    onClick={() => handleDelete(c.id, c.name)}
                    className="hud-control-btn"
                    style={{ padding: '0.55rem 0.65rem' }}
                    title="Delete contact"
                  >
                    <Trash2 size={14} color="#f43f5e" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Right Column: Notification & Grace Period Settings */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.6rem',
                marginBottom: '1.2rem',
              }}
            >
              <Sliders size={20} color="#5eead4" />
              <h2
                style={{
                  fontFamily: 'var(--font-display)',
                  fontSize: '1.2rem',
                  fontWeight: 700,
                  color: '#fff',
                }}
              >
                Alert & Grace Period Settings
              </h2>
            </div>

            {/* Grace Period Slider */}
            <div style={{ marginBottom: '1.5rem' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginBottom: '0.5rem',
                }}
              >
                <span style={{ fontSize: '0.88rem', color: '#fff', fontWeight: 600 }}>
                  Grace Countdown Timeout
                </span>
                <span style={{ fontSize: '0.88rem', color: '#5eead4', fontWeight: 700 }}>
                  {graceSec} Seconds
                </span>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.7rem' }}>
                Window allowed for Eleanor to cancel accidental stumbles before escalation dispatch.
              </p>
              <input
                type="range"
                min="10"
                max="45"
                step="5"
                value={graceSec}
                onChange={(e) => {
                  setGraceSec(Number(e.target.value));
                  playSound('click');
                  triggerToast(`Grace period updated to ${e.target.value}s`);
                }}
                className="interactive-slider"
              />
            </div>

            {/* Chime Volume */}
            <div style={{ marginBottom: '1.5rem' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginBottom: '0.5rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Volume2 size={16} color="#5eead4" />
                  <span style={{ fontSize: '0.88rem', color: '#fff', fontWeight: 600 }}>
                    Caregiver Chime Volume
                  </span>
                </div>
                <span style={{ fontSize: '0.88rem', color: '#5eead4', fontWeight: 700 }}>
                  {chimeVolume}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={chimeVolume}
                onChange={(e) => {
                  setChimeVolume(Number(e.target.value));
                  playSound('ping');
                }}
                className="interactive-slider"
              />
            </div>

            {/* Notification Toggles */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.85rem 1rem',
                  borderRadius: '12px',
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid var(--border-light)',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#fff' }}>
                    SMS Urgent Notifications
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Instant SMS on verified high-confidence event
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={smsAlerts}
                  onChange={(e) => {
                    setEmailAlerts(e.target.checked);
                    playSound('click');
                    triggerToast(`SMS notifications ${e.target.checked ? 'enabled' : 'disabled'}`);
                  }}
                  style={{ width: 18, height: 18, accentColor: '#14b8a6', cursor: 'pointer' }}
                />
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.85rem 1rem',
                  borderRadius: '12px',
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid var(--border-light)',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#fff' }}>
                    Email Safety Digest
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Daily report and timestamp summaries
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={emailAlerts}
                  onChange={(e) => {
                    setEmailAlerts(e.target.checked);
                    playSound('click');
                    triggerToast(`Email alerts ${e.target.checked ? 'enabled' : 'disabled'}`);
                  }}
                  style={{ width: 18, height: 18, accentColor: '#14b8a6', cursor: 'pointer' }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Add Contact Modal ────────────────────────────────────────── */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div
            className="modal-card animate-scale-up"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: 480 }}
          >
            <div
              style={{
                padding: '1.4rem 1.6rem',
                borderBottom: '1px solid var(--border-light)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <UserPlus size={18} color="#5eead4" />
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff' }}>
                  Add Care Team Member
                </h3>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
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

            <form onSubmit={handleAddContact} style={{ padding: '1.4rem 1.6rem', display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: '0.3rem' }}>
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Maria Gonzalez"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="search-input"
                  style={{ paddingLeft: '1rem' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: '0.3rem' }}>
                  Role / Relationship
                </label>
                <input
                  type="text"
                  placeholder="e.g. Next-door Neighbor, Physical Therapist"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="search-input"
                  style={{ paddingLeft: '1rem' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
                <div>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: '0.3rem' }}>
                    Phone Number *
                  </label>
                  <input
                    type="tel"
                    required
                    placeholder="(555) 000-0000"
                    value={newPhone}
                    onChange={(e) => setNewPhone(e.target.value)}
                    className="search-input"
                    style={{ paddingLeft: '1rem' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: '0.3rem' }}>
                    Badge Tag
                  </label>
                  <select
                    value={newBadge}
                    onChange={(e) => setNewBadge(e.target.value)}
                    className="search-input"
                    style={{ paddingLeft: '0.8rem', cursor: 'pointer' }}
                  >
                    <option value="Care Circle">Care Circle</option>
                    <option value="Neighbor">Neighbor</option>
                    <option value="Medical">Medical Specialist</option>
                    <option value="Family">Family Member</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: '0.3rem' }}>
                  Email Address
                </label>
                <input
                  type="email"
                  placeholder="maria@example.com"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="search-input"
                  style={{ paddingLeft: '1rem' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.6rem', marginTop: '0.8rem' }}>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="action-btn btn-secondary-quiet"
                  style={{ padding: '0.6rem 1.2rem', fontSize: '0.85rem' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="action-btn btn-attending"
                  style={{ padding: '0.6rem 1.4rem', fontSize: '0.85rem' }}
                >
                  Save Contact
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
