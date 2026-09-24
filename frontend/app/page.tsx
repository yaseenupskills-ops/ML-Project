"use client";

import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, BarChart2, Cpu, Globe, Users, CloudRain, Thermometer, MapPin, Bell, Layers, Target, ShieldCheck, Box, Network, Activity, BrainCircuit, CheckCircle2 } from 'lucide-react';
import { useState } from 'react';

export default function PremiumLandingPage() {
  return (
    <div className="w-full flex flex-col overflow-x-hidden min-h-screen font-sans bg-[#010613]">
      
      {/* ================= 1. HERO SECTION ================= */}
      <section 
        className="w-full h-screen relative flex flex-col justify-center pl-12 md:pl-24 lg:pl-32"
        style={{
          backgroundImage: 'url(/Hero-bg.png)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-[#010613]/95 via-[#010613]/60 to-transparent"></div>

        <div className="relative z-10 flex flex-col max-w-2xl">
          {/* Logo Text Only */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.2, ease: "easeOut" }}
            className="mb-8"
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-mono font-semibold mb-4">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
              MoES / NCMRWF — SIH PROBLEM STATEMENT 26080
            </div>
            <h1 className="text-3xl md:text-5xl font-medium tracking-[0.3em] text-white">R A I N - A I</h1>
          </motion.div>

          {/* Catchphrase */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1.2, delay: 0.2, ease: "easeOut" }}
            className="flex flex-col gap-2 mb-8"
          >
            <div className="text-[12px] md:text-[14px] font-medium tracking-[0.6em] text-gray-300">D E T E C T .</div>
            <div className="text-[12px] md:text-[14px] font-medium tracking-[0.6em] text-gray-300">C O R R E C T .</div>
            <div className="text-[12px] md:text-[14px] font-medium tracking-[0.6em] text-gray-300">E X P L A I N .</div>
            <div className="text-[12px] md:text-[14px] font-medium tracking-[0.6em] text-cyan-400">V E R I F Y .</div>
            
            {/* Subtle glow line */}
            <div className="w-72 h-[1px] bg-gradient-to-r from-cyan-400/50 via-cyan-800/30 to-transparent mt-4 relative">
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.8)]"></div>
            </div>
          </motion.div>

          <p className="text-slate-300 text-xs md:text-sm leading-relaxed mb-8 max-w-xl">
            Regime-Aware AI Post-Processing of Numerical Weather Prediction (NWP) Monsoon Rainfall Forecasts. Learning systematic physics errors to deliver calibrated district-level rainfall intelligence.
          </p>

          {/* Explore Button */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: 0.8, ease: "easeOut" }}>
            <Link href="/app">
              <button className="flex items-center gap-4 group cursor-pointer">
                <div className="w-11 h-11 rounded-full border border-cyan-500/50 flex items-center justify-center group-hover:border-cyan-300 group-hover:bg-cyan-900/40 transition-all backdrop-blur-sm shadow-lg shadow-cyan-950/50">
                  <ArrowRight size={16} className="text-cyan-400 group-hover:text-cyan-200 transition-colors" />
                </div>
                <span className="text-[11px] font-bold tracking-[0.3em] text-gray-300 group-hover:text-white transition-colors">
                  LAUNCH &nbsp; RAIN-AI &nbsp; DASHBOARD
                </span>
              </button>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ================= 2. ABOUT RAIN-AI ================= */}
      <section className="w-full py-32 px-8 md:px-24 bg-[#010916] relative overflow-hidden">
        <div className="absolute inset-0 w-full h-full z-0">
          <img src="/turtle.png" alt="Atmosphere" className="w-full h-full object-cover object-right opacity-40 mix-blend-luminosity" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#010916] via-[#010916]/90 to-transparent"></div>
          <div className="absolute inset-0 bg-gradient-to-b from-[#010613] via-transparent to-[#010613]"></div>
        </div>

        <div className="max-w-7xl mx-auto flex flex-col lg:flex-row gap-16 items-center relative z-10">
          
          {/* Left Text */}
          <div className="lg:w-5/12">
            <h4 className="text-cyan-500 font-semibold tracking-[0.2em] text-[10px] mb-4 uppercase">ABOUT RAIN-AI</h4>
            <h2 className="text-3xl md:text-5xl font-light text-white leading-tight mb-6">
              Physics + AI.<br/>
              A Better <span className="text-cyan-400 font-normal">Forecast.</span>
            </h2>
            <p className="text-gray-400 text-sm leading-relaxed mb-10 max-w-sm">
              Physics-based NWP models simulate complex atmospheric dynamics but suffer from systematic regime-dependent errors. RAIN-AI classifies prevailing weather regimes and applies calibrated machine learning post-processing.
            </p>
            <a href="#features">
              <button className="flex items-center gap-6 px-6 py-3 border border-cyan-800 rounded-full hover:border-cyan-400 hover:bg-cyan-900/20 transition-all text-[11px] text-gray-300 tracking-wider cursor-pointer">
                Explore Core Capabilities <ArrowRight size={14} className="text-cyan-500" />
              </button>
            </a>
          </div>

          {/* Floating Glass Cards */}
          <div className="lg:w-7/12 relative min-h-[450px] md:min-h-[550px] w-full">
            
            <div className="absolute top-6 right-10 bg-[#010613]/80 backdrop-blur-md border border-cyan-800/60 py-3 px-5 rounded-xl flex items-center gap-4 shadow-xl">
              <CloudRain size={20} className="text-cyan-400" />
              <div>
                <div className="text-[9px] text-gray-400 tracking-wider font-mono">RAW NWP FORECAST</div>
                <div className="text-[12px] font-bold text-white">105.0 mm / 24h</div>
              </div>
            </div>

            <div className="absolute top-1/3 left-4 bg-[#010613]/80 backdrop-blur-md border border-emerald-500/50 py-3 px-5 rounded-xl flex items-center gap-4 shadow-xl">
              <BrainCircuit size={20} className="text-emerald-400" />
              <div>
                <div className="text-[9px] text-gray-400 tracking-wider font-mono">RAIN-AI CORRECTED</div>
                <div className="text-[12px] font-bold text-emerald-400">84.0 mm (-20% Error Corrected)</div>
              </div>
            </div>

            <div className="absolute bottom-20 right-16 bg-[#010613]/80 backdrop-blur-md border border-cyan-800/60 py-3 px-5 rounded-xl flex items-center gap-4 shadow-xl">
              <Activity size={20} className="text-teal-400" />
              <div>
                <div className="text-[9px] text-gray-400 tracking-wider font-mono">WEATHER REGIME</div>
                <div className="text-[12px] font-bold text-white">Active Monsoon (92% Conf)</div>
              </div>
            </div>

            <div className="absolute -bottom-4 left-1/4 bg-[#010613]/80 backdrop-blur-md border border-rose-500/50 py-3 px-5 rounded-xl flex items-center gap-4 shadow-xl">
              <Bell size={20} className="text-rose-400" />
              <div>
                <div className="text-[9px] text-gray-400 tracking-wider font-mono">HEAVY RAIN P(&gt;64.5mm)</div>
                <div className="text-[12px] font-bold text-rose-300">94% High Probability</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================= 3. FEATURES ================= */}
      <section id="features" className="w-full py-24 px-8 bg-[#010613]">
        <div className="max-w-7xl mx-auto">
          <h4 className="text-cyan-500 font-semibold tracking-[0.3em] text-[10px] mb-16 text-center uppercase">CORE PLATFORM CAPABILITIES</h4>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="border border-cyan-900/50 p-8 rounded-xl hover:border-cyan-600 transition-colors bg-transparent">
              <Target size={24} className="text-cyan-500 mb-6" strokeWidth={1.5} />
              <h3 className="text-[13px] font-medium text-white mb-3">Regime Classification</h3>
              <p className="text-gray-400 text-[11px] leading-relaxed">XGBoost classifier categorizes 7 distinct monsoon regimes (Active, Break, Lows, Orographic, Coastal, Western Disturbance).</p>
            </div>
            
            <div className="border border-cyan-900/50 p-8 rounded-xl hover:border-cyan-600 transition-colors bg-transparent">
              <BrainCircuit size={24} className="text-cyan-500 mb-6" strokeWidth={1.5} />
              <h3 className="text-[13px] font-medium text-white mb-3">Bias Correction</h3>
              <p className="text-gray-400 text-[11px] leading-relaxed">Regime-specific XGBoost regressors correct systematic NWP errors across lead times and complex geography.</p>
            </div>
            
            <div className="border border-cyan-900/50 p-8 rounded-xl hover:border-cyan-600 transition-colors bg-transparent">
              <BarChart2 size={24} className="text-cyan-500 mb-6" strokeWidth={1.5} />
              <h3 className="text-[13px] font-medium text-white mb-3">Heavy Rain Probability</h3>
              <p className="text-gray-400 text-[11px] leading-relaxed">Isotonic calibrated probability estimation for operational thresholds (Heavy &gt;64.5mm, Very Heavy &gt;115.5mm).</p>
            </div>
            
            <div className="border border-cyan-900/50 p-8 rounded-xl hover:border-cyan-600 transition-colors bg-transparent">
              <CheckCircle2 size={24} className="text-cyan-500 mb-6" strokeWidth={1.5} />
              <h3 className="text-[13px] font-medium text-white mb-3">Verification Suite</h3>
              <p className="text-gray-400 text-[11px] leading-relaxed">Complete meteorological verification center with RMSE, ETS, CSI, POD, FAR, and Fractional Skill Score (FSS).</p>
            </div>
          </div>
        </div>
      </section>

      {/* ================= 4. IMPACT METRICS ================= */}
      <section className="w-full py-32 px-8 md:px-24 bg-[#010916] relative overflow-hidden">
        <div className="max-w-7xl mx-auto flex flex-col lg:flex-row gap-16 items-center relative z-10">
          
          <div className="lg:w-1/2 relative z-10 pl-0 lg:pl-10">
            <h4 className="text-cyan-500 font-semibold tracking-[0.2em] text-[10px] mb-4 uppercase">MODEL BENCHMARKS</h4>
            <h2 className="text-3xl md:text-5xl font-light text-white leading-tight mb-16">
              Proven Accuracy.<br/>
              Calibrated <span className="text-cyan-400 font-normal">Skill.</span>
            </h2>
            
            <div className="grid grid-cols-2 relative">
              <div className="absolute top-1/2 left-0 right-0 h-[1px] bg-cyan-900/40"></div>
              <div className="absolute top-0 bottom-0 left-1/2 w-[1px] bg-cyan-900/40"></div>

              <div className="flex items-center gap-5 p-8 pl-0">
                <BarChart2 size={24} className="text-cyan-500" strokeWidth={1.5} />
                <div>
                  <div className="text-2xl font-normal text-white mb-1">42.8%</div>
                  <div className="text-[9px] text-gray-500 uppercase tracking-wide">RMSE Error Reduction</div>
                </div>
              </div>

              <div className="flex items-center gap-5 p-8 pr-0 pl-12">
                <Globe size={24} className="text-cyan-500" strokeWidth={1.5} />
                <div>
                  <div className="text-2xl font-normal text-white mb-1">0.76</div>
                  <div className="text-[9px] text-gray-500 uppercase tracking-wide">Fractional Skill Score</div>
                </div>
              </div>

              <div className="flex items-center gap-5 p-8 pl-0">
                <Target size={24} className="text-cyan-500" strokeWidth={1.5} />
                <div>
                  <div className="text-2xl font-normal text-white mb-1">7</div>
                  <div className="text-[9px] text-gray-500 uppercase tracking-wide">Monsoon Regimes</div>
                </div>
              </div>

              <div className="flex items-center gap-5 p-8 pr-0 pl-12">
                <Users size={24} className="text-cyan-500" strokeWidth={1.5} />
                <div>
                  <div className="text-2xl font-normal text-white mb-1">700+</div>
                  <div className="text-[9px] text-gray-500 uppercase tracking-wide">Districts Intelligence</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================= 5. FOOTER ================= */}
      <div 
        className="w-full flex flex-col relative overflow-hidden"
        style={{
          backgroundImage: 'url(/footer-bg.png)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      >
        <div className="w-full bg-[#010613]/70 backdrop-blur-sm relative z-10">
          
          <section className="w-full pt-28 pb-20 px-8 flex flex-col items-center justify-center text-center relative z-10">
            <h4 className="text-cyan-500 font-semibold tracking-[0.2em] text-[10px] mb-6 uppercase">READY FOR OPERATIONAL DEMO</h4>
            <h2 className="text-2xl md:text-4xl font-light text-white leading-tight mb-10 max-w-2xl">
              Empowering forecasters & disaster teams with <br/>
              calibrated <span className="text-cyan-400 font-normal">rainfall AI.</span>
            </h2>
            
            <Link href="/app">
              <button className="flex items-center gap-4 px-8 py-3 border border-cyan-600 rounded-full hover:bg-cyan-900/40 transition-all text-[11px] tracking-wider text-white bg-[#010613]/60 backdrop-blur-md cursor-pointer">
                Enter RAIN-AI Workspace <ArrowRight size={14} className="text-cyan-500" />
              </button>
            </Link>
          </section>

          <footer className="w-full py-8 px-12 md:px-24 flex flex-col md:flex-row justify-between items-center text-[10px] text-gray-400 relative z-10 border-t border-cyan-950">
            <div className="flex items-center gap-4 mb-6 md:mb-0">
              <div className="flex items-center gap-2 text-white font-medium text-sm tracking-widest">
                RAIN-AI
              </div>
              <span className="ml-4">© 2026 RAIN-AI. MoES / NCMRWF — SIH PS 26080.</span>
            </div>
          </footer>

        </div>
      </div>

    </div>
  );
}
