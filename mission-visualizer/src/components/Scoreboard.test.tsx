import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Scoreboard } from './Scoreboard';
import type { ParsedMission } from '../lib/missionParser';

const mockMission: ParsedMission = {
  mission_name: 'Test Mission',
  departure_date: '2026-01-01',
  total_delta_v_km_s: 10.5,
  max_distance_AU: 4.5,
  mission_duration_days: 500,
  tier: 'Gold',
  phases: [],
  flybys: [],
};

describe('Scoreboard', () => {
  it('renders max distance with AU unit', () => {
    render(<Scoreboard mission={mockMission} />);
    expect(screen.getByText(/4.50 AU/)).toBeInTheDocument();
  });

  it('renders total delta-v', () => {
    render(<Scoreboard mission={mockMission} />);
    expect(screen.getByText(/10.50 km\/s/)).toBeInTheDocument();
  });

  it('renders mission duration', () => {
    render(<Scoreboard mission={mockMission} />);
    expect(screen.getByText(/500 days/)).toBeInTheDocument();
  });

  it('renders correct tier badge', () => {
    render(<Scoreboard mission={mockMission} />);
    expect(screen.getByText('Gold')).toBeInTheDocument();
  });

  it('tier badge has correct color class', () => {
    const tiers: Array<{ tier: 'Bronze' | 'Silver' | 'Gold' | 'Platinum'; expectedClass: string }> = [
      { tier: 'Bronze', expectedClass: 'text-amber-600' },
      { tier: 'Silver', expectedClass: 'text-gray-400' },
      { tier: 'Gold', expectedClass: 'text-yellow-400' },
      { tier: 'Platinum', expectedClass: 'text-cyan-300' },
    ];

    tiers.forEach(({ tier, expectedClass }) => {
      const { unmount } = render(<Scoreboard mission={{ ...mockMission, tier }} />);
      const badge = screen.getByText(tier);
      expect(badge).toHaveClass(expectedClass);
      unmount();
    });
  });

  it('renders mission name', () => {
    render(<Scoreboard mission={mockMission} />);
    expect(screen.getByText('Test Mission')).toBeInTheDocument();
  });
});
