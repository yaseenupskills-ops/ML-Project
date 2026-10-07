import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';
import { ShieldCheck, Heart, History, Users, Lock } from 'lucide-react';

export const metadata: Metadata = {
  title: 'FallGuard Care — Peaceful Safety & Fall Detection',
  description: 'A compassionate, caregiver-first fall detection and resident safety console.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body suppressHydrationWarning>
        <header className="navbar">
          <div className="nav-container">
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
              <Link href="/" className="brand">
                <div className="brand-icon">
                  <ShieldCheck size={22} />
                </div>
                <div>
                  <div style={{ color: '#fff', lineHeight: 1.1 }}>FallGuard Care</div>
                  <div style={{ fontSize: '0.68rem', color: '#5eead4', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    Home & Family
                  </div>
                </div>
              </Link>

              <div className="resident-badge">
                <div className="resident-avatar">EV</div>
                <span>Eleanor Vance</span>
                <span style={{ color: 'var(--text-subtle)' }}>·</span>
                <span style={{ color: '#5eead4' }}>Room 102 (Living Area)</span>
              </div>
            </div>

            <nav className="nav-links">
              <Link href="/" className="nav-btn">
                <Heart size={16} />
                <span>Home & Live</span>
              </Link>
              <Link href="/history" className="nav-btn">
                <History size={16} />
                <span>Care Log</span>
              </Link>
              <Link href="/contacts" className="nav-btn">
                <Users size={16} />
                <span>Care Team</span>
              </Link>
            </nav>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <div style={{
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
              }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#10b981', display: 'inline-block' }}></span>
                Private & Local
              </div>
            </div>
          </div>
        </header>

        <main style={{ maxWidth: 1240, margin: '0 auto', padding: '0 1.5rem 3rem' }}>
          {children}
        </main>

        <footer style={{
          borderTop: '1px solid var(--border-light)',
          padding: '1.8rem 1.5rem',
          textAlign: 'center',
          color: 'var(--text-subtle)',
          fontSize: '0.82rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.7rem',
        }}>
          <Lock size={14} />
          <span>Local Privacy Shield: Video processing stays strictly on your local device.</span>
        </footer>
      </body>
    </html>
  );
}
