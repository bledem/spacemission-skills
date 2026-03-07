import { useRef, useEffect, useMemo } from 'react';
import * as d3 from 'd3';
import type { Phase } from '../lib/missionParser';
import { sampleHyperbola } from '../lib/orbitalMath';
import { planets } from '../data/planets';

interface FlybyDetailProps {
  flybyPhase: Phase | null;
  onClose: () => void;
  width?: number;
  height?: number;
}

export function FlybyDetail({
  flybyPhase,
  onClose,
  width = 500,
  height = 500,
}: FlybyDetailProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  const planet = useMemo(() => {
    if (!flybyPhase?.planet) return null;
    return planets.find((p) => p.name === flybyPhase.planet) || null;
  }, [flybyPhase]);

  const hyperbolaPoints = useMemo(() => {
    if (!flybyPhase?.orbit) return [];
    const { a_AU, e, omega_rad } = flybyPhase.orbit;
    // For flyby visualization, use smaller scale
    return sampleHyperbola(a_AU * 0.1, e, omega_rad, 100);
  }, [flybyPhase]);

  useEffect(() => {
    if (!svgRef.current || !flybyPhase || !planet) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const centerX = width / 2;
    const centerY = height / 2;
    const scale = d3.scaleLinear()
      .domain([-0.5, 0.5])
      .range([50, width - 50]);

    const g = svg.append('g');

    // Draw planet
    g.append('circle')
      .attr('cx', centerX)
      .attr('cy', centerY)
      .attr('r', planet.radius * 2)
      .attr('fill', planet.color)
      .attr('data-testid', 'flyby-planet')
      .style('filter', `drop-shadow(0 0 8px ${planet.color})`);

    // Draw hyperbolic trajectory
    if (hyperbolaPoints.length > 0) {
      const line = d3.line<[number, number]>()
        .x((d) => centerX + scale(d[0]))
        .y((d) => centerY - scale(d[1]));

      g.append('path')
        .attr('d', line(hyperbolaPoints) || '')
        .attr('fill', 'none')
        .attr('stroke', '#EF4444')
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', '5,5')
        .attr('data-testid', 'hyperbola');
    }

    // Draw periapsis marker
    if (flybyPhase.flyby_details) {
      const periapsisRadius = planet.radius * 2 + (flybyPhase.flyby_details.periapsis_altitude_km / 1000);
      g.append('circle')
        .attr('cx', centerX)
        .attr('cy', centerY)
        .attr('r', periapsisRadius)
        .attr('fill', 'none')
        .attr('stroke', 'rgba(255, 255, 255, 0.3)')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '3,3')
        .attr('data-testid', 'periapsis');
    }

    // Draw velocity arrows
    const arrowLength = 60;
    const turnAngle = (flybyPhase.flyby_details?.turn_angle_deg || 45) * Math.PI / 180;

    // Incoming velocity
    g.append('line')
      .attr('x1', centerX - arrowLength)
      .attr('y1', centerY + arrowLength / 2)
      .attr('x2', centerX)
      .attr('y2', centerY)
      .attr('stroke', '#3B82F6')
      .attr('stroke-width', 2)
      .attr('marker-end', 'url(#arrow-blue)')
      .attr('data-testid', 'incoming-velocity');

    // Outgoing velocity (rotated by turn angle)
    const outgoingX = centerX + arrowLength * Math.cos(-turnAngle + Math.PI / 4);
    const outgoingY = centerY + arrowLength * Math.sin(-turnAngle + Math.PI / 4);
    g.append('line')
      .attr('x1', centerX)
      .attr('y1', centerY)
      .attr('x2', outgoingX)
      .attr('y2', outgoingY)
      .attr('stroke', '#22C55E')
      .attr('stroke-width', 2)
      .attr('marker-end', 'url(#arrow-green)')
      .attr('data-testid', 'outgoing-velocity');

    // Arrow markers
    svg.append('defs')
      .append('marker')
      .attr('id', 'arrow-blue')
      .attr('viewBox', '0 0 10 10')
      .attr('refX', 8)
      .attr('refY', 5)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M 0 0 L 10 5 L 0 10 z')
      .attr('fill', '#3B82F6');

    svg.append('defs')
      .append('marker')
      .attr('id', 'arrow-green')
      .attr('viewBox', '0 0 10 10')
      .attr('refX', 8)
      .attr('refY', 5)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M 0 0 L 10 5 L 0 10 z')
      .attr('fill', '#22C55E');

    // Turn angle arc
    const arcRadius = 40;
    const arc = d3.arc()
      .innerRadius(arcRadius - 5)
      .outerRadius(arcRadius)
      .startAngle(Math.PI / 4)
      .endAngle(Math.PI / 4 + turnAngle);

    g.append('path')
      .attr('d', arc({ innerRadius: arcRadius - 5, outerRadius: arcRadius, startAngle: Math.PI / 4, endAngle: Math.PI / 4 + turnAngle }) || '')
      .attr('fill', 'rgba(255, 255, 255, 0.5)')
      .attr('transform', `translate(${centerX}, ${centerY})`);

  }, [flybyPhase, planet, hyperbolaPoints, width, height]);

  if (!flybyPhase) return null;

  return (
    <div
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 flyby-backdrop"
      onClick={onClose}
    >
      <div
        className="bg-space-bg border border-white/20 rounded-lg p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-white">
            {flybyPhase.planet} Gravity Assist
          </h3>
          <button
            onClick={onClose}
            className="text-white/50 hover:text-white text-xl"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <svg
          ref={svgRef}
          width={width}
          height={height}
          className="bg-space-bg rounded"
        />

        <div className="mt-4 grid grid-cols-2 gap-4 text-sm text-white/70">
          <div>
            <span className="text-white/50">Periapsis Altitude</span>
            <p className="font-mono">{flybyPhase.flyby_details?.periapsis_altitude_km} km</p>
          </div>
          <div>
            <span className="text-white/50">Turn Angle</span>
            <p className="font-mono">δ = {flybyPhase.flyby_details?.turn_angle_deg.toFixed(1)}°</p>
          </div>
          <div>
            <span className="text-white/50">Incoming V∞</span>
            <p className="font-mono">{flybyPhase.flyby_details?.incoming_v_inf_km_s} km/s</p>
          </div>
          <div>
            <span className="text-white/50">Outgoing V∞</span>
            <p className="font-mono">{flybyPhase.flyby_details?.outgoing_v_inf_km_s} km/s</p>
          </div>
        </div>
      </div>
    </div>
  );
}
