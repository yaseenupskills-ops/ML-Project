'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ShieldCheck, AlertCircle, ArrowRight, Loader2 } from 'lucide-react';

function getNextPath(): string {
  if (typeof window === 'undefined') return '/';
  const next = new URLSearchParams(window.location.search).get('next');
  if (next && next.startsWith('/') && !next.startsWith('//')) return next;
  return '/';
}

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);

  // Already signed in (or auth disabled) → skip the login screen
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('/api/auth/me', { cache: 'no-store' });
        if (!cancelled && res.ok) {
          const data = await res.json();
          if (!data.guest) {
            router.replace(getNextPath());
            return;
          }
        }
      } catch {
        // API unreachable — show the form; submit will surface the error
      }
      if (!cancelled) setChecking(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(body?.detail || 'Sign-in failed. Please try again.');
        setLoading(false);
        return;
      }
      router.replace(getNextPath());
      router.refresh();
    } catch {
      setError('Cannot reach the FallGuard API. Is it running on port 8000?');
      setLoading(false);
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.85rem 1rem',
    background: 'var(--bg-subtle)',
    border: '1px solid var(--border-light)',
    borderRadius: 'var(--radius-sm)',
    color: 'var(--text-main)',
    fontSize: '0.95rem',
    fontFamily: 'var(--font-main)',
    outline: 'none',
    transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
  };

  return (
    <div
      style={{
        minHeight: '62vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem 1rem',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 400,
          background: 'var(--bg-card)',
          border: '1px solid var(--border-light)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-card)',
          padding: '2.4rem 2.2rem',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.4rem', marginBottom: '1.8rem' }}>
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: 'var(--radius-md)',
              background: 'rgba(16, 185, 129, 0.14)',
              border: '1px solid var(--border-glow)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '0.4rem',
            }}
          >
            <ShieldCheck size={26} color="#10b981" />
          </div>
          <h1
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '1.5rem',
              fontWeight: 700,
              letterSpacing: '-0.02em',
            }}
          >
            Welcome back
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
            Sign in to your FallGuard Care console
          </p>
        </div>

        {checking ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem 0', color: 'var(--text-muted)' }}>
            <Loader2 size={22} className="animate-spin" />
          </div>
        ) : (
          <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              Username
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. admin"
                autoComplete="username"
                autoFocus
                required
                style={inputStyle}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-glow)';
                  e.currentTarget.style.boxShadow = '0 0 0 3px rgba(94, 234, 212, 0.12)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-light)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />
            </label>

            <label style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                required
                style={inputStyle}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-glow)';
                  e.currentTarget.style.boxShadow = '0 0 0 3px rgba(94, 234, 212, 0.12)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-light)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />
            </label>

            {error && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.7rem 0.9rem',
                  background: 'var(--danger-red-bg)',
                  border: '1px solid var(--danger-red-glow)',
                  borderRadius: 'var(--radius-sm)',
                  color: '#fda4af',
                  fontSize: '0.84rem',
                }}
                role="alert"
              >
                <AlertCircle size={15} style={{ flexShrink: 0 }} />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                padding: '0.9rem 1rem',
                background: loading ? 'rgba(16, 185, 129, 0.5)' : 'var(--safe-green)',
                color: '#04110c',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.95rem',
                fontWeight: 700,
                fontFamily: 'var(--font-main)',
                cursor: loading ? 'wait' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                transition: 'filter 0.2s ease',
              }}
              onMouseEnter={(e) => {
                if (!loading) e.currentTarget.style.filter = 'brightness(1.08)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.filter = 'none';
              }}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Signing in…
                </>
              ) : (
                <>
                  Sign in
                  <ArrowRight size={16} />
                </>
              )}
            </button>

            <p
              style={{
                textAlign: 'center',
                color: 'var(--text-subtle)',
                fontSize: '0.76rem',
                lineHeight: 1.6,
              }}
            >
              Demo accounts — <span style={{ color: 'var(--text-muted)' }}>admin / admin123</span>
              <br />
              <span style={{ color: 'var(--text-muted)' }}>caregiver / care123</span>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
