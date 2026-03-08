---
skill: Mission Design CONOPS
description: >
  General-purpose mission design skill. Given a natural-language mission
  description, produce a complete CONOPS as mission_plan.json.
  Handles lunar, planetary, asteroid, relay, and deep-space missions.
---

# Mission Design CONOPS — General-Purpose Skill

## Goal

Design a mission from a user prompt, compute the trajectory using `spacecraft_sim`,
and produce `/app/mission_plan.json`. The plan must satisfy all verifier constraints
and follow the 8-phase CONOPS structure.

---

## 1. Mission Analysis Framework

Decompose ANY mission prompt into:

| Element | How to Extract |
|---------|---------------|
| **Destination** | Moon, Mars, asteroid, Jupiter, deep space, etc. |
| **Mission type** | Flyby, orbit insertion, relay, rendezvous, sample return, mapping |
| **Key constraints** | From the MarCO-X spacecraft spec sheet (see Sections 2 & 2b) |
| **Success criteria** | What the prompt asks to maximize or achieve |

Map these to CONOPS sections:
1. **Mission Overview** — name, objective, destination, success criteria
2. **Mission Requirements** — table of constraints (from spec sheet + task)
3. **Design Parameters** — orbital elements, delta-v budget, mass breakdown
4. **Mission Architecture** — vehicle, transfer type, operations concept
5. **CONOPS Phases 1-8** — launch through end-of-life (see Section 6)

---

## 2. Spacecraft: MarCO-X 6U Deep Space CubeSat

Based on MarCO flight heritage (NASA/JPL, 2018). All specs from public datasheets.

### Platform

| Parameter | Value | Notes |
|-----------|-------|-------|
| Bus standard | 6U CubeSat (CDS Rev 14.1) | 22.6 x 10.0 x 36.6 cm stowed |
| Total wet mass | ~14.0 kg | ~8.6 kg dry + ~3.5 kg propulsion |
| Deployed span | ~1.5 m | Solar arrays deployed |
| Design life | 1-2 years (deep space) | |
| Heritage | MarCO A/B — Mars 2018 (TRL 9) | |

### Propulsion — VACCO MiPS (Cold Gas)

| Parameter | Value | Notes |
|-----------|-------|-------|
| Technology | ChEMS cold gas | All-welded Al; non-toxic |
| Propellant | R-236FA | Self-pressurising refrigerant |
| Total impulse | 755 N-s | Full mission budget |
| Thrust | 25 mN per thruster | 4 thrusters (pitch, yaw, roll, dv) |
| ISP | ~40 s | Cold gas typical |
| dv (14 kg wet) | ~54 m/s | 755 N-s / 14 kg (Tsiolkovsky) |
| Min impulse bit | 0.5 mN-s | ACS fine control resolution |
| Op temp | -30 to +55 C | HARD LIMITS — heater required below -30 C |
| Op voltage | 9.0 to 12.6 VDC | Direct from battery bus |
| Wet mass | 3.49 kg | Includes propellant + tank + valves |

### Power

| Parameter | Value | Notes |
|-----------|-------|-------|
| Solar arrays | MMA eHaWK, Spectrolab UTJ 28.3% | |
| BOL power (1 AU) | 72 W | |
| Power at 1.52 AU (Mars) | ~31 W | 72 W x (1/1.52)^2 |
| Battery | 18650B Li-Ion 3S4P, ~38 Wh | 12V nominal bus |
| Avg draw | 1-5 W cruise / 15-20 W comms | |

### Communications — JPL Iris V2

| Parameter | Value | Notes |
|-----------|-------|-------|
| Bands | X-band 7.2/8.4 GHz + UHF 390-450 MHz | |
| RF output | 4 W (35 W DC) | |
| Downlink at 1 AU | 8 kbps | Via DSN 70m |
| Max downlink (close range) | 256 kbps | |
| Ground network | NASA DSN | |

### ADCS — BCT XACT

| Parameter | Value | Notes |
|-----------|-------|-------|
| Pointing accuracy | < 0.01 deg | Star tracker + RWA + IMU |
| Form factor | 0.5U, 0.885 kg | |
| De-tumble time | < 6 min | From worst-case tumble |

---

## 2b. Operational Constraints (from Spec Sheet)

