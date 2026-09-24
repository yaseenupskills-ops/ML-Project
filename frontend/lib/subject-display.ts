export function formatSubjectName(displayName?: string | null, subjectId?: string, isMasked: boolean = false): string {
  if (isMasked && subjectId) return `Subject ···${subjectId.slice(-4)}`;
  if (displayName) return displayName;
  if (subjectId) return `Subject ···${subjectId.slice(-4)}`;
  return 'Unknown subject';
}