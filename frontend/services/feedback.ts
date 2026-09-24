import { apiFetch } from './api';
import type { CaregiverFeedback, FeedbackRequest } from '@/types';

export async function submitFeedback(data: FeedbackRequest): Promise<CaregiverFeedback> {
  return apiFetch<CaregiverFeedback>('/caregiver-feedback', { method: 'POST', body: JSON.stringify(data) });
}