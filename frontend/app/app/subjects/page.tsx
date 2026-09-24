'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader, DataTable, Button, Pill, Modal, Input, Select } from '@/components/ui';
import { RoleGuard } from '@/components/layout/RoleGuard';
import { getSubjects, createSubject, updateSubject } from '@/services/subjects';
import { getDevices } from '@/services/devices';
import { getUsers } from '@/services/users';
import { queryKeys } from '@/lib/constants';
import { useToast } from '@/components/ui/Toast';
import type { Subject, CreateSubjectRequest } from '@/types';

export default function SubjectsPage() {
  return (
    <RoleGuard allowedRoles={['admin']}>
      <SubjectsContent />
    </RoleGuard>
  );
}

function SubjectsContent() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  
  const { data: subjects, isLoading } = useQuery({
    queryKey: queryKeys.subjects.list(),
    queryFn: getSubjects
  });

  const { data: devices } = useQuery({
    queryKey: queryKeys.devices.list(),
    queryFn: getDevices
  });
  
  const { data: users } = useQuery({
    queryKey: queryKeys.users.list(),
    queryFn: getUsers
  });

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSubject, setEditingSubject] = useState<Subject | null>(null);

  const saveMutation = useMutation({
    mutationFn: (data: Partial<Subject> & CreateSubjectRequest) => {
      if (editingSubject) {
        return updateSubject(editingSubject.id, data);
      }
      return createSubject(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.subjects.all });
      toast('success', `Subject ${editingSubject ? 'updated' : 'created'} successfully`);
      setIsModalOpen(false);
      setEditingSubject(null);
    }
  });

  const handleOpenEdit = (subject: Subject) => {
    setEditingSubject(subject);
    setIsModalOpen(true);
  };

  const handleOpenCreate = () => {
    setEditingSubject(null);
    setIsModalOpen(true);
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    saveMutation.mutate({
      display_name: formData.get('display_name') as string,
      location: formData.get('location') as string,
      status: formData.get('status') as 'active' | 'inactive',
      device_id: formData.get('device_id') as string || undefined,
    });
  };

  const columns = ['Display Name', 'Location', 'Status', 'Caregivers', 'Device', 'Action'];
  const data = (subjects || []).map(sub => {
    const dev = devices?.find(d => d.id === sub.device_id);
    const caregiverCount = sub.assigned_caregivers?.length || 0;
    
    return [
      <span key="name" className="font-medium text-white">{sub.display_name}</span>,
      sub.location || <span key="loc" className="text-gray-500">—</span>,
      <Pill key="status" className={sub.status === 'active' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-slate-500/20 text-slate-400'}>
        {sub.status}
      </Pill>,
      <span key="cgs">{caregiverCount}</span>,
      dev?.name || <span key="dev" className="text-gray-500">—</span>,
      <Button key="btn" variant="secondary" className="px-2 py-1 text-xs" onClick={() => handleOpenEdit(sub)}>
        Edit
      </Button>
    ];
  });

  return (
    <div className="flex flex-col h-full gap-4">
      <div className="flex justify-between items-start">
        <PageHeader title="Subjects" description="Manage individuals being monitored" />
        <Button onClick={handleOpenCreate}>Add Subject</Button>
      </div>

      {isLoading ? (
        <div className="animate-pulse space-y-4">
          <div className="h-10 bg-ink-900 rounded-xl" />
          <div className="h-20 bg-ink-900 rounded-xl" />
        </div>
      ) : (
        <DataTable columns={columns} data={data} />
      )}

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editingSubject ? 'Edit Subject' : 'Add Subject'}>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-400">Display Name</label>
            <Input name="display_name" required defaultValue={editingSubject?.display_name} placeholder="e.g., John Doe" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-400">Location</label>
            <Input name="location" defaultValue={editingSubject?.location} placeholder="e.g., Unit 102" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-400">Status</label>
            <Select name="status" defaultValue={editingSubject?.status || 'active'}>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </Select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-400">Assigned Device</label>
            <Select name="device_id" defaultValue={editingSubject?.device_id || ''}>
              <option value="">-- None --</option>
              {devices?.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </Select>
          </div>
          <div className="flex justify-end gap-2 mt-4">
            <Button type="button" variant="secondary" onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving...' : 'Save'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
