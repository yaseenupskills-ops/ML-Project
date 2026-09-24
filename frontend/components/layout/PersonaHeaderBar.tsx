import React from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore, UserRole, DisclosureLevel } from '../../lib/store';
import { CloudRain, ShieldAlert, Cpu, Activity, User, LogOut, Compass, ShieldCheck, Route as RouteIcon, Sliders, Signal, CheckCircle2 } from 'lucide-react';

const ROLE_METADATA: Record<UserRole, { label: string; icon: React.ReactNode; color: string }> = {
  meteorologist: { label: 'Meteorologist', icon: <CloudRain size={14} />, color: 'text-cyan-400 border-cyan-500/40 bg-cyan-500/10' },
  disaster_manager: { label: 'Disaster Management', icon: <ShieldAlert size={14} />, color: 'text-rose-400 border-rose-500/40 bg-rose-500/10' },
  researcher: { label: 'Researcher / AI Lab', icon: <Cpu size={14} />, color: 'text-purple-400 border-purple-500/40 bg-purple-500/10' },
  operational: { label: 'NWP Ops Team', icon: <Activity size={14} />, color: 'text-amber-400 border-amber-500/40 bg-amber-500/10' },
  general: { label: 'General / Agro User', icon: <User size={14} />, color: 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10' },
};

const DISCLOSURE_LABELS: Record<DisclosureLevel, { short: string; desc: string }> = {
  1: { short: 'L1: Simple Advice', desc: 'Direct rainfall summary & alerts' },
  2: { short: 'L2: Weather Regime', desc: 'Monsoon regime soft-classification' },
  3: { short: 'L3: Multi-NWP Signals', desc: 'Raw vs. Ensemble model consensus' },
  4: { short: 'L4: SHAP Attribution', desc: 'Explainable AI feature impacts' },
  5: { short: 'L5: Raw NWP Data', desc: 'Unfiltered model grids & gauges' },
};

export function PersonaHeaderBar() {
  const router = useRouter();
  const {
    activeRole,
    disclosureLevel,
    setDisclosureLevel,
    bandwidthMode,
    setBandwidthMode,
    setGlobeTarget,
    setRoutePath,
    showGeofence,
    setShowGeofence,
    setViewMode,
    logout
  } = useAppStore();

  const currentRoleMeta = ROLE_METADATA[activeRole] || ROLE_METADATA.meteorologist;

  return (
    <header className="w-full bg-space-950/90 backdrop-blur-md border-b border-space-800 px-4 py-2 flex flex-wrap items-center justify-between gap-3 z-30">
      
      {/* 1. Authenticated User Profile Role Badge & Log Out */}
      <div className="flex items-center gap-3">
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-bold border shadow-sm ${currentRoleMeta.color}`}>
          <User size={14} />
          <span>ROLE: <strong className="uppercase">{currentRoleMeta.label}</strong></span>
        </div>
        <button
          onClick={() => {
            logout();
            router.push('/login');
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-rose-400 border border-rose-500/30 hover:bg-rose-500/10 transition-all cursor-pointer"
          title="Sign out of current session"
        >
          <LogOut size={13} />
          <span className="hidden sm:inline">Log Out</span>
        </button>
      </div>

      {/* 2. 1-CLICK QUICK ACTION WORKFLOW BAR */}
      <div className="hidden xl:flex items-center gap-1.5 bg-[#020612]/90 border border-cyan-500/30 p-1 rounded-2xl shadow-inner">
        <span className="text-[10px] font-bold text-cyan-400 px-2 tracking-wider uppercase font-mono">1-Click Actions:</span>
        
        <button
          onClick={() => {
            setGlobeTarget({
              lat: 19.0760,
              lon: 72.8777,
              title: "Mumbai Suburban",
              severity: "warning",
              desc: "1-Click Regime Focus: Coastal Rainfall Regime (92% Conf). Raw NWP: 112.5mm -> Corrected: 84.0mm."
            });
            setViewMode('2d');
          }}
          className="flex items-center gap-1 px-2.5 py-1 bg-cyan-500/15 hover:bg-cyan-500/30 border border-cyan-500/30 text-cyan-300 rounded-xl text-[11px] font-medium transition-all"
        >
          <Compass size={12} />
          <span>Quick Regime</span>
        </button>

        <button
          onClick={() => {
            setGlobeTarget({
              lat: 11.6854,
              lon: 76.1320,
              title: "Wayanad Orographic Alert",
              severity: "critical",
              desc: "1-Click Heavy Rain Check: P(Rain > 64.5mm) = 99%. Orographic lifting along Western Ghats."
            });
          }}
          className="flex items-center gap-1 px-2.5 py-1 bg-rose-500/15 hover:bg-rose-500/30 border border-rose-500/30 text-rose-300 rounded-xl text-[11px] font-medium transition-all"
        >
          <ShieldAlert size={12} />
          <span>Heavy Rain Alert</span>
        </button>

        <button
          onClick={() => {
            setRoutePath([[18.9, 72.8], [19.0, 73.0], [19.2, 73.4]]);
            setViewMode('2d');
          }}
          className="flex items-center gap-1 px-2.5 py-1 bg-purple-500/15 hover:bg-purple-500/30 border border-purple-500/30 text-purple-300 rounded-xl text-[11px] font-medium transition-all"
        >
          <RouteIcon size={12} />
          <span>Risk Corridor</span>
        </button>

        <button
          onClick={() => setShowGeofence(!showGeofence)}
          className={`flex items-center gap-1 px-2.5 py-1 rounded-xl text-[11px] font-medium transition-all border ${
            showGeofence 
              ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' 
              : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'
          }`}
        >
          <CheckCircle2 size={12} />
          <span>Subdivisions: {showGeofence ? 'ON' : 'OFF'}</span>
        </button>
      </div>

      {/* Right Controls: Disclosure Level Slider & Low Bandwidth */}
      <div className="flex items-center gap-2 sm:gap-3 flex-wrap">

        {/* Progressive Disclosure Level Slider (1 - 5) */}
        <div className="flex items-center gap-2 bg-space-900/80 px-3 py-1.5 rounded-xl border border-space-800 shadow-sm">
          <Sliders size={13} className="text-cyan-400" />
          <div className="flex flex-col">
            <div className="flex items-center justify-between gap-2 text-[10px] text-slate-400 tech-mono">
              <span>DISCLOSURE</span>
              <span className="text-cyan-400 font-bold">{DISCLOSURE_LABELS[disclosureLevel].short}</span>
            </div>
            <input
              type="range"
              min={1}
              max={5}
              step={1}
              value={disclosureLevel}
              onChange={(e) => setDisclosureLevel(Number(e.target.value) as DisclosureLevel)}
              className="w-20 sm:w-24 h-1 accent-cyan-500 cursor-pointer bg-space-700 rounded-lg"
              title={DISCLOSURE_LABELS[disclosureLevel].desc}
            />
          </div>
        </div>

        {/* Bandwidth Mode Toggle */}
        <button
          onClick={() => setBandwidthMode(bandwidthMode === 'normal' ? 'low' : 'normal')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer shadow-sm ${
            bandwidthMode === 'low'
              ? 'bg-amber-500/20 text-amber-400 border-amber-500/50 animate-pulse'
              : 'bg-space-900/80 text-slate-400 border-space-800 hover:text-white hover:bg-space-800'
          }`}
          title="Low-Bandwidth Mode optimizes text payload for low-connectivity field areas"
        >
          <Signal size={13} />
          <span className="hidden sm:inline">{bandwidthMode === 'low' ? 'LOW-BW (FIELD)' : 'NORMAL'}</span>
        </button>

      </div>

    </header>
  );
}
