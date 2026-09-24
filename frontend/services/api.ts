import { MOCK_RAINFALL_FORECASTS, MOCK_ALERTS, MOCK_EVIDENCE_SOURCES } from '../data/mockData';
import { WeatherAlert, EvidenceSource } from '../types';

const API_URL = process.env.NEXT_PUBLIC_API_URL;
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export type BackendAgentStep = {
  type: 'thought' | 'status' | 'final' | 'error';
  name: string;
  content: string;
};

export const apiService = {
  getAlerts: async (): Promise<WeatherAlert[]> => {
    await delay(400);
    return MOCK_ALERTS;
  },

  getEvidence: async (): Promise<EvidenceSource[]> => {
    await delay(400);
    return MOCK_EVIDENCE_SOURCES;
  },

  getPFZ: async (): Promise<any[]> => {
    await delay(300);
    return [];
  },

  getEEZBoundaries: async (): Promise<any> => {
    await delay(200);
    return null;
  },

  getRawPFZ: async (_zone?: string): Promise<any> => {
    await delay(200);
    return null;
  },

  getGeofences: async (): Promise<any[]> => {
    await delay(200);
    return [];
  },

  getRoutes: async (): Promise<any[]> => {
    await delay(200);
    return [];
  },

  sendChatMessage: async (message: string): Promise<string> => {
    await delay(800);
    const lowerMsg = message.toLowerCase();

    if (lowerMsg.includes('regime') || lowerMsg.includes('mumbai') || lowerMsg.includes('coastal')) {
      return JSON.stringify({
        type: 'pfz_card',
        content: 'Weather Regime Classification & NWP Bias Correction complete for Mumbai Suburban / Konkan Sub-division.',
        data: {
          id: 'REGIME-KONKAN-01',
          name: 'Mumbai Suburban (Coastal Regime)',
          suitability: 92,
          safety: 84,
          sst: 112.5,
          chlorophyll: '-28.5 mm',
          lat: 19.076,
          lon: 72.877
        }
      });
    }

    if (lowerMsg.includes('heavy') || lowerMsg.includes('wayanad') || lowerMsg.includes('risk') || lowerMsg.includes('alert')) {
      return JSON.stringify({
        type: 'hazard_card',
        content: 'Extremely Heavy Rainfall Warning for Wayanad District (Kerala). Orographic lifting along Western Ghats active.',
        data: {
          status: 'EXTREMELY HEAVY RAIN RED ALERT',
          waveHeight: '142.0 mm / 24h',
          windSpeed: 'P(>64.5mm) = 99%',
          currentSpeed: 'P(>115.5mm) = 88%',
          visibility: 'P(>204.4mm) = 45%',
          advisory: 'RAIN-AI corrects raw NWP forecast from 68mm to 142mm. Landslide & flash flood warnings issued.'
        }
      });
    }

    if (lowerMsg.includes('why') || lowerMsg.includes('shap') || lowerMsg.includes('explain') || lowerMsg.includes('bias')) {
      return JSON.stringify({
        type: 'conflict_card',
        content: 'SHAP Feature Attribution analysis explaining why RAIN-AI adjusted raw NWP rainfall forecast by -28.5mm.',
        data: {
          source1: { name: 'Raw NWP Base Output (NCUM)', conclusion: '112.5 mm / 24h' },
          source2: { name: 'SHAP Corrections (Regime + Moisture + Terrain)', conclusion: '-28.5 mm (Final RAIN-AI: 84.0 mm)' }
        }
      });
    }

    return JSON.stringify({
      type: 'advisory_card',
      content: 'RAIN-AI Monsoon Intelligence Summary for NCMRWF Operational Forecast Cycle:',
      data: {
        title: 'MONSOON FORECAST POST-PROCESSING OVERVIEW',
        sstAvg: '84.0 mm (Mumbai)',
        windSpeed: 'Active Monsoon',
        activeNodes: '700+ DISTRICTS',
        imblStatus: '-42.8% RMSE',
        recommendation: 'Physics-based NWP corrected across active coastal & orographic monsoon regimes.'
      }
    });
  },

  streamChat: async (
    message: string, 
    role: string,
    lang: string,
    lat: number,
    long: number,
    onStep: (step: BackendAgentStep) => void,
    disclosureLevel?: number,
    bandwidthMode?: string
  ): Promise<string> => {
    if (!API_URL) {
      const mockSteps = [
        { name: 'PlannerAgent', content: 'Parsing spatial intent & lead time (24h)...' },
        { name: 'RegimeClassifierAgent', content: 'Classifying prevailing weather regime (Coastal Monsoon 92% Conf)...' },
        { name: 'BiasCorrectionAgent', content: 'Applying regime-aware XGBoost bias correction (-28.5mm)...' },
        { name: 'HeavyRainProbAgent', content: 'Computing isotonic calibrated heavy rain exceedance probabilities...' },
        { name: 'VerificationAgent', content: 'Verifying forecast skill against observation network (FSS = 0.76)...' }
      ];

      for (let i = 0; i < mockSteps.length; i++) {
        await delay(500);
        onStep({ type: 'status', name: mockSteps[i].name, content: mockSteps[i].content });
      }
      return apiService.sendChatMessage(message);
    }

    return apiService.sendChatMessage(message);
  },
};
