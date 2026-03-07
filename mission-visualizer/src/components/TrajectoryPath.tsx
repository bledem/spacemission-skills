import { useMemo } from 'react';
import * as d3 from 'd3';
import type { Phase } from '../lib/missionParser';

interface TrajectoryPathProps {
  phases: Phase[];
  currentTime: number;
  scale: (value: number) => number;
  centerX: number;
  centerY: number;
}

export function TrajectoryPath({
  phases,
  currentTime,
  scale,
  centerX,
  centerY,
}: TrajectoryPathProps) {
  // Combine all trajectory points from all phases
  const allPoints = useMemo(() => {
    return phases
      .filter((p) => p.trajectoryPoints && p.trajectoryPoints.length > 0)
      .flatMap((p) => p.trajectoryPoints!);
  }, [phases]);

  // Calculate spacecraft position based on currentTime
  const spacecraftPosition = useMemo(() => {
    if (allPoints.length === 0) return [centerX, centerY];

    const index = Math.min(
      Math.floor(currentTime * (allPoints.length - 1)),
      allPoints.length - 1
    );
    const [x, y] = allPoints[index];
    return [centerX + scale(x), centerY - scale(y)];
  }, [allPoints, currentTime, scale, centerX, centerY]);

  // Trail points (all points up to current position)
  const trailPoints = useMemo(() => {
    if (allPoints.length === 0) return [];

    const endIndex = Math.min(
      Math.floor(currentTime * (allPoints.length - 1)),
      allPoints.length - 1
    );
    return allPoints.slice(0, endIndex + 1);
  }, [allPoints, currentTime]);

  const trailPath = useMemo(() => {
    if (trailPoints.length < 2) return '';

    const line = d3.line<[number, number]>()
      .x((d) => centerX + scale(d[0]))
      .y((d) => centerY - scale(d[1]));

    return line(trailPoints) || '';
  }, [trailPoints, scale, centerX, centerY]);

  return (
    <g>
      {/* Trail */}
      {trailPath && (
        <path
          d={trailPath}
          fill="none"
          stroke="rgba(255, 255, 255, 0.3)"
          strokeWidth={2}
          strokeLinecap="round"
          data-testid="trail"
        />
      )}

      {/* Spacecraft */}
      <circle
        cx={spacecraftPosition[0]}
        cy={spacecraftPosition[1]}
        r={6}
        fill="#FFFFFF"
        data-testid="spacecraft"
        style={{ filter: 'drop-shadow(0 0 8px #FFFFFF)' }}
      />
    </g>
  );
}
