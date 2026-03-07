import { useRef, useEffect, useMemo, useState } from 'react';
import * as d3 from 'd3';
import type { ParsedMission } from '../lib/missionParser';
import { planets, sunColor, sunRadius } from '../data/planets';
import { sampleEllipse, planetPositionAtDate } from '../lib/orbitalMath';

interface SolarSystemViewProps {
  mission: ParsedMission;
  showOuterPlanets?: boolean;
  currentTime?: number;
}

const phaseColors: Record<string, string> = {
  earth_departure: '#3B82F6',
  flyby: '#EF4444',
  return_departure: '#22C55E',
  earth_arrival: '#3B82F6',
};

export function SolarSystemView({
  mission,
  showOuterPlanets = false,
  currentTime = 0,
}: SolarSystemViewProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Responsive sizing
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      // Maintain 4:3 aspect ratio, capped at a reasonable height
      setDimensions({ width, height: Math.min(width * 0.75, 700) });
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const { width, height } = dimensions;

  const maxAU = useMemo(() => {
    if (showOuterPlanets) {
      return Math.max(mission.max_distance_AU, 35);
    }
    return Math.max(mission.max_distance_AU, 2);
  }, [mission.max_distance_AU, showOuterPlanets]);

  // Scale maps AU values directly to pixel positions, with 0 AU at center
  const scaleX = useMemo(() => {
    const padding = 50;
    return d3.scaleLinear()
      .domain([-maxAU, maxAU])
      .range([padding, width - padding]);
  }, [width, maxAU]);

  const scaleY = useMemo(() => {
    const padding = 50;
    return d3.scaleLinear()
      .domain([-maxAU, maxAU])
      .range([height - padding, padding]); // Y is inverted in SVG
  }, [height, maxAU]);

  const centerX = scaleX(0);
  const centerY = scaleY(0);

  const planetPositions = useMemo(() => {
    const departureDate = new Date(mission.departure_date);
    const positions: Record<string, [number, number]> = {};
    planets.forEach((planet) => {
      positions[planet.name] = planetPositionAtDate(planet.name, departureDate);
    });
    return positions;
  }, [mission.departure_date]);

  // Combine all trajectory points for spacecraft animation
  const allTrajectoryPoints = useMemo(() => {
    return mission.phases
      .filter((p) => p.trajectoryPoints && p.trajectoryPoints.length > 0)
      .flatMap((p) => p.trajectoryPoints!);
  }, [mission.phases]);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const g = svg.append('g');

    // Draw planetary orbits
    planets.forEach((planet) => {
      const orbitPoints = sampleEllipse(planet.semiMajorAxisAU, planet.eccentricity, 0, 200);
      const line = d3.line<[number, number]>()
        .x((d) => scaleX(d[0]))
        .y((d) => scaleY(d[1]));

      g.append('path')
        .attr('d', line(orbitPoints) || '')
        .attr('fill', 'none')
        .attr('stroke', 'rgba(255, 255, 255, 0.15)')
        .attr('stroke-width', 1)
        .attr('data-planet-orbit', planet.name);
    });

    // Draw Sun
    g.append('circle')
      .attr('cx', centerX)
      .attr('cy', centerY)
      .attr('r', sunRadius)
      .attr('fill', sunColor)
      .attr('data-testid', 'sun')
      .style('filter', 'drop-shadow(0 0 10px #FDB813)');

    // Draw planets
    planets.forEach((planet) => {
      const [px, py] = planetPositions[planet.name];

      g.append('circle')
        .attr('cx', scaleX(px))
        .attr('cy', scaleY(py))
        .attr('r', planet.radius)
        .attr('fill', planet.color)
        .attr('data-planet', planet.name)
        .style('filter', `drop-shadow(0 0 4px ${planet.color})`);

      // Planet label
      g.append('text')
        .attr('x', scaleX(px))
        .attr('y', scaleY(py) - planet.radius - 4)
        .attr('text-anchor', 'middle')
        .attr('fill', 'rgba(255, 255, 255, 0.5)')
        .attr('font-size', '10px')
        .text(planet.name);
    });

    // Draw spacecraft trajectories for each phase
    mission.phases.forEach((phase) => {
      if (!phase.trajectoryPoints || phase.trajectoryPoints.length === 0) return;

      const line = d3.line<[number, number]>()
        .x((d) => scaleX(d[0]))
        .y((d) => scaleY(d[1]));

      const color = phaseColors[phase.phase] || '#FFFFFF';

      g.append('path')
        .attr('d', line(phase.trajectoryPoints) || '')
        .attr('fill', 'none')
        .attr('stroke', color)
        .attr('stroke-width', 2)
        .attr('stroke-opacity', 0.8)
        .attr('data-testid', 'trajectory')
        .attr('data-phase', phase.phase);
    });

    // Draw spacecraft trail + position
    if (allTrajectoryPoints.length > 0) {
      const idx = Math.min(
        Math.floor(currentTime * (allTrajectoryPoints.length - 1)),
        allTrajectoryPoints.length - 1
      );
      const trailPts = allTrajectoryPoints.slice(0, idx + 1);

      if (trailPts.length >= 2) {
        const trailLine = d3.line<[number, number]>()
          .x((d) => scaleX(d[0]))
          .y((d) => scaleY(d[1]));

        g.append('path')
          .attr('d', trailLine(trailPts) || '')
          .attr('fill', 'none')
          .attr('stroke', 'rgba(255, 255, 255, 0.4)')
          .attr('stroke-width', 2)
          .attr('stroke-linecap', 'round')
          .attr('data-testid', 'trail');
      }

      const [sx, sy] = allTrajectoryPoints[idx];

      // Outer glow ring for visibility
      g.append('circle')
        .attr('cx', scaleX(sx))
        .attr('cy', scaleY(sy))
        .attr('r', 16)
        .attr('fill', 'none')
        .attr('stroke', '#00FFFF')
        .attr('stroke-width', 2)
        .attr('stroke-opacity', 0.5);

      // Spacecraft dot — bright cyan, large, with strong glow
      g.append('circle')
        .attr('cx', scaleX(sx))
        .attr('cy', scaleY(sy))
        .attr('r', 10)
        .attr('fill', '#00FFFF')
        .attr('data-testid', 'spacecraft')
        .style('filter', 'drop-shadow(0 0 12px #00FFFF) drop-shadow(0 0 24px #00FFFF)');

      // Label
      g.append('text')
        .attr('x', scaleX(sx))
        .attr('y', scaleY(sy) - 20)
        .attr('text-anchor', 'middle')
        .attr('fill', '#00FFFF')
        .attr('font-size', '11px')
        .attr('font-weight', 'bold')
        .text('🚀 Spacecraft');
    }

  }, [scaleX, scaleY, centerX, centerY, planetPositions, mission.phases, allTrajectoryPoints, currentTime]);

  return (
    <div ref={containerRef} className="w-full">
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="bg-space-bg rounded-lg w-full"
        role="img"
        aria-label="Solar system view showing planetary orbits and spacecraft trajectory"
      />
    </div>
  );
}
