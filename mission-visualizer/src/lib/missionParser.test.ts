import { describe, it, expect } from 'vitest';
import { parseMissionPlan, getScoringTier } from './missionParser';
import sampleMission from '../data/sampleMission.json';
import sampleMissionFlyby from '../data/sampleMissionFlyby.json';

describe('parseMissionPlan', () => {
  it('parses sample Hohmann mission — extracts all phases', () => {
    const result = parseMissionPlan(sampleMission);
    expect(result.phases).toHaveLength(3);
    expect(result.phases[0].phase).toBe('earth_departure');
    expect(result.phases[1].phase).toBe('return_departure');
    expect(result.phases[2].phase).toBe('earth_arrival');
  });

  it('parses flyby mission — identifies flyby phase', () => {
    const result = parseMissionPlan(sampleMissionFlyby);
    const flybyPhase = result.phases.find(p => p.phase === 'flyby');
    expect(flybyPhase).toBeDefined();
    expect(flybyPhase?.planet).toBe('Venus');
  });

  it('computes total delta-v from verification breakdown', () => {
    const result = parseMissionPlan(sampleMission);
    const breakdown = (sampleMission as typeof sampleMission & { verification: { delta_v_breakdown_km_s: Record<string, number> } }).verification.delta_v_breakdown_km_s;
    const sumFromBreakdown = Object.values(breakdown).reduce((sum, v) => sum + v, 0);
    expect(sumFromBreakdown).toBeCloseTo(result.total_delta_v_km_s, 1);
  });

  it('computes mission duration in days', () => {
    const result = parseMissionPlan(sampleMission);
    expect(result.mission_duration_days).toBe(970);
  });

  it('determines scoring tier from max_distance_AU', () => {
    const bronze = parseMissionPlan({ ...sampleMission, max_distance_AU: 1.8 });
    expect(bronze.tier).toBe('Bronze');

    const silver = parseMissionPlan({ ...sampleMission, max_distance_AU: 3.0 });
    expect(silver.tier).toBe('Silver');

    const gold = parseMissionPlan({ ...sampleMission, max_distance_AU: 5.0 });
    expect(gold.tier).toBe('Gold');

    const platinum = parseMissionPlan({ ...sampleMission, max_distance_AU: 7.0 });
    expect(platinum.tier).toBe('Platinum');
  });

  it('rejects invalid JSON (missing required fields)', () => {
    expect(() => parseMissionPlan({})).toThrow();
    expect(() => parseMissionPlan({ mission_name: 'Test' })).toThrow();
  });

  it('handles mission with zero flyby phases', () => {
    const result = parseMissionPlan(sampleMission);
    expect(result.flybys).toHaveLength(0);
  });
});

describe('getScoringTier', () => {
  it('returns Bronze for distance < 2 AU', () => {
    expect(getScoringTier(1.5)).toBe('Bronze');
    expect(getScoringTier(1.99)).toBe('Bronze');
  });

  it('returns Silver for distance 2-4 AU', () => {
    expect(getScoringTier(2.0)).toBe('Silver');
    expect(getScoringTier(3.5)).toBe('Silver');
    expect(getScoringTier(3.99)).toBe('Silver');
  });

  it('returns Gold for distance 4-6 AU', () => {
    expect(getScoringTier(4.0)).toBe('Gold');
    expect(getScoringTier(5.5)).toBe('Gold');
    expect(getScoringTier(5.99)).toBe('Gold');
  });

  it('returns Platinum for distance >= 6 AU', () => {
    expect(getScoringTier(6.0)).toBe('Platinum');
    expect(getScoringTier(10.0)).toBe('Platinum');
  });
});
