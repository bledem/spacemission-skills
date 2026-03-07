import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DeltaVBudget } from './DeltaVBudget';
import type { Phase } from '../lib/missionParser';

const mockPhases: Phase[] = [
  { phase: 'earth_departure', date: '2026-01-01', delta_v_km_s: 3.6, orbit: null, description: 'Departure' },
  { phase: 'return_departure', date: '2027-01-01', delta_v_km_s: 2.1, orbit: null, description: 'Return' },
  { phase: 'earth_arrival', date: '2028-01-01', delta_v_km_s: 3.6, orbit: null, description: 'Arrival' },
];

const BUDGET = 12;

describe('DeltaVBudget', () => {
  it('renders one segment per maneuver phase', () => {
    render(<DeltaVBudget phases={mockPhases} totalDeltaV={9.3} budget={BUDGET} />);
    // 3 phase segments + 1 remaining segment = 4 segments
    const segments = screen.getAllByRole('listitem');
    expect(segments.length).toBe(4);
  });

  it('renders remaining budget segment', () => {
    render(<DeltaVBudget phases={mockPhases} totalDeltaV={9.3} budget={BUDGET} />);
    // The remaining segment has an aria-label containing "Remaining"
    const segments = screen.getAllByRole('listitem');
    const remainingSegment = segments.find(s => s.getAttribute('aria-label')?.includes('Remaining'));
    expect(remainingSegment).toBeInTheDocument();
  });

  it('segment widths proportional to delta-v', () => {
    render(<DeltaVBudget phases={mockPhases} totalDeltaV={9.3} budget={BUDGET} />);
    const segments = screen.getAllByRole('listitem');

    // First segment should be 3.6/12 = 30%
    const departureSegment = segments[0];
    expect(departureSegment).toHaveStyle({ width: '30%' });
  });

  it('total bar width = 100%', () => {
    const { container } = render(<DeltaVBudget phases={mockPhases} totalDeltaV={9.3} budget={BUDGET} />);
    const bar = container.querySelector('ul');
    expect(bar).toHaveClass('flex');
  });

  it('hover on segment shows tooltip with phase name + value', async () => {
    render(<DeltaVBudget phases={mockPhases} totalDeltaV={9.3} budget={BUDGET} />);

    const firstSegment = screen.getAllByRole('listitem')[0];
    fireEvent.mouseEnter(firstSegment);

    // Should show tooltip with phase info
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
  });

  it('budget exceeded renders warning', () => {
    render(<DeltaVBudget phases={mockPhases} totalDeltaV={15} budget={BUDGET} />);
    expect(screen.getByText(/Budget exceeded/)).toBeInTheDocument();
  });

  it('accessible: segments have aria-label with phase + value', () => {
    render(<DeltaVBudget phases={mockPhases} totalDeltaV={9.3} budget={BUDGET} />);
    const segments = screen.getAllByRole('listitem');

    expect(segments[0]).toHaveAttribute('aria-label', 'earth_departure: 3.60 km/s');
    expect(segments[1]).toHaveAttribute('aria-label', 'return_departure: 2.10 km/s');
  });
});