These are the **real spacecraft limits** that constrain every mission design.

### Power Constraints

| Parameter | GREEN | YELLOW | RED | EMERGENCY |
|-----------|-------|--------|-----|-----------|
| Battery SOC | > 60% | 30-60% | < 30% | < 20% (auto safe-mode) |
| Battery voltage | > 11.0 V | 9.5-11.0 V | < 9.5 V | < 9.0 V |
| Solar input power | > 10 W | 5-10 W | < 5 W | < 2 W (power-negative) |

### Thermal Constraints

| Subsystem | Op Min (C) | Op Max (C) | Notes |
|-----------|-----------|-----------|-------|
| VACCO MiPS propulsion | -30 | +55 | HARD LIMITS — hold maneuver if violated |
| BCT XACT ADCS | -30 | +70 | Safe-mode if > +70 C |
| Iris V2 transponder | -40 | +70 | Reduce Tx duty cycle if > +65 C |
| Battery (charge) | 0 | +45 | NEVER charge below 0 C |
| Battery (discharge) | -20 | +60 | Capacity derate below -10 C |

### Propulsion Constraints

| Parameter | Value | Notes |
|-----------|-------|-------|
| Total impulse budget | 755 N-s | Reserve >= 15% (113 N-s) for contingency |
| Pre-maneuver prop temp | -30 to +55 C | Hold maneuver until heaters bring >= -20 C |
| Pre-maneuver battery V | >= 9.0 VDC | Below 9.0 V: valve solenoids unreliable |
| Pointing pre-maneuver | < 0.1 deg | ADCS must be in fine reference before dv burn |

### Communications Constraints

| Parameter | GREEN | YELLOW | RED |
|-----------|-------|--------|-----|
| Link margin (X-band) | > 6 dB | 3-6 dB | < 3 dB (hold downlink) |
| DSN pass duration | > 30 min | 15-30 min | < 15 min |
| Data buffer fill | < 50% | 50-80% | > 80% (hold observations) |
| Blackout (conjunction) | < 3 days | 3-10 days | > 10 days (pre-load autonomy) |

### Mission Profile Feasibility

| Mission Type | dv Required | MiPS Feasible? | Notes |
|-------------|-------------|---------------|-------|
| Lunar (direct) | 600-900 m/s | Flyby only | Need upgraded prop for orbit insertion |
| Lunar (low-energy BLT) | 200-400 m/s | Maybe (tight) | Ballistic lunar transfer |
| Mars (flyby) | 40-80 m/s (TCMs only) | YES | Heritage mission |
| Mars (orbit insertion) | 800-1200 m/s | NO — needs upgrade | VACCO Hybrid ADN: 1828 N-s |

### Task-Level Overrides

The task/sim environment may override spacecraft parameters for scoring purposes.
Always check `task/instruction.md` for the authoritative values:

| Parameter | Spec Sheet | Task Override (if present) |
|-----------|-----------|--------------------------|
| Mass | 14 kg | 2000 kg |
| ISP | ~40 s | 300 s |
| dv budget | ~54 m/s | 12 km/s |
| Parking orbit | — | 300 km LEO (r = 6678 km) |
| Departure window | — | 2025-01-01 to 2035-12-31 |
| Max duration | 1-2 years | 20 years (7305 days) |

**When task overrides exist, use them for trajectory computation and JSON output.**
The spec sheet constraints (power, thermal, comms, ADCS) still apply to CONOPS design.

---

## 3. Available API (`spacecraft_sim`)

### Ephemeris
```python
# Planet position at a date — returns (r_vec, v_vec) in km, km/s (heliocentric)
R, V = InterplanetaryTrajectories.ephemeris(CelestialBody.MARS, datetime(2028, 7, 1))
```

### Lambert Solver
```python
# CRITICAL: set Sun as central body BEFORE solving
OrbitDetermination.set_celestial_body(CelestialBody.SUN)

dt = (arr_date - dep_date).total_seconds()
VD, VA, oe, theta = OrbitDetermination.solve_lambert_problem(R1, R2, dt)
# oe.a = semi-major axis (km), oe.e = eccentricity, oe.i = inclination (rad)
```

