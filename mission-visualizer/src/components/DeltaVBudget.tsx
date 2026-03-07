import { useState } from 'react';
import type { Phase } from '../lib/missionParser';

interface DeltaVBudgetProps {
  phases: Phase[];
  totalDeltaV: number;
  budget?: number;
}

const phaseColors: Record<string, string> = {
  earth_departure: '#3B82F6',
  flyby: '#EF4444',
  return_departure: '#22C55E',
  earth_arrival: '#3B82F6',
};

const remainingColor = '#4B5563';

export function DeltaVBudget({ phases, totalDeltaV, budget = 12 }: DeltaVBudgetProps) {
  const [hoveredPhase, setHoveredPhase] = useState<string | null>(null);
  const budgetExceeded = totalDeltaV > budget;
  const remaining = Math.max(0, budget - totalDeltaV);

  const segments = [
    ...phases.map((phase) => ({
      name: phase.phase,
      value: phase.delta_v_km_s,
      percentage: (phase.delta_v_km_s / budget) * 100,
      color: phaseColors[phase.phase] || '#6B7280',
    })),
    ...(remaining > 0
      ? [{ name: 'Remaining', value: remaining, percentage: (remaining / budget) * 100, color: remainingColor }]
      : []),
  ];

  return (
    <div className="bg-space-bg/80 backdrop-blur-sm border border-white/10 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-white/70 mb-2">Delta-V Budget</h3>

      {budgetExceeded && (
        <p className="text-red-400 text-xs mb-2">⚠️ Budget exceeded by {(totalDeltaV - budget).toFixed(2)} km/s</p>
      )}

      <ul className="flex h-6 rounded overflow-hidden" role="list">
        {segments.map((segment, index) => (
          <li
            key={index}
            className="transition-opacity hover:opacity-80 relative"
            style={{ width: `${segment.percentage}%`, backgroundColor: segment.color }}
            onMouseEnter={() => setHoveredPhase(segment.name)}
            onMouseLeave={() => setHoveredPhase(null)}
            aria-label={`${segment.name}: ${segment.value.toFixed(2)} km/s`}
            role="listitem"
          >
            {hoveredPhase === segment.name && (
              <div
                role="tooltip"
                className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-black/90 text-white text-xs rounded whitespace-nowrap z-10"
              >
                {segment.name}: {segment.value.toFixed(2)} km/s
              </div>
            )}
          </li>
        ))}
      </ul>

      <div className="flex justify-between text-xs text-white/50 mt-1">
        <span>0</span>
        <span>{totalDeltaV.toFixed(2)} / {budget} km/s</span>
        <span>{budget}</span>
      </div>
    </div>
  );
}
