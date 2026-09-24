import React from 'react';
import { PageHeader, EmptyState } from '../../../../components/ui';

export default function Page() {
  return (
    <div className="flex flex-col h-full gap-4">
      <PageHeader title="Alert Details" description="Placeholder for Alert Details" />
      <EmptyState message="Not built yet" />
    </div>
  );
}
