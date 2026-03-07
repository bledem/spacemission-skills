import { planets } from '../data/planets';

/**
 * Sample points along an elliptical orbit.
 * Uses polar form: r = a(1-e²) / (1 + e·cos(θ))
 */
export function sampleEllipse(
  a: number,
  e: number,
  omega: number,
  nPoints: number = 200
): [number, number][] {
  const points: [number, number][] = [];

  for (let i = 0; i < nPoints; i++) {
    const theta = (2 * Math.PI * i) / nPoints;
    const r = (a * (1 - e * e)) / (1 + e * Math.cos(theta));
    const x = r * Math.cos(theta + omega);
    const y = r * Math.sin(theta + omega);
    points.push([x, y]);
  }

  return points;
}

/**
 * Sample points along a hyperbolic trajectory.
 * Valid for θ where |θ| < arccos(-1/e)
 */
export function sampleHyperbola(
  a: number,
  e: number,
  omega: number,
  nPoints: number = 200
): [number, number][] {
  const points: [number, number][] = [];

  // Maximum valid true anomaly
  const maxTheta = Math.acos(-1 / e);
  // Sample within the valid range, leaving some margin
  const margin = 0.05;
  const thetaMin = -maxTheta + margin;
  const thetaMax = maxTheta - margin;

  for (let i = 0; i < nPoints; i++) {
    const theta = thetaMin + ((thetaMax - thetaMin) * i) / (nPoints - 1);
    const r = (a * (e * e - 1)) / (1 + e * Math.cos(theta));
    const x = r * Math.cos(theta + omega);
    const y = r * Math.sin(theta + omega);
    points.push([x, y]);
  }

  return points;
}

/**
 * Solve Kepler's equation M = E - e·sin(E) for E using Newton-Raphson.
 */
export function solveKeplerEquation(M: number, e: number, tolerance: number = 1e-12): number {
  // Initial guess
  let E = M;

  for (let i = 0; i < 100; i++) {
    const f = E - e * Math.sin(E) - M;
    const fPrime = 1 - e * Math.cos(E);
    const delta = f / fPrime;
    E = E - delta;

    if (Math.abs(delta) < tolerance) {
      break;
    }
  }

  return E;
}

/**
 * Get position (x, y) in orbital plane at time t.
 * t is time since periapsis passage.
 */
export function positionAtTime(
  a: number,
  e: number,
  omega: number,
  period: number,
  t: number
): [number, number] {
  // Mean anomaly
  const n = (2 * Math.PI) / period; // Mean motion
  const M = n * t;

  // Eccentric anomaly
  const E = solveKeplerEquation(M, e);

  // True anomaly
  const cosNu = (Math.cos(E) - e) / (1 - e * Math.cos(E));
  const sinNu = (Math.sqrt(1 - e * e) * Math.sin(E)) / (1 - e * Math.cos(E));
  const nu = Math.atan2(sinNu, cosNu);

  // Radius
  const r = a * (1 - e * e) / (1 + e * Math.cos(nu));

  // Position in orbital plane, rotated by argument of periapsis
  const x = r * Math.cos(nu + omega);
  const y = r * Math.sin(nu + omega);

  return [x, y];
}

// J2000 epoch reference date
const J2000 = new Date('2000-01-01T12:00:00Z').getTime();
const MS_PER_DAY = 86400000;

// Simplified mean element ephemeris for planets
// These are approximate values good enough for visualization
const planetEphemeris: Record<string, { meanAnomalyJ2000: number; meanMotion: number }> = {
  Mercury: { meanAnomalyJ2000: 174.796, meanMotion: 4.092334 },
  Venus: { meanAnomalyJ2000: 50.115, meanMotion: 1.602130 },
  Earth: { meanAnomalyJ2000: 357.529, meanMotion: 0.985600 },
  Mars: { meanAnomalyJ2000: 19.373, meanMotion: 0.524039 },
  Jupiter: { meanAnomalyJ2000: 20.020, meanMotion: 0.083085 },
  Saturn: { meanAnomalyJ2000: 317.020, meanMotion: 0.033444 },
  Uranus: { meanAnomalyJ2000: 142.238, meanMotion: 0.011728 },
  Neptune: { meanAnomalyJ2000: 256.228, meanMotion: 0.005981 },
};

/**
 * Get planet position (x, y) in AU at a given date.
 * Uses simplified mean-element ephemeris.
 */
export function planetPositionAtDate(planetName: string, date: Date): [number, number] {
  const planet = planets.find(p => p.name === planetName);
  if (!planet) {
    throw new Error(`Unknown planet: ${planetName}`);
  }

  const ephemeris = planetEphemeris[planetName];
  if (!ephemeris) {
    throw new Error(`No ephemeris data for planet: ${planetName}`);
  }

  // Days since J2000
  const daysSinceJ2000 = (date.getTime() - J2000) / MS_PER_DAY;

  // Mean anomaly at date (in radians)
  const M = ((ephemeris.meanAnomalyJ2000 + ephemeris.meanMotion * daysSinceJ2000) % 360) * Math.PI / 180;

  // Solve Kepler's equation for eccentric anomaly
  const E = solveKeplerEquation(M, planet.eccentricity);

  // True anomaly
  const e = planet.eccentricity;
  const cosNu = (Math.cos(E) - e) / (1 - e * Math.cos(E));
  const sinNu = (Math.sqrt(1 - e * e) * Math.sin(E)) / (1 - e * Math.cos(E));
  const nu = Math.atan2(sinNu, cosNu);

  // Radius
  const r = planet.semiMajorAxisAU * (1 - e * e) / (1 + e * Math.cos(nu));

  // Position (assuming omega = 0 for simplicity in this visualization)
  const x = r * Math.cos(nu);
  const y = r * Math.sin(nu);

  return [x, y];
}
