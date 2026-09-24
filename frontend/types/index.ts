export type UserRole = 'meteorologist' | 'disaster_manager' | 'researcher' | 'operational' | 'general';

export type WeatherRegime = 
  | 'active_monsoon' 
  | 'break_monsoon' 
  | 'monsoon_low' 
  | 'depression' 
  | 'coastal_rainfall' 
  | 'orographic_rainfall' 
  | 'western_disturbance';

export type LeadTime = 6 | 12 | 24 | 48 | 72;

export type DisclosureLevel = 1 | 2 | 3 | 4 | 5;

export type ChatMessage = {
  id: string;
  role: "user" | "rain_ai" | "orca" | "assistant";
  content: string;
  detectedLanguage?: string;
  timestamp: string;
  contextLabel?: string;
  attachments?: {
    type: "map" | "chart" | "evidence";
    id: string;
  }[];
};

export type DistrictRainfallForecast = {
  id: string;
  district: string;
  state: string;
  subdivision: string;
  lat: number;
  lon: number;
  rawNwpMm: number;
  correctedRainfallMm: number;
  predictedErrorMm: number;
  dominantRegime: WeatherRegime;
  regimeConfidence: number;
  regimeProbabilities: Record<WeatherRegime, number>;
  heavyRainProbability: number;     // P(Rain > 64.5mm)
  veryHeavyRainProbability: number; // P(Rain > 115.5mm)
  extremelyHeavyProbability: number;// P(Rain > 204.4mm)
  riskLevel: 'low' | 'moderate' | 'high' | 'very_high';
  uncertainty: {
    p10: number;
    p50: number;
    p90: number;
  };
  shapAttributions: {
    feature: string;
    impactMm: number;
    description: string;
  }[];
};

export type WeatherAlert = {
  id: string;
  type: "heavy_rain" | "cyclone" | "depression" | "flash_flood" | "thunderstorm" | "wind" | "weather" | "waves";
  severity: "low" | "moderate" | "high" | "critical";
  title: string;
  location: string;
  timestamp: string;
  description: string;
  coordinates?: [number, number];
};

export type VerificationMetrics = {
  rmse: number;       // Root Mean Square Error (mm)
  ets: number;        // Equitable Threat Score (0-1)
  csi: number;        // Critical Success Index (0-1)
  pod: number;        // Probability of Detection (0-1)
  far: number;        // False Alarm Ratio (0-1)
  fss: number;        // Fractional Skill Score (0-1)
  regimeWiseScores: {
    regime: WeatherRegime;
    nwpRmse: number;
    rainAiRmse: number;
    improvementPct: number;
  }[];
};

export type EvidenceSource = {
  id: string;
  name: string;
  category: "nwp" | "observations" | "satellite" | "geography" | "ocean";
  status: "used" | "available";
  summary: string;
};

export type AgentStep = {
  id: string;
  agent: string;
  status: "pending" | "running" | "complete";
  detail?: string;
};

export type MapLayer = "raw_nwp" | "rain_ai" | "regimes" | "heavy_rain" | "districts" | "radar" | "pfz" | "alerts";

// Backward Compatibility Aliases for Map Components
export type MarineAlert = WeatherAlert;
export type PFZZone = DistrictRainfallForecast;
export type Geofence = {
  id: string;
  name: string;
  coordinates: [number, number][];
  description: string;
  riskLevel: "restricted" | "warning";
};
export type VesselRoute = {
  id: string;
  name: string;
  path: [number, number][];
  status: "safe" | "caution" | "unsafe";
};
