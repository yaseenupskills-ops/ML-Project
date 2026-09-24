'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Button } from './button';
import { login, devBypassUser, isDevBypass } from '@/services/auth';
import { useStore } from '@/lib/store';

import {
    AppleIcon,
    AtSignIcon,
    ChevronLeftIcon,
    Eye,
    EyeOff,
    Grid2x2PlusIcon,
    LockIcon,
} from 'lucide-react';
import { Input } from './input';

export function AuthPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const router = useRouter();
    const setUser = useStore((s) => s.setUser);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            let user;
            if (email === 'dev@fallguard.local' && isDevBypass()) {
                user = devBypassUser();
            } else {
                user = await login({ email, password });
            }
            setUser(user);
            router.push('/app');
        } catch (err: any) {
            setError(err.message || 'Login failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="relative md:h-screen md:overflow-hidden lg:grid lg:grid-cols-2 bg-slate-900 text-white">
            <div className="bg-slate-800/60 relative hidden h-full flex-col border-r p-10 lg:flex">
                <div className="from-background absolute inset-0 z-10 bg-gradient-to-t to-transparent" />
                <div className="z-10 flex items-center gap-2">
                    <Grid2x2PlusIcon className="size-6" />
                    <p className="text-xl font-semibold">Asme</p>
                </div>
                <div className="z-10 mt-auto">
                    <blockquote className="space-y-2">
                        <p className="text-xl">
                            &ldquo;This Platform has helped me to save time and serve my
                            clients faster than ever before.&rdquo;
                        </p>
                        <footer className="font-mono text-sm font-semibold">
                            ~ Ali Hassan
                        </footer>
                    </blockquote>
                </div>
                <div className="absolute inset-0">
                    <FloatingPaths position={1} />
                    <FloatingPaths position={-1} />
                </div>
            </div>
            <div className="relative flex min-h-screen flex-col justify-center p-4">
                <div
                    aria-hidden
                    className="absolute inset-0 isolate contain-strict -z-10 opacity-60"
                >
                    <div className="bg-[radial-gradient(68.54%_68.72%_at_55.02%_31.46%,color-mix(in_oklab,var(--color-foreground)_6%,transparent)_0,hsla(0,0%,55%,.02)_50%,color-mix(in_oklab,var(--color-foreground)_1%,transparent)_80%)] absolute top-0 right-0 h-320 w-140 -translate-y-87.5 rounded-full" />
                    <div className="bg-[radial-gradient(50%_50%_at_50%_50%,color-mix(in_oklab,var(--color-foreground)_4%,transparent)_0,color-mix(in_oklab,var(--color-foreground)_1%,transparent)_80%,transparent_100%)] absolute top-0 right-0 h-320 w-60 [translate:5%_-50%] rounded-full" />
                    <div className="bg-[radial-gradient(50%_50%_at_50%_50%,color-mix(in_oklab,var(--color-foreground)_4%,transparent)_0,color-mix(in_oklab,var(--color-foreground)_1%,transparent)_80%,transparent_100%)] absolute top-0 right-0 h-320 w-60 -translate-y-87.5 rounded-full" />
                </div>
                <Button variant="ghost" className="absolute top-7 left-5" asChild>
                    <a href="/">
                        <ChevronLeftIcon className='size-4 me-2' />
                        Home
                    </a>
                </Button>
                <div className="mx-auto space-y-4 sm:w-sm">
                    <div className="flex items-center gap-2 lg:hidden">
                        <Grid2x2PlusIcon className="size-6" />
                        <p className="text-xl font-semibold">Asme</p>
                    </div>
                    <div className="flex flex-col space-y-1">
                        <h1 className="font-heading text-2xl font-bold tracking-wide text-white">
                            Sign In or Join Now!
                        </h1>
                        <p className="text-slate-300 text-base">
                            login or create your asme account.
                        </p>
                    </div>
                    <div className="space-y-2">
                        <Button type="button" size="lg" className="w-full">
                            <GoogleIcon className='size-4 me-2' />
                            Continue with Google
                        </Button>
                        <Button type="button" size="lg" className="w-full">
                            <AppleIcon className='size-4 me-2' />
                            Continue with Apple
                        </Button>
                        <Button type="button" size="lg" className="w-full">
                            <GithubIcon className='size-4 me-2' />
                            Continue with GitHub
                        </Button>
                    </div>

                    <AuthSeparator />

                    <form onSubmit={handleSubmit} className="space-y-2">
                        <p className="text-slate-300 text-start text-xs">
                            Enter your email and password to sign in
                        </p>
                        <div className="relative h-max">
                            <Input
                                placeholder="your.email@example.com"
                                className="peer ps-9"
                                type="email"
                                name="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                disabled={loading}
                                required
                            />
                            <div className="text-slate-300 pointer-events-none absolute inset-y-0 start-0 flex items-center justify-center ps-3 peer-disabled:opacity-50">
                                <AtSignIcon className="size-4" aria-hidden="true" />
                            </div>
                        </div>

                        <div className="relative h-max">
                            <Input
                                placeholder="Password"
                                className="peer ps-9 pe-10"
                                type={showPassword ? 'text' : 'password'}
                                name="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                disabled={loading}
                                required
                            />
                            <div className="text-slate-300 pointer-events-none absolute inset-y-0 start-0 flex items-center justify-center ps-3 peer-disabled:opacity-50">
                                <LockIcon className="size-4" aria-hidden="true" />
                            </div>
                            <button
                                type="button"
                                onClick={() => setShowPassword((v) => !v)}
                                className="text-slate-300 absolute inset-y-0 end-0 flex items-center justify-center pe-3 hover:text-foreground"
                                aria-label={showPassword ? 'Hide password' : 'Show password'}
                                disabled={loading}
                            >
                                {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                            </button>
                        </div>

                        {error && <div className="text-red-400 text-sm text-center">{error}</div>}

                        {isDevBypass() && (
                            <div className="p-2 bg-blue-900/20 border border-blue-600/30 rounded text-xs text-blue-300 text-center">
                                Dev bypass active. Use: <strong>dev@fallguard.local</strong> with any password.
                            </div>
                        )}

                        <Button type="submit" className="w-full" disabled={loading}>
                            <span>{loading ? 'Signing in...' : 'Continue With Email'}</span>
                        </Button>
                    </form>
                    <p className="text-slate-300 mt-8 text-sm">
                        By clicking continue, you agree to our{' '}
                        <a
                            href="#"
                            className="hover:text-primary underline underline-offset-4"
                        >
                            Terms of Service
                        </a>{' '}
                        and{' '}
                        <a
                            href="#"
                            className="hover:text-primary underline underline-offset-4"
                        >
                            Privacy Policy
                        </a>
                        .
                    </p>
                </div>
            </div>
        </main>
    );
}

function FloatingPaths({ position }: { position: number }) {
    const paths = Array.from({ length: 14 }, (_, i) => ({
        id: i,
        d: `M-${380 - i * 5 * position} -${189 + i * 6}C-${
            380 - i * 5 * position
        } -${189 + i * 6} -${312 - i * 5 * position} ${216 - i * 6} ${
            152 - i * 5 * position
        } ${343 - i * 6}C${616 - i * 5 * position} ${470 - i * 6} ${
            684 - i * 5 * position
        } ${875 - i * 6} ${684 - i * 5 * position} ${875 - i * 6}`,
        color: `rgba(15,23,42,${0.1 + i * 0.03})`,
        width: 0.5 + i * 0.03,
    }));

    return (
        <div className="pointer-events-none absolute inset-0">
            <svg
                className="h-full w-full text-white"
                viewBox="0 0 696 316"
                fill="none"
            >
                <title>Background Paths</title>
                {paths.map((path) => (
                    <motion.path
                        key={path.id}
                        d={path.d}
                        stroke="currentColor"
                        strokeWidth={path.width}
                        strokeOpacity={0.35 + path.id * 0.04}
                        initial={{ pathLength: 0.3, opacity: 0.7 }}
                        animate={{
                            pathOffset: [0, 1, 0],
                        }}
                        transition={{
                            duration: 20 + (path.id % 10),
                            repeat: Number.POSITIVE_INFINITY,
                            ease: 'linear',
                        }}
                    />
                ))}
            </svg>
        </div>
    );
}

const GoogleIcon = (props: React.ComponentProps<'svg'>) => (
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="currentColor"
        {...props}
    >
        <g>
            <path d="M12.479,14.265v-3.279h11.049c0.108,0.571,0.164,1.247,0.164,1.979c0,2.46-0.672,5.502-2.84,7.669   C18.744,22.829,16.051,24,12.483,24C5.869,24,0.308,18.613,0.308,12S5.869,0,12.483,0c3.659,0,6.265,1.436,8.223,3.307L18.392,5.62   c-1.404-1.317-3.307-2.341-5.913-2.341C7.65,3.279,3.873,7.171,3.873,12s3.777,8.721,8.606,8.721c3.132,0,4.916-1.258,6.059-2.401   c0.927-0.927,1.537-2.251,1.777-4.059L12.479,14.265z" />
        </g>
    </svg>
);

const GithubIcon = (props: React.ComponentProps<'svg'>) => (
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="currentColor"
        {...props}
    >
        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.11.81 2.25 0 1.635-.015 2.945-.015 3.36 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
    </svg>
);

const AuthSeparator = () => {
    return (
        <div className="flex w-full items-center justify-center">
            <div className="bg-border h-px w-full" />
            <span className="text-slate-300 px-2 text-xs">OR</span>
            <div className="bg-border h-px w-full" />
        </div>
    );
};
