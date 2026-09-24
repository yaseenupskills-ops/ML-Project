import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useStore } from '../../lib/store';
import { UserRole } from '../../types';
import { 
  Home, 
  Bell, 
  Video, 
  Users, 
  BarChart2, 
  Box, 
  Settings, 
  Cpu, 
  Search, 
  ChevronsUpDown 
} from 'lucide-react';

export interface NavItem {
  label: string;
  href: string;
  roles: UserRole[] | 'all';
  icon: React.ElementType;
}

export const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/app', roles: 'all', icon: Home },
  { label: 'Alerts', href: '/app/alerts', roles: ['caregiver', 'admin'], icon: Bell },
  { label: 'Devices', href: '/app/devices', roles: ['admin', 'operator'], icon: Video },
  { label: 'Subjects', href: '/app/subjects', roles: ['admin'], icon: Users },
  { label: 'Analytics', href: '/app/analytics', roles: ['caregiver', 'admin', 'ml_engineer'], icon: BarChart2 },
  { label: 'Models', href: '/app/models', roles: ['admin', 'ml_engineer'], icon: Box },
  { label: 'System', href: '/app/system', roles: ['caregiver', 'admin', 'operator'], icon: Cpu },
  { label: 'Settings', href: '/app/settings', roles: 'all', icon: Settings },
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
      
      {/* Profile Section */}
      <div className="p-4 pt-6">
        <div className="flex items-center gap-3 cursor-pointer hover:bg-ink-900 p-2 rounded-xl transition-colors">
          <div className="w-10 h-10 rounded-xl bg-ink-900 border border-ink-800 flex items-center justify-center flex-shrink-0">
            <span className="text-lg font-bold text-cyan-500">
              {user?.name?.charAt(0) || 'F'}
            </span>
          </div>
          <div className="flex flex-col flex-1 overflow-hidden">
            <span className="font-semibold text-sm text-gray-200 truncate">
              {user?.name || 'User'}
            </span>
            <span className="text-xs text-gray-500 truncate">
              {user?.email || 'user@fallguard.co'}
            </span>
          </div>
          <ChevronsUpDown className="w-4 h-4 text-gray-500 flex-shrink-0" />
        </div>
      </div>

      <div className="px-4 pb-4">
        <div className="h-px bg-ink-800/50 w-full mb-4"></div>
        
        {/* Search Bar */}
        <div className="relative flex items-center bg-ink-900 border border-ink-800 rounded-lg overflow-hidden group focus-within:border-cyan-500/50 transition-colors">
          <div className="pl-3 text-gray-400">
            <Search className="w-4 h-4" />
          </div>
          <input 
            type="text" 
            placeholder="Search" 
            className="w-full bg-transparent text-sm py-2 px-2 text-gray-200 placeholder-gray-500 focus:outline-none"
          />
          <div className="pr-2">
            <div className="bg-ink-800 text-gray-400 text-[10px] font-mono px-1.5 py-0.5 rounded border border-ink-700">
              /
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 overflow-y-auto px-3 pb-4 flex flex-col gap-1 custom-scrollbar">
        {filteredNav.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/app' && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link 
              key={item.href} 
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all ${
                isActive 
                  ? 'bg-ink-800 text-white font-medium shadow-sm border border-ink-700/50' 
                  : 'text-gray-400 hover:text-gray-200 hover:bg-ink-900/50 border border-transparent font-normal'
              }`}
            >
              <Icon className={`w-5 h-5 ${isActive ? 'text-cyan-400' : 'text-gray-500'}`} />
              <span className="text-sm">{item.label}</span>
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
        const Icon = item.icon;
        return (
          <Link 
            key={item.href} 
            href={item.href}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl whitespace-nowrap text-sm ${
              isActive ? 'bg-ink-800 text-white font-medium' : 'text-gray-400'
            }`}
          >
            <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : ''}`} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
