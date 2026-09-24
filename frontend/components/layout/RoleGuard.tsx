'use client';

import React from 'react';
import { useStore } from '@/lib/store';
import { ForbiddenState } from '@/components/ui';
import type { UserRole } from '@/types';

interface RoleGuardProps {
  allowedRoles: UserRole[];
  children: React.ReactNode;
}

export function RoleGuard({ allowedRoles, children }: RoleGuardProps) {
  const user = useStore(state => state.user);

  if (!user || !allowedRoles.includes(user.role)) {
    return (
      <div className="h-full flex items-center justify-center">
        <ForbiddenState />
      </div>
    );
  }

  return <>{children}</>;
}