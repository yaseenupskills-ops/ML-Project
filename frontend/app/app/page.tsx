"use client";

import { useState } from 'react';
import { IntelligenceChat } from '../../components/chat/IntelligenceChat';
import { ContextPanel } from '../../components/layout/ContextPanel';
import { MessageSquare, Map as MapIcon, LayoutDashboard } from 'lucide-react';
import { useAppStore } from '../../lib/store';

export default function WorkspacePage() {
  const [mobileTab, setMobileTab] = useState<'chat' | 'context'>('chat');
  const { activeRole } = useAppStore();

  return (
    <div className="flex flex-col md:flex-row w-full h-full bg-space-950 overflow-hidden relative">
      
      {/* Mobile Top View Switcher (< md) */}
      <div className="flex md:hidden bg-[#040c1d] border-b border-cyan-500/30 p-1.5 justify-around items-center z-20 shrink-0 shadow-lg">
        <button
          onClick={() => setMobileTab('chat')}
          className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
            mobileTab === 'chat'
              ? 'bg-cyan-500 text-space-950 shadow-md font-bold'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <MessageSquare size={14} /> AI Intelligence
        </button>
        <button
          onClick={() => setMobileTab('context')}
          className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
            mobileTab === 'context'
              ? 'bg-cyan-500 text-space-950 shadow-md font-bold'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <MapIcon size={14} /> Spatial Map & Dashboard
        </button>
      </div>

      {/* Intelligence Chat Container */}
      <div className={`w-full md:w-80 lg:w-96 xl:w-[420px] h-full flex-shrink-0 ${
        mobileTab === 'chat' ? 'flex' : 'hidden md:flex'
      }`}>
        <IntelligenceChat />
      </div>

      {/* Spatial Map & Dashboard Panel Container */}
      <div className={`flex-1 h-full relative overflow-hidden ${
        mobileTab === 'context' ? 'flex' : 'hidden md:flex'
      }`}>
        <ContextPanel />
      </div>
    </div>
  );
}
