import type { Metadata } from 'next';
import './globals.css';
import { Lock } from 'lucide-react';
import InteractiveNavbar from './components/Navbar';

export const metadata: Metadata = {
  title: 'FallGuard — Peaceful Safety & Fall Detection',
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
        <InteractiveNavbar />

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
