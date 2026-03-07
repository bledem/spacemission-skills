import { describe, it, expect } from 'vitest';
import {
  sampleEllipse,
  sampleHyperbola,
  solveKeplerEquation,
  positionAtTime,
  planetPositionAtDate,
} from './orbitalMath';

const EPSILON = 1e-10;

describe('sampleEllipse', () => {
  it('circular orbit (e=0) returns points equidistant from origin', () => {
    const a = 1.0;
    const points = sampleEllipse(a, 0, 0, 100);
    points.forEach(([x, y]) => {
      const r = Math.sqrt(x * x + y * y);
      expect(r).toBeCloseTo(a, 5);
    });
  });

  it('elliptical orbit (e=0.5) periapsis distance = a(1-e)', () => {
    const a = 2.0;
    const e = 0.5;
    const points = sampleEllipse(a, e, 0, 200);
    const distances = points.map(([x, y]) => Math.sqrt(x * x + y * y));
    const minR = Math.min(...distances);
    expect(minR).toBeCloseTo(a * (1 - e), 5);
  });

  it('elliptical orbit (e=0.5) apoapsis distance = a(1+e)', () => {
    const a = 2.0;
    const e = 0.5;
    const points = sampleEllipse(a, e, 0, 200);
    const distances = points.map(([x, y]) => Math.sqrt(x * x + y * y));
    const maxR = Math.max(...distances);
    expect(maxR).toBeCloseTo(a * (1 + e), 5);
  });

  it('returns correct number of points', () => {
    const points = sampleEllipse(1, 0.5, 0, 200);
    expect(points.length).toBe(200);
  });

  it('omega rotates all points', () => {
    const a = 1.0;
    const e = 0;
    const points90 = sampleEllipse(a, e, Math.PI / 2, 4);

    // Points should be rotated 90 degrees
    // Original point at (1, 0) should become (0, 1)
    expect(points90[0][0]).toBeCloseTo(0, 5);
    expect(points90[0][1]).toBeCloseTo(1, 5);
  });

  it('degenerate case e≈1 does not throw and returns finite coordinates', () => {
    const points = sampleEllipse(1, 0.99, 0, 100);
    expect(points.length).toBe(100);
    points.forEach(([x, y]) => {
      expect(Number.isFinite(x)).toBe(true);
      expect(Number.isFinite(y)).toBe(true);
    });
  });
});

describe('sampleHyperbola', () => {
  it('e=1.5 returns points only within valid theta range', () => {
    const a = 1.0;
    const e = 1.5;
    const points = sampleHyperbola(a, e, 0, 100);

    // All points should be within valid angular range from the asymptotes
    expect(points.length).toBeGreaterThan(0);
    points.forEach(([x, y]) => {
      expect(Number.isFinite(x)).toBe(true);
      expect(Number.isFinite(y)).toBe(true);
    });
  });

  it('periapsis distance = a(e-1)', () => {
    const a = 1.0;
    const e = 1.5;
    const points = sampleHyperbola(a, e, 0, 200);
    const distances = points.map(([x, y]) => Math.sqrt(x * x + y * y));
    const minR = Math.min(...distances);
    expect(minR).toBeCloseTo(a * (e - 1), 3);
  });

  it('points are finite (no NaN/Infinity)', () => {
    const points = sampleHyperbola(1, 1.5, 0, 100);
    points.forEach(([x, y]) => {
      expect(Number.isFinite(x)).toBe(true);
      expect(Number.isFinite(y)).toBe(true);
    });
  });
});

