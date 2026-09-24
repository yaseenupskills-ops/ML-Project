import { apiFetch } from './api';
import type { AnalyticsSummary, AlertsOverTime, StateBreakdown, ResponseTimeHistogram, AlertsBySubject, FeedbackBreakdown, ModelVersionDistribution } from '@/types';

function buildQs(days?: number) {
  return days ? `?days=${days}` : '';
}

export async function getAnalyticsSummary(params?: { days?: number }): Promise<AnalyticsSummary> {
  return apiFetch<AnalyticsSummary>(`/analytics/summary${buildQs(params?.days)}`);
}

export async function getAlertsOverTime(params?: { days?: number }): Promise<AlertsOverTime> {
  return apiFetch<AlertsOverTime>(`/analytics/alerts-over-time${buildQs(params?.days)}`);
}

export async function getStateBreakdown(params?: { days?: number }): Promise<StateBreakdown> {
  return apiFetch<StateBreakdown>(`/analytics/state-breakdown${buildQs(params?.days)}`);
}

export async function getResponseTimeHistogram(params?: { days?: number }): Promise<ResponseTimeHistogram> {
  return apiFetch<ResponseTimeHistogram>(`/analytics/response-time-histogram${buildQs(params?.days)}`);
}

export async function getAlertsBySubject(params?: { days?: number }): Promise<AlertsBySubject> {
  return apiFetch<AlertsBySubject>(`/analytics/alerts-by-subject${buildQs(params?.days)}`);
}

export async function getFeedbackBreakdown(params?: { days?: number }): Promise<FeedbackBreakdown> {
  return apiFetch<FeedbackBreakdown>(`/analytics/feedback-breakdown${buildQs(params?.days)}`);
}

export async function getModelVersionDistribution(): Promise<ModelVersionDistribution> {
  return apiFetch<ModelVersionDistribution>('/analytics/model-version-distribution');
}