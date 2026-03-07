# Deep Space Explorer: Interplanetary Mission Design Challenge

> Design a spacecraft mission that reaches the furthest possible heliocentric distance and returns to Earth, given a fixed propellant budget.

---

## Overview

This task evaluates an AI agent's ability to reason about orbital mechanics, plan multi-phase space missions, and optimize under constraints. The agent receives a spacecraft with a fixed delta-v budget and must design a complete round-trip interplanetary mission — choosing departure dates, transfer trajectories, and burn allocations — that maximizes the aphelion distance reached while guaranteeing a valid return to Earth.

Unlike open-ended optimization problems, every decision the agent makes is verifiable: the SpacecraftSimulator's physics engine either confirms the trajectory is valid or it doesn't. There's no hand-waving — the math has to close.

---

## Why This Task

1. **Multi-step reasoning under constraints.** The agent must plan a sequence of maneuvers where each decision constrains future options. Spending too much delta-v on departure leaves nothing for return. Choosing the wrong departure date means planetary alignment doesn't work.

2. **Domain knowledge matters but isn't sufficient.** Knowing that Hohmann transfers exist is table stakes. The interesting decisions are: which transfer type to use, whether a gravity assist saves enough delta-v to justify the longer flight time, and how to split the budget between departure and return.

3. **Deterministic verification.** Every trajectory can be independently verified by propagating the orbit forward. The simulator computes positions, velocities, and delta-v costs from first principles — no approximations the agent can exploit.

4. **Grounded in the existing codebase.** Every computation required is already implemented in the SpacecraftSimulator's `tools/` layer. The agent doesn't need to implement physics — it needs to use the existing tools intelligently.

---

## Mission Specification

### Spacecraft Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Initial mass | 2000 kg | Wet mass at Earth departure |
| Specific impulse (I_sp) | 300 s | Chemical propulsion, typical bipropellant |
| Total delta-v budget | 12 km/s | All maneuvers combined (departure + return + any mid-course) |
| Parking orbit altitude | 300 km above Earth | Circular LEO, radius = 6678 km |

The delta-v budget of 12 km/s is deliberately generous enough to reach Mars and return via Hohmann, but tight enough that reaching Jupiter or Saturn requires clever trajectory design (gravity assists, bi-elliptic transfers, or favorable planetary alignment).

### Mission Phases

The agent must design a mission with these phases:

#### Phase 1: Earth Departure
- Depart from a 300 km circular parking orbit around Earth
- Execute a departure burn to enter a heliocentric transfer orbit
- The departure hyperbola cost is computed via `InterplanetaryTrajectories.departure()` or `optimal_transfer()`

#### Phase 2: Outbound Transfer
- Coast along the heliocentric transfer orbit toward the target
- Optionally perform a gravity assist flyby at an intermediate planet using `InterplanetaryTrajectories.flyby()`
- The transfer orbit is solved via the Lambert problem (`OrbitDetermination.solve_lambert_problem()`) given departure and arrival positions from `InterplanetaryTrajectories.ephemeris()`

#### Phase 3: Aphelion / Maximum Distance
- The scoring point: the maximum heliocentric distance achieved on the outbound trajectory
- This is the apoapsis of the transfer orbit (for a direct transfer) or the post-flyby orbit (for a gravity-assist trajectory)
- Computed from the orbital elements of the transfer orbit: `r_a = a * (1 + e)` or `r_a = h² / (μ_sun * (1 - e))` for the heliocentric orbit

#### Phase 4: Return Transfer
- Enter a return transfer orbit back toward Earth
- This may be a separate Lambert-solved trajectory or the natural return of an elliptical orbit
- If using a gravity assist on the way out, the return leg is independent and must be separately planned

