# Universe State Schema

The complete state of the simulation at any point in time. This is what the sim produces, the agent perceives, and verification checks against.

---

## Top-Level: `UniverseState`

```python
@dataclass(frozen=True)
class UniverseState:
    time: SimTime                      # Current simulation time
    bodies: tuple[CelestialBodyState, ...]  # All celestial bodies
    spacecraft: tuple[SpacecraftState, ...]  # All spacecraft (1 for now, extensible)
    events: tuple[Event, ...]          # Events this step (SOI entry, collision, etc.)
```

Immutable. Each sim step produces a new `UniverseState`.

---

## Time

```python
@dataclass(frozen=True)
class SimTime:
    elapsed_s: float          # Seconds since sim start
    epoch: datetime           # Absolute datetime (for ephemeris lookups)
    step: int                 # Discrete step counter
```

---

## Celestial Bodies

```python
@dataclass(frozen=True)
class CelestialBodyState:
    body: CelestialBody               # Enum: SUN, EARTH, MOON, MARS, etc.
    position_km: tuple[float, float, float]  # Heliocentric or parent-centric [km]
    velocity_km_s: tuple[float, float, float]  # [km/s]
    mu_km3_s2: float                   # Gravitational parameter
    radius_km: float                   # Equatorial radius
    soi_km: float                      # Sphere of influence radius
    orbital_elements: OrbitalElements | None  # Current Keplerian elements (None for Sun)
```

**Notes:**
- Positions from `InterplanetaryTrajectories.ephemeris(body, date)` for planets
- Moon position relative to Earth (or heliocentric, TBD)
- Sun is at origin in heliocentric frame; Earth is at origin in geocentric frame
- Which frame depends on the spacecraft's current dominant body

---

## Spacecraft

```python
@dataclass(frozen=True)
class SpacecraftState:
    id: str                            # Identifier
    position_km: tuple[float, float, float]  # In current reference frame [km]
    velocity_km_s: tuple[float, float, float]  # [km/s]
    mass_kg: float                     # Current total mass (dry + fuel)
    dry_mass_kg: float                 # Mass without fuel
    fuel_kg: float                     # Remaining propellant
    isp_s: float                       # Specific impulse [s]
    reference_body: CelestialBody      # Dominant gravitational body (for frame)
    orbit: OrbitState                  # Derived orbital info
    subsystems: SubsystemState         # Power, thermal, propulsion, comms, ADCS
    status: SpacecraftStatus           # NOMINAL, CRASHED, ESCAPED, OUT_OF_FUEL
```

```python
class SpacecraftStatus(Enum):
    NOMINAL = "nominal"
    CRASHED = "crashed"           # Hit a body surface
    ESCAPED = "escaped"           # Left all SOIs (heliocentric escape)
    OUT_OF_FUEL = "out_of_fuel"   # Can still coast, can't burn
    IN_ORBIT = "in_orbit"         # Stable closed orbit achieved
    MISSION_COMPLETE = "mission_complete"
```

```python
@dataclass(frozen=True)
class OrbitState:
    elements: OrbitalElements          # h, e, i, Omega, omega, theta, a
    parameters: OrbitalParameters      # T, r_a, r_p, epsilon, etc.
    altitude_km: float                 # Above reference body surface
    period_s: float                    # Orbital period (inf for hyperbolic)
    orbit_type: OrbitType              # Classification
```

```python
class OrbitType(Enum):
    CIRCULAR = "circular"         # e < 0.001
    ELLIPTICAL = "elliptical"     # 0.001 <= e < 1.0
    PARABOLIC = "parabolic"       # e == 1.0 (within tolerance)
    HYPERBOLIC = "hyperbolic"     # e > 1.0
    SUBORBITAL = "suborbital"     # Periapsis below surface
```

---

## Proximity & Hazards

```python
@dataclass(frozen=True)
class ProximityInfo:
    body: CelestialBody
    distance_km: float                 # Center-to-center
    altitude_km: float                 # Above surface (distance - radius)
    within_soi: bool                   # Inside sphere of influence
    closing_speed_km_s: float          # Relative approach speed (negative = closing)
```
Computed for every body each step. Part of the agent's perception.

---

## Events

```python
@dataclass(frozen=True)
class Event:
    type: EventType
    time: SimTime
    body: CelestialBody | None
    details: dict                      # Event-specific data

class EventType(Enum):
    SOI_ENTER = "soi_enter"            # Entered a body's SOI
    SOI_EXIT = "soi_exit"              # Left a body's SOI
    COLLISION = "collision"            # Hit surface
    PERIAPSIS_PASS = "periapsis_pass"  # Passed closest approach
    APOAPSIS_PASS = "apoapsis_pass"    # Passed farthest point
    BURN_COMPLETE = "burn_complete"    # Maneuver finished
    FUEL_DEPLETED = "fuel_depleted"    # Ran out of propellant
    ORBIT_ACHIEVED = "orbit_achieved"  # Stable orbit detected
```

