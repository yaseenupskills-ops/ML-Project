import os

frontend_dir = 'frontend'

pages = {
    'app/app/page.tsx': 'Dashboard',
    'app/app/alerts/page.tsx': 'Alerts',
    'app/app/alerts/[id]/page.tsx': 'Alert Details',
    'app/app/devices/page.tsx': 'Devices',
    'app/app/subjects/page.tsx': 'Subjects',
    'app/app/analytics/page.tsx': 'Analytics',
    'app/app/models/page.tsx': 'Models',
    'app/app/system/page.tsx': 'System',
    'app/app/settings/page.tsx': 'Settings'
}

for path, title in pages.items():
    full_path = os.path.join(frontend_dir, os.path.normpath(path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    content = f"""import React from 'react';
import {{ PageHeader, EmptyState }} from '@/components/ui';

export default function Page() {{
  return (
    <div className="flex flex-col h-full gap-4">
      <PageHeader title="{title}" description="Placeholder for {title}" />
      <EmptyState message="Not built yet" />
    </div>
  );
}}
"""
    # Wait, the path for components/ui might need relative imports because tsconfig might not have @/. Let me check if @ is configured.
    # Actually I can just use relative paths based on depth.
    depth = path.count('/') - 1
    rel = '../' * depth
    if depth == 1:
        rel = '../../'
    elif depth == 2:
        rel = '../../../'
    elif depth == 3:
        rel = '../../../../'
    
    # Or just use @/components/ui if tsconfig has it. The default next.js app has it.
    # Let me just use absolute relative path.
    
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content.replace('@/components/ui', f'{rel}components/ui'))

print("Created placeholder pages.")
