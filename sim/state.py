"""Universe state dataclasses — immutable state for each simulation tick."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from spacecraft_sim import CelestialBody, OrbitalElements, OrbitalParameters


# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SimTime:
    elapsed_s: float          # Seconds since sim start
    epoch: datetime           # Absolute datetime (for ephemeris lookups)
    step: int                 # Discrete step counter


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SpacecraftStatus(Enum):
    NOMINAL = "nominal"
    CRASHED = "crashed"
    ESCAPED = "escaped"
    OUT_OF_FUEL = "out_of_fuel"
    IN_ORBIT = "in_orbit"
    MISSION_COMPLETE = "mission_complete"


class OrbitType(Enum):
    CIRCULAR = "circular"
    ELLIPTICAL = "elliptical"
    PARABOLIC = "parabolic"
    HYPERBOLIC = "hyperbolic"
    SUBORBITAL = "suborbital"


class HealthStatus(Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    EMERGENCY = "emergency"


class ADCSMode(Enum):
    DETUMBLE = "detumble"
    SUN_POINT = "sun_point"
    FINE_REFERENCE = "fine_reference"
    SLEW = "slew"


class EventType(Enum):
    SOI_ENTER = "soi_enter"
    SOI_EXIT = "soi_exit"
    COLLISION = "collision"
    PERIAPSIS_PASS = "periapsis_pass"
    APOAPSIS_PASS = "apoapsis_pass"
    BURN_COMPLETE = "burn_complete"
    FUEL_DEPLETED = "fuel_depleted"
    ORBIT_ACHIEVED = "orbit_achieved"


class MissionPhase(Enum):
    LAUNCH_DEPLOY = "launch_deploy"
    EARLY_OPS = "early_ops"
    TRANSFER = "transfer"
    CRUISE = "cruise"
    APPROACH = "approach"
    ARRIVAL_INSERTION = "arrival_insertion"
    PRIMARY_OPS = "primary_ops"
    EXTENDED_OPS = "extended_ops"
    END_OF_MISSION = "end_of_mission"


class ActionType(Enum):
    BURN = "burn"
    COAST = "coast"
    DEPLOY = "deploy"
    CHECKOUT = "checkout"
    SAFE_MODE = "safe_mode"
    DESATURATE = "desaturate"
    DOWNLINK = "downlink"
    UPLINK_REQUEST = "uplink_request"
    TCM = "tcm"
    NAV_UPDATE = "nav_update"
    ADVANCE_PHASE = "advance_phase"


# ---------------------------------------------------------------------------
# Celestial Bodies
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CelestialBodyState:
    body: CelestialBody
    position_km: tuple[float, float, float]
    velocity_km_s: tuple[float, float, float]
    mu_km3_s2: float
    radius_km: float
    soi_km: float
    orbital_elements: OrbitalElements | None


# ---------------------------------------------------------------------------
# Spacecraft Subsystems
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PowerState:
    status: HealthStatus
    battery_soc_pct: float
    battery_voltage_v: float
    solar_input_w: float
    solar_max_w: float
    distance_au: float
    in_eclipse: bool


@dataclass(frozen=True)
class ThermalState:
    status: HealthStatus
    propulsion_temp_c: float
    battery_temp_c: float
    electronics_temp_c: float


@dataclass(frozen=True)
class PropulsionState:
    status: HealthStatus
    fuel_kg: float
    total_impulse_remaining_ns: float
    thrust_n: float
    isp_s: float
    can_fire: bool
    fire_inhibit_reason: str | None


@dataclass(frozen=True)
class CommsState:
    status: HealthStatus
    link_margin_db: float
    downlink_rate_kbps: float
    data_buffer_fill_pct: float
    in_blackout: bool
    dsn_pass_active: bool


@dataclass(frozen=True)
class ADCSState:
    status: HealthStatus
    pointing_error_deg: float
    mode: ADCSMode
    rw_saturation_pct: float


@dataclass(frozen=True)
class SubsystemState:
    power: PowerState
    thermal: ThermalState
    propulsion: PropulsionState
    comms: CommsState
    adcs: ADCSState


# ---------------------------------------------------------------------------
# Orbit & Spacecraft
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OrbitState:
    elements: OrbitalElements
    parameters: OrbitalParameters
    altitude_km: float
    period_s: float
    orbit_type: OrbitType


@dataclass(frozen=True)
class SpacecraftState:
    id: str
    position_km: tuple[float, float, float]
    velocity_km_s: tuple[float, float, float]
    mass_kg: float
    dry_mass_kg: float
    fuel_kg: float
    isp_s: float
    reference_body: CelestialBody
    orbit: OrbitState
    subsystems: SubsystemState
    status: SpacecraftStatus


# ---------------------------------------------------------------------------
# Proximity & Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProximityInfo:
    body: CelestialBody
    distance_km: float
    altitude_km: float
    within_soi: bool
    closing_speed_km_s: float


@dataclass(frozen=True)
class Event:
    type: EventType
    time: SimTime
    body: CelestialBody | None
    details: dict


# ---------------------------------------------------------------------------
# Mission & Phase
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PhaseState:
    current_phase: MissionPhase
    phase_start_time: SimTime
    phase_elapsed_s: float
    entry_criteria_met: tuple[str, ...]
    exit_criteria: tuple[str, ...]
    available_actions: tuple[ActionType, ...]


@dataclass(frozen=True)
class MissionState:
    objective: str
    target_body: CelestialBody | None
    target_orbit: OrbitalElements | None
    delta_v_used_km_s: float
    delta_v_budget_km_s: float
    impulse_used_ns: float
    impulse_budget_ns: float
    elapsed_s: float
    max_duration_s: float


# ---------------------------------------------------------------------------
# Agent Actions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BurnCommand:
    direction: tuple[float, float, float]  # Unit vector
    magnitude_km_s: float


@dataclass(frozen=True)
class CoastCommand:
    duration_s: float
    stop_at_event: EventType | None = None


@dataclass(frozen=True)
class SystemCommand:
    subsystem: str
    action: str


@dataclass(frozen=True)
class CommCommand:
    data_type: str
    priority: int


@dataclass(frozen=True)
class AgentAction:
    type: ActionType
    payload: BurnCommand | CoastCommand | SystemCommand | CommCommand | None = None


# ---------------------------------------------------------------------------
# Observation (what the agent sees)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Observation:
    time: SimTime
    spacecraft: SpacecraftState
    proximity: tuple[ProximityInfo, ...]
    events: tuple[Event, ...]
    mission: MissionState
    phase: PhaseState


# ---------------------------------------------------------------------------
# Top-Level Universe State
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class UniverseState:
    time: SimTime
    bodies: tuple[CelestialBodyState, ...]
    spacecraft: tuple[SpacecraftState, ...]
    events: tuple[Event, ...]
