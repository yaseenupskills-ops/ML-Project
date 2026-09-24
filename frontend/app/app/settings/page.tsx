"use client";

import { Settings, Satellite, Database, Activity } from 'lucide-react';
import { useState } from 'react';

export default function SettingsPage() {
  const [links, setLinks] = useState({
    copernicus: true,
    noaa: true,
    ais: false
  });

  return (
    <div className="flex-1 h-full flex flex-col px-12 py-10 relative z-10 bg-space-950 overflow-y-auto">
       <div className="flex items-center gap-4 text-slate-400 font-medium mb-8">
         <Settings size={24} />
         <span>SYSTEM PREFERENCES</span>
       </div>
       
       <h1 className="text-3xl font-semibold text-white tracking-wide mb-8">Configuration</h1>
       
       <div className="flex flex-col gap-8 max-w-3xl">
         
         {/* Section 1 */}
         <div className="glass-panel p-6 rounded-sm">
            <h3 className="text-white font-medium mb-6 flex items-center gap-2">
              <Satellite size={18} className="text-cyan-500" />
              SATELLITE DATA LINKS
            </h3>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-space-900 border border-space-800 rounded-sm">
                <div>
                  <div className="text-white font-medium mb-1">Copernicus Marine Service (CMEMS)</div>
                  <div className="text-slate-400 text-xs">High-resolution SST and Chlorophyll-a layers.</div>
                </div>
                <button 
                  onClick={() => setLinks(prev => ({...prev, copernicus: !prev.copernicus}))}
                  className={`w-12 h-6 rounded-full transition-colors relative ${links.copernicus ? 'bg-cyan-500' : 'bg-space-700'}`}
                >
                  <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform ${links.copernicus ? 'left-7' : 'left-1'}`}></div>
                </button>
              </div>

              <div className="flex items-center justify-between p-4 bg-space-900 border border-space-800 rounded-sm">
                <div>
                  <div className="text-white font-medium mb-1">NOAA Data Source</div>
                  <div className="text-slate-400 text-xs">Global wave models and wind vectors.</div>
                </div>
                <button 
                  onClick={() => setLinks(prev => ({...prev, noaa: !prev.noaa}))}
                  className={`w-12 h-6 rounded-full transition-colors relative ${links.noaa ? 'bg-cyan-500' : 'bg-space-700'}`}
                >
                  <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform ${links.noaa ? 'left-7' : 'left-1'}`}></div>
                </button>
              </div>
            </div>
         </div>

         {/* Section 2 */}
         <div className="glass-panel p-6 rounded-sm">
            <h3 className="text-white font-medium mb-6 flex items-center gap-2">
              <Activity size={18} className="text-teal-500" />
              LIVE TRACKING
            </h3>
            
            <div className="flex items-center justify-between p-4 bg-space-900 border border-space-800 rounded-sm">
                <div>
                  <div className="text-white font-medium mb-1">AIS Vessel Tracking (Spire)</div>
                  <div className="text-slate-400 text-xs">Real-time commercial vessel tracking. Requires premium key.</div>
                </div>
                <button 
                  onClick={() => setLinks(prev => ({...prev, ais: !prev.ais}))}
                  className={`w-12 h-6 rounded-full transition-colors relative ${links.ais ? 'bg-teal-500' : 'bg-space-700'}`}
                >
                  <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform ${links.ais ? 'left-7' : 'left-1'}`}></div>
                </button>
            </div>
         </div>

         {/* Apply */}
         <div className="flex justify-end pt-4">
           <button className="px-8 py-3 bg-white text-space-950 font-medium rounded-sm hover:bg-slate-200 transition-colors">
             SAVE CONFIGURATION
           </button>
         </div>

       </div>
    </div>
  );
}