### Optimal Transfer
```python
# Full Lambert transfer with departure/arrival burns
# Returns (maneuver_dep, maneuver_arr, orbit_elements, theta)
man_dep, man_arr, oe, _ = InterplanetaryTrajectories.optimal_transfer(
    CelestialBody.EARTH, CelestialBody.MARS,
    dep_date, arr_date,
    r_p_D=6678, r_p_A=3590, T=0, m=2000
)
# man_dep.dv, man_arr.dv = delta-v in km/s
```

### Flyby
```python
# Gravity assist — returns ManeuverResult with post-flyby heliocentric orbit
result = InterplanetaryTrajectories.flyby(
    CelestialBody.EARTH, CelestialBody.VENUS,
    r_p=6351+300, theta_1=..., m=2000, side=FlybySide.DARK_SIDE
)
# result.oe.h, result.oe.e = post-flyby orbit
```

### Orbit Propagation
```python
LagrangeCoefficients.mu = AstronomicalData.gravitational_parameter(CelestialBody.SUN)
r_f, v_f = LagrangeCoefficients.calculate_position_velocity_by_time(r_0, v_0, dt_seconds)
```

### Orbital Elements from State Vector
```python
ThreeDimensionalOrbit.set_celestial_body(CelestialBody.SUN)
oe = ThreeDimensionalOrbit.calculate_orbital_elements(r_vec, v_vec)
```

### Constants
```python
AstronomicalData.gravitational_parameter(CelestialBody.SUN)    # mu km^3/s^2
AstronomicalData.semi_major_axis(CelestialBody.MARS)            # orbital radius km
AstronomicalData.sphere_of_influence(CelestialBody.EARTH)       # SOI in km
AstronomicalData.equatiorial_radius(CelestialBody.VENUS)        # surface radius km
InterplanetaryTrajectories.synodic_period(CelestialBody.EARTH, CelestialBody.MARS)
```

### Celestial Bodies
`SUN, MERCURY, VENUS, EARTH, MOON, MARS, JUPITER, SATURN, URANUS, NEPTUNE, PLUTO`

---

## 4. Delta-V Formulas

### Critical: dv_from_vinf
```python
def dv_from_vinf(v_inf, mu, r_p):
    """Delta-v from circular parking orbit to hyperbolic escape (or capture).
    mu = gravitational parameter of DEPARTURE/ARRIVAL body.
    r_p = parking orbit radius (km).
    """
    v_p = np.sqrt(v_inf**2 + 2 * mu / r_p)
    v_c = np.sqrt(mu / r_p)
    return abs(v_p - v_c)
```

- Earth departure/arrival: `mu = 398600.4418`, `r_p = 6678`
- Mars departure: `mu = 42828.375`, `r_p = equatorial_radius(MARS) + 300`

### Reference Constants
```python
AU_KM       = 149_597_870.7
PARKING_R   = 6678.0          # 300 km LEO radius (km)
mu_sun      = 1.327124400189e11
mu_earth    = 398600.4418
mu_venus    = 324858.592
mu_mars     = 42828.375
```

### Reference Delta-V Budgets

| Mission Type | Typical One-Way Delta-V | Notes |
|-------------|------------------------|-------|
| LEO to Lunar orbit | ~4.1 km/s | TLI ~3.1 + LOI ~0.8 |
| LEO to Mars orbit | ~5.6 km/s | Hohmann, one-way |
| LEO to Jupiter flyby | ~6.3 km/s | One-way |
| Mars round-trip | ~12-16 km/s | Often exceeds 12 km/s budget |
| Venus gravity assist | ~3-4 km/s departure | Free redirect outward |

### Max Distance Calculation (Scored Distance)
```python
# Apoapsis of the heliocentric transfer orbit
r_apoapsis_km = oe.a * (1 + oe.e)
max_distance_AU = r_apoapsis_km / AU_KM
```

---

## 5. Strategy Selection

### Strategy A: Direct Lambert Transfer (Bronze/Silver, 1.5-2.0 AU)
- Earth-Mars-Earth round trip
- Use date scanning to find optimal departure windows
- Typical total dv: 12-14 km/s (tight budget)

