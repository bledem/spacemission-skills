import { sampleEllipse } from './orbitalMath';

export type PhaseType = 'earth_departure' | 'flyby' | 'return_departure' | 'earth_arrival';
export type ScoringTier = 'Bronze' | 'Silver' | 'Gold' | 'Platinum';

export interface OrbitData {
  a_AU: number;
  e: number;
  omega_rad: number;
  period_days: number;
}

export interface FlybyDetails {
  periapsis_altitude_km: number;
  turn_angle_deg: number;
  incoming_v_inf_km_s: number;
  outgoing_v_inf_km_s: number;
}

export interface Phase {
  phase: PhaseType | string;
  date: string;
  delta_v_km_s: number;
  orbit: OrbitData | null;
  description: string;
  planet?: string;
  flyby_details?: FlybyDetails;
  trajectoryPoints?: [number, number][];
}

export interface Flyby {
  planet: string;
  date: string;
  periapsis_altitude_km: number;
  turn_angle_deg: number;
  incoming_v_inf_km_s: number;
  outgoing_v_inf_km_s: number;
}

export interface MissionPlan {
  mission_name: string;
  departure_date: string;
  total_delta_v_km_s: number;
  max_distance_AU: number;
  verification: {
    mission_duration_days: number;
    delta_v_breakdown_km_s: Record<string, number>;
  };
  phases: Phase[];
  flybys: Flyby[];
}

export interface ParsedMission {
  mission_name: string;
  departure_date: string;
  total_delta_v_km_s: number;
  max_distance_AU: number;
  mission_duration_days: number;
  tier: ScoringTier;
  phases: Phase[];
  flybys: Flyby[];
}

/**
 * Determine scoring tier based on max heliocentric distance.
 */
export function getScoringTier(maxDistanceAU: number): ScoringTier {
  if (maxDistanceAU >= 6.0) return 'Platinum';
  if (maxDistanceAU >= 4.0) return 'Gold';
  if (maxDistanceAU >= 2.0) return 'Silver';
  return 'Bronze';
}

/**
 * Parse and validate a mission plan JSON.
 */
export function parseMissionPlan(json: unknown): ParsedMission {
  // Validate required fields
  if (!json || typeof json !== 'object') {
    throw new Error('Mission plan must be an object');
  }

  const data = json as Record<string, unknown>;

  if (typeof data.mission_name !== 'string') {
    throw new Error('Missing required field: mission_name');
  }
  if (typeof data.departure_date !== 'string') {
    throw new Error('Missing required field: departure_date');
  }
  if (typeof data.total_delta_v_km_s !== 'number') {
    throw new Error('Missing required field: total_delta_v_km_s');
  }
  if (typeof data.max_distance_AU !== 'number') {
    throw new Error('Missing required field: max_distance_AU');
  }
  if (!data.verification || typeof data.verification !== 'object') {
    throw new Error('Missing required field: verification');
  }
  if (!Array.isArray(data.phases)) {
    throw new Error('Missing required field: phases');
  }
  if (!Array.isArray(data.flybys)) {
    throw new Error('Missing required field: flybys');
  }

  const verification = data.verification as Record<string, unknown>;
  const mission_duration_days = typeof verification.mission_duration_days === 'number'
    ? verification.mission_duration_days
    : 0;

  // Process phases and generate trajectory points
  const phases = (data.phases as Phase[]).map(phase => ({
    ...phase,
    trajectoryPoints: phase.orbit
      ? sampleEllipse(phase.orbit.a_AU, phase.orbit.e, phase.orbit.omega_rad, 200)
      : undefined,
  }));

  return {
    mission_name: data.mission_name as string,
    departure_date: data.departure_date as string,
    total_delta_v_km_s: data.total_delta_v_km_s as number,
    max_distance_AU: data.max_distance_AU as number,
    mission_duration_days,
    tier: getScoringTier(data.max_distance_AU as number),
    phases,
    flybys: data.flybys as Flyby[],
  };
}
