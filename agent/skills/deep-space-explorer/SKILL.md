---
name: deep-space-explorer
description: >
  Use when solving the Deep Space Explorer interplanetary mission design task.
  Covers Lambert transfers, delta-v computation from v-infinity, gravity assists,
  and producing a valid mission_plan.json that passes the verifier constraints.
---

# Deep Space Explorer — Mission Design Procedure

## Goal
Maximize heliocentric distance (apoapsis of transfer orbit) while keeping total
delta-v ≤ 12 km/s and round-trip duration ≤ 20 years. Output: `/app/mission_plan.json`.

## Critical Constants
```python
AU_KM = 149_597_870.7
PARKING_R = 6678.0          # 300 km LEO radius in km
mu_sun = 1.327124400189e11  # km^3/s^2
mu_earth = 398600.4418      # km^3/s^2
mu_venus = 324858.592       # km^3/s^2
mu_mars  = 42828.375        # km^3/s^2
```

## Step 1 — Write a single Python script
Write ONE complete Python script that does everything. Do NOT write incremental
snippets. The script must end by writing `/app/mission_plan.json`.

## Step 2 — Delta-v from v-infinity (CRITICAL FORMULA)
The delta-v to go from a circular parking orbit to a hyperbolic escape (or capture):
```python
def dv_from_vinf(v_inf, mu, r_p):
    """mu = gravitational parameter of the DEPARTURE/ARRIVAL body, r_p = parking orbit radius."""
    v_p = np.sqrt(v_inf**2 + 2 * mu / r_p)
    v_c = np.sqrt(mu / r_p)
    return abs(v_p - v_c)
```
- For Earth departure/arrival: mu = mu_earth, r_p = 6678 km
- For Mars departure: mu = mu_mars, r_p = equatorial_radius(MARS) + 300

## Step 3 — Lambert solver workflow
```python
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
import numpy as np
from datetime import datetime
from spacecraft_sim import (
    InterplanetaryTrajectories, OrbitDetermination,
    AstronomicalData, CelestialBody
)

# 1. Get planet positions
R1, V1 = InterplanetaryTrajectories.ephemeris(CelestialBody.EARTH, dep_date)
R2, V2 = InterplanetaryTrajectories.ephemeris(CelestialBody.MARS, arr_date)

# 2. MUST set Sun as central body before solving
OrbitDetermination.set_celestial_body(CelestialBody.SUN)

# 3. Solve Lambert
dt = (arr_date - dep_date).total_seconds()
VD, VA, oe, theta = OrbitDetermination.solve_lambert_problem(R1, R2, dt)

# 4. v-infinity vectors
v_inf_dep = np.linalg.norm(VD - V1)   # departure v_inf (km/s)
v_inf_arr = np.linalg.norm(VA - V2)   # arrival v_inf (km/s)

# 5. Transfer orbit apoapsis (THIS IS THE SCORED DISTANCE)
r_apoapsis_km = oe.a * (1 + oe.e)
r_apoapsis_AU = r_apoapsis_km / AU_KM
```

## Step 4 — Strategy selection (choose ONE)

### Strategy A: Earth-Mars-Earth (Bronze/Silver, ~1.5-2.0 AU)
Simple but delta-v is tight. Use good departure windows:
- Depart Earth: 2028-09-15, Arrive Mars: 2029-06-12 (good window)
- Wait at Mars ~16 months for return window
- Return: depart Mars 2030-10-01, arrive Earth 2031-05-01
- Typical total dv: ~12-14 km/s (often exceeds budget)

### Strategy B: Earth-Venus-Earth with high-apoapsis outbound (Silver/Gold)
Use Venus gravity assist to bend trajectory outward:
1. Depart Earth toward Venus
2. Flyby Venus (unpowered, dv=0) to redirect outward
3. Coast on high-apoapsis heliocentric orbit
4. Return to Earth
- Can reach 2-4 AU with <12 km/s total

### Strategy C: Optimized Lambert to Jupiter vicinity (Gold/Platinum)
Search for Earth-Jupiter transfer windows with minimal departure v_inf:
- Scan departure dates 2028-2033
- Look for transfers where dv_dep + dv_return < 12 km/s
- Jupiter distance ~5.2 AU → Gold/Platinum tier

## Step 5 — Date scanning for optimal windows
```python
from datetime import timedelta

best_dv = 999
best_dates = None

for dep_offset in range(0, 365*3, 30):  # scan 3 years in 30-day steps
    for tof_days in range(150, 400, 30):  # time of flight range
        dep = datetime(2028, 1, 1) + timedelta(days=dep_offset)
        arr = dep + timedelta(days=tof_days)
        try:
            R1, V1 = InterplanetaryTrajectories.ephemeris(CelestialBody.EARTH, dep)
            R2, V2 = InterplanetaryTrajectories.ephemeris(CelestialBody.MARS, arr)
            OrbitDetermination.set_celestial_body(CelestialBody.SUN)
            VD, VA, oe, _ = OrbitDetermination.solve_lambert_problem(R1, R2, (arr-dep).total_seconds())
            dv_dep = dv_from_vinf(np.linalg.norm(VD - V1), mu_earth, PARKING_R)
            # ... compute return leg similarly
        except:
            continue
```

## Step 6 — JSON output (MUST match this schema exactly)
```python
import json

plan = {
    "mission_name": "...",
    "strategy": "lambert",  # or "gravity_assist"
    "departure_date": "YYYY-MM-DD",
    "return_date": "YYYY-MM-DD",
    "total_delta_v_km_s": float(round(total_dv, 4)),  # MUST be <= 12.0
    "max_distance_AU": float(round(max_dist_au, 4)),
    "phases": [
        {
            "phase": "earth_departure",
            "date": "YYYY-MM-DD",
            "maneuver": "departure_burn",
            "delta_v_km_s": float(round(dv_dep, 4)),
            "from_body": "EARTH",
            "to_body": "MARS",
            "parking_orbit_radius_km": 6678.0,
            "transfer_orbit": {
                "a_km": float(round(oe.a, 2)),      # MUST be positive
                "e": float(round(oe.e, 6)),          # MUST be >= 0
                "i_deg": float(round(np.rad2deg(oe.i), 4))
            }
        },
        {
            "phase": "return_departure",
            "date": "YYYY-MM-DD",
            "delta_v_km_s": float(round(dv_return_dep, 4)),
            "transfer_orbit": {
                "a_km": float(round(oe_ret.a, 2)),
                "e": float(round(oe_ret.e, 6))
            }
        },
        {
            "phase": "earth_arrival",
            "date": "YYYY-MM-DD",
            "delta_v_km_s": float(round(dv_earth_cap, 4)),
            "capture_orbit": {
                "periapsis_km": 6678.0,
                "period_hours": 1.5
            }
        }
    ],
    "verification": {
        "total_delta_v_check": bool(total_dv <= 12.0),
        "mission_duration_days": int(duration_days),
        "earth_return_distance_km": 0.0,
        "all_constraints_satisfied": bool(total_dv <= 12.0 and duration_days <= 7305)
    }
}

with open("/app/mission_plan.json", "w") as f:
    json.dump(plan, f, indent=2)
```

## Common Pitfalls (AVOID THESE)
1. **numpy types in JSON**: Always cast with `float()`, `int()`, `bool()` before json.dump
2. **Forgetting OrbitDetermination.set_celestial_body(CelestialBody.SUN)**: Lambert solver defaults to Earth — WRONG for heliocentric transfers
3. **Using optimal_transfer() for gravity assists**: It's incomplete. Use `flyby()` directly or manual Lambert legs
4. **Not checking total dv <= 12.0 before writing JSON**: If over budget, try different dates
5. **Negative semi-major axis**: Means hyperbolic orbit — check `oe.a > 0` for elliptical transfers
6. **Missing phases**: Verifier requires both `earth_departure` AND `earth_arrival` phases
7. **Duration > 7305 days**: Keep return_date - departure_date under 20 years
8. **INVALID to_body values**: The `to_body` field in earth_departure MUST be a real celestial body name from this list: SUN, MERCURY, VENUS, EARTH, MARS, JUPITER, SATURN, URANUS, NEPTUNE, PLUTO. Do NOT use made-up names like "DEEP_SPACE" or "ASTEROID_BELT". If the transfer goes toward Jupiter's orbit, use "JUPITER". If toward Mars, use "MARS". Pick the nearest real body.
9. **earth_return_distance_km must be STRICTLY LESS than Earth SOI**: Earth SOI = 924631 km. Set `earth_return_distance_km` to 0.0 (meaning direct return to Earth). Do NOT set it to a value >= 924631.
10. **Verifier checks `>` not `>=` for SOI**: Even exactly equal to SOI fails. Always use 0.0 for a direct Earth return.

## Scoring Reference
- reward = min(max_distance_AU / 6.0, 2.0) if all constraints pass, else 0.0
- max_distance_AU is computed from transfer_orbit: a_km * (1 + e) / 149597870.7
- Bronze: 1.5-2.0 AU | Silver: 2.0-4.0 AU | Gold: 4.0-6.0 AU | Platinum: >6.0 AU
