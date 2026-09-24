import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useStore } from '../../lib/store';
import { UserRole } from '../../types';
import { APP_NAME } from '../../lib/constants';

interface NavItem {
  label: string;
  href: string;
  roles: UserRole[] | 'all';
}

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/app', roles: 'all' },
  { label: 'Alerts', href: '/app/alerts', roles: ['caregiver', 'admin'] },
  { label: 'Devices', href: '/app/devices', roles: ['admin', 'operator'] },
  { label: 'Subjects', href: '/app/subjects', roles: ['admin'] },
  { label: 'Analytics', href: '/app/analytics', roles: ['caregiver', 'admin', 'ml_engineer'] },
  { label: 'Models', href: '/app/models', roles: ['admin', 'ml_engineer'] },
  { label: 'System', href: '/app/system', roles: ['caregiver', 'admin', 'operator'] },
  { label: 'Settings', href: '/app/settings', roles: 'all' },
];

export function Sidebar() {
  const pathname = usePathname();
  const user = useStore(state => state.user);

  const filteredNav = navItems.filter(item => {
    if (item.roles === 'all') return true;
    if (!user) return false;
    return item.roles.includes(user.role);
  });

  return (
    <aside className="w-64 flex-shrink-0 border-r border-ink-800 bg-ink-950 flex flex-col h-screen hidden md:flex">
      <div className="h-16 flex items-center px-6 border-b border-ink-800">
        <div className="font-bold text-xl flex items-center gap-2">
          <span className="text-cyan-500 font-mono">F.</span>
          <span>{APP_NAME}</span>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto py-4 px-3 flex flex-col gap-1">
        {filteredNav.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/app' && pathname.startsWith(item.href));
          return (
            <Link 
              key={item.href} 
              href={item.href}
              className={`px-3 py-2 rounded-xl transition-colors ${
                isActive ? 'bg-ink-800 text-white font-medium' : 'text-gray-400 hover:text-white hover:bg-ink-900/50'
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export function MobileBar() {
  const pathname = usePathname();
  const user = useStore(state => state.user);

  const filteredNav = navItems.filter(item => {
    if (item.roles === 'all') return true;
    if (!user) return false;
    return item.roles.includes(user.role);
  });

  return (
    <nav className="md:hidden flex overflow-x-auto border-t border-ink-800 bg-ink-950 p-2 gap-2 fixed bottom-0 w-full z-50">
      {filteredNav.map((item) => {
        const isActive = pathname === item.href || (item.href !== '/app' && pathname.startsWith(item.href));
        return (
          <Link 
            key={item.href} 
            href={item.href}
            className={`px-4 py-2 rounded-xl whitespace-nowrap text-sm ${
              isActive ? 'bg-ink-800 text-white font-medium' : 'text-gray-400'
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
