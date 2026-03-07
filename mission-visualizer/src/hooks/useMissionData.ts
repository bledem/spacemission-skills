import { useMemo } from 'react';
import { parseMissionPlan } from '../lib/missionParser';
import type { ParsedMission, Phase } from '../lib/missionParser';
import { planetPositionAtDate } from '../lib/orbitalMath';
import { planets } from '../data/planets';

interface PlanetPositions {
  [key: string]: [number, number];
}

interface UseMissionDataResult {
  mission: ParsedMission | null;
  planetPositions: PlanetPositions;
  isLoading: boolean;
  error: string | null;
  hasFlyby: boolean;
  flybyPhases: Phase[];
}

export function useMissionData(missionJson: unknown): UseMissionDataResult {
  return useMemo(() => {
    try {
      const mission = parseMissionPlan(missionJson);

      // Calculate planet positions at departure date
      const departureDate = new Date(mission.departure_date);
      const planetPositions: PlanetPositions = {};

      planets.forEach(planet => {
        planetPositions[planet.name] = planetPositionAtDate(planet.name, departureDate);
      });

      // Identify flyby phases
      const flybyPhases = mission.phases.filter(p => p.phase === 'flyby');
      const hasFlyby = flybyPhases.length > 0;

      return {
        mission,
        planetPositions,
        isLoading: false,
        error: null,
        hasFlyby,
        flybyPhases,
      };
    } catch (err) {
      return {
        mission: null,
        planetPositions: {},
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to parse mission data',
        hasFlyby: false,
        flybyPhases: [],
      };
    }
  }, [missionJson]);
}
