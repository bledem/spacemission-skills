"""CONOPS Executor — runs a CONOPS plan through the SimEngine step by step.

Takes the agent's CONOPS output, translates each phase into sim actions,
executes them, collects results, and produces a scored mission report.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import timedelta

import numpy as np

from spacecraft_sim import CelestialBody

from sim.conops import (
    CONOPS,
    ArrivalPhase,
    ArrivalStrategy,
    CruisePhase,
    EarlyOpsPhase,
    EndOfLifePhase,
    ExtendedOpsPhase,
    LaunchPhase,
    PrimaryOpsPhase,
    TransferManeuver,
    TransferPhase,
)
from sim.engine import step as _step
from sim.server import create_initial_state

# Recording wrapper for step — captures states when _trajectory is not None
_trajectory: list | None = None


def step(state, action, mission, phase):
    new_state, obs = _step(state, action, mission, phase)
    if _trajectory is not None:
        _trajectory.append(new_state)
    return new_state, obs
from sim.state import (
    ActionType,
    AgentAction,
    BurnCommand,
    CoastCommand,
    MissionPhase,
    MissionState,
    Observation,
    PhaseState,
    SpacecraftStatus,
    SystemCommand,
    UniverseState,
)


# ---------------------------------------------------------------------------
# Phase result tracking
# ---------------------------------------------------------------------------

@dataclass
class PhaseResult:
    phase_name: str
    success: bool
    delta_v_used_km_s: float
    fuel_consumed_kg: float
    duration_s: float
    events: list[str]
    notes: str = ""


@dataclass
class MissionReport:
    conops_name: str
    phases: list[PhaseResult]
    total_delta_v_used_km_s: float
    total_fuel_consumed_kg: float
    total_duration_s: float
    final_status: str
    score: float              # 0.0 to 1.0
    scoring_breakdown: dict
    trajectory: list | None = None  # List of UniverseState if recorded


# ---------------------------------------------------------------------------
# Maneuver translation
# ---------------------------------------------------------------------------

def _direction_to_vector(direction: str, velocity_km_s: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert a direction string to a unit vector in the current frame."""
    vx, vy, vz = velocity_km_s
    v_mag = math.sqrt(vx**2 + vy**2 + vz**2)

    if v_mag == 0:
        return (1.0, 0.0, 0.0)

    # Prograde: along velocity
    prograde = (vx / v_mag, vy / v_mag, vz / v_mag)
    # Normal: perpendicular to orbital plane (r × v direction)
    # Approximation: z-axis component
    normal = (0.0, 0.0, 1.0)

    direction_lower = direction.lower()
    if "prograde" in direction_lower:
        return prograde
    if "retrograde" in direction_lower:
        return (-prograde[0], -prograde[1], -prograde[2])
    if "normal" in direction_lower:
        return normal
    if "anti-normal" in direction_lower or "antinormal" in direction_lower:
        return (0.0, 0.0, -1.0)
    # Default: prograde
    return prograde


def _execute_maneuver(
    maneuver: TransferManeuver,
    state: UniverseState,
    mission: MissionState,
    phase: PhaseState,
) -> tuple[UniverseState, MissionState, list[str]]:
    """Execute a single maneuver: coast to the right time, then burn."""
    events_log: list[str] = []
    sc = state.spacecraft[0]

    # Coast to maneuver time if needed, chunked to avoid propagator overflow
    target_epoch = maneuver.date
    dt = (target_epoch - state.time.epoch).total_seconds()
    if dt > 0:
        remaining = dt
        while remaining > 0:
            # Use smaller steps near body SOIs (hyperbolic escape),
            # larger steps in heliocentric cruise
            sc = state.spacecraft[0]
            if sc.reference_body != CelestialBody.SUN:
                max_chunk = 600.0  # 10 min steps near bodies
            else:
                max_chunk = 86400.0  # 1 day in heliocentric
            chunk = min(remaining, max_chunk)
            coast_action = AgentAction(
                type=ActionType.COAST,
                payload=CoastCommand(duration_s=chunk),
            )
            state, obs = step(state, coast_action, mission, phase)
            mission = obs.mission
            remaining -= chunk
        events_log.append(f"Coasted {dt/86400:.1f} days to maneuver time")

    # Execute burn
    sc = state.spacecraft[0]
    direction = _direction_to_vector(maneuver.direction, sc.velocity_km_s)
    burn_action = AgentAction(
        type=ActionType.BURN,
        payload=BurnCommand(
            direction=direction,
            magnitude_km_s=maneuver.delta_v_km_s,
        ),
    )
    state, obs = step(state, burn_action, mission, phase)
    mission = obs.mission

    # Log
    events_log.append(
        f"{maneuver.name}: Δv={maneuver.delta_v_km_s*1000:.1f} m/s {maneuver.direction}"
    )
    for ev in state.events:
        events_log.append(f"  EVENT: {ev.type.value} {ev.details}")

    return state, mission, events_log


