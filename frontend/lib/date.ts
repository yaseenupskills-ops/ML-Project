/**
 * Format an ISO date string to local time with timezone label.
 */
export function formatDateTimeTz(isoString: string): string {
  if (!isoString) return '';
  const date = new Date(isoString);
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    timeZoneName: 'short',
  }).format(date);
}

export function formatDateTime(isoString: string): string {
  if (!isoString) return '';
  const date = new Date(isoString);
  return new Intl.DateTimeFormat('en-US', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(date);
}

export function formatRelativeTime(isoString: string): string {
  if (!isoString) return '';
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;
  const diffS = Math.floor(diffMs / 1000);
  
  if (diffS < 60) return `${diffS} s ago`;
  const diffM = Math.floor(diffS / 60);
  if (diffM < 60) return `${diffM} min ago`;
  const diffH = Math.floor(diffM / 60);
  if (diffH < 24) return `${diffH} h ago`;
  const diffD = Math.floor(diffH / 24);
  return `${diffD} d ago`;
}

export function formatCountdown(totalSeconds: number): string {
  if (totalSeconds <= 0) return '0:00';
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

export function formatOfflineDuration(lastSeenIso: string): string {
  if (!lastSeenIso) return 'unknown';
  const diffMs = Date.now() - new Date(lastSeenIso).getTime();
  const diffM = Math.floor(diffMs / 60000);
  if (diffM < 1) return 'just now';
  if (diffM < 60) return `${diffM} min`;
  const diffH = Math.floor(diffM / 60);
  if (diffH < 24) return `${diffH} h`;
  return `${Math.floor(diffH / 24)} d`;
}