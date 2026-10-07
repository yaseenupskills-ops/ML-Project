export function formatPct(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatNumber(value: number): string {
  return value.toLocaleString();
}

export function formatDt(unix: number | null): string {
  if (unix === null || unix === undefined) return '—';
  return new Date(unix * 1000).toLocaleString();
}

export function formatDate(unix: number | null): string {
  if (unix === null || unix === undefined) return '—';
  return new Date(unix * 1000).toLocaleDateString();
}

export function formatDateLocal(dateStr: string): string {
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString();
}

export function formatSeconds(sec: number): string {
  if (sec === undefined || sec === null || isNaN(sec)) return '—';
  if (sec < 60) return `${sec.toFixed(1)}s`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  if (m < 60) return `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

export function formatUptime(sec: number): string {
  if (sec === undefined || sec === null || isNaN(sec)) return '—';
  if (sec < 60) return `${Math.floor(sec)}s`;
  const m = Math.floor(sec / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ${m % 60}m`;
  return `${Math.floor(h / 24)}d ${h % 24}h`;
}

export function formatMb(mb: number): string {
  if (mb === undefined || mb === null) return '—';
  if (mb < 1) return `${(mb * 1024).toFixed(0)} KB`;
  return `${mb.toFixed(2)} MB`;
}

export function tierColor(tier: string): string {
  switch (tier) {
    case 'high':
      return 'bg-red-500/10 text-red-400 border-red-500/30';
    case 'medium':
      return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    default:
      return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
  }
}

export function statusColor(status: string): string {
  switch (status) {
    case 'pending':
      return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    case 'acknowledged':
      return 'bg-teal-500/10 text-teal-400 border-teal-500/30';
    case 'escalated':
      return 'bg-red-500/10 text-red-400 border-red-500/30';
    default:
      return 'bg-gray-500/10 text-gray-400 border-gray-500/30';
  }
}