### Strategy B: Venus Gravity Assist (Silver/Gold, 2-4 AU)
- Earth to Venus flyby (unpowered, dv=0) to redirect outward
- Coast on high-apoapsis heliocentric orbit, return to Earth
- Can reach 2-4 AU within 12 km/s budget

### Strategy C: Jupiter-Class Lambert (Gold/Platinum, 4-6+ AU)
- Scan Earth-Jupiter transfer windows 2028-2033
- Look for transfers where dv_dep + dv_return < 12 km/s
- Jupiter distance ~5.2 AU

### Date Scanning Pattern
```python
from datetime import timedelta

best_dv = 999
for dep_offset in range(0, 365*3, 30):       # 3 years, 30-day steps
    for tof_days in range(150, 400, 30):      # time-of-flight range
        dep = datetime(2028, 1, 1) + timedelta(days=dep_offset)
        arr = dep + timedelta(days=tof_days)
        try:
            R1, V1 = InterplanetaryTrajectories.ephemeris(CelestialBody.EARTH, dep)
            R2, V2 = InterplanetaryTrajectories.ephemeris(CelestialBody.MARS, arr)
            OrbitDetermination.set_celestial_body(CelestialBody.SUN)
            VD, VA, oe, _ = OrbitDetermination.solve_lambert_problem(
                R1, R2, (arr - dep).total_seconds()
            )
            dv_dep = dv_from_vinf(np.linalg.norm(VD - V1), mu_earth, PARKING_R)
            # ... compute return leg similarly
        except Exception:
            continue
```

---

## 6. CONOPS Phase Design Guide

### Phase 1: Launch & Deploy
| Field | What to Decide |
|-------|---------------|
| `launch_site` | Default: "Cape Canaveral SLC-41" |
| `launch_vehicle` | Default: "Atlas V 401" (heritage) or SLS secondary |
| `launch_date` | From departure_date |
| `injection_orbit` | LEO 300 km circular (or GTO/TLI if prompt specifies) |
| `launch_direction` | Default: "Due east, 28.5 deg inclination" |
| `launch_window_days` | Default: 21 |

Key activities: Array deploy, attitude acquire, first DSN contact.
Constraint: Must be power-positive before battery depletes.
Failure modes: Array stuck, comms not acquired, high tumble rate.

### Phase 2: Early Orbit Operations (LEOP)
| Field | What to Decide |
|-------|---------------|
| `separation_orbit` | Same as injection orbit |
| `post_separation_actions` | Default: ("comms", "adcs", "propulsion") |
| `transfer_readiness_condition` | Default: "All subsystems nominal; nav fix established" |
| `duration_hours` | Lunar: 1-3 days, Mars: 1-7 days |

Key activities: Commissioning, subsystem checkout, orbit determination.
Failure modes: C&DH fault, ADCS cal failure, propulsion leak.

### Phase 3: Transfer Trajectory
| Field | What to Decide |
|-------|---------------|
| `transfer_type` | lambert, hohmann, gravity_assist, direct, low_energy, spiral |
| `maneuvers` | List of burns with date, delta_v_km_s, direction |
| `departure_body` | Default: "Earth" |
| `arrival_body` | From destination analysis |
| `departure_date` / `arrival_date` | Computed from trajectory |
| `total_delta_v_km_s` | Sum of all maneuvers |

### Phase 4: Cruise
| Field | What to Decide |
|-------|---------------|
| `cruise_mode` | "spin-stabilized" or "3-axis fine pointing" |
| `nav_strategy` | Default: "DSN tracking" |
| `tcm_schedule` | Planned trajectory correction maneuvers |
| `critical_constraints` | "solar power > 5W", "battery SOC > 30%", "prop temp > -20 C" |
| `dsn_contact_schedule` | Default: "Weekly 30-min passes" |

Key activities: TCM maneuvers, health checks, nav tracking.
Constraints: Power budget degrades at Mars range (~31W); thermal deep space;
RW desaturation ~1 m/s/year budget.
Failure modes: Nav error accumulation, RW saturation.

### Phase 5: Arrival
| Field | What to Decide |
|-------|---------------|
| `arrival_strategy` | orbit_insertion, flyby, aerobrake, or landing |
| `orbit_insertion_maneuver` | Capture burn details (None for flyby) |
| `initial_captured_orbit` | e.g., "500 x 50000 km, i=93 deg" |
| `final_operational_orbit` | e.g., "400 km circular polar" |
| `closest_approach_km` | For flybys |

### Phase 6: Primary Science Operations
| Field | What to Decide |
|-------|---------------|
| `science_orbit` | Operational orbit description |
| `observation_strategy` | From prompt or "Standard science ops" |
| `primary_payloads` | From prompt or ("wide-angle camera",) |
| `mission_success_metric` | From prompt's success criteria |
| `duration_days` | From prompt or 30 |

### Phase 7: Extended Mission (Optional)
| Field | What to Decide |
|-------|---------------|
| `entry_condition` | "Primary mission complete, resources remaining" |
| `remaining_resources` | e.g., "12% fuel, battery SOC > 50%" |
| `new_objective` | Extended science or relay duties |
| `duration_days` | Remaining mission time |

### Phase 8: End of Life
| Field | What to Decide |
|-------|---------------|
| `end_condition` | "Fuel depleted" or "Mission duration complete" |
| `disposal_strategy` | deorbit, graveyard_orbit, heliocentric, lunar_impact, passivation |
| `final_spacecraft_state` | e.g., "Passivated in heliocentric orbit" |
| `disposal_delta_v_km_s` | Default: 0.0 |

---

## 7. Output JSON Schema

The `phases` array is what `sim/bridge.py` and the verifier consume. The `conops`
block is optional CONOPS narrative for documentation.

```json
{
  "mission_name": "string",
  "mission_objective": "string",
  "strategy": "lambert | gravity_assist | hohmann | direct",
  "departure_date": "YYYY-MM-DD",
  "return_date": "YYYY-MM-DD",
  "total_delta_v_km_s": 0.0,
  "max_distance_AU": 0.0,
  "spacecraft": {
    "mass_kg": 2000,
    "isp_s": 300,
    "fuel_kg": 0.0
  },
  "phases": [
    {
      "phase": "earth_departure",
      "date": "YYYY-MM-DD",
      "maneuver": "departure_burn",
      "delta_v_km_s": 0.0,
      "from_body": "EARTH",
      "to_body": "MARS",
      "parking_orbit_radius_km": 6678.0,
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
      "side": "dark",
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
        "periapsis_km": 6678.0,
        "period_hours": 1.5
      }
    }
  ],
  "conops": {
    "launch": { "site": "Cape Canaveral", "vehicle": "Atlas V 401" },
    "early_ops": { "duration_hours": 24 },
    "cruise": { "mode": "spin-stabilized", "nav": "DSN tracking" },
    "arrival": { "strategy": "orbit_insertion" },
    "primary_ops": { "duration_days": 30, "payloads": ["camera"] },
    "end_of_life": { "disposal": "heliocentric" }
  },
  "mission_timeline": [
    { "event": "Launch", "date": "YYYY-MM-DD" },
    { "event": "Earth departure burn", "date": "YYYY-MM-DD" },
    { "event": "Arrival", "date": "YYYY-MM-DD" }
  ],
  "risks": [
    { "risk": "Missed departure window", "mitigation": "21-day launch window" }
  ],
  "verification": {
    "total_delta_v_check": true,
    "mission_duration_days": 0,
    "earth_return_distance_km": 0.0,
    "all_constraints_satisfied": true
  }
}
```

### Required Fields (verifier checks these)
- `phases` — non-empty array
- `departure_date` — string "YYYY-MM-DD"
- `total_delta_v_km_s` — float
- At least one phase with `"phase": "earth_departure"`
- Each phase must have: `phase`, `date`, `delta_v_km_s`
- `delta_v_km_s` must be >= 0 for every phase

### Scored Distance
The verifier computes `max_distance_AU` from the `transfer_orbit` in phases:
```
max_distance_AU = a_km * (1 + e) / 149597870.7
```

---

## 8. Mission Type Templates

### Lunar Direct
- **Transit**: 3-5 days
- **dv**: 600-900 m/s (MiPS: flyby only; orbit insertion needs upgraded prop)
- **Power at dest**: ~72 W (1 AU)
- **Comms**: up to 256 kbps
- **Key risk**: dv for LOI; lunar shadow eclipses (~3 hr)
- **to_body**: "MOON"
- **disposal**: lunar_impact or passivation

