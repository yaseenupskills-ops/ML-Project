"use client";

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAppStore } from '../../lib/store';
import { 
  Command, 
  MessageSquare, 
  Globe, 
  Map, 
  ShieldAlert, 
  Settings 
} from 'lucide-react';

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { viewMode, setViewMode } = useAppStore();

  const navItems = [
    { id: 'command', icon: Command, label: 'Command', href: '/app' },
    { id: 'conversations', icon: MessageSquare, label: 'Chat', href: '/app/conversations' },
    { id: 'globe', icon: Globe, label: '3D Globe', href: '/app' },
    { id: 'map', icon: Map, label: 'Map', href: '/app' },
    { id: 'alerts', icon: ShieldAlert, label: 'Alerts', href: '/app/alerts' },
  ];

  return (
    <>
      {/* Desktop Sidebar (md and larger) */}
      <aside className="hidden md:flex w-16 lg:w-20 h-full border-r border-space-800 bg-[#010613] flex-col items-center py-6 flex-shrink-0 z-50">
        {/* Logo */}
        <Link href="/" className="mb-10 font-bold text-xl tracking-widest text-white hover:text-cyan-400 transition-colors">
          O.
        </Link>

        {/* Main Nav */}
        <nav className="flex flex-col gap-5 w-full items-center flex-1">
          {navItems.map((item) => {
            let isActive = pathname === item.href;
            if (item.id === 'globe') isActive = pathname === '/app' && viewMode === '3d';
            if (item.id === 'map') isActive = pathname === '/app' && viewMode === '2d';
            if (item.id === 'command') isActive = pathname === '/app' && viewMode === '3d';
            
            const Icon = item.icon;
            
            const handleClick = (e: React.MouseEvent) => {
              e.preventDefault();
              if (item.id === 'globe') {
                setViewMode('3d');
                router.push('/app');
              } else if (item.id === 'map') {
                setViewMode('2d');
                router.push('/app');
              } else {
                router.push(item.href);
              }
            };
            
            return (
              <button 
                key={item.id}
                onClick={handleClick}
                className={`relative flex items-center justify-center w-11 h-11 rounded-2xl transition-all duration-200 group cursor-pointer
                  ${isActive ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-lg shadow-cyan-950/50' : 'text-slate-400 hover:text-white hover:bg-space-900/60'}
                `}
                title={item.label}
              >
                <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
                
                {/* Active Indicator */}
                {isActive && (
                  <div className="absolute -left-3 lg:-left-5 w-1 h-6 bg-cyan-400 rounded-r-full shadow-[0_0_8px_rgba(34,211,238,0.8)]" />
                )}
                
                {/* Tooltip */}
                <div className="absolute left-16 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto bg-[#040c1d] text-white text-xs px-3 py-1.5 rounded-xl whitespace-nowrap transition-opacity z-50 shadow-2xl border border-cyan-500/30 font-medium">
                  {item.label}
                </div>
              </button>
            );
          })}
        </nav>

        {/* Settings at bottom */}
        <Link 
          href="/app/settings"
          className="text-slate-400 hover:text-cyan-300 transition-colors mt-auto group relative flex items-center justify-center w-11 h-11 rounded-2xl hover:bg-space-900/60"
          title="Settings"
        >
          <Settings size={20} strokeWidth={2} />
          <div className="absolute left-16 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto bg-[#040c1d] text-white text-xs px-3 py-1.5 rounded-xl whitespace-nowrap transition-opacity z-50 shadow-2xl border border-cyan-500/30 font-medium">
            Settings
          </div>
        </Link>
      </aside>

      {/* Mobile Bottom Navigation Bar (< md) */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-[#040c1d]/95 backdrop-blur-xl border-t border-cyan-500/30 flex items-center justify-around z-50 px-2 shadow-2xl">
        {navItems.map((item) => {
          let isActive = pathname === item.href;
          if (item.id === 'globe') isActive = pathname === '/app' && viewMode === '3d';
          if (item.id === 'map') isActive = pathname === '/app' && viewMode === '2d';
          if (item.id === 'command') isActive = pathname === '/app' && viewMode === '3d';
          
          const Icon = item.icon;
          
          const handleClick = (e: React.MouseEvent) => {
            e.preventDefault();
            if (item.id === 'globe') {
              setViewMode('3d');
              router.push('/app');
            } else if (item.id === 'map') {
              setViewMode('2d');
              router.push('/app');
            } else {
              router.push(item.href);
            }
          };
          
          return (
            <button
              key={item.id}
              onClick={handleClick}
              className={`flex flex-col items-center justify-center py-1 px-3 rounded-xl transition-all ${
                isActive ? 'text-cyan-400 font-bold' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Icon size={18} />
              <span className="text-[10px] mt-0.5">{item.label}</span>
            </button>
          );
        })}
        <Link 
          href="/app/settings"
          className="flex flex-col items-center justify-center py-1 px-3 rounded-xl text-slate-400 hover:text-slate-200"
        >
          <Settings size={18} />
          <span className="text-[10px] mt-0.5">Settings</span>
        </Link>
      </div>
    </>
  );
}
