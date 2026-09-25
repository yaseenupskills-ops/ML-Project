'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader, Card, Pill, Loading } from '../../../components/ui';
import { getMe, getHealth } from '../../../services/api';

export default function SettingsPage() {
  const me = useQuery({ queryKey: ['me'], queryFn: getMe });
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, refetchInterval: 15000 });

  if (me.isLoading) return <Loading />;

  const user = me.data;

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      <PageHeader title="Settings" description="Account and device configuration" />

      <Card>
        <h3 className="font-semibold mb-4">Current Session</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="flex flex-col gap-1">
            <span className="text-xs uppercase text-gray-400">Username</span>
            <span className="text-white">{user?.username}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs uppercase text-gray-400">Display name</span>
            <span className="text-white">{user?.display_name}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs uppercase text-gray-400">Role</span>
            <Pill className="mt-1 w-fit">{user?.role ?? '—'}</Pill>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-2">Auth</h3>
        <p className="text-sm text-gray-400">
          Backend is running with <span className="text-cyan-500">auth.enabled: false</span> — every
          request is treated as the default guest/admin user. Real username/password login will be
          enabled once the auth provider is deployed.
        </p>
      </Card>

      <Card>
        <h3 className="font-semibold mb-2">Device</h3>
        <p className="text-sm text-gray-400">
          Backend liveness: <span className={health.data?.status === 'ok' ? 'text-teal-400' : 'text-red-400'}>
            {health.data?.status}
          </span>{' '}
          · Camera: {health.data?.camera ? 'connected' : 'unavailable'} · API binds to 127.0.0.1
          (privacy).
        </p>
      </Card>

      <Card>
        <h3 className="font-semibold mb-2">Privacy</h3>
        <p className="text-sm text-gray-400">
          No video leaves this device. Only alert text (timestamp, confidence, tier) is sent
          externally, and only on escalation via Gmail SMTP. Recording is opt-in and off by default.
        </p>
      </Card>
    </div>
  );
}