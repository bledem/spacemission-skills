# Deep Space Explorer: Interplanetary Mission Design Challenge

You are a spacecraft mission designer. Your goal is to design a round-trip interplanetary mission that reaches the **maximum possible heliocentric distance** from the Sun and returns safely to Earth, all within a fixed propellant (delta-v) budget.

## Mission Parameters

| Parameter | Value |
|-----------|-------|
| Total delta-v budget | **12 km/s** (all maneuvers combined) |
| Parking orbit | 300 km circular LEO (radius = 6678 km) |
| Mission duration limit | **20 years** (7305 days) |
| Departure window | 2025-01-01 to 2035-12-31 |
| Spacecraft mass | 2000 kg |
| Specific impulse | 300 s |

## What You Must Do

1. Choose a departure date and mission strategy
2. Compute all trajectory legs using the `spacecraft_sim` Python package (pre-installed)
3. Produce a JSON mission plan file at `/app/mission_plan.json`

## Available API

The `spacecraft_sim` package is installed in the environment. Use it in Python:

```python
from spacecraft_sim import (
    InterplanetaryTrajectories, OrbitDetermination, OrbitalManeuvers,
    AstronomicalData, LagrangeCoefficients, ThreeDimensionalOrbit,
    CelestialBody, FlybySide, OrbitalElements
)
from datetime import datetime
import numpy as np
```

### Key Functions

```python
# Planet position at a date (returns [r_vec, v_vec] in km, km/s — heliocentric)
InterplanetaryTrajectories.ephemeris(CelestialBody.MARS, datetime(2028, 7, 1))

# Synodic period between two planets (seconds)
InterplanetaryTrajectories.synodic_period(CelestialBody.EARTH, CelestialBody.MARS)

# Lambert-based optimal transfer (returns [maneuver_dep, maneuver_arr, orbit_elements, theta])
# r_p_D = departure parking orbit radius (km), r_p_A = arrival orbit radius (km)
# T = arrival orbit period (s), m = spacecraft mass (kg)
InterplanetaryTrajectories.optimal_transfer(
    CelestialBody.EARTH, CelestialBody.MARS,
    datetime(2028, 7, 1), datetime(2029, 2, 1),
    r_p_D=6678, r_p_A=3590, T=0, m=2000
)
# maneuver.dv = delta-v in km/s, maneuver.oe = orbital elements of the hyperbola

# Gravity assist flyby (returns ManeuverResult with post-flyby heliocentric orbit)
# theta_1 = true anomaly of flyby planet on pre-flyby orbit
InterplanetaryTrajectories.flyby(
    CelestialBody.EARTH, CelestialBody.VENUS,
    r_p=6351+300, theta_1=..., m=2000, side=FlybySide.DARK_SIDE
)
# result.oe.h, result.oe.e give the post-flyby heliocentric orbit

# Departure from parking orbit (Hohmann-based v_inf estimate)
InterplanetaryTrajectories.departure(CelestialBody.EARTH, CelestialBody.MARS, r_p=6678, m=2000)

# Arrival capture into orbit
InterplanetaryTrajectories.rendezvous(CelestialBody.MARS, CelestialBody.EARTH, r_p_A=6678, T=0, m=2000)

# Lambert problem solver (heliocentric — set mu to Sun first)
OrbitDetermination.set_celestial_body(CelestialBody.SUN)
v1, v2, oe, theta2 = OrbitDetermination.solve_lambert_problem(r1_vec, r2_vec, dt_seconds)

# Orbit propagation
LagrangeCoefficients.mu = AstronomicalData.gravitational_parameter(CelestialBody.SUN)
r_f, v_f = LagrangeCoefficients.calculate_position_velocity_by_time(r_0, v_0, dt_seconds)

# Orbital elements from state vector
ThreeDimensionalOrbit.set_celestial_body(CelestialBody.SUN)
oe = ThreeDimensionalOrbit.calculate_orbital_elements(r_vec, v_vec)
# oe.a = semi-major axis (km), oe.e = eccentricity, oe.h = angular momentum

# Astronomical constants
AstronomicalData.gravitational_parameter(CelestialBody.SUN)   # mu_sun km^3/s^2
AstronomicalData.semi_major_axis(CelestialBody.MARS)           # orbital radius km
AstronomicalData.sphere_of_influence(CelestialBody.EARTH)      # SOI in km
AstronomicalData.equatiorial_radius(CelestialBody.VENUS)       # surface radius km
```

### Celestial Bodies
`SUN, MERCURY, VENUS, EARTH, MOON, MARS, JUPITER, SATURN, URANUS, NEPTUNE, PLUTO`

## Strategy Hints

- **Direct Hohmann** to Mars costs ~5.6 km/s round-trip → Bronze tier (1.5-2 AU)
- **Lambert-optimized** transfers with good date selection can reduce costs
- **Gravity assists** (e.g., Venus flyby) can provide free delta-v to reach further
- **Key insight**: apoapsis of the heliocentric transfer orbit = `a * (1 + e)` where a, e come from the Lambert solution orbital elements
- Use `synodic_period()` and `ephemeris()` to find good departure windows

## Constraints (violation = score 0)

1. Total delta-v of all maneuvers ≤ 12.0 km/s
2. Mission duration ≤ 20 years (7305 days)
3. Return trajectory must arrive within Earth's sphere of influence (~925,000 km)
4. Any flyby periapsis must be above planet surface + 300 km
5. All orbital elements must be physically valid (e ≥ 0, a > 0 for elliptical)
6. Must depart from 300 km circular Earth parking orbit (r = 6678 km)

## Output Format

Write a JSON file to `/app/mission_plan.json` with this structure:

```json
{
  "mission_name": "descriptive name",
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

Flyby phases (if used) should include:
```json
{
  "phase": "flyby",
  "date": "YYYY-MM-DD",
  "body": "VENUS",
  "periapsis_km": 0.0,
  "delta_v_km_s": 0.0,
  "side": "dark",
  "post_flyby_orbit": {
    "a_km": 0.0,
    "e": 0.0,
    "r_apoapsis_AU": 0.0
  }
}
```

## Scoring

Your score is based on the maximum heliocentric distance achieved:

| Tier | Distance | Description |
|------|----------|-------------|
| Bronze | 1.5 - 2.0 AU | Mars-class mission |
| Silver | 2.0 - 4.0 AU | Asteroid belt reach |
| Gold | 4.0 - 6.0 AU | Jupiter-class (requires gravity assist) |
| Platinum | > 6.0 AU | Saturn-class or beyond |

The reward is: `min(max_distance_AU / 6.0, 2.0)` if all constraints pass, else `0.0`.

## Important Notes

- The `optimal_transfer()` function handles the full Lambert-based transfer including departure and arrival burns — use it for direct transfers
- For gravity assists, use `flyby()` directly (the gravity assist path in `optimal_transfer()` is incomplete)
- The Lambert solver assumes prograde transfers only
- 1 AU = 149,597,870.7 km