# ---------------------------------------------------------------------------
# Phase executors
# ---------------------------------------------------------------------------

def _execute_launch(
    phase_def: LaunchPhase,
    state: UniverseState,
    mission: MissionState,
) -> tuple[UniverseState, MissionState, PhaseResult]:
    """Launch phase — spacecraft already in injection orbit (LV did the work)."""
    phase_state = PhaseState(
        current_phase=MissionPhase.LAUNCH_DEPLOY,
        phase_start_time=state.time,
        phase_elapsed_s=0.0,
        entry_criteria_met=("sim_start",),
        exit_criteria=("arrays_deployed", "attitude_acquired"),
        available_actions=(ActionType.DEPLOY,),
    )

    # Deploy arrays
    action = AgentAction(
        type=ActionType.DEPLOY,
        payload=SystemCommand(subsystem="solar_arrays", action="deploy"),
    )
    state, obs = step(state, action, mission, phase_state)
    mission = obs.mission

    return state, mission, PhaseResult(
        phase_name="launch",
        success=True,
        delta_v_used_km_s=0.0,
        fuel_consumed_kg=0.0,
        duration_s=60.0,
        events=["Solar arrays deployed", "Attitude acquired"],
    )


def _execute_early_ops(
    phase_def: EarlyOpsPhase,
    state: UniverseState,
    mission: MissionState,
) -> tuple[UniverseState, MissionState, PhaseResult]:
    """LEOP — commission subsystems, establish nav fix."""
    phase_state = PhaseState(
        current_phase=MissionPhase.EARLY_OPS,
        phase_start_time=state.time,
        phase_elapsed_s=0.0,
        entry_criteria_met=("arrays_deployed",),
        exit_criteria=("all_commissioned",),
        available_actions=(ActionType.CHECKOUT, ActionType.COAST),
    )

    events_log = []
    for action_name in phase_def.post_separation_actions:
        action = AgentAction(
            type=ActionType.CHECKOUT,
            payload=SystemCommand(subsystem=action_name, action="commission"),
        )
        state, obs = step(state, action, mission, phase_state)
        mission = obs.mission
        events_log.append(f"Commissioned: {action_name}")

    # Coast for remaining LEOP duration
    remaining_s = phase_def.duration_hours * 3600.0 - len(phase_def.post_separation_actions) * 60.0
    if remaining_s > 0:
        action = AgentAction(
            type=ActionType.COAST,
            payload=CoastCommand(duration_s=remaining_s),
        )
        state, obs = step(state, action, mission, phase_state)
        mission = obs.mission

    return state, mission, PhaseResult(
        phase_name="early_ops",
        success=True,
        delta_v_used_km_s=0.0,
        fuel_consumed_kg=0.0,
        duration_s=phase_def.duration_hours * 3600.0,
        events=events_log,
    )


