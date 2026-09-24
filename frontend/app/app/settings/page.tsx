'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader, Tabs, Card, Input, Button, DataTable, Pill, Modal, Select, CopyOnce } from '@/components/ui';
import { useStore } from '@/lib/store';
import { changePassword } from '@/services/auth';
import { getUsers, createUser, resetPassword, assignSubjects } from '@/services/users';
import { getSubjects } from '@/services/subjects';
import { queryKeys } from '@/lib/constants';
import { useToast } from '@/components/ui/Toast';
import type { User, UserRole } from '@/types';

export default function SettingsPage() {
  const user = useStore(state => state.user);
  const setUser = useStore(state => state.setUser);
  const [activeTab, setActiveTab] = useState('profile');
  const { toast } = useToast();

  const [currentPwd, setCurrentPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [loading, setLoading] = useState(false);
  const [pwdError, setPwdError] = useState('');

  const isAdmin = user?.role === 'admin';

  const tabs = [{ label: 'Profile', value: 'profile' }];
  if (isAdmin) {
    tabs.push({ label: 'Users', value: 'users' });
    tabs.push({ label: 'Notifications', value: 'notifications' });
  }

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwdError('');
    setLoading(true);

    if (newPwd.length < 10) {
      setPwdError('Password must be at least 10 characters long');
      setLoading(false);
      return;
    }

    try {
      await changePassword({ current_password: currentPwd, new_password: newPwd });
      toast('success', 'Password updated successfully');
      setCurrentPwd('');
      setNewPwd('');
      if (user?.must_change_password) {
        setUser({ ...user, must_change_password: false });
      }
    } catch (err: any) {
      setPwdError(err.message || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full gap-6 max-w-5xl mx-auto w-full">
      <PageHeader 
        title="Settings" 
        description={user?.must_change_password ? "Please change your password to continue." : undefined} 
      />
      
      {!user?.must_change_password && (
        <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />
      )}

      {activeTab === 'profile' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="flex flex-col gap-4">
            <h3 className="text-lg font-bold">Profile Information</h3>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-gray-400">Name</label>
              <div className="text-white font-medium">{user?.name}</div>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-gray-400">Email</label>
              <div className="text-white font-medium">{user?.email}</div>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-gray-400">Role</label>
              <div className="text-white font-medium capitalize">{user?.role.replace('_', ' ')}</div>
            </div>
          </Card>

          <Card className="flex flex-col gap-4">
            <h3 className="text-lg font-bold">Change Password</h3>
            <form onSubmit={handlePasswordChange} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1">
                <label className="text-sm text-gray-300">Current Password</label>
                <Input type="password" value={currentPwd} onChange={e => setCurrentPwd(e.target.value)} required />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-sm text-gray-300">New Password</label>
                <Input type="password" value={newPwd} onChange={e => setNewPwd(e.target.value)} required placeholder="Min. 10 characters" />
              </div>
              {pwdError && <p className="text-sm text-rose-400">{pwdError}</p>}
              <Button type="submit" disabled={loading} className="mt-2 self-start">
                {loading ? 'Saving...' : 'Update Password'}
              </Button>
            </form>
          </Card>
        </div>
      )}

      {activeTab === 'users' && isAdmin && <UsersTabContent />}

      {activeTab === 'notifications' && isAdmin && (
        <Card className="max-w-2xl">
          <h3 className="text-lg font-bold mb-4">Notification Configuration</h3>
          <p className="text-gray-400 mb-4">
            Email and SMS providers are configured via backend environment variables.
          </p>
          <div className="flex flex-col gap-1 mb-4">
            <label className="text-sm text-gray-400">Escalation Timeout</label>
            <div className="text-white font-medium">300 seconds (5 minutes)</div>
          </div>
        </Card>
      )}
    </div>
  );
}

function UsersTabContent() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: users, isLoading } = useQuery({ queryKey: queryKeys.users.list(), queryFn: getUsers });
  const { data: subjects } = useQuery({ queryKey: queryKeys.subjects.list(), queryFn: getSubjects });

  const [createOpen, setCreateOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [tempPassword, setTempPassword] = useState<string | null>(null);
  const [assignedSubjects, setAssignedSubjects] = useState<string[]>([]);

  const createMut = useMutation({
    mutationFn: (data: { name: string; email: string; role: UserRole }) => createUser(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
      setTempPassword(data.temporary_password);
      toast('success', 'User created');
    }
  });

  const resetMut = useMutation({
    mutationFn: (id: string) => resetPassword(id),
    onSuccess: (data) => {
      setTempPassword(data.temporary_password);
      toast('success', 'Password reset');
    }
  });

  const assignMut = useMutation({
    mutationFn: ({ userId, subIds }: { userId: string, subIds: string[] }) => assignSubjects(userId, subIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
      toast('success', 'Subjects assigned');
      setAssignOpen(false);
    }
  });

  const handleCreate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createMut.mutate({
      name: formData.get('name') as string,
      email: formData.get('email') as string,
      role: formData.get('role') as UserRole,
    });
  };

  const handleOpenAssign = (u: User) => {
    setSelectedUser(u);
    setAssignedSubjects(u.assigned_subjects || []);
    setAssignOpen(true);
  };

  const handleSaveAssign = () => {
    if (selectedUser) {
      assignMut.mutate({ userId: selectedUser.id, subIds: assignedSubjects });
    }
  };

  const cols = ['Name', 'Email', 'Role', 'Status', 'Subjects', 'Action'];
  const data = (users || []).map(u => [
    <span key="name" className="text-white font-medium">{u.name}</span>,
    <span key="email" className="text-gray-400">{u.email}</span>,
    <Pill key="role">{u.role.replace('_', ' ')}</Pill>,
    <Pill key="status" className={(u.is_active ?? true) ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-500/20 text-slate-400'}>
      {(u.is_active ?? true) ? 'Active' : 'Inactive'}
    </Pill>,
    <span key="sub">{u.assigned_subjects?.length || 0}</span>,
    <div key="act" className="flex gap-2">
      {u.role === 'caregiver' && (
        <Button variant="secondary" className="px-2 py-1 text-xs" onClick={() => handleOpenAssign(u)}>Assign</Button>
      )}
      <Button variant="secondary" className="px-2 py-1 text-xs text-amber-500 border-amber-900/50" onClick={() => resetMut.mutate(u.id)}>
        Reset Pwd
      </Button>
    </div>
  ]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button onClick={() => setCreateOpen(true)}>Create User</Button>
      </div>

      {isLoading ? <div className="h-48 bg-ink-900 rounded-2xl animate-pulse" /> : <DataTable columns={cols} data={data} />}

      <Modal isOpen={createOpen} onClose={() => { setCreateOpen(false); setTempPassword(null); }} title="Create User">
        {tempPassword ? (
          <div className="flex flex-col gap-4">
            <CopyOnce value={tempPassword} label="Temporary Password" warning="Share this with the user. They must change it on first login." />
            <Button onClick={() => { setCreateOpen(false); setTempPassword(null); }}>Done</Button>
          </div>
        ) : (
          <form onSubmit={handleCreate} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-sm text-gray-400">Name</label>
              <Input name="name" required />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-gray-400">Email</label>
              <Input name="email" type="email" required />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-gray-400">Role</label>
              <Select name="role">
                <option value="caregiver">Caregiver</option>
                <option value="admin">Admin</option>
                <option value="operator">Operator</option>
                <option value="ml_engineer">ML Engineer</option>
              </Select>
            </div>
            <div className="flex justify-end gap-2 mt-2">
              <Button type="button" variant="secondary" onClick={() => setCreateOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={createMut.isPending}>
                {createMut.isPending ? 'Creating...' : 'Create'}
              </Button>
            </div>
          </form>
        )}
      </Modal>

      <Modal isOpen={tempPassword !== null && !createOpen} onClose={() => setTempPassword(null)} title="Password Reset">
        <div className="flex flex-col gap-4">
          <CopyOnce value={tempPassword || ''} label="New Temporary Password" warning="Share this with the user." />
          <Button onClick={() => setTempPassword(null)}>Done</Button>
        </div>
      </Modal>

      <Modal isOpen={assignOpen} onClose={() => setAssignOpen(false)} title={`Assign Subjects to ${selectedUser?.name}`}>
        <div className="flex flex-col gap-3 max-h-[60vh] overflow-y-auto pr-2">
          {subjects?.map(s => (
            <label key={s.id} className="flex items-center gap-3 p-3 bg-ink-900 border border-ink-800 rounded-xl cursor-pointer hover:bg-ink-800">
              <input 
                type="checkbox" 
                className="w-4 h-4 text-cyan-500 bg-ink-950 border-ink-700 rounded"
                checked={assignedSubjects.includes(s.id)}
                onChange={(e) => {
                  if (e.target.checked) setAssignedSubjects(prev => [...prev, s.id]);
                  else setAssignedSubjects(prev => prev.filter(id => id !== s.id));
                }}
              />
              <div className="flex flex-col">
                <span className="text-white font-medium">{s.display_name}</span>
                {s.location && <span className="text-xs text-gray-400">{s.location}</span>}
              </div>
            </label>
          ))}
          {(!subjects || subjects.length === 0) && <p className="text-gray-400">No subjects found.</p>}
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <Button variant="secondary" onClick={() => setAssignOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveAssign} disabled={assignMut.isPending}>
            {assignMut.isPending ? 'Saving...' : 'Save Assignments'}
          </Button>
        </div>
      </Modal>
    </div>
  );
}