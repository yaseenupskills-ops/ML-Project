"use client";

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore, UserRole } from '../../lib/store';
import { Shield, Lock, Mail, ArrowRight, CloudRain, Cpu, ShieldAlert, Activity, User, ChevronDown, Check, Sparkles } from 'lucide-react';

const ROLE_OPTIONS: { id: UserRole; label: string; desc: string; icon: React.ReactNode; color: string }[] = [
  { id: 'meteorologist', label: 'Meteorologist', desc: 'Regime classification, NWP bias correction & forecast comparison', icon: <CloudRain size={16} />, color: 'text-cyan-400 border-cyan-500/40 bg-cyan-500/10' },
  { id: 'disaster_manager', label: 'Disaster Management', desc: 'Heavy rainfall threshold exceedance & district alert matrix', icon: <ShieldAlert size={16} />, color: 'text-rose-400 border-rose-500/40 bg-rose-500/10' },
  { id: 'researcher', label: 'Researcher / AI Lab', desc: 'RMSE, ETS, CSI, POD, FAR, FSS verification scorecard', icon: <Cpu size={16} />, color: 'text-purple-400 border-purple-500/40 bg-purple-500/10' },
  { id: 'operational', label: 'NWP Ops Team', desc: 'SHAP feature attributions & quantile confidence bounds', icon: <Activity size={16} />, color: 'text-amber-400 border-amber-500/40 bg-amber-500/10' },
  { id: 'general', label: 'General / Agro User', desc: 'Spatial district-level rainfall intelligence explorer', icon: <User size={16} />, color: 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10' },
];

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAppStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>('meteorologist');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const activeRoleMeta = ROLE_OPTIONS.find(r => r.id === role) || ROLE_OPTIONS[0];

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (email && password) {
      login(role);
      router.push('/app');
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[#020612] relative overflow-hidden py-12 px-4">
      
      {/* Dynamic Background Glowing Layers */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/3 w-[500px] h-[500px] bg-cyan-600/15 rounded-full blur-[140px] animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/3 w-[500px] h-[500px] bg-blue-600/15 rounded-full blur-[140px] animate-pulse"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-teal-500/10 rounded-full blur-[160px]"></div>
      </div>

      <div className="z-10 w-full max-w-md flex flex-col items-center">
        
        {/* Header Branding */}
        <div className="flex flex-col items-center mb-8 text-center">
          <div className="relative mb-4">
            <div className="w-16 h-16 bg-space-950 border border-cyan-500/40 rounded-2xl flex items-center justify-center shadow-[0_0_40px_rgba(6,182,212,0.25)]">
              <CloudRain className="text-cyan-400" size={32} />
            </div>
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-teal-400 rounded-full animate-ping"></div>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-[0.2em] mb-1 font-sans">R A I N - A I</h1>
          <p className="text-slate-400 text-xs tracking-widest uppercase tech-mono flex items-center gap-1.5 justify-center">
            <Sparkles size={12} className="text-cyan-400" />
            MoES / NCMRWF MONSOON INTELLIGENCE TERMINAL
          </p>
        </div>

        {/* Form Card */}
        <div className="w-full bg-[#050c1e]/80 backdrop-blur-xl p-8 rounded-2xl border border-cyan-900/40 shadow-[0_20px_50px_rgba(0,0,0,0.8)] relative overflow-visible flex flex-col gap-6">
          
          <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan-400/80 to-transparent pointer-events-none rounded-t-2xl"></div>

          <form onSubmit={handleLogin} className="flex flex-col gap-5">
            
            {/* 1. Custom Role Dropdown Picker */}
            <div className="flex flex-col gap-2 relative z-50" ref={dropdownRef}>
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider tech-mono flex justify-between items-center">
                <span>Select User Role Persona</span>
                <span className="text-cyan-400 text-[10px] font-bold">AUTHENTICATION</span>
              </label>

              <button
                type="button"
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className={`w-full bg-space-950/90 border p-3 rounded-xl flex items-center justify-between text-left transition-all ${
                  isDropdownOpen
                    ? 'border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.3)] ring-1 ring-cyan-500'
                    : 'border-space-700 hover:border-space-600'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className={`p-2 rounded-lg border ${activeRoleMeta.color}`}>
                    {activeRoleMeta.icon}
                  </div>
                  <div className="flex flex-col min-w-0">
                    <span className="text-xs font-bold text-white tracking-wide">{activeRoleMeta.label}</span>
                    <span className="text-[10px] text-slate-400 truncate">{activeRoleMeta.desc}</span>
                  </div>
                </div>
                <ChevronDown size={16} className={`text-slate-400 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180 text-cyan-400' : ''}`} />
              </button>

              {isDropdownOpen && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-[#050c1e] border border-cyan-900/80 rounded-xl p-2 shadow-2xl z-50 flex flex-col gap-1.5 backdrop-blur-2xl max-h-64 overflow-y-auto animate-in fade-in duration-150 border-t-2 border-t-cyan-500">
                  <div className="sticky top-0 bg-[#050c1e] px-2 py-1 text-[10px] tech-mono font-bold text-slate-400 uppercase border-b border-space-800 pb-1.5 mb-0.5 z-10">
                    CHOOSE OPERATIVE ROLE
                  </div>
                  {ROLE_OPTIONS.map((r) => {
                    const isSelected = role === r.id;
                    return (
                      <button
                        key={r.id}
                        type="button"
                        onClick={() => {
                          setRole(r.id);
                          setIsDropdownOpen(false);
                        }}
                        className={`w-full p-2.5 rounded-lg border text-left flex items-center justify-between transition-all ${
                          isSelected
                            ? `${r.color} shadow-sm ring-1 ring-cyan-500/50`
                            : 'border-space-800 bg-space-950/40 text-slate-300 hover:bg-space-900 hover:text-white hover:border-space-700'
                        }`}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div className="p-1.5 rounded-md bg-space-900 border border-space-800">
                            {r.icon}
                          </div>
                          <div className="flex flex-col min-w-0">
                            <span className="text-xs font-bold text-white">{r.label}</span>
                            <span className="text-[10px] text-slate-400 truncate">{r.desc}</span>
                          </div>
                        </div>
                        {isSelected && <Check size={14} className="text-cyan-400 flex-shrink-0" />}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* 2. Operative ID / Email */}
            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider tech-mono">Operative ID / Email</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <Mail size={16} className="text-slate-500" />
                </div>
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-space-950/90 border border-space-700 text-white text-xs rounded-xl focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500 block pl-10 p-3 outline-none transition-all placeholder:text-slate-600"
                  placeholder="forecaster@ncmrwf.gov.in"
                  required
                />
              </div>
            </div>

            {/* 3. Password */}
            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider tech-mono">Security Passkey</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <Lock size={16} className="text-slate-500" />
                </div>
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-space-950/90 border border-space-700 text-white text-xs rounded-xl focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500 block pl-10 p-3 outline-none transition-all placeholder:text-slate-600"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            {/* Submit Button */}
            <button 
              type="submit"
              className="mt-2 w-full flex items-center justify-center gap-2 bg-gradient-to-r from-cyan-500 via-teal-500 to-blue-600 hover:brightness-110 text-space-950 font-bold py-3.5 px-4 rounded-xl text-xs tracking-wider transition-all shadow-[0_0_25px_rgba(6,182,212,0.4)] cursor-pointer"
            >
              AUTHENTICATE AS {activeRoleMeta.label.toUpperCase()} <ArrowRight size={16} />
            </button>
          </form>
        </div>

        <div className="mt-8 text-center">
          <p className="text-[10px] text-slate-600 uppercase tracking-widest tech-mono">
            ENCRYPTED BY MoES NCMRWF MONSOON INTELLIGENCE NETWORK
          </p>
        </div>
      </div>
    </div>
  );
}
