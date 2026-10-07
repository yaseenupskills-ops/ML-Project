'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  ShieldCheck,
  Heart,
  History,
  Users,
  Volume2,
  VolumeX,
  PhoneCall,
  Command,
  Menu,
  ChevronDown,
  X,
  Check,
  Copy,
  ExternalLink,
} from 'lucide-react';
import { isSoundEnabled, setSoundEnabled, playSound } from '@/lib/sound';

export default function InteractiveNavbar() {
  const pathname = usePathname();
  const [soundOn, setSoundOn] = useState(true);
  const [showSpeedDial, setShowSpeedDial] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [showSidebar, setShowSidebar] = useState(false);
  const [showResidentMenu, setShowResidentMenu] = useState(false);
  const [selectedResident, setSelectedResident] = useState({
    name: 'Eleanor Vance',
    room: 'Room 102 (Living Area)',
    initials: 'EV',
  });
  const [copiedNumber, setCopiedNumber] = useState<string | null>(null);

  useEffect(() => {
    setSoundOn(isSoundEnabled());
  }, []);

  const closeSidebar = () => {
    setShowSidebar(false);
    setShowResidentMenu(false);
  };

  // Close the slide bar on navigation
  useEffect(() => {
    setShowSidebar(false);
    setShowResidentMenu(false);
  }, [pathname]);

  // Close the slide bar on Escape
  useEffect(() => {
    if (!showSidebar) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowSidebar(false);
        setShowResidentMenu(false);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [showSidebar]);

  const handleToggleSound = () => {
    const next = !soundOn;
    setSoundOn(next);
    setSoundEnabled(next);
    if (next) {
      playSound('ping');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard?.writeText(text);
    setCopiedNumber(text);
    playSound('click');
    setTimeout(() => setCopiedNumber(null), 2000);
  };

  return (
    <>
      <header className="navbar">
        <div className="nav-container">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
            {/* Slide-in Sidebar Toggle */}
            <button
              onClick={() => {
                setShowSidebar(true);
                playSound('click');
              }}
              className="hud-control-btn"
              title="Open navigation slide bar"
              style={{ padding: '0.45rem 0.6rem' }}
            >
              <Menu size={16} />
            </button>

            <Link href="/" className="brand">
              <div className="brand-icon">
                <ShieldCheck size={22} />
              </div>
              <div>
                <div style={{ color: '#fff', lineHeight: 1.1 }}>FallGuard Care</div>
                <div
                  style={{
                    fontSize: '0.68rem',
                    color: '#5eead4',
                    fontWeight: 600,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                  }}
                >
                  Home & Family
                </div>
              </div>
            </Link>

          </div>

          {/* Interactive Tool Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            {/* Audio Toggle */}
            <button
              onClick={handleToggleSound}
              className="hud-control-btn"
              title={soundOn ? 'Audible chime alerts enabled. Click to mute.' : 'Sound muted. Click to enable chimes.'}
              style={{
                borderColor: soundOn ? 'rgba(20, 184, 166, 0.4)' : 'rgba(255, 255, 255, 0.12)',
              }}
            >
              {soundOn ? (
                <>
                  <Volume2 size={16} color="#5eead4" />
                  <div className="sound-bars">
                    <div className="sound-bar" />
                    <div className="sound-bar" />
                    <div className="sound-bar" />
                  </div>
                </>
              ) : (
                <>
                  <VolumeX size={16} color="#94a3b8" />
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Muted</span>
                </>
              )}
            </button>

            {/* Speed Dial Modal Launcher */}
            <button
              onClick={() => {
                setShowSpeedDial(true);
                playSound('ping');
              }}
              className="hud-control-btn"
              title="Emergency Speed Dial contacts"
              style={{
                background: 'rgba(244, 63, 94, 0.12)',
                borderColor: 'rgba(244, 63, 94, 0.35)',
                color: '#fda4af',
              }}
            >
              <PhoneCall size={15} />
              <span style={{ display: 'none' }}>Dial</span>
              <span style={{ fontSize: '0.8rem', fontWeight: 700 }}>Speed Dial</span>
            </button>

            {/* Keyboard Shortcuts Dialog */}
            <button
              onClick={() => {
                setShowShortcuts(true);
                playSound('click');
              }}
              className="hud-control-btn"
              title="Keyboard shortcuts & help"
              style={{ padding: '0.45rem 0.6rem' }}
            >
              <Command size={15} />
            </button>

            {/* Privacy Status Badge */}
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.45rem',
                padding: '0.35rem 0.8rem',
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                borderRadius: '999px',
                fontSize: '0.78rem',
                fontWeight: 600,
                color: '#34d399',
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
              Private & Local
            </div>
          </div>
        </div>
      </header>

      {/* ─── Slide-in Navigation Sidebar ─────────────────────────────── */}
      {showSidebar && (
        <div className="sidebar-overlay" onClick={closeSidebar}>
          <aside
            className="sidebar-panel animate-slide-left"
            onClick={(e) => e.stopPropagation()}
            aria-label="Navigation menu"
          >
            {/* Panel Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <ShieldCheck size={18} color="#5eead4" />
                <span style={{ fontWeight: 700, fontSize: '1rem', color: '#fff' }}>
                  Navigation
                </span>
              </div>
              <button
                onClick={() => {
                  closeSidebar();
                  playSound('click');
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: 4,
                }}
                title="Close navigation"
              >
                <X size={18} />
              </button>
            </div>

            {/* Interactive Resident Switcher */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => {
                  setShowResidentMenu(!showResidentMenu);
                  playSound('click');
                }}
                className="resident-badge"
                style={{
                  cursor: 'pointer',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  maxWidth: '100%',
                  flexWrap: 'wrap',
                }}
                title="Click to switch resident monitor"
              >
                <div className="resident-avatar">{selectedResident.initials}</div>
                <span style={{ color: '#f8fafc', fontWeight: 600 }}>{selectedResident.name}</span>
                <span style={{ color: 'var(--text-subtle)' }}>·</span>
                <span style={{ color: '#5eead4' }}>{selectedResident.room}</span>
                <ChevronDown size={14} style={{ marginLeft: 2, color: 'var(--text-subtle)' }} />
              </button>

              {showResidentMenu && (
                <div
                  className="animate-scale-up"
                  style={{
                    position: 'absolute',
                    top: 'calc(100% + 8px)',
                    left: 0,
                    width: 260,
                    background: '#0f172a',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    borderRadius: '16px',
                    boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
                    padding: '0.5rem',
                    zIndex: 100,
                  }}
                >
                  <div
                    style={{
                      padding: '0.5rem 0.75rem',
                      fontSize: '0.72rem',
                      color: 'var(--text-subtle)',
                      textTransform: 'uppercase',
                      fontWeight: 700,
                      letterSpacing: '0.05em',
                    }}
                  >
                    Select Resident
                  </div>
                  {[
                    { name: 'Eleanor Vance', room: 'Room 102 (Living Area)', initials: 'EV' },
                    { name: 'Eleanor Vance', room: 'Room 102 (Bedroom)', initials: 'EV' },
                    { name: 'Arthur Vance', room: 'Room 105 (Studio)', initials: 'AV' },
                  ].map((r, i) => (
                    <button
                      key={i}
                      onClick={() => {
                        setSelectedResident(r);
                        setShowResidentMenu(false);
                        playSound('ping');
                      }}
                      style={{
                        width: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '0.65rem 0.8rem',
                        borderRadius: '10px',
                        background:
                          selectedResident.room === r.room ? 'rgba(20, 184, 166, 0.15)' : 'transparent',
                        color: '#fff',
                        border: 'none',
                        cursor: 'pointer',
                        textAlign: 'left',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                        <div
                          className="resident-avatar"
                          style={{
                            background:
                              r.initials === 'EV'
                                ? 'linear-gradient(135deg, #10b981, #0d9488)'
                                : '#6366f1',
                          }}
                        >
                          {r.initials}
                        </div>
                        <div>
                          <div style={{ fontSize: '0.86rem', fontWeight: 600 }}>{r.name}</div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            {r.room}
                          </div>
                        </div>
                      </div>
                      {selectedResident.room === r.room && <Check size={16} color="#5eead4" />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Primary Navigation */}
            <nav className="nav-links sidebar-links">
              <Link
                href="/"
                className={`nav-btn ${pathname === '/' ? 'active' : ''}`}
                onClick={() => {
                  playSound('click');
                  closeSidebar();
                }}
              >
                <Heart size={16} />
                <span>Home & Live</span>
              </Link>
              <Link
                href="/history"
                className={`nav-btn ${pathname === '/history' ? 'active' : ''}`}
                onClick={() => {
                  playSound('click');
                  closeSidebar();
                }}
              >
                <History size={16} />
                <span>Care Log</span>
              </Link>
              <Link
                href="/contacts"
                className={`nav-btn ${pathname === '/contacts' ? 'active' : ''}`}
                onClick={() => {
                  playSound('click');
                  closeSidebar();
                }}
              >
                <Users size={16} />
                <span>Care Team</span>
              </Link>
            </nav>
          </aside>
        </div>
      )}

      {/* Speed Dial Modal */}
      {showSpeedDial && (
        <div className="modal-overlay" onClick={() => setShowSpeedDial(false)}>
          <div
            className="modal-card animate-scale-up"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: 520 }}
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
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div
                  style={{
                    width: 38,
                    height: 38,
                    borderRadius: '12px',
                    background: 'rgba(244, 63, 94, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#f43f5e',
                  }}
                >
                  <PhoneCall size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff' }}>
                    Emergency Speed Dial
                  </h3>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Immediate voice contacts for Eleanor Vance
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowSpeedDial(false)}
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

            <div style={{ padding: '1.4rem 1.6rem', display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
              {[
                {
                  name: 'Sarah Miller (Daughter)',
                  role: 'Primary Caregiver · On Duty',
                  phone: '(555) 234-5678',
                  urgent: true,
                },
                {
                  name: 'Oakridge On-Site Nursing Desk',
                  role: 'Floor 1 Medical Team',
                  phone: '(555) 991-0022',
                  urgent: false,
                },
                {
                  name: 'Dr. Robert Chen',
                  role: 'Primary Care Physician',
                  phone: '(555) 876-5432',
                  urgent: false,
                },
                {
                  name: '911 Emergency Services',
                  role: 'Dispatch & Paramedics',
                  phone: '911',
                  urgent: true,
                },
              ].map((contact, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '1rem 1.2rem',
                    borderRadius: '14px',
                    background: contact.urgent ? 'rgba(244, 63, 94, 0.08)' : 'rgba(255, 255, 255, 0.04)',
                    border: `1px solid ${contact.urgent ? 'rgba(244, 63, 94, 0.3)' : 'rgba(255, 255, 255, 0.08)'}`,
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '0.96rem', color: '#fff' }}>
                      {contact.name}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {contact.role}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#5eead4', fontWeight: 600, marginTop: '0.2rem' }}>
                      {contact.phone}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      onClick={() => copyToClipboard(contact.phone)}
                      className="action-btn btn-secondary-quiet"
                      style={{ padding: '0.45rem 0.8rem', fontSize: '0.8rem' }}
                      title="Copy phone number"
                    >
                      {copiedNumber === contact.phone ? <Check size={14} color="#34d399" /> : <Copy size={14} />}
                      <span>{copiedNumber === contact.phone ? 'Copied' : 'Copy'}</span>
                    </button>
                    <a
                      href={`tel:${contact.phone}`}
                      className={`action-btn ${contact.urgent ? 'btn-primary-urgent' : 'btn-attending'}`}
                      style={{ padding: '0.45rem 1rem', fontSize: '0.82rem' }}
                      onClick={() => playSound('warning')}
                    >
                      <PhoneCall size={14} />
                      <span>Call</span>
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Keyboard Shortcuts Modal */}
      {showShortcuts && (
        <div className="modal-overlay" onClick={() => setShowShortcuts(false)}>
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
                <Command size={18} color="#5eead4" />
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff' }}>
                  Interactive Shortcuts
                </h3>
              </div>
              <button
                onClick={() => setShowShortcuts(false)}
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

            <div style={{ padding: '1.4rem 1.6rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              {[
                { key: 'Space', desc: 'Dismiss grace countdown / mark false alarm' },
                { key: 'A', desc: 'Mark fall event as attended' },
                { key: 'P', desc: 'Toggle dignity & privacy shield' },
                { key: 'D', desc: 'Switch to fall simulation demo clip' },
                { key: 'M', desc: 'Toggle sound chimes on/off' },
                { key: 'Esc', desc: 'Close any active drawer or modal' },
              ].map((item, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.55rem 0',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                  }}
                >
                  <span style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>{item.desc}</span>
                  <span className="kbd-badge">{item.key}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