---

## Spacecraft Subsystems

Operational constraints that gate what the spacecraft can do. Inspired by MarCO-X flight heritage.

```python
@dataclass(frozen=True)
class SubsystemState:
    power: PowerState
    thermal: ThermalState
    propulsion: PropulsionState
    comms: CommsState
    adcs: ADCSState

class HealthStatus(Enum):
    GREEN = "green"        # Nominal
    YELLOW = "yellow"      # Caution — degraded but functional
    RED = "red"            # Critical — functionality impaired
    EMERGENCY = "emergency"  # Autonomous safe-mode triggered
```

### Power

```python
@dataclass(frozen=True)
class PowerState:
    status: HealthStatus
    battery_soc_pct: float             # State of charge [%]
    battery_voltage_v: float           # Bus voltage [V]
    solar_input_w: float               # Current solar array output [W]
    solar_max_w: float                 # BOL power at 1 AU [W]
    distance_au: float                 # Heliocentric distance (solar power scales as 1/r²)
    in_eclipse: bool                   # Shadowed by a body
```

Thresholds (MarCO-X reference):
- GREEN: SOC > 60%, voltage > 11.0 V, solar > 10 W
- YELLOW: SOC 30–60%, voltage 9.5–11.0 V, solar 5–10 W
- RED: SOC < 30%, voltage < 9.5 V, solar < 5 W
- EMERGENCY: SOC < 20% → auto safe-mode

### Thermal

```python
@dataclass(frozen=True)
class ThermalState:
    status: HealthStatus
    propulsion_temp_c: float           # Propulsion system temperature [°C]
    battery_temp_c: float              # Battery pack temperature [°C]
    electronics_temp_c: float          # C&DH / avionics temperature [°C]
```

Thresholds (MarCO-X reference):
- Propulsion: operational -30°C to +55°C (HARD LIMITS)
- Battery charge: 0°C to +45°C (NEVER charge below 0°C)
- Battery discharge: -20°C to +60°C
- Electronics: -40°C to +85°C

### Propulsion

```python
@dataclass(frozen=True)
class PropulsionState:
    status: HealthStatus
    fuel_kg: float                     # Remaining propellant mass [kg]
    total_impulse_remaining_ns: float  # Remaining total impulse [N·s]
    thrust_n: float                    # Per-thruster thrust level [N]
    isp_s: float                       # Specific impulse [s]
    can_fire: bool                     # False if temp/voltage/pointing out of range
    fire_inhibit_reason: str | None    # Why firing is blocked (temp, voltage, attitude)
```

Pre-burn gates (all must pass):
- Propulsion temp ≥ -20°C (caution) / ≥ -30°C (hard limit)
- Battery voltage ≥ 9.0 V
- Pointing error < 0.1° (< 0.5° hard limit)
- Fuel remaining > 0

### Communications

```python
@dataclass(frozen=True)
class CommsState:
    status: HealthStatus
    link_margin_db: float              # Current link margin [dB]
    downlink_rate_kbps: float          # Achievable downlink rate [kbps]
    data_buffer_fill_pct: float        # Onboard data buffer usage [%]
    in_blackout: bool                  # Solar conjunction or occultation
    dsn_pass_active: bool              # Currently in contact with ground
```

### Attitude Determination & Control

```python
@dataclass(frozen=True)
class ADCSState:
    status: HealthStatus
    pointing_error_deg: float          # Current pointing error [°]
    mode: ADCSMode                     # Current control mode
    rw_saturation_pct: float           # Reaction wheel saturation [%]

class ADCSMode(Enum):
    DETUMBLE = "detumble"              # Post-deploy spin reduction
    SUN_POINT = "sun_point"            # Safe-mode attitude (power survival)
    FINE_REFERENCE = "fine_reference"  # Precision pointing (comms, burns)
    SLEW = "slew"                      # Reorienting to new target
```

---

## CONOPS Mission Phases

The agent operates within a phase-based mission structure. Each phase has entry/exit criteria and available actions.