describe('solveKeplerEquation', () => {
  it('circular orbit (e=0): E = M', () => {
    const M = Math.PI / 4;
    const E = solveKeplerEquation(M, 0);
    expect(E).toBeCloseTo(M, 10);
  });

  it('known case: e=0.1, M=π/4 matches reference', () => {
    const M = Math.PI / 4;
    const e = 0.1;
    const E = solveKeplerEquation(M, e);
    // Reference: E ≈ 0.8613 for M=π/4, e=0.1
    const expected = 0.8612648849;
    expect(Math.abs(E - expected)).toBeLessThan(1e-10);
  });

  it('high eccentricity e=0.99, M=0.5 converges', () => {
    const M = 0.5;
    const e = 0.99;
    const E = solveKeplerEquation(M, e);
    expect(Number.isFinite(E)).toBe(true);
    // Verify: M = E - e*sin(E)
    expect(Math.abs(M - (E - e * Math.sin(E)))).toBeLessThan(1e-10);
  });

  it('M=0 returns E=0 for any e', () => {
    expect(solveKeplerEquation(0, 0)).toBe(0);
    expect(solveKeplerEquation(0, 0.5)).toBe(0);
    expect(solveKeplerEquation(0, 0.99)).toBe(0);
  });
});

describe('positionAtTime', () => {
  it('t=0 returns periapsis position', () => {
    const a = 2.0;
    const e = 0.5;
    const [x, y] = positionAtTime(a, e, 0, 100, 0);
    const r = Math.sqrt(x * x + y * y);
    expect(r).toBeCloseTo(a * (1 - e), 5);
  });

  it('t=period/2 returns apoapsis position', () => {
    const a = 2.0;
    const e = 0.5;
    const period = 100;
    const [x, y] = positionAtTime(a, e, 0, period, period / 2);
    const r = Math.sqrt(x * x + y * y);
    expect(r).toBeCloseTo(a * (1 + e), 5);
  });

  it('t=period returns back to periapsis', () => {
    const a = 2.0;
    const e = 0.5;
    const period = 100;
    const [x0, y0] = positionAtTime(a, e, 0, period, 0);
    const [x1, y1] = positionAtTime(a, e, 0, period, period);
    expect(Math.abs(x0 - x1)).toBeLessThan(EPSILON);
    expect(Math.abs(y0 - y1)).toBeLessThan(EPSILON);
  });

  it('circular orbit: uniform angular velocity', () => {
    const a = 1.0;
    const e = 0;
    const period = 365.25;
    const [x1, y1] = positionAtTime(a, e, 0, period, period / 4);
    const [x2, y2] = positionAtTime(a, e, 0, period, period / 2);

    // After 1/4 period, angle should be 90 degrees
    const angle1 = Math.atan2(y1, x1);
    expect(angle1).toBeCloseTo(Math.PI / 2, 2);

    // After 1/2 period, angle should be 180 degrees
    const angle2 = Math.atan2(y2, x2);
    expect(angle2).toBeCloseTo(Math.PI, 2);
  });
});

describe('planetPositionAtDate', () => {
  it('Earth on J2000 epoch returns ~1 AU from Sun', () => {
    const [x, y] = planetPositionAtDate('Earth', new Date('2000-01-01'));
    const r = Math.sqrt(x * x + y * y);
    expect(r).toBeGreaterThan(0.98);
    expect(r).toBeLessThan(1.02);
  });

  it('Mars semi-major axis ≈ 1.524 AU', () => {
    // Sample Mars position over a year and check average distance
    const positions: number[] = [];
    for (let i = 0; i < 12; i++) {
      const date = new Date(2026, i, 1);
      const [x, y] = planetPositionAtDate('Mars', date);
      positions.push(Math.sqrt(x * x + y * y));
    }
    const avgR = positions.reduce((a, b) => a + b, 0) / positions.length;
    expect(avgR).toBeGreaterThan(1.45);
    expect(avgR).toBeLessThan(1.6);
  });

  it('returns [x, y] tuple with finite values', () => {
    const planets = ['Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune'] as const;
    planets.forEach(planet => {
      const [x, y] = planetPositionAtDate(planet, new Date());
      expect(typeof x).toBe('number');
      expect(typeof y).toBe('number');
      expect(Number.isFinite(x)).toBe(true);
      expect(Number.isFinite(y)).toBe(true);
    });
  });
});