### Lunar Low-Energy (Ballistic Transfer)
- **Transit**: 3-4 months
- **dv**: 200-400 m/s (MiPS: maybe feasible, tight budget)
- **Key risk**: navigation accuracy over long transfer
- **to_body**: "MOON"
- **disposal**: lunar_impact or graveyard_orbit

### Mars Flyby (MarCO Heritage)
- **Transit**: 7-9 months
- **dv**: 40-80 m/s (TCMs only) — MiPS fully feasible
- **Power at dest**: ~31 W at 1.52 AU
- **Comms**: 8 kbps at 1 AU via DSN 70m; Madrid preferred
- **Key risk**: long comms delay; solar conjunction blackout
- **Duration**: ~9 months
- **to_body**: "MARS"
- **disposal**: heliocentric

### Mars Orbit Insertion
- **Transit**: 7-9 months
- **dv**: 800-1200 m/s — MiPS NOT feasible, needs VACCO Hybrid ADN (1828 N-s)
- **Power at dest**: ~31 W at 1.52 AU
- **Duration**: 1-2 years
- **to_body**: "MARS"
- **disposal**: graveyard_orbit

### Asteroid Rendezvous
- **Transfer**: Lambert to NEA
- **Proximity ops**: station-keeping at ~1 km
- **Duration**: 6 months science ops
- **to_body**: nearest major body (MARS for main belt, EARTH for NEAs)
- **disposal**: heliocentric

### Deep Space Explorer (maximize distance)
- **Goal**: maximize heliocentric distance within delta-v budget
- **Strategy**: Lambert or gravity assist
- **Round-trip**: must return to Earth
- **to_body**: target body on outbound leg (MARS, JUPITER, etc.)
- **Scoring**: reward = min(max_distance_AU / 6.0, 2.0)
  - Bronze: 1.5-2 AU, Silver: 2-4 AU, Gold: 4-6 AU, Platinum: >6 AU

---

## 9. Common Pitfalls (AVOID THESE)

1. **numpy types in JSON** — always cast with `float()`, `int()`, `bool()` before `json.dump`
2. **Forgetting `OrbitDetermination.set_celestial_body(CelestialBody.SUN)`** — Lambert solver defaults to Earth, WRONG for heliocentric transfers
3. **total_dv must be <= budget before writing JSON** — if over budget, try different dates
4. **`earth_return_distance_km` must be < 924631 km** (Earth SOI) — use 0.0 for direct return. Even exactly equal fails (verifier checks `>`, not `>=`)
5. **All `to_body` values must be real CelestialBody names** — SUN, MERCURY, VENUS, EARTH, MARS, JUPITER, SATURN, URANUS, NEPTUNE, PLUTO. Never use made-up names like "DEEP_SPACE"
6. **Duration <= 7305 days** (20 years)
7. **`a > 0` for elliptical orbits** — negative a means hyperbolic (invalid for transfer scoring)
8. **Missing phases** — verifier requires both `earth_departure` AND `earth_arrival`
9. **Using `optimal_transfer()` for gravity assists** — it's incomplete for that path. Use `flyby()` directly or manual Lambert legs
10. **Departure date outside 2025-2035** — verifier rejects dates outside this window

---

## 10. Scoring Reference

```
reward = min(max_distance_AU / 6.0, 2.0)   if all constraints pass
reward = 0.0                                 if ANY constraint violated
```

Constraints (violation = score 0):
1. Total delta-v of all maneuvers <= 12.0 km/s (5% tolerance)
2. Mission duration <= 7305 days (20 years)
3. Return within Earth SOI (~925,000 km)
4. Flyby periapsis > planet surface + 300 km
5. Orbital elements physically valid (e >= 0, a > 0)
6. Depart from 300 km circular LEO (r = 6678 km)
7. Departure date within 2025-2035
8. max_distance_AU >= 1.0 AU

Tiers:
| Tier | Distance | Example |
|------|----------|---------|
| Bronze | 1.5-2.0 AU | Mars-class |
| Silver | 2.0-4.0 AU | Asteroid belt |
| Gold | 4.0-6.0 AU | Jupiter-class |
| Platinum | > 6.0 AU | Saturn+ |
