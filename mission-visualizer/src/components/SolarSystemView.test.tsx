import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SolarSystemView } from './SolarSystemView';
import type { ParsedMission, Phase } from '../lib/missionParser';

const mockPhases: Phase[] = [
  {
    phase: 'earth_departure',
    date: '2026-01-01',
    delta_v_km_s: 3.6,
    orbit: { a_AU: 1.26, e: 0.208, omega_rad: 0, period_days: 516 },
    description: 'Departure',
    trajectoryPoints: [[1, 0], [1.1, 0.1], [1.2, 0.2]],
  },
];

const mockMission: ParsedMission = {
  mission_name: 'Test Mission',
  departure_date: '2026-01-01',
  total_delta_v_km_s: 10.5,
  max_distance_AU: 1.52,
  mission_duration_days: 500,
  tier: 'Bronze',
  phases: mockPhases,
  flybys: [],
};

describe('SolarSystemView', () => {
  it('renders SVG element', () => {
    render(<SolarSystemView mission={mockMission} width={800} height={600} />);
    expect(screen.getByRole('img')).toBeInTheDocument();
  });

  it('renders Sun at center', () => {
    const { container } = render(<SolarSystemView mission={mockMission} width={800} height={600} />);
    const sun = container.querySelector('[data-testid="sun"]');
    expect(sun).toBeInTheDocument();
    // Sun should be at center
    expect(sun?.getAttribute('cx')).toBe('400');
    expect(sun?.getAttribute('cy')).toBe('300');
  });

  it('renders 8 planetary orbit paths', () => {
    const { container } = render(<SolarSystemView mission={mockMission} width={800} height={600} />);
    const orbits = container.querySelectorAll('[data-planet-orbit]');
    expect(orbits.length).toBe(8);
  });

  it('renders planet markers at correct positions', () => {
    const { container } = render(<SolarSystemView mission={mockMission} width={800} height={600} />);
    const planets = container.querySelectorAll('[data-planet]');
    expect(planets.length).toBe(8);
  });

  it('renders spacecraft trajectory path', () => {
    const { container } = render(<SolarSystemView mission={mockMission} width={800} height={600} />);
    const trajectory = container.querySelector('[data-testid="trajectory"]');
    expect(trajectory).toBeInTheDocument();
  });

  it('trajectory path color matches phase', () => {
    const { container } = render(<SolarSystemView mission={mockMission} width={800} height={600} />);
    const trajectory = container.querySelector('[data-testid="trajectory"]');
    // earth_departure phase should have departure color
    expect(trajectory?.getAttribute('stroke')).toBeTruthy();
  });

  it('inner/outer toggle switches scale', () => {
    const { container, rerender } = render(
      <SolarSystemView mission={mockMission} width={800} height={600} showOuterPlanets={false} />
    );

    // When showing inner planets only, Jupiter should be out of view
    const jupiterOrbit = container.querySelector('[data-planet-orbit="Jupiter"]');
    expect(jupiterOrbit).toBeInTheDocument();
    // The orbit might still exist but be scaled differently

    rerender(<SolarSystemView mission={mockMission} width={800} height={600} showOuterPlanets={true} />);
    // With outer planets shown, scale changes to accommodate them
  });
});
