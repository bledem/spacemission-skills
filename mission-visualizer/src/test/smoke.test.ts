import { describe, it, expect } from 'vitest';

describe('Smoke Test', () => {
  it('verifies test infrastructure is working', () => {
    expect(true).toBe(true);
  });

  it('can import sample mission data', async () => {
    const mission = await import('../data/sampleMission.json');
    expect(mission.mission_name).toBe('Mars Hohmann Round-Trip');
    expect(mission.phases).toHaveLength(3);
  });

  it('can import flyby mission data', async () => {
    const mission = await import('../data/sampleMissionFlyby.json');
    expect(mission.mission_name).toBe('Venus Gravity Assist to Outer System');
    expect(mission.flybys).toHaveLength(1);
  });
});