```python
class MissionPhase(Enum):
    LAUNCH_DEPLOY = "launch_deploy"          # Array deploy, attitude acquire, first contact
    EARLY_OPS = "early_ops"                  # Commissioning, subsystem checkout, orbit determination
    TRANSFER = "transfer"                    # Cruise trajectory toward destination
    CRUISE = "cruise"                        # Coast phase — TCMs, health monitoring, nav tracking
    APPROACH = "approach"                    # Final approach — optical nav, intensive tracking, final TCMs
    ARRIVAL_INSERTION = "arrival_insertion"   # Orbit insertion or flyby execution
    PRIMARY_OPS = "primary_ops"              # Science, relay, imaging at destination
    EXTENDED_OPS = "extended_ops"            # Optional continued operations
    END_OF_MISSION = "end_of_mission"        # Final downlink, disposal, decommission

@dataclass(frozen=True)
class PhaseState:
    current_phase: MissionPhase
    phase_start_time: SimTime
    phase_elapsed_s: float
    entry_criteria_met: tuple[str, ...]      # What conditions triggered phase entry
    exit_criteria: tuple[str, ...]           # What must be true to advance
    available_actions: tuple[ActionType, ...]  # What the agent can do in this phase
```

### Phase Transitions

```
LAUNCH_DEPLOY → EARLY_OPS
    when: arrays deployed, attitude acquired, first DSN contact

EARLY_OPS → TRANSFER
    when: all subsystems commissioned, nav fix established, departure burn executed

TRANSFER → CRUISE
    when: on transfer trajectory, TCM-1 complete

CRUISE → APPROACH
    when: within approach distance of target body (body-specific threshold)

APPROACH → ARRIVAL_INSERTION
    when: final TCM complete, within SOI of target body

ARRIVAL_INSERTION → PRIMARY_OPS
    when: stable orbit achieved (or flyby data collection started)

PRIMARY_OPS → EXTENDED_OPS
    when: primary mission objectives met, spacecraft healthy

PRIMARY_OPS | EXTENDED_OPS → END_OF_MISSION
    when: fuel depleted, or battery EOL, or mission duration exceeded
```

---

## Agent Actions (what the agent sends back)

Actions are phase-aware — some are only available in certain phases.

```python
@dataclass(frozen=True)
class AgentAction:
    type: ActionType
    payload: BurnCommand | CoastCommand | SystemCommand | CommCommand

class ActionType(Enum):
    # Propulsion
    BURN = "burn"                      # Execute a delta-v maneuver
    COAST = "coast"                    # Free-flight for a duration

    # Spacecraft management
    DEPLOY = "deploy"                  # Deploy arrays, antennas (LAUNCH_DEPLOY only)
    CHECKOUT = "checkout"              # Commission a subsystem (EARLY_OPS only)
    SAFE_MODE = "safe_mode"            # Enter safe mode (any phase)
    DESATURATE = "desaturate"          # Dump reaction wheel momentum

    # Communications
    DOWNLINK = "downlink"              # Transmit data to ground
    UPLINK_REQUEST = "uplink_request"  # Request commands/nav update from ground

    # Navigation
    TCM = "tcm"                        # Trajectory correction maneuver (small burn)
    NAV_UPDATE = "nav_update"          # Request orbit determination from ground

    # Phase control
    ADVANCE_PHASE = "advance_phase"    # Request transition to next mission phase

@dataclass(frozen=True)
class BurnCommand:
    direction: tuple[float, float, float]  # Unit vector in current frame
    magnitude_km_s: float                  # Delta-v magnitude [km/s]

@dataclass(frozen=True)
class CoastCommand:
    duration_s: float                  # How long to coast [s]
    stop_at_event: EventType | None    # Optional: stop early if event occurs

@dataclass(frozen=True)
class SystemCommand:
    subsystem: str                     # Which subsystem to act on
    action: str                        # "deploy_arrays", "checkout_adcs", "heater_on", etc.

@dataclass(frozen=True)
class CommCommand:
    data_type: str                     # "telemetry", "science", "nav_request"
    priority: int                      # 1=routine, 2=urgent, 3=emergency
```

---

## Agent Observation (perception layer output)

What the agent actually receives each step — derived from UniverseState:

```python
@dataclass(frozen=True)
class Observation:
    time: SimTime
    spacecraft: SpacecraftState
    proximity: tuple[ProximityInfo, ...]    # Sorted by distance
    events: tuple[Event, ...]               # Events since last observation
    mission: MissionState                   # Goal tracking
    phase: PhaseState                       # Current CONOPS phase
```

```python
@dataclass(frozen=True)
class MissionState:
    objective: str                     # Human-readable goal
    target_body: CelestialBody | None  # Where we're trying to go
    target_orbit: OrbitalElements | None  # What orbit we want
    delta_v_used_km_s: float           # Total delta-v spent so far
    delta_v_budget_km_s: float         # Total allowed
    impulse_used_ns: float             # Total impulse spent [N·s]
    impulse_budget_ns: float           # Total impulse available [N·s]
    elapsed_s: float                   # Mission time elapsed
    max_duration_s: float              # Mission time limit
```

---

## Reference Frames

The simulation uses **patched conics**: spacecraft state is always relative to one dominant body.

