import { positionAtTime, planetPositionAtDate } from './orbitalMath';

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

  // Process phases and generate trajectory arc points
  const rawPhases = data.phases as Phase[];
  const departureDate = new Date(data.departure_date as string);
  const endMs = departureDate.getTime() + mission_duration_days * 86400000;

  const phaseDayOffsets = rawPhases.map((p) =>
    (new Date(p.date).getTime() - departureDate.getTime()) / 86400000
  );
  const phaseDurations = rawPhases.map((_, i) => {
    const nextDay =
      i < rawPhases.length - 1
        ? phaseDayOffsets[i + 1]
        : (endMs - departureDate.getTime()) / 86400000;
    return Math.max(0, nextDay - phaseDayOffsets[i]);
  });

  // Compute t-since-periapsis for each phase start (position-continuous across burns)
  const phaseStartTs: number[] = new Array(rawPhases.length).fill(0);
  if (rawPhases[0]?.orbit) {
    const { e, omega_rad, period_days } = rawPhases[0].orbit;
    const [ex, ey] = planetPositionAtDate('Earth', departureDate);
    const nu0 = Math.atan2(ey, ex) - omega_rad;
    const nu2 = ((nu0 % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
    const E = 2 * Math.atan2(Math.sqrt(1 - e) * Math.sin(nu2 / 2), Math.sqrt(1 + e) * Math.cos(nu2 / 2));
    const Enorm = ((E % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
    phaseStartTs[0] = ((Enorm - e * Math.sin(Enorm)) / (2 * Math.PI)) * period_days;
  }
  for (let i = 1; i < rawPhases.length; i++) {
    const prev = rawPhases[i - 1];
    const curr = rawPhases[i];
    if (!prev.orbit || !curr.orbit) { phaseStartTs[i] = 0; continue; }
    const prevEndT = phaseStartTs[i - 1] + phaseDurations[i - 1];
    if (prev.orbit.a_AU === curr.orbit.a_AU && prev.orbit.e === curr.orbit.e) {
      phaseStartTs[i] = prevEndT;
    } else {
      const [ex, ey] = positionAtTime(prev.orbit.a_AU, prev.orbit.e, prev.orbit.omega_rad, prev.orbit.period_days, prevEndT);
      const nu = Math.atan2(ey, ex) - curr.orbit.omega_rad;
      const e = curr.orbit.e;
      const nu2 = ((nu % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
      const E = 2 * Math.atan2(Math.sqrt(1 - e) * Math.sin(nu2 / 2), Math.sqrt(1 + e) * Math.cos(nu2 / 2));
      const Enorm = ((E % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
      phaseStartTs[i] = ((Enorm - e * Math.sin(Enorm)) / (2 * Math.PI)) * curr.orbit.period_days;
    }
  }

  const phases = rawPhases.map((phase, i) => {
    if (!phase.orbit || phaseDurations[i] <= 0) return { ...phase, trajectoryPoints: undefined };
    const { a_AU, e, omega_rad, period_days } = phase.orbit;
    const tStart = phaseStartTs[i];
    const tEnd = tStart + phaseDurations[i];
    const nPts = Math.max(20, Math.round(phaseDurations[i] * 2));
    const trajectoryPoints: [number, number][] = [];
    for (let k = 0; k <= nPts; k++) {
      const t = tStart + ((tEnd - tStart) * k) / nPts;
      trajectoryPoints.push(positionAtTime(a_AU, e, omega_rad, period_days, t));
    }
    return { ...phase, trajectoryPoints };
  });

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
