import * as d3 from 'd3';

/**
 * Create a D3 linear scale that maps AU coordinates to pixel coordinates.
 * The origin (0, 0) is at the center of the viewport.
 */
export function createAUScale(
  viewportWidth: number,
  maxAU: number,
  padding: number = 50
): d3.ScaleLinear<number, number> {
  return d3.scaleLinear()
    .domain([-maxAU, maxAU])
    .range([padding, viewportWidth - padding]);
}