#### Phase 5: Earth Arrival
- Arrive at Earth and perform a capture burn into a stable Earth orbit
- Capture orbit: any closed orbit around Earth (elliptical is fine, doesn't need to be circular)
- The arrival cost is computed via `InterplanetaryTrajectories.rendezvous()`

### Constraints

1. **Delta-v budget**: Sum of all impulsive maneuvers ≤ 12 km/s
   - Departure burn (Phase 1)
   - Any powered flyby corrections (Phase 2, if applicable)
   - Return departure burn (Phase 4, if the outbound orbit doesn't naturally return)
   - Earth capture burn (Phase 5)

2. **Mission duration**: Total mission time ≤ 20 years (7305 days)
   - Measured from Earth departure to Earth arrival
   - This prevents degenerate solutions like multi-decade coasting on barely-bound orbits

3. **Departure window**: Any date between 2025-01-01 and 2035-12-31
   - The agent chooses the departure date
   - Planetary positions are computed via `InterplanetaryTrajectories.ephemeris(planet, date)`

4. **Return must intersect Earth**: The return trajectory must arrive within Earth's sphere of influence
   - Verified by computing Earth's position at the arrival date and checking that the trajectory passes within Earth's SOI (~925,000 km)

5. **Flyby altitude constraint**: Any gravity assist flyby must have periapsis above the planet's surface + 300 km
   - `r_p_flyby > equatorial_radius(planet) + 300`

---

## Available Simulator API

The agent has access to these modules (all in `SpacecraftSimulator/tools/`):

### Core Computations

```python
# Planetary positions at any date
InterplanetaryTrajectories.ephemeris(planet: CelestialBody, date: datetime) -> [r, v]

# Synodic period between two planets (alignment frequency)
InterplanetaryTrajectories.synodic_period(departure: CelestialBody, arrival: CelestialBody) -> float

# Wait time for next transfer window
InterplanetaryTrajectories.wait_time(departure: CelestialBody, arrival: CelestialBody) -> [t_wait, phi_0, phi_f]

# Departure hyperbola delta-v from parking orbit
InterplanetaryTrajectories.departure(departure: CelestialBody, arrival: CelestialBody, r_p: float, m: float) -> ManeuverResult

# Arrival capture into orbit around target planet
InterplanetaryTrajectories.rendezvous(departure: CelestialBody, arrival: CelestialBody, r_p_A: float, T: float, m: float) -> ManeuverResult

# Gravity assist flyby (free delta-v from planet's gravity)
InterplanetaryTrajectories.flyby(departure: CelestialBody, arrival: CelestialBody, r_p: float, theta_1: float, m: float, side: FlybySide) -> ManeuverResult

# Full Lambert-based optimal transfer between two planets on specific dates
InterplanetaryTrajectories.optimal_transfer(
    departure: CelestialBody, arrival: CelestialBody,
    departureDate: datetime, arrivalDate: datetime,
    r_p_D: float, r_p_A: float, T: float, m: float
) -> [ManeuverResult_departure, ManeuverResult_arrival, OrbitalElements, theta_2]

# Pork chop plot: sweep departure/arrival dates to find optimal windows
InterplanetaryTrajectories.pork_chop(
    departure: CelestialBody, arrival: CelestialBody,
    launchWindow: [date_start, date_end],
    arrivalWindow: [date_start, date_end],
    step: int
) -> None  # generates delta-v contour data
```

### Supporting Computations

```python
# Lambert problem: given two positions and transfer time, find the orbit
OrbitDetermination.solve_lambert_problem(r_1, r_2, dt) -> [v_1, v_2, OrbitalElements, theta_2]

# Hohmann transfer delta-v (for baseline comparison)
OrbitalManeuvers.hohmann_transfer(r_p_1, r_a_1, r_p_2, r_a_2, direction, m) -> ManeuverResult

# Propellant mass from delta-v (Tsiolkovsky equation)
OrbitalManeuvers.propellant_mass(m, dv) -> float

# Astronomical data for all planets
AstronomicalData.gravitational_parameter(body) -> float  # μ in km³/s²
AstronomicalData.semi_major_axis(body) -> float          # orbital radius in km
AstronomicalData.sphere_of_influence(body) -> float      # SOI in km
AstronomicalData.equatiorial_radius(body) -> float       # surface radius in km
AstronomicalData.sidereal_orbital_period(body) -> float  # orbital period in seconds

# Orbit propagation
LagrangeCoefficients.calculate_position_velocity_by_time(r_0, v_0, dt) -> [r_f, v_f]

# Orbital elements from state vector
ThreeDimensionalOrbit.calculate_orbital_elements(r, v) -> OrbitalElements

# Two-body orbital parameters
TwoBodyProblem.calculate_orbital_parameters(r, v) -> OrbitalParameters
```

### Available Celestial Bodies

```
SUN, MERCURY, VENUS, EARTH, MOON, MARS, JUPITER, SATURN, URANUS, NEPTUNE, PLUTO
```

All have ephemeris data, gravitational parameters, and orbital elements available.

---

## Strategy Space

The agent must choose from (at minimum) these strategy families:

### Strategy A: Direct Hohmann Transfer
- Earth → Planet → Earth via two Hohmann transfers
- Simple, well-understood, but delta-v expensive for outer planets
- Earth → Mars Hohmann: ~5.6 km/s total (departure + arrival), leaves ~6.4 km/s for return
- Earth → Jupiter Hohmann: ~14+ km/s total — exceeds budget, not feasible without assists

### Strategy B: Lambert-Optimized Direct Transfer
- Use `optimal_transfer()` with specific departure/arrival dates
- Can be more efficient than Hohmann if dates are chosen well (non-circular planetary orbits create opportunities)
- The agent must search over departure dates to find favorable windows

### Strategy C: Gravity Assist Trajectory
- Use a planetary flyby to gain heliocentric velocity for free
- Example: Earth → Venus flyby → outer solar system → return
- The `flyby()` function computes the post-flyby orbit
- The turn angle δ = 2·arcsin(1/e) depends on flyby altitude — lower altitude = more deflection but must stay above surface + 300 km
- This is the key to reaching beyond Mars on a 12 km/s budget

### Strategy D: Bi-Elliptic with Gravity Assist
- Combine a bi-elliptic transfer with a gravity assist
- Use the intermediate apoapsis of the bi-elliptic as the scoring point
- Return via the second ellipse

### Strategy E: Free-Return Trajectory
- Design an orbit that naturally returns to Earth without a return burn
- Saves the entire return delta-v budget for a bigger departure burn
- Requires the transfer orbit period to be a rational multiple of Earth's orbital period
- Extremely constrained but maximally efficient if achievable

---

## Scoring

### Primary Metric: Maximum Heliocentric Distance

```python
score = max_heliocentric_distance_AU  # in Astronomical Units (1 AU = 149,597,870.7 km)
```

The maximum distance is the apoapsis of the heliocentric orbit achieved after the last outbound maneuver (departure burn + any flyby).

### Validity Checks (all must pass or score = 0)

1. **Delta-v budget**: `sum(all_maneuver_dv) ≤ 12.0 km/s`
2. **Mission duration**: `total_time ≤ 20 years`
3. **Earth return**: Return trajectory arrives within Earth's SOI
4. **Flyby altitude**: All flyby periapses above planet surface + 300 km
5. **Physical consistency**: All orbital elements are physically valid (e ≥ 0, a > 0 for elliptical, h > 0)
6. **Departure orbit**: Departs from 300 km circular Earth orbit

### Scoring Tiers

| Tier | Distance | Interpretation |
|------|----------|----------------|
| Bronze | 1.5 - 2.0 AU | Mars-class mission, direct Hohmann |
| Silver | 2.0 - 4.0 AU | Asteroid belt reach, optimized transfer or single flyby |
| Gold | 4.0 - 6.0 AU | Jupiter-class, requires gravity assist |
| Platinum | > 6.0 AU | Saturn-class or beyond, multi-flyby or exceptional optimization |

### Reward Function (for benchmark)

```python
if not all_constraints_satisfied:
    reward = 0.0
else:
    reward = max_distance_AU / 6.0  # normalized so Jupiter-distance ≈ 1.0
    reward = min(reward, 2.0)       # cap at 2.0 to prevent gaming
```

---

## Verification Process

```
1. Parse the agent's mission plan (sequence of maneuvers with dates, planets, delta-v values)
2. For each maneuver:
   a. Compute planetary ephemeris at the specified date
   b. Solve the Lambert problem for the specified transfer
   c. Verify the delta-v matches the agent's claim (within 1% tolerance)
   d. Accumulate total delta-v
3. Compute the maximum heliocentric distance from the transfer orbit elements
4. Verify Earth return:
   a. Propagate the return trajectory to the specified arrival date
   b. Compute distance to Earth at arrival
   c. Confirm distance < Earth SOI
5. Check all constraints
6. Compute score
```

---

## Agent Output Format

The agent must produce a structured mission plan:

```json
{
  "mission_name": "string",
  "strategy": "direct | lambert | gravity_assist | bi_elliptic | free_return",
  "departure_date": "YYYY-MM-DD",
  "return_date": "YYYY-MM-DD",
  "total_delta_v_km_s": 0.0,
  "max_distance_AU": 0.0,
  "phases": [
    {
      "phase": "earth_departure",
      "date": "YYYY-MM-DD",
      "maneuver": "departure_burn",
      "delta_v_km_s": 0.0,
      "from_body": "EARTH",
      "to_body": "TARGET",
      "parking_orbit_radius_km": 6678,
      "transfer_orbit": {
        "a_km": 0.0,
        "e": 0.0,
        "i_deg": 0.0
      }
    },
    {
      "phase": "flyby",
      "date": "YYYY-MM-DD",
      "body": "VENUS",
      "periapsis_km": 0.0,
      "delta_v_km_s": 0.0,
      "side": "dark | sunlit",
      "post_flyby_orbit": {
        "a_km": 0.0,
        "e": 0.0,
        "r_apoapsis_AU": 0.0
      }
    },
    {
      "phase": "return_departure",
      "date": "YYYY-MM-DD",
      "delta_v_km_s": 0.0,
      "transfer_orbit": {
        "a_km": 0.0,
        "e": 0.0
      }
    },
    {
      "phase": "earth_arrival",
      "date": "YYYY-MM-DD",
      "delta_v_km_s": 0.0,
      "capture_orbit": {
        "periapsis_km": 0.0,
        "period_hours": 0.0
      }
    }
  ],
  "verification": {
    "total_delta_v_check": true,
    "mission_duration_days": 0,
    "earth_return_distance_km": 0.0,
    "all_constraints_satisfied": true
  }
}
```

---

## What Makes This Hard

1. **Combinatorial search over dates.** Planetary alignment varies continuously. The agent must reason about synodic periods to identify promising departure windows, then refine with Lambert solutions. Brute-force search over all dates is possible but slow — the agent should use `synodic_period()` and `wait_time()` to narrow the search space intelligently.

2. **Budget allocation is a coupled problem.** The departure delta-v determines the transfer orbit, which determines the arrival conditions, which determines the return cost. The agent can't optimize each phase independently.

3. **Gravity assists require geometric reasoning.** A Venus flyby only helps if the post-flyby velocity vector points toward the outer solar system. The agent must reason about the flyby geometry (approach angle, periapsis altitude, dark vs. sunlit side) to get the desired deflection.

4. **Return trajectory feasibility.** It's easy to reach far away — just burn everything on departure. The hard part is having enough delta-v left to get back. The agent must balance ambition with feasibility.

5. **Numerical precision.** The Lambert solver can fail for near-180° transfers or very short/long transfer times. The agent must choose transfer parameters that keep the numerics well-conditioned.

6. **No single "right answer."** Unlike the TDD task where bugs are binary, this task has a continuous score. A naive agent gets Bronze. A sophisticated agent that understands gravity assists and planetary alignment gets Gold or Platinum. The scoring distribution reveals the depth of the agent's orbital mechanics reasoning.

---

## Feasibility Notes (SpacecraftSimulator Capabilities)

Everything in this task is computable with the existing codebase:

- **Ephemeris**: `InterplanetaryTrajectories.ephemeris()` computes planet positions for any date using Algorithm 8.1 from Curtis, with orbital elements and rates from JPL data. Accuracy is sufficient for this task (mean elements, not full perturbation model).

- **Lambert solver**: `OrbitDetermination.solve_lambert_problem()` handles prograde transfers. The universal variable formulation works for elliptical and hyperbolic transfers.

- **Flyby**: `InterplanetaryTrajectories.flyby()` computes the post-flyby heliocentric orbit given approach geometry. It handles both dark-side and sunlit-side flybys.

- **Departure/Arrival**: `InterplanetaryTrajectories.departure()` and `rendezvous()` compute the hyperbolic excess velocity and parking orbit delta-v.

- **Optimal transfer**: `InterplanetaryTrajectories.optimal_transfer()` wraps the full Lambert-based transfer computation including departure and arrival maneuvers.

- **Pork chop plots**: `InterplanetaryTrajectories.pork_chop()` sweeps departure/arrival date combinations — useful for the agent to identify optimal windows.

**Known limitations**:
- The gravity assist path in `optimal_transfer()` is incomplete (has a `return` statement before full computation). The agent should use `flyby()` directly for gravity assist legs.
- Ephemeris uses mean orbital elements with linear rates — adequate for mission design but not for navigation-grade accuracy.
- The Lambert solver assumes prograde transfers only (no retrograde option exposed).
- Multi-revolution Lambert solutions are not implemented.

---

## Benchmark Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Agent timeout | 600s | Date search + Lambert solutions + strategy evaluation |
| Verifier timeout | 120s | Re-run Lambert problems and propagate trajectories |
| Memory | 2048 MB | numpy + scipy for orbital computations |
| Storage | 10240 MB | Mission plan output + intermediate computations |
| Internet | true | Agent may reference orbital mechanics formulas |
| CPUs | 1 | Sequential computation is sufficient |

---
