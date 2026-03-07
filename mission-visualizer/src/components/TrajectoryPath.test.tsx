import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { TrajectoryPath } from './TrajectoryPath';
import type { Phase } from '../lib/missionParser';

const mockPhases: Phase[] = [
  {
    phase: 'earth_departure',
    date: '2026-01-01',
    delta_v_km_s: 3.6,
    orbit: { a_AU: 1.26, e: 0.208, omega_rad: 0, period_days: 516 },
    description: 'Departure',
    trajectoryPoints: [[1, 0], [1.1, 0.1], [1.2, 0.2], [1.3, 0.3]],
  },
  {
    phase: 'return_departure',
    date: '2027-01-01',
    delta_v_km_s: 2.1,
    orbit: { a_AU: 1.26, e: 0.208, omega_rad: 3.14159, period_days: 516 },
    description: 'Return',
    trajectoryPoints: [[1.3, 0.3], [1.2, 0.2], [1.1, 0.1], [1, 0]],
  },
];

describe('TrajectoryPath', () => {
  it('renders spacecraft marker element', () => {
    const { container } = render(
      <TrajectoryPath
        phases={mockPhases}
        currentTime={0}
        scale={(v: number) => v * 100}
        centerX={400}
        centerY={300}
      />
    );

    const spacecraft = container.querySelector('[data-testid="spacecraft"]');
    expect(spacecraft).toBeInTheDocument();
  });

  it('at t=0, spacecraft is at departure position', () => {
    const { container } = render(
      <TrajectoryPath
        phases={mockPhases}
        currentTime={0}
        scale={(v: number) => v * 100}
        centerX={400}
        centerY={300}
      />
    );

    const spacecraft = container.querySelector('[data-testid="spacecraft"]');
    // First trajectory point is [1, 0]
    // x = centerX + scale(1) = 400 + 100 = 500
    // y = centerY - scale(0) = 300 - 0 = 300
    expect(spacecraft?.getAttribute('cx')).toBe('500');
    expect(spacecraft?.getAttribute('cy')).toBe('300');
  });

  it('at t=1, spacecraft is at arrival position', () => {
    const { container } = render(
      <TrajectoryPath
        phases={mockPhases}
        currentTime={1}
        scale={(v: number) => v * 100}
        centerX={400}
        centerY={300}
      />
    );

    const spacecraft = container.querySelector('[data-testid="spacecraft"]');
    // Last trajectory point is [1, 0]
    expect(spacecraft?.getAttribute('cx')).toBe('500');
    expect(spacecraft?.getAttribute('cy')).toBe('300');
  });

  it('trail renders behind spacecraft', () => {
    const { container } = render(
      <TrajectoryPath
        phases={mockPhases}
        currentTime={0.5}
        scale={(v: number) => v * 100}
        centerX={400}
        centerY={300}
      />
    );

    const trail = container.querySelector('[data-testid="trail"]');
    expect(trail).toBeInTheDocument();
  });

  it('trail length grows with t', () => {
    const { container, rerender } = render(
      <TrajectoryPath
        phases={mockPhases}
        currentTime={0.1}
        scale={(v: number) => v * 100}
        centerX={400}
        centerY={300}
      />
    );

    const trail1 = container.querySelector('[data-testid="trail"]');
    const d1 = trail1?.getAttribute('d') || '';

    rerender(
      <TrajectoryPath
        phases={mockPhases}
        currentTime={0.5}
        scale={(v: number) => v * 100}
        centerX={400}
        centerY={300}
      />
    );

    const trail2 = container.querySelector('[data-testid="trail"]');
    const d2 = trail2?.getAttribute('d') || '';

    // Trail at t=0.5 should have more points than at t=0.1
    // (more characters in the path 'd' attribute)
    expect(d2.length).toBeGreaterThan(d1.length);
  });
});
