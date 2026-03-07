import { useRef, useEffect, useMemo } from 'react';
import * as d3 from 'd3';
import type { ParsedMission } from '../lib/missionParser';
import { planets, sunColor, sunRadius } from '../data/planets';
import { sampleEllipse, planetPositionAtDate } from '../lib/orbitalMath';

interface SolarSystemViewProps {
  mission: ParsedMission;
  width: number;
  height: number;
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
  width,
  height,
  showOuterPlanets = false,
  currentTime: _currentTime = 0,
}: SolarSystemViewProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  const maxAU = useMemo(() => {
    if (showOuterPlanets) {
      return Math.max(mission.max_distance_AU, 35);
    }
    return Math.max(mission.max_distance_AU, 2);
  }, [mission.max_distance_AU, showOuterPlanets]);

  const scale = useMemo(() => {
    const padding = 50;
    const minDimension = Math.min(width, height);
    return d3.scaleLinear()
      .domain([-maxAU, maxAU])
      .range([padding, minDimension - padding]);
  }, [width, height, maxAU]);

  const centerX = width / 2;
  const centerY = height / 2;

  const planetPositions = useMemo(() => {
    const departureDate = new Date(mission.departure_date);
    const positions: Record<string, [number, number]> = {};
    planets.forEach((planet) => {
      positions[planet.name] = planetPositionAtDate(planet.name, departureDate);
    });
    return positions;
  }, [mission.departure_date]);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);

    // Clear previous content
    svg.selectAll('*').remove();

    // Create main group for transforms
    const g = svg.append('g');

    // Draw planetary orbits
    planets.forEach((planet) => {
      const orbitPoints = sampleEllipse(planet.semiMajorAxisAU, planet.eccentricity, 0, 100);
      const line = d3.line<[number, number]>()
        .x((d) => centerX + scale(d[0]))
        .y((d) => centerY - scale(d[1]));

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
      const x = centerX + scale(px);
      const y = centerY - scale(py);

      g.append('circle')
        .attr('cx', x)
        .attr('cy', y)
        .attr('r', planet.radius)
        .attr('fill', planet.color)
        .attr('data-planet', planet.name)
        .style('filter', `drop-shadow(0 0 4px ${planet.color})`);
    });

    // Draw spacecraft trajectories for each phase
    mission.phases.forEach((phase) => {
      if (!phase.trajectoryPoints || phase.trajectoryPoints.length === 0) return;

      const line = d3.line<[number, number]>()
        .x((d) => centerX + scale(d[0]))
        .y((d) => centerY - scale(d[1]));

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

  }, [scale, centerX, centerY, planetPositions, mission.phases, maxAU]);

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      className="bg-space-bg rounded-lg"
      role="img"
      aria-label="Solar system view showing planetary orbits and spacecraft trajectory"
    />
  );
}
