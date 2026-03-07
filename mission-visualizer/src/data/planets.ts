export interface Planet {
  name: string;
  semiMajorAxisAU: number;
  eccentricity: number;
  orbitalPeriodDays: number;
  color: string;
  radius: number;
}

export const planets: Planet[] = [
  { name: 'Mercury', semiMajorAxisAU: 0.387, eccentricity: 0.206, orbitalPeriodDays: 88, color: '#B7B8B9', radius: 4 },
  { name: 'Venus', semiMajorAxisAU: 0.723, eccentricity: 0.007, orbitalPeriodDays: 225, color: '#FFC649', radius: 6 },
  { name: 'Earth', semiMajorAxisAU: 1.0, eccentricity: 0.017, orbitalPeriodDays: 365.25, color: '#6B93D6', radius: 6 },
  { name: 'Mars', semiMajorAxisAU: 1.524, eccentricity: 0.093, orbitalPeriodDays: 687, color: '#C1440E', radius: 5 },
  { name: 'Jupiter', semiMajorAxisAU: 5.203, eccentricity: 0.049, orbitalPeriodDays: 4333, color: '#D8CA9D', radius: 12 },
  { name: 'Saturn', semiMajorAxisAU: 9.537, eccentricity: 0.057, orbitalPeriodDays: 10759, color: '#F4D59E', radius: 10 },
  { name: 'Uranus', semiMajorAxisAU: 19.19, eccentricity: 0.046, orbitalPeriodDays: 30687, color: '#D1E7E7', radius: 8 },
  { name: 'Neptune', semiMajorAxisAU: 30.07, eccentricity: 0.011, orbitalPeriodDays: 60190, color: '#5B5DDF', radius: 8 },
];

export const sunColor = '#FDB813';
export const sunRadius = 15;
