import { describe, it, expect } from 'vitest';
import { createAUScale } from './scales';

describe('createAUScale', () => {
  it('0 AU maps to center of viewport', () => {
    const viewportWidth = 800;
    const scale = createAUScale(viewportWidth, 5);
    expect(scale(0)).toBe(viewportWidth / 2);
  });

  it('scale is linear', () => {
    const viewportWidth = 800;
    const scale = createAUScale(viewportWidth, 5);
    const diff1 = scale(2) - scale(1);
    const diff2 = scale(1) - scale(0);
    expect(diff1).toBeCloseTo(diff2, 5);
  });

  it('max AU fits within viewport with padding', () => {
    const viewportWidth = 800;
    const maxAU = 5;
    const padding = 50;
    const scale = createAUScale(viewportWidth, maxAU, padding);
    expect(scale(maxAU)).toBeLessThanOrEqual(viewportWidth - padding);
    expect(scale(-maxAU)).toBeGreaterThanOrEqual(padding);
  });

  it('negative AU maps correctly', () => {
    const viewportWidth = 800;
    const scale = createAUScale(viewportWidth, 5);
    expect(scale(-1)).toBeLessThan(scale(0));
  });
});
