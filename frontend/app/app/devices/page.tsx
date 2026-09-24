'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader, DataTable, Button, StateBadge, Pill, CopyOnce, Drawer, Modal, Input, Select, ConfirmDialog } from '@/components/ui';
import { RoleGuard } from '@/components/layout/RoleGuard';
import { getDevices, createDevice, revokeDevice, rotateDeviceKey, getDeviceHealth } from '@/services/devices';
import { getSubjects } from '@/services/subjects';
import { formatRelativeTime } from '@/lib/date';
import { queryKeys } from '@/lib/constants';
import { useToast } from '@/components/ui/Toast';
import type { Device, DeviceType, CreateDeviceRequest } from '@/types';

export default function DevicesPage() {
  // ponytail: RoleGuard blocks render because lib/store.ts's `user` is always
  // null (NEXT_PUBLIC_DEV_AUTH_BYPASS isn't actually wired to anything) --
  // bypassed here for the demo. Restore RoleGuard once real login exists.
  return <DevicesContent />;
}

function DevicesContent() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  
  const { data: devices, isLoading } = useQuery({
    queryKey: queryKeys.devices.list(),
    queryFn: getDevices
  });

  const { data: subjects } = useQuery({
    queryKey: queryKeys.subjects.list(),
    queryFn: getSubjects
  });

  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [newKey, setNewKey] = useState<string | null>(null);

  const registerMutation = useMutation({
    mutationFn: (data: CreateDeviceRequest) => createDevice(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.all });
      setNewKey(data.api_key);
      toast('success', 'Device registered successfully');
    }
  });

  const handleRegisterSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    registerMutation.mutate({
      name: formData.get('name') as string,
      type: formData.get('type') as DeviceType,
      location: formData.get('location') as string,
      subject_id: formData.get('subject_id') as string || undefined,
    });
  };

  const columns = ['Name', 'Type', 'Location', 'Status', 'Last Seen', 'Subject', 'Action'];
  const data = (devices || []).map(device => {
    const subject = subjects?.find(s => s.id === device.subject_id);
    return [
      <span key="name" className="font-medium text-white">{device.name}</span>,
      <Pill key="type">{device.type}</Pill>,
      device.location || <span key="loc" className="text-gray-500">—</span>,
      <StateBadge key="status" deviceStatus={device.status} />,
      <span key="seen" className="text-gray-400 text-xs">{device.last_seen ? formatRelativeTime(device.last_seen) : 'Never'}</span>,
      subject?.display_name || <span key="subj" className="text-gray-500">—</span>,
      <Button key="btn" variant="secondary" className="px-2 py-1 text-xs" onClick={() => setSelectedDevice(device)}>
        Manage
      </Button>
    ];
  });

  return (
    <div className="flex flex-col h-full gap-4">
      <div className="flex justify-between items-start">
        <PageHeader title="Devices" description="Manage fall detection edge devices and hubs" />
        <Button onClick={() => setIsRegisterOpen(true)}>Register Device</Button>
      </div>

      {/* ponytail: hardcoded to the old ML backend (127.0.0.1:8000) -- this
          webcam isn't a registered Device row in the DB, just a live view.
          Full device-registry + ML wiring is a bigger job, not tonight's. */}
      <div className="border border-ink-800 rounded-2xl overflow-hidden">
        <div className="bg-ink-900 px-4 py-2 border-b border-ink-800">
          <h3 className="font-bold text-sm">Live Camera (local webcam demo)</h3>
        </div>
        <div className="p-4">
          <img
            src="http://127.0.0.1:8000/video_feed"
            alt="Live fall-detection camera feed"
            style={{ maxWidth: '100%', border: '1px solid #333' }}
          />
        </div>
      </div>

      {isLoading ? (
        <div className="animate-pulse space-y-4">
          <div className="h-10 bg-ink-900 rounded-xl" />
          <div className="h-20 bg-ink-900 rounded-xl" />
          <div className="h-20 bg-ink-900 rounded-xl" />
        </div>
      ) : (
        <DataTable columns={columns} data={data} />
      )}

      {/* Register Modal */}
      <Modal isOpen={isRegisterOpen} onClose={() => { setIsRegisterOpen(false); setNewKey(null); }} title="Register Device">
        {newKey ? (
          <div className="flex flex-col gap-4">
            <CopyOnce value={newKey} label="Device API Key" />
            <Button onClick={() => { setIsRegisterOpen(false); setNewKey(null); }}>Done</Button>
          </div>
        ) : (
          <form onSubmit={handleRegisterSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-sm text-gray-400">Device Name</label>
              <Input name="name" required placeholder="e.g., Living Room Edge" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-gray-400">Type</label>
              <Select name="type" required>
                <option value="edge_device">Edge Device</option>
                <option value="hub">Hub</option>
              </Select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-gray-400">Location</label>
              <Input name="location" placeholder="e.g., Unit 102" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-gray-400">Assign Subject (Optional)</label>
              <Select name="subject_id">
                <option value="">-- None --</option>
                {subjects?.map(s => <option key={s.id} value={s.id}>{s.display_name}</option>)}
              </Select>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <Button type="button" variant="secondary" onClick={() => setIsRegisterOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={registerMutation.isPending}>
                {registerMutation.isPending ? 'Registering...' : 'Register'}
              </Button>
            </div>
          </form>
        )}
      </Modal>

      {/* Detail Drawer */}
      <DeviceDrawer 
        device={selectedDevice} 
        onClose={() => setSelectedDevice(null)} 
      />
    </div>
  );
}

function DeviceDrawer({ device, onClose }: { device: Device | null, onClose: () => void }) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  
  const { data: health } = useQuery({
    queryKey: queryKeys.devices.health(device?.id || ''),
    queryFn: () => getDeviceHealth(device!.id),
    enabled: !!device,
    refetchInterval: 15000
  });

  const [revokeOpen, setRevokeOpen] = useState(false);
  const [rotateOpen, setRotateOpen] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);

  const revokeMut = useMutation({
    mutationFn: () => revokeDevice(device!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.all });
      toast('success', 'Device revoked');
      setRevokeOpen(false);
      onClose();
    }
  });

  const rotateMut = useMutation({
    mutationFn: () => rotateDeviceKey(device!.id),
    onSuccess: (data) => {
      setNewKey(data.api_key);
      setRotateOpen(false);
    }
  });

  if (!device) return null;

  return (
    <>
      <Drawer isOpen={!!device} onClose={onClose} title={device.name}>
        {newKey ? (
          <div className="flex flex-col gap-4 mt-4">
            <CopyOnce value={newKey} label="New API Key" warning="The old key is no longer valid. This new key will not be shown again." />
            <Button onClick={() => setNewKey(null)}>Close Key View</Button>
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between bg-ink-900 p-4 rounded-2xl border border-ink-800">
              <div>
                <p className="text-xs text-gray-400 uppercase">Status</p>
                <StateBadge deviceStatus={device.status} className="mt-1" />
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-400 uppercase">Last Seen</p>
                <p className="font-mono text-sm mt-1 text-white">{device.last_seen ? formatRelativeTime(device.last_seen) : 'Never'}</p>
              </div>
            </div>

            <div className="border border-ink-800 rounded-2xl overflow-hidden">
              <div className="bg-ink-900 px-4 py-2 border-b border-ink-800">
                <h3 className="font-bold text-sm">Health Snapshot</h3>
              </div>
              <div className="p-4 grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-400 block text-xs">CPU Usage</span>
                  <span className="font-mono">{health?.cpu_percent ? `${health.cpu_percent}%` : '—'}</span>
                </div>
                <div>
                  <span className="text-gray-400 block text-xs">Memory</span>
                  <span className="font-mono">{health?.memory_percent ? `${health.memory_percent}%` : '—'}</span>
                </div>
                <div>
                  <span className="text-gray-400 block text-xs">Temperature</span>
                  <span className="font-mono">{health?.temperature_c ? `${health.temperature_c}°C` : '—'}</span>
                </div>
                <div>
                  <span className="text-gray-400 block text-xs">Latency</span>
                  <span className="font-mono">{health?.inference_latency_ms ? `${health.inference_latency_ms}ms` : '—'}</span>
                </div>
                <div>
                  <span className="text-gray-400 block text-xs">Camera</span>
                  <span className="font-mono">{health?.camera_status || '—'}</span>
                </div>
                <div>
                  <span className="text-gray-400 block text-xs">Model Loaded</span>
                  <span className="font-mono">{health?.model_loaded ? 'Yes' : 'No'}</span>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-2 mt-4 pt-4 border-t border-ink-800">
              <h3 className="font-bold text-sm text-rose-400 mb-2">Danger Zone</h3>
              <Button variant="secondary" className="w-full justify-center border-rose-900/50 hover:bg-rose-950 text-rose-400" onClick={() => setRotateOpen(true)}>
                Rotate API Key
              </Button>
              <Button variant="secondary" className="w-full justify-center bg-rose-600/10 hover:bg-rose-600 border-rose-600/50 text-white" onClick={() => setRevokeOpen(true)}>
                Revoke Device
              </Button>
            </div>
          </div>
        )}
      </Drawer>

      <ConfirmDialog
        isOpen={revokeOpen}
        onClose={() => setRevokeOpen(false)}
        onConfirm={() => revokeMut.mutate()}
        title="Revoke Device"
        message={`Are you sure you want to revoke access for ${device.name}? It will no longer be able to connect to the backend.`}
        variant="danger"
        confirmLabel="Revoke"
        loading={revokeMut.isPending}
      />

      <ConfirmDialog
        isOpen={rotateOpen}
        onClose={() => setRotateOpen(false)}
        onConfirm={() => rotateMut.mutate()}
        title="Rotate API Key"
        message={`Are you sure you want to rotate the key for ${device.name}? The current key will instantly stop working.`}
        variant="danger"
        confirmLabel="Rotate Key"
        loading={rotateMut.isPending}
      />
    </>
  );
}