def _execute_transfer(
    phase_def: TransferPhase,
    state: UniverseState,
    mission: MissionState,
) -> tuple[UniverseState, MissionState, PhaseResult]:
    """Execute transfer trajectory maneuvers."""
    phase_state = PhaseState(
        current_phase=MissionPhase.TRANSFER,
        phase_start_time=state.time,
        phase_elapsed_s=0.0,
        entry_criteria_met=("leop_complete",),
        exit_criteria=("transfer_burns_complete",),
        available_actions=(ActionType.BURN, ActionType.COAST),
    )

    all_events: list[str] = []
    dv_start = mission.delta_v_used_km_s
    fuel_start = state.spacecraft[0].fuel_kg

    for maneuver in phase_def.maneuvers:
        state, mission, events = _execute_maneuver(maneuver, state, mission, phase_state)
        all_events.extend(events)

        if state.spacecraft[0].status == SpacecraftStatus.CRASHED:
            return state, mission, PhaseResult(
                phase_name="transfer",
                success=False,
                delta_v_used_km_s=mission.delta_v_used_km_s - dv_start,
                fuel_consumed_kg=fuel_start - state.spacecraft[0].fuel_kg,
                duration_s=state.time.elapsed_s,
                events=all_events,
                notes="Spacecraft crashed during transfer",
            )

    return state, mission, PhaseResult(
        phase_name="transfer",
        success=True,
        delta_v_used_km_s=mission.delta_v_used_km_s - dv_start,
        fuel_consumed_kg=fuel_start - state.spacecraft[0].fuel_kg,
        duration_s=phase_def.transfer_duration_days * 86400.0,
        events=all_events,
    )


def _execute_cruise(
    phase_def: CruisePhase,
    state: UniverseState,
    mission: MissionState,
) -> tuple[UniverseState, MissionState, PhaseResult]:
    """Cruise phase — coast with periodic TCMs."""
    phase_state = PhaseState(
        current_phase=MissionPhase.CRUISE,
        phase_start_time=state.time,
        phase_elapsed_s=0.0,
        entry_criteria_met=("on_transfer_trajectory",),
        exit_criteria=("approach_distance_reached",),
        available_actions=(ActionType.COAST, ActionType.TCM, ActionType.NAV_UPDATE),
    )

    all_events: list[str] = []
    dv_start = mission.delta_v_used_km_s
    fuel_start = state.spacecraft[0].fuel_kg

    for tcm in phase_def.tcm_schedule:
        state, mission, events = _execute_maneuver(tcm, state, mission, phase_state)
        all_events.extend(events)

    # Coast for remaining cruise duration, chunked
    elapsed_since_start = (state.time.epoch - phase_state.phase_start_time.epoch).total_seconds()
    remaining_s = phase_def.duration_days * 86400.0 - elapsed_since_start
    MAX_COAST_S = 86400.0
    while remaining_s > 0:
        chunk = min(remaining_s, MAX_COAST_S)
        action = AgentAction(
            type=ActionType.COAST,
            payload=CoastCommand(duration_s=chunk),
        )
        state, obs = step(state, action, mission, phase_state)
        mission = obs.mission
        remaining_s -= chunk

    return state, mission, PhaseResult(
        phase_name="cruise",
        success=True,
        delta_v_used_km_s=mission.delta_v_used_km_s - dv_start,
        fuel_consumed_kg=fuel_start - state.spacecraft[0].fuel_kg,
        duration_s=phase_def.duration_days * 86400.0,
        events=all_events,
    )


def _execute_arrival(
    phase_def: ArrivalPhase,
    state: UniverseState,
    mission: MissionState,
) -> tuple[UniverseState, MissionState, PhaseResult]:
    """Arrival — orbit insertion or flyby."""
    phase_state = PhaseState(
        current_phase=MissionPhase.ARRIVAL_INSERTION,
        phase_start_time=state.time,
        phase_elapsed_s=0.0,
        entry_criteria_met=("within_soi",),
        exit_criteria=("orbit_captured",) if phase_def.arrival_strategy == ArrivalStrategy.ORBIT_INSERTION else ("flyby_complete",),
        available_actions=(ActionType.BURN, ActionType.COAST),
    )

    all_events: list[str] = []
    dv_start = mission.delta_v_used_km_s
    fuel_start = state.spacecraft[0].fuel_kg

    if phase_def.orbit_insertion_maneuver is not None:
        state, mission, events = _execute_maneuver(
            phase_def.orbit_insertion_maneuver, state, mission, phase_state,
        )
        all_events.extend(events)
    else:
        all_events.append(f"Flyby — no insertion burn (closest approach: {phase_def.closest_approach_km} km)")

    return state, mission, PhaseResult(
        phase_name="arrival",
        success=True,
        delta_v_used_km_s=mission.delta_v_used_km_s - dv_start,
        fuel_consumed_kg=fuel_start - state.spacecraft[0].fuel_kg,
        duration_s=3600.0,  # Arrival is brief
        events=all_events,
    )


