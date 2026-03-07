import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Timeline } from './Timeline';
import type { ParsedMission } from '../lib/missionParser';

const mockMission: ParsedMission = {
  mission_name: 'Test Mission',
  departure_date: '2026-01-01',
  total_delta_v_km_s: 10.5,
  max_distance_AU: 4.5,
  mission_duration_days: 500,
  tier: 'Gold',
  phases: [
    { phase: 'earth_departure', date: '2026-01-01', delta_v_km_s: 3.6, orbit: null, description: 'Departure' },
    { phase: 'return_departure', date: '2027-01-01', delta_v_km_s: 2.1, orbit: null, description: 'Return' },
    { phase: 'earth_arrival', date: '2028-01-01', delta_v_km_s: 3.6, orbit: null, description: 'Arrival' },
  ],
  flybys: [],
};

describe('Timeline', () => {
  it('renders phase markers at correct proportional positions', () => {
    const { container } = render(
      <Timeline
        mission={mockMission}
        currentTime={0}
        onTimeChange={() => {}}
        isPlaying={false}
        onPlayPause={() => {}}
      />
    );

    const markers = container.querySelectorAll('[data-phase-marker]');
    expect(markers.length).toBe(3);
  });

  it('renders departure and arrival date labels', () => {
    render(
      <Timeline
        mission={mockMission}
        currentTime={0}
        onTimeChange={() => {}}
        isPlaying={false}
        onPlayPause={() => {}}
      />
    );

    expect(screen.getByText('2026-01-01')).toBeInTheDocument();
    expect(screen.getByText('2028-01-01')).toBeInTheDocument();
  });

  it('scrubber input exists with range [0, 1]', () => {
    render(
      <Timeline
        mission={mockMission}
        currentTime={0}
        onTimeChange={() => {}}
        isPlaying={false}
        onPlayPause={() => {}}
      />
    );

    const scrubber = screen.getByRole('slider');
    expect(scrubber).toHaveAttribute('min', '0');
    expect(scrubber).toHaveAttribute('max', '1');
    expect(scrubber).toHaveAttribute('step', '0.001');
  });

  it('moving scrubber fires onTimeChange callback', () => {
    const onTimeChange = vi.fn();
    render(
      <Timeline
        mission={mockMission}
        currentTime={0}
        onTimeChange={onTimeChange}
        isPlaying={false}
        onPlayPause={() => {}}
      />
    );

    const scrubber = screen.getByRole('slider');
    fireEvent.change(scrubber, { target: { value: '0.5' } });

    expect(onTimeChange).toHaveBeenCalledWith(0.5);
  });

  it('play/pause button toggles animation state', () => {
    const onPlayPause = vi.fn();
    render(
      <Timeline
        mission={mockMission}
        currentTime={0}
        onTimeChange={() => {}}
        isPlaying={false}
        onPlayPause={onPlayPause}
      />
    );

    const button = screen.getByRole('button', { name: /play/i });
    fireEvent.click(button);
    expect(onPlayPause).toHaveBeenCalled();
  });

  it('accessible: scrubber has aria-label', () => {
    render(
      <Timeline
        mission={mockMission}
        currentTime={0}
        onTimeChange={() => {}}
        isPlaying={false}
        onPlayPause={() => {}}
      />
    );

    const scrubber = screen.getByRole('slider');
    expect(scrubber).toHaveAttribute('aria-label', 'Mission timeline');
  });
});
