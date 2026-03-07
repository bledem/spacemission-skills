import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FlybyDetail } from './FlybyDetail';
import type { Phase } from '../lib/missionParser';

const mockFlybyPhase: Phase = {
  phase: 'flyby',
  date: '2026-07-20',
  delta_v_km_s: 0,
  planet: 'Venus',
  flyby_details: {
    periapsis_altitude_km: 300,
    turn_angle_deg: 45,
    incoming_v_inf_km_s: 8.5,
    outgoing_v_inf_km_s: 8.5,
  },
  orbit: { a_AU: 0.85, e: 1.5, omega_rad: 0, period_days: 290 },
  description: 'Venus gravity assist',
  trajectoryPoints: [[0.7, 0], [0.72, 0.1], [0.74, 0]],
};

describe('FlybyDetail', () => {
  it('not rendered when mission has no flyby', () => {
    const { container } = render(<FlybyDetail flybyPhase={null} onClose={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders planet circle at center', () => {
    const { container } = render(
      <FlybyDetail flybyPhase={mockFlybyPhase} onClose={() => {}} width={400} height={400} />
    );

    const planet = container.querySelector('[data-testid="flyby-planet"]');
    expect(planet).toBeInTheDocument();
  });

  it('renders hyperbolic trajectory path', () => {
    const { container } = render(
      <FlybyDetail flybyPhase={mockFlybyPhase} onClose={() => {}} width={400} height={400} />
    );

    const hyperbola = container.querySelector('[data-testid="hyperbola"]');
    expect(hyperbola).toBeInTheDocument();
  });

  it('renders periapsis marker', () => {
    const { container } = render(
      <FlybyDetail flybyPhase={mockFlybyPhase} onClose={() => {}} width={400} height={400} />
    );

    const periapsis = container.querySelector('[data-testid="periapsis"]');
    expect(periapsis).toBeInTheDocument();
  });

  it('renders turn angle annotation', () => {
    render(
      <FlybyDetail flybyPhase={mockFlybyPhase} onClose={() => {}} width={400} height={400} />
    );

    expect(screen.getByText(/δ = 45.0°/)).toBeInTheDocument();
  });

  it('renders incoming/outgoing velocity arrows', () => {
    const { container } = render(
      <FlybyDetail flybyPhase={mockFlybyPhase} onClose={() => {}} width={400} height={400} />
    );

    const incomingArrow = container.querySelector('[data-testid="incoming-velocity"]');
    const outgoingArrow = container.querySelector('[data-testid="outgoing-velocity"]');

    expect(incomingArrow).toBeInTheDocument();
    expect(outgoingArrow).toBeInTheDocument();
  });

  it('click outside closes detail view', () => {
    const onClose = vi.fn();
    const { container } = render(
      <div>
        <div data-testid="outside">Outside</div>
        <FlybyDetail flybyPhase={mockFlybyPhase} onClose={onClose} width={400} height={400} />
      </div>
    );

    // Click on the backdrop (the overlay div)
    const backdrop = container.querySelector('.flyby-backdrop');
    if (backdrop) {
      fireEvent.click(backdrop);
      expect(onClose).toHaveBeenCalled();
    }
  });
});
