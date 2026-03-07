"""CONOPS output schema — what the agent produces given a mission definition.

The agent reads the mission definition + spacecraft config and outputs a
complete CONOPS as a sequence of phases. The SimEngine executor then runs
each phase, verifying physics and constraints at every step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ---------------------------------------------------------------------------
# Phase 1: Launch
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LaunchPhase:
    launch_site: str                          # e.g., "Cape Canaveral SLC-41"
    launch_vehicle: str                       # e.g., "Atlas V 401"
    target_injection_orbit: InjectionOrbit    # What orbit the LV puts us in
    launch_direction: str                     # e.g., "Due east, 28.5° inclination"
    launch_date: datetime                     # Planned launch date
    launch_window_days: int = 21              # Window width


@dataclass(frozen=True)
class InjectionOrbit:
    type: str                    # "LEO", "GTO", "heliocentric", "TLI"
    altitude_km: float           # Circular altitude or perigee
    apoapsis_km: float | None    # None if circular
    inclination_deg: float
    raan_deg: float | None = None


# ---------------------------------------------------------------------------
# Phase 2: Early Orbit Operations (LEOP)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EarlyOpsPhase:
    separation_orbit: InjectionOrbit          # Orbit at separation from LV
    post_separation_actions: tuple[str, ...]  # Ordered checklist
    transfer_readiness_condition: str          # What must be true to proceed
    duration_hours: float                     # Expected phase duration


# ---------------------------------------------------------------------------
# Phase 3: Transfer Trajectory
# ---------------------------------------------------------------------------

class TransferType(Enum):
    HOHMANN = "hohmann"
    BI_ELLIPTIC = "bi_elliptic"
    LAMBERT = "lambert"
    LOW_ENERGY = "low_energy"          # Ballistic lunar transfer
    GRAVITY_ASSIST = "gravity_assist"
    DIRECT = "direct"                  # Direct injection (no transfer burn)
    SPIRAL = "spiral"                  # Low-thrust spiral


@dataclass(frozen=True)
class TransferManeuver:
    name: str                          # e.g., "TLI burn", "TCM-1"
    date: datetime                     # When to execute
    delta_v_km_s: float                # Burn magnitude
    direction: str                     # "prograde", "retrograde", "normal", or vector description
    location: str                      # "perigee", "apogee", "ascending node", etc.
    pre_burn_orbit: str                # Description of orbit before burn
    post_burn_orbit: str               # Description of orbit after burn


@dataclass(frozen=True)
class TransferPhase:
    transfer_type: TransferType
    maneuvers: tuple[TransferManeuver, ...]   # All burns in this phase
    propulsion_source: str                     # "VACCO MiPS cold gas", "bipropellant", etc.
    transfer_duration_days: float
    departure_body: str                        # e.g., "Earth"
    arrival_body: str                          # e.g., "Mars"
    departure_date: datetime
    arrival_date: datetime
    total_delta_v_km_s: float                  # Sum of all maneuvers


# ---------------------------------------------------------------------------
# Phase 4: Cruise
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CruisePhase:
    cruise_mode: str                           # e.g., "spin-stabilized", "3-axis fine pointing"
    nav_strategy: str                          # e.g., "DSN tracking + TCMs every 30 days"
    tcm_schedule: tuple[TransferManeuver, ...] # Planned trajectory corrections
    critical_constraints: tuple[str, ...]      # e.g., "solar power > 5W", "battery temp > 0°C"
    duration_days: float
    dsn_contact_schedule: str                  # e.g., "Weekly 30-min passes via Madrid 70m"


# ---------------------------------------------------------------------------
# Phase 5: Arrival and Orbit Insertion
# ---------------------------------------------------------------------------

class ArrivalStrategy(Enum):
    ORBIT_INSERTION = "orbit_insertion"  # Capture into orbit
    FLYBY = "flyby"                     # No capture, collect data during pass
    AEROBRAKE = "aerobrake"             # Use atmosphere to slow down
    LANDING = "landing"                 # Direct descent


@dataclass(frozen=True)
class ArrivalPhase:
    arrival_strategy: ArrivalStrategy
    orbit_insertion_maneuver: TransferManeuver | None  # None for flyby
    initial_captured_orbit: str | None                  # e.g., "500 x 50000 km, i=93°"
    final_operational_orbit: str | None                 # e.g., "400 km circular polar"
    approach_nav: str                                   # e.g., "Optical nav + DSN final TCM"
    closest_approach_km: float | None                   # For flybys


# ---------------------------------------------------------------------------
# Phase 6: Primary Science Operations
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PrimaryOpsPhase:
    science_orbit: str                         # e.g., "400 km sun-synchronous" or "flyby trajectory"
    observation_strategy: str                  # e.g., "Continuous nadir imaging, 2 orbits/day downlink"
    primary_payloads: tuple[str, ...]          # e.g., ("wide-angle camera", "UHF relay")
    mission_success_metric: str                # e.g., "Relay InSight EDL telemetry to Earth"
    duration_days: float
    data_volume_gb: float | None = None


# ---------------------------------------------------------------------------
# Phase 7: Extended Mission (Optional)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExtendedOpsPhase:
    entry_condition: str                       # What triggers extended mission
    remaining_resources: str                   # e.g., "12% fuel, battery SOC > 50%"
    new_objective: str                         # e.g., "Orbit Mars for 6 more months"
    operational_change: str                    # e.g., "Reduce downlink cadence to weekly"
    duration_days: float


# ---------------------------------------------------------------------------
# Phase 8: End-of-Life / Disposal
# ---------------------------------------------------------------------------

class DisposalStrategy(Enum):
    DEORBIT = "deorbit"                  # Controlled reentry
    GRAVEYARD_ORBIT = "graveyard_orbit"  # Raise to disposal orbit
    HELIOCENTRIC = "heliocentric"        # Leave in solar orbit
    LUNAR_IMPACT = "lunar_impact"        # Targeted impact
    PASSIVATION = "passivation"          # Vent fuel, discharge batteries, drift


@dataclass(frozen=True)
class EndOfLifePhase:
    end_condition: str                         # e.g., "Fuel depleted", "2-year mission complete"
    disposal_strategy: DisposalStrategy
    final_spacecraft_state: str                # e.g., "Passivated in 1.05 AU heliocentric orbit"
    disposal_delta_v_km_s: float = 0.0         # Delta-v reserved for disposal


# ---------------------------------------------------------------------------
# Complete CONOPS
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CONOPS:
    """Complete Concept of Operations — the agent's output."""

    mission_name: str
    mission_objective: str                     # One-sentence summary

    # Spacecraft reference
    spacecraft_id: str                         # e.g., "marco-x"
    spacecraft_config: str                     # e.g., "MarCO-X 6U CubeSat"

    # Delta-v budget summary
    total_delta_v_budget_km_s: float
    total_delta_v_allocated_km_s: float        # Sum of all phase maneuvers
    delta_v_margin_km_s: float                 # Budget - allocated (must be >= 0)

    # Mission timeline
    mission_start: datetime
    mission_end: datetime
    mission_duration_days: float

    # Phases (ordered)
    launch: LaunchPhase
    early_ops: EarlyOpsPhase
    transfer: TransferPhase
    cruise: CruisePhase
    arrival: ArrivalPhase
    primary_ops: PrimaryOpsPhase
    extended_ops: ExtendedOpsPhase | None      # Optional
    end_of_life: EndOfLifePhase

    # Verification hints (for the sim executor)
    key_constraints: tuple[str, ...] = field(default_factory=tuple)
    risk_mitigations: tuple[str, ...] = field(default_factory=tuple)
