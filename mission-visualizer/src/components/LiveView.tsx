/**
 * LiveView — renders the solar system with real-time sim data via WebSocket.
 * Supports pan (drag) and zoom (scroll wheel).
 */

import { useRef, useEffect, useMemo, useCallback } from 'react';
import * as d3 from 'd3';
import { planets as planetData } from '../data/planets';
import type { LiveSimData } from '../hooks/useSimConnection';

// Planet colors (matching existing viewer style)
const PLANET_COLORS: Record<string, string> = {
  Sun: '#FDB813',
  Mercury: '#B5B5B5',
  Venus: '#E8CDA0',
  Earth: '#4B9CD3',
  Moon: '#888888',
  Mars: '#C1440E',
  Jupiter: '#C88B3A',
  Saturn: '#EAD6B8',
  Uranus: '#D1E7E7',
  Neptune: '#5B5EA6',
};

interface LiveViewProps {
  sim: LiveSimData;
  showOuterPlanets?: boolean;
}

export function LiveView({ sim, showOuterPlanets = false }: LiveViewProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const gRef = useRef<SVGGElement | null>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const transformRef = useRef<d3.ZoomTransform>(d3.zoomIdentity);

  // Determine view scale from tracked bodies
  const maxAU = useMemo(() => {
    if (showOuterPlanets) return 6.0;
    const maxBody = Math.max(
      ...sim.bodies.map(b => Math.sqrt(b.position_au[0] ** 2 + b.position_au[1] ** 2)),
      0.1,
    );
    return Math.min(Math.max(maxBody * 1.2, 2.0), 6.0);
  }, [sim.bodies, showOuterPlanets]);

  // Set up zoom behavior once
  useEffect(() => {
    const svgEl = svgRef.current;
    if (!svgEl) return;

    const svg = d3.select(svgEl);

    // Create persistent <g> for all content
    svg.selectAll('g.scene').remove();
    const g = svg.append('g').attr('class', 'scene');
    gRef.current = g.node();

    // Zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 50])
      .on('zoom', (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
        transformRef.current = event.transform;
        g.attr('transform', event.transform.toString());
      });

    svg.call(zoom);
    zoomRef.current = zoom;

    return () => {
      svg.on('.zoom', null);
    };
  }, []);

  // Draw content on every tick
  const draw = useCallback(() => {
    const g = gRef.current ? d3.select(gRef.current) : null;
    const container = containerRef.current;
    if (!g || !container) return;

    const width = container.clientWidth;
    const height = container.clientHeight || 500;

    d3.select(svgRef.current).attr('width', width).attr('height', height);

    // Scales: AU → pixels, centered
    const cx = width / 2;
    const cy = height / 2;
    const scale = Math.min(width, height) / 2 / maxAU * 0.85;

    const toX = (au: number) => cx + au * scale;
    const toY = (au: number) => cy - au * scale;

    // Clear scene content (but keep the <g> and its transform)
    g.selectAll('*').remove();

    // Grid circles
    const gridAU = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0].filter(r => r <= maxAU);
    gridAU.forEach(r => {
      g.append('circle')
        .attr('cx', cx).attr('cy', cy)
        .attr('r', r * scale)
        .attr('fill', 'none')
        .attr('stroke', 'rgba(255,255,255,0.05)')
        .attr('stroke-dasharray', '2,4');
    });

    // Planet orbits
    planetData.forEach(planet => {
      if (!showOuterPlanets && planet.semiMajorAxisAU > 2.5) return;
      const r = planet.semiMajorAxisAU * scale;
      if (r > Math.max(width, height) * 3) return;

      g.append('circle')
        .attr('cx', cx).attr('cy', cy)
        .attr('r', r)
        .attr('fill', 'none')
        .attr('stroke', 'rgba(255,255,255,0.08)')
        .attr('stroke-width', 0.5);
    });

    // Sun
    g.append('circle')
      .attr('cx', cx).attr('cy', cy)
      .attr('r', 8)
      .attr('fill', '#FDB813');

    // Bodies
    sim.bodies.forEach(body => {
      if (body.name === 'Sun') return;
      const bx = toX(body.position_au[0]);
      const by = toY(body.position_au[1]);
      const color = PLANET_COLORS[body.name] ?? '#888';
      const radius = body.name === 'Jupiter' ? 6 : body.name === 'Saturn' ? 5 : 4;
      const distAU = Math.sqrt(body.position_au[0] ** 2 + body.position_au[1] ** 2);

      g.append('circle')
        .attr('cx', bx).attr('cy', by)
        .attr('r', radius)
        .attr('fill', color);

      g.append('text')
        .attr('x', bx + radius + 3).attr('y', by + 3)
        .attr('fill', 'rgba(255,255,255,0.5)')
        .attr('font-size', '10px')
        .text(body.name);

      g.append('text')
        .attr('x', bx + radius + 3).attr('y', by + 14)
        .attr('fill', 'rgba(255,255,255,0.3)')
        .attr('font-size', '9px')
        .attr('font-family', 'monospace')
        .text(`${distAU.toFixed(3)} AU`);
    });

    // Trajectory trail
    if (sim.trajectoryHistory.length > 1) {
      const line = d3.line<[number, number]>()
        .x(d => toX(d[0]))
        .y(d => toY(d[1]));

      g.append('path')
        .datum(sim.trajectoryHistory)
        .attr('d', line)
        .attr('fill', 'none')
        .attr('stroke', '#3B82F6')
        .attr('stroke-width', 1.5)
        .attr('stroke-opacity', 0.6);
    }

    // Spacecraft
    if (sim.spacecraft) {
      const [sx, sy] = sim.spacecraft.position_au;
      const px = toX(sx);
      const py = toY(sy);

      g.append('circle')
        .attr('cx', px).attr('cy', py)
        .attr('r', 8)
        .attr('fill', 'rgba(59, 130, 246, 0.3)');

      g.append('circle')
        .attr('cx', px).attr('cy', py)
        .attr('r', 4)
        .attr('fill', '#3B82F6');

      g.append('text')
        .attr('x', px + 10).attr('y', py - 5)
        .attr('fill', '#3B82F6')
        .attr('font-size', '11px')
        .attr('font-weight', 'bold')
        .text('MarCO-X');
    }

    // Scale label (in screen space — append to SVG, not the transformed g)
    const svg = d3.select(svgRef.current);
    svg.selectAll('text.scale-label').remove();
    svg.append('text')
      .attr('class', 'scale-label')
      .attr('x', 10).attr('y', height - 10)
      .attr('fill', 'rgba(255,255,255,0.3)')
      .attr('font-size', '10px')
      .text(`Scale: ±${maxAU.toFixed(1)} AU  |  scroll to zoom, drag to pan`);
  }, [sim, maxAU, showOuterPlanets]);

  useEffect(() => {
    draw();
  }, [draw]);

  return (
    <div
      ref={containerRef}
      className="bg-space-bg/80 backdrop-blur-sm border border-white/10 rounded-lg overflow-hidden"
      style={{ minHeight: '500px', cursor: 'grab' }}
    >
      <svg ref={svgRef} className="w-full h-full" />
    </div>
  );
}
