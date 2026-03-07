import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useMissionData } from './useMissionData';
import sampleMission from '../data/sampleMission.json';
import sampleMissionFlyby from '../data/sampleMissionFlyby.json';

describe('useMissionData', () => {
  it('returns parsed mission data when given valid JSON', () => {
    const { result } = renderHook(() => useMissionData(sampleMission));
    expect(result.current.mission).toBeDefined();
    expect(result.current.mission?.mission_name).toBe('Mars Hohmann Round-Trip');
  });

  it('returns trajectoryPoints array for each phase with orbit', () => {
    const { result } = renderHook(() => useMissionData(sampleMission));
    const phasesWithOrbits = result.current.mission?.phases.filter(p => p.orbit);
    phasesWithOrbits?.forEach(phase => {
      expect(phase.trajectoryPoints).toBeDefined();
      expect(phase.trajectoryPoints!.length).toBeGreaterThan(0);
    });
  });

  it('returns planetPositions at departure date', () => {
    const { result } = renderHook(() => useMissionData(sampleMission));
    expect(result.current.planetPositions).toBeDefined();
    expect(result.current.planetPositions['Earth']).toBeDefined();
    expect(result.current.planetPositions['Mars']).toBeDefined();
  });

  it('loading state is false after parse', () => {
    const { result } = renderHook(() => useMissionData(sampleMission));
    expect(result.current.isLoading).toBe(false);
  });

  it('error state set on invalid input', () => {
    const { result } = renderHook(() => useMissionData({}));
    expect(result.current.error).toBeDefined();
    expect(result.current.mission).toBeNull();
  });

  it('identifies flyby missions correctly', () => {
    const { result } = renderHook(() => useMissionData(sampleMissionFlyby));
    expect(result.current.hasFlyby).toBe(true);
    expect(result.current.flybyPhases).toHaveLength(1);
  });

  it('identifies non-flyby missions correctly', () => {
    const { result } = renderHook(() => useMissionData(sampleMission));
    expect(result.current.hasFlyby).toBe(false);
    expect(result.current.flybyPhases).toHaveLength(0);
  });
});