```
Heliocentric (Sun-centered)
  - Used when spacecraft is in interplanetary space
  - Planets and spacecraft positions in this frame

Planetocentric (e.g., Earth-centered)
  - Used when spacecraft is within a body's SOI
  - Position/velocity relative to the planet

Frame switches happen at SOI boundaries (generates SOI_ENTER / SOI_EXIT events).
```

---

## Example Spacecraft Config: MarCO-X (6U Deep Space CubeSat)

Based on NASA/JPL MarCO A/B flight heritage (Mars 2018). All specs from public datasheets.

```python
MARCO_X_CONFIG = SpacecraftConfig(
    id="marco-x",
    name="MarCO-X Extended Config",
    bus="6U CubeSat (CDS Rev 14.1)",

    # Mass
    wet_mass_kg=14.0,
    dry_mass_kg=8.6,
    fuel_kg=5.4,               # R-236FA cold gas

    # Propulsion (VACCO MiPS)
    isp_s=40.0,                # Cold gas R-236FA
    thrust_n=0.025,            # 25 mN per thruster
    total_impulse_ns=755.0,    # Full mission budget
    min_impulse_bit_ns=0.5,    # Finest ACS resolution
    num_thrusters=4,           # Pitch, yaw, roll, delta-v
    prop_temp_range_c=(-30.0, 55.0),    # HARD LIMITS
    prop_voltage_min_v=9.0,

    # Power (MMA eHaWK solar + 18650B Li-Ion)
    solar_power_bol_w=72.0,    # BOL at 1 AU
    battery_capacity_wh=38.0,
    battery_voltage_nominal_v=12.0,
    battery_charge_temp_c=(0.0, 45.0),   # NEVER charge below 0°C
    battery_discharge_temp_c=(-20.0, 60.0),

    # Comms (JPL Iris V2)
    comms_band="X-band",
    rf_power_w=4.0,
    dc_power_tx_w=35.0,
    dc_power_rx_w=12.6,
    downlink_rate_1au_kbps=8.0,
    max_downlink_rate_kbps=256.0,

    # ADCS (BCT XACT)
    pointing_accuracy_deg=0.01,
    adcs_mass_kg=0.885,
    adcs_peak_power_w=3.0,
    detumble_time_s=360.0,     # < 6 minutes

    # Mission profiles
    missions={
        "lunar_direct":   {"transit_days": (3, 5),    "dv_ms": (600, 900),  "feasible": False},  # MiPS can't do LOI
        "lunar_lowenergy":{"transit_days": (90, 120),  "dv_ms": (200, 400),  "feasible": False},  # Marginal
        "mars_flyby":     {"transit_days": (210, 270), "dv_ms": (40, 80),    "feasible": True},   # TCMs only
        "mars_orbit":     {"transit_days": (210, 270), "dv_ms": (800, 1200), "feasible": False},  # Needs upgrade
    },

    # Operational thresholds
    thresholds=OperationalThresholds(
        battery_soc_green=60.0, battery_soc_yellow=30.0, battery_soc_red=20.0,
        solar_green_w=10.0, solar_yellow_w=5.0, solar_red_w=2.0,
        pointing_burn_max_deg=0.1, pointing_hard_limit_deg=0.5,
        rw_saturation_caution_pct=67.0,  # 3000/4500 rpm
    ),
)
```

Delta-v budget reality check:
- Total impulse: 755 N·s at 14 kg wet mass → ~54 m/s total delta-v
- This is a flyby/relay craft, NOT an orbiter
- Mars flyby (40–80 m/s for TCMs): feasible
- Lunar orbit insertion (600+ m/s): impossible without propulsion upgrade
- Agent must be extremely fuel-efficient

---

## Mapping to Existing spacecraft_sim API

| Schema field | Computed via |
|---|---|
| `CelestialBodyState.position/velocity` | `InterplanetaryTrajectories.ephemeris(body, date)` |
| `CelestialBodyState.mu` | `AstronomicalData.gravitational_parameter(body)` |
| `CelestialBodyState.radius` | `AstronomicalData.equatiorial_radius(body)` |
| `CelestialBodyState.soi` | `AstronomicalData.sphere_of_influence(body)` |
| `OrbitState.elements` | `ThreeDimensionalOrbit.calculate_orbital_elements(r, v)` |
| `OrbitState.parameters` | `TwoBodyProblem.calculate_orbital_parameters(r, v)` |
| `ProximityInfo.distance` | `norm(spacecraft_pos - body_pos)` |
| Propagation (coast) | `LagrangeCoefficients.calculate_position_velocity_by_time(r, v, dt)` |
| Fuel consumption | `OrbitalManeuvers.propellant_mass(m, dv)` |
| Maneuver planning | `OrbitalManeuvers.hohmann_transfer(...)`, `solve_lambert_problem(...)` |