def _execute_primary_ops(
    phase_def: PrimaryOpsPhase,
    state: UniverseState,
    mission: MissionState,
) -> tuple[UniverseState, MissionState, PhaseResult]:
    """Primary science operations — coast in science orbit."""
    phase_state = PhaseState(
        current_phase=MissionPhase.PRIMARY_OPS,
        phase_start_time=state.time,
        phase_elapsed_s=0.0,
        entry_criteria_met=("orbit_captured",),
        exit_criteria=("primary_objectives_met",),
        available_actions=(ActionType.COAST, ActionType.DOWNLINK),
    )

    remaining_s = phase_def.duration_days * 86400.0
    MAX_COAST_S = 86400.0
    while remaining_s > 0:
        chunk = min(remaining_s, MAX_COAST_S)
        action = AgentAction(
            type=ActionType.COAST,
            payload=CoastCommand(duration_s=chunk),
        )
        state, obs = step(state, action, mission, phase_state)
        mission = obs.mission
        remaining_s -= chunk

    return state, mission, PhaseResult(
        phase_name="primary_ops",
        success=True,
        delta_v_used_km_s=0.0,
        fuel_consumed_kg=0.0,
        duration_s=phase_def.duration_days * 86400.0,
        events=[f"Science ops: {phase_def.observation_strategy}"],
    )


def _execute_end_of_life(
    phase_def: EndOfLifePhase,
    state: UniverseState,
    mission: MissionState,
) -> tuple[UniverseState, MissionState, PhaseResult]:
    """End of life — disposal maneuver if any."""
    phase_state = PhaseState(
        current_phase=MissionPhase.END_OF_MISSION,
        phase_start_time=state.time,
        phase_elapsed_s=0.0,
        entry_criteria_met=("mission_complete",),
        exit_criteria=("disposed",),
        available_actions=(ActionType.BURN, ActionType.COAST),
    )

    events_log = [f"End condition: {phase_def.end_condition}"]

    if phase_def.disposal_delta_v_km_s > 0:
        sc = state.spacecraft[0]
        direction = _direction_to_vector("retrograde", sc.velocity_km_s)
        action = AgentAction(
            type=ActionType.BURN,
            payload=BurnCommand(direction=direction, magnitude_km_s=phase_def.disposal_delta_v_km_s),
        )
        state, obs = step(state, action, mission, phase_state)
        mission = obs.mission
        events_log.append(f"Disposal burn: {phase_def.disposal_delta_v_km_s*1000:.1f} m/s")

    events_log.append(f"Disposal: {phase_def.disposal_strategy.value}")
    events_log.append(f"Final state: {phase_def.final_spacecraft_state}")

    return state, mission, PhaseResult(
        phase_name="end_of_life",
        success=True,
        delta_v_used_km_s=phase_def.disposal_delta_v_km_s,
        fuel_consumed_kg=0.0,
        duration_s=0.0,
        events=events_log,
    )


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------

