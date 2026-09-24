import { apiFetch } from './api';
import type { Device, CreateDeviceRequest, CreateDeviceResponse, DeviceHealth, DeviceHealthHistory, Camera, RotateKeyResponse } from '@/types';

export async function getDevices(): Promise<Device[]> {
  return apiFetch<Device[]>('/devices');
}

export async function getDevice(id: string): Promise<Device> {
  return apiFetch<Device>(`/devices/${id}`);
}

export async function createDevice(data: CreateDeviceRequest): Promise<CreateDeviceResponse> {
  return apiFetch<CreateDeviceResponse>('/devices', { method: 'POST', body: JSON.stringify(data) });
}

export async function updateDevice(id: string, data: Partial<Device>): Promise<Device> {
  return apiFetch<Device>(`/devices/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
}

export async function getDeviceHealth(id: string, hours?: number): Promise<DeviceHealth> {
  const qs = hours ? `?hours=${hours}` : '';
  return apiFetch<DeviceHealth>(`/devices/${id}/health${qs}`);
}

export async function getDeviceHealthHistory(id: string, hours?: number): Promise<DeviceHealthHistory> {
  const qs = hours ? `?hours=${hours}` : '';
  return apiFetch<DeviceHealthHistory>(`/devices/${id}/health-history${qs}`);
}

export async function rotateDeviceKey(id: string): Promise<RotateKeyResponse> {
  return apiFetch<RotateKeyResponse>(`/devices/${id}/rotate-key`, { method: 'POST' });
}

export async function revokeDevice(id: string): Promise<void> {
  await apiFetch<void>(`/devices/${id}/revoke`, { method: 'POST' });
}

export async function addCamera(deviceId: string, data: { name: string }): Promise<Camera> {
  return apiFetch<Camera>(`/devices/${deviceId}/cameras`, { method: 'POST', body: JSON.stringify(data) });
}

export async function updateCamera(cameraId: string, data: Partial<Camera>): Promise<Camera> {
  return apiFetch<Camera>(`/cameras/${cameraId}`, { method: 'PATCH', body: JSON.stringify(data) });
}