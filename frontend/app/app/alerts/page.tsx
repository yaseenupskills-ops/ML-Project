"use client";

import { ShieldAlert, AlertTriangle, Info, Bell } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '../../../lib/store';
import { useEffect, useState } from 'react';
import { apiService } from '../../../services/api';
import { MarineAlert } from '../../../types';

// This app's alert-card severities are critical/warning/info; the backend's
// Alert.severity is critical/high/moderate/low (docs/MIGRATION_TRACKER.md
// Contract Parity Gate). Mapped here at the display boundary.
function toCardSeverity(severity: MarineAlert['severity']): 'critical' | 'warning' | 'info' {
  if (severity === 'critical') return 'critical';
  if (severity === 'high' || severity === 'moderate') return 'warning';
  return 'info';
}

export default function AlertsPage() {
  const router = useRouter();
  const { setGlobeTarget } = useAppStore();
  const [alerts, setAlerts] = useState<MarineAlert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiService.getAlerts()
      .then(setAlerts)
      .finally(() => setLoading(false));
  }, []);

  const handleViewOnMap = (alert: MarineAlert) => {
    if (!alert.coordinates) return;
    const [lat, lon] = alert.coordinates;
    setGlobeTarget({
      lat,
      lon,
      title: alert.title,
      severity: toCardSeverity(alert.severity),
      desc: alert.description
    });
    router.push('/app');
  };

  return (
    <div className="flex-1 h-full flex flex-col px-12 py-10 relative z-10 bg-space-950 overflow-y-auto">
       <div className="flex items-center gap-4 text-rose-500 font-medium mb-8">
         <ShieldAlert size={24} />
         <span>SYSTEM ALERTS</span>
       </div>
       
       <h1 className="text-3xl font-semibold text-white tracking-wide mb-8">Active Hazards & Warnings</h1>
       
       {loading && <p className="text-slate-500 text-sm">Loading alerts...</p>}

       <div className="flex flex-col gap-4 max-w-4xl">
         {alerts.map((alert) => {
           const cardSeverity = toCardSeverity(alert.severity);
           return (
           <div key={alert.id} className="glass-panel p-6 rounded-sm border-l-4 border-l-transparent" style={{ borderLeftColor: cardSeverity === 'critical' ? '#f43f5e' : cardSeverity === 'warning' ? '#f59e0b' : '#3b82f6' }}>
             <div className="flex items-start gap-4">

               <div className="mt-1">
                 {cardSeverity === 'critical' && <AlertTriangle size={24} className="text-rose-500" />}
                 {cardSeverity === 'warning' && <AlertTriangle size={24} className="text-amber-500" />}
                 {cardSeverity === 'info' && <Info size={24} className="text-blue-500" />}
               </div>

               <div className="flex-1">
                 <div className="flex items-center justify-between mb-2">
                   <h3 className="text-white font-medium text-lg">{alert.title}</h3>
                   <span className="tech-mono text-xs text-slate-500 flex items-center gap-2">
                     <Bell size={12} /> {new Date(alert.timestamp).toLocaleString()}
                   </span>
                 </div>
                 <p className="text-slate-400 text-sm leading-relaxed">{alert.description}</p>

                 <div className="mt-4 flex gap-3">
                   {alert.coordinates && (
                     <button
                       onClick={() => handleViewOnMap(alert)}
                       className="px-4 py-2 bg-space-800 text-white text-xs font-medium rounded-sm hover:bg-space-700 transition-colors"
                     >
                       VIEW ON MAP
                     </button>
                   )}
                   <button
                     onClick={() => setAlerts(prev => prev.filter(a => a.id !== alert.id))}
                     className="px-4 py-2 border border-space-700 text-slate-300 text-xs font-medium rounded-sm hover:bg-space-800 transition-colors"
                   >
                     DISMISS
                   </button>
                 </div>
               </div>

             </div>
           </div>
           );
         })}
       </div>
    </div>
  );
}