def execute_conops(
    conops: CONOPS,
    record_trajectory: bool = False,
) -> MissionReport:
    """Execute a complete CONOPS through the sim and produce a mission report.

    If record_trajectory=True, the report will include a 'trajectory' field
    with a list of UniverseState snapshots at each step.
    """
    global _trajectory
    if record_trajectory:
        _trajectory = []
    else:
        _trajectory = None

    state, mission, _ = create_initial_state(
        epoch=conops.mission_start,
        altitude_km=conops.launch.target_injection_orbit.altitude_km,
        inclination_deg=conops.launch.target_injection_orbit.inclination_deg,
    )

    # Override mission state with CONOPS values
    mission = replace(
        mission,
        objective=conops.mission_objective,
        delta_v_budget_km_s=conops.total_delta_v_budget_km_s,
        max_duration_s=conops.mission_duration_days * 86400.0,
    )

    phase_results: list[PhaseResult] = []
    initial_fuel = state.spacecraft[0].fuel_kg

    # Execute each phase in order
    state, mission, result = _execute_launch(conops.launch, state, mission)
    phase_results.append(result)

    state, mission, result = _execute_early_ops(conops.early_ops, state, mission)
    phase_results.append(result)

    state, mission, result = _execute_transfer(conops.transfer, state, mission)
    phase_results.append(result)

    if state.spacecraft[0].status != SpacecraftStatus.CRASHED:
        state, mission, result = _execute_cruise(conops.cruise, state, mission)
        phase_results.append(result)

        state, mission, result = _execute_arrival(conops.arrival, state, mission)
        phase_results.append(result)

        state, mission, result = _execute_primary_ops(conops.primary_ops, state, mission)
        phase_results.append(result)

        state, mission, result = _execute_end_of_life(conops.end_of_life, state, mission)
        phase_results.append(result)

    # Score the mission
    score, breakdown = _score_mission(conops, mission, state, phase_results)

    recorded = list(_trajectory) if _trajectory is not None else None
    _trajectory = None

    return MissionReport(
        conops_name=conops.mission_name,
        phases=phase_results,
        total_delta_v_used_km_s=mission.delta_v_used_km_s,
        total_fuel_consumed_kg=initial_fuel - state.spacecraft[0].fuel_kg,
        total_duration_s=state.time.elapsed_s,
        final_status=state.spacecraft[0].status.value,
        score=score,
        scoring_breakdown=breakdown,
        trajectory=recorded,
    )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score_mission(
    conops: CONOPS,
    mission: MissionState,
    state: UniverseState,
    phases: list[PhaseResult],
) -> tuple[float, dict]:
    """Score the mission execution. Returns (score, breakdown)."""
    breakdown: dict = {}

    # 1. Did all phases succeed?
    phases_passed = sum(1 for p in phases if p.success)
    phases_total = len(phases)
    breakdown["phases_passed"] = f"{phases_passed}/{phases_total}"
    phase_score = phases_passed / phases_total if phases_total > 0 else 0.0

    # 2. Delta-v budget compliance
    dv_used = mission.delta_v_used_km_s
    dv_budget = conops.total_delta_v_budget_km_s
    within_budget = dv_used <= dv_budget
    breakdown["dv_used_km_s"] = round(dv_used, 4)
    breakdown["dv_budget_km_s"] = round(dv_budget, 4)
    breakdown["within_budget"] = within_budget
    budget_score = 1.0 if within_budget else max(0.0, 1.0 - (dv_used - dv_budget) / dv_budget)

    # 3. Spacecraft health
    sc = state.spacecraft[0]
    status_scores = {
        SpacecraftStatus.NOMINAL: 1.0,
        SpacecraftStatus.IN_ORBIT: 1.0,
        SpacecraftStatus.MISSION_COMPLETE: 1.0,
        SpacecraftStatus.OUT_OF_FUEL: 0.7,
        SpacecraftStatus.ESCAPED: 0.3,
        SpacecraftStatus.CRASHED: 0.0,
    }
    health_score = status_scores.get(sc.status, 0.5)
    breakdown["final_status"] = sc.status.value
    breakdown["health_score"] = health_score

    # 4. Duration compliance
    duration_s = state.time.elapsed_s
    max_s = conops.mission_duration_days * 86400.0
    within_time = duration_s <= max_s
    breakdown["duration_days"] = round(duration_s / 86400.0, 1)
    breakdown["max_duration_days"] = round(max_s / 86400.0, 1)
    time_score = 1.0 if within_time else max(0.0, 1.0 - (duration_s - max_s) / max_s)

    # Weighted total
    score = (
        0.30 * phase_score
        + 0.30 * budget_score
        + 0.25 * health_score
        + 0.15 * time_score
    )
    breakdown["score_weights"] = "phases=0.30, budget=0.30, health=0.25, time=0.15"

    return round(min(1.0, max(0.0, score)), 3), breakdown